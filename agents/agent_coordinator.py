"""
Agent Coordinator for managing communication between all agents in the CareCloud system.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import structlog

from agents.base_agent import BaseAgent
from agents.database_agent import DatabaseAgent
from agents.medicine_agent import MedicineAgent
from agents.patient_monitoring_agent import PatientMonitoringAgent
from agents.stock_management_agent import StockManagementAgent
from agents.appointment_agent import AppointmentAgent

logger = structlog.get_logger(__name__)


class AgentType(Enum):
    """Enumeration of available agent types."""
    MEDICINE = "medicine"
    PATIENT_MONITORING = "patient_monitoring"
    STOCK_MANAGEMENT = "stock_management"
    APPOINTMENT = "appointment"
    DATABASE = "database"


@dataclass
class AgentRequest:
    """Represents a request to be processed by an agent."""
    request_id: str
    agent_type: AgentType
    input_data: Any
    timestamp: float
    metadata: Dict[str, Any] = None


@dataclass
class AgentResponse:
    """Represents a response from an agent."""
    request_id: str
    agent_type: AgentType
    response: Any
    processing_time: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None


class AgentCoordinator:
    """
    Coordinates communication between all agents in the system.
    Manages the agent loop and ensures proper response routing.
    """

    def __init__(self):
        """Initialize the agent coordinator."""
        self.logger = logger.bind(component="agent_coordinator")
        self.agents: Dict[AgentType, BaseAgent] = {}
        self.database_agent: Optional[DatabaseAgent] = None
        self.request_queue: asyncio.Queue = asyncio.Queue()
        self.response_cache: Dict[str, AgentResponse] = {}
        self.is_running = False
        self.processing_task: Optional[asyncio.Task] = None

    async def initialize(self, agent_configs: Dict[str, Any]) -> None:
        """Initialize all agents and start the coordinator."""
        try:
            self.logger.info("Initializing Agent Coordinator")

            # Initialize database agent first (required by other agents)
            if "database" in agent_configs:
                self.database_agent = DatabaseAgent(
                    config=agent_configs["database"]["config"],
                    prisma_service=agent_configs["database"]["prisma_service"]
                )
                await self.database_agent.start()
                self.agents[AgentType.DATABASE] = self.database_agent
                self.logger.info("Database agent initialized")

            # Initialize specialized agents
            agent_mappings = {
                AgentType.MEDICINE: ("medicine", MedicineAgent),
                AgentType.PATIENT_MONITORING: ("patient_monitoring", PatientMonitoringAgent),
                AgentType.STOCK_MANAGEMENT: ("stock_management", StockManagementAgent),
                AgentType.APPOINTMENT: ("appointment", AppointmentAgent),
            }

            for agent_type, (config_key, agent_class) in agent_mappings.items():
                if config_key in agent_configs:
                    config = agent_configs[config_key]
                    agent = agent_class(
                        config=config["config"],
                        database_agent=self.database_agent
                    )
                    await agent.start()
                    self.agents[agent_type] = agent
                    self.logger.info(f"{agent_type.value} agent initialized")

            # Start the processing loop
            self.is_running = True
            self.processing_task = asyncio.create_task(self._process_requests())
            self.logger.info("Agent Coordinator initialized successfully")

        except Exception as e:
            self.logger.error("Failed to initialize Agent Coordinator", error=str(e))
            raise

    async def shutdown(self) -> None:
        """Shutdown the coordinator and all agents."""
        try:
            self.logger.info("Shutting down Agent Coordinator")
            self.is_running = False

            if self.processing_task:
                self.processing_task.cancel()
                try:
                    await self.processing_task
                except asyncio.CancelledError:
                    pass

            # Shutdown all agents
            for agent_type, agent in self.agents.items():
                try:
                    await agent.stop()
                    self.logger.info(f"{agent_type.value} agent shutdown")
                except Exception as e:
                    self.logger.error(f"Error shutting down {agent_type.value} agent", error=str(e))

            self.logger.info("Agent Coordinator shutdown completed")

        except Exception as e:
            self.logger.error("Error during coordinator shutdown", error=str(e))

    async def process_request(
        self,
        agent_type: AgentType,
        input_data: Any,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process a request through the specified agent with proper routing.

        Args:
            agent_type: Type of agent to process the request
            input_data: Input data for the agent
            request_id: Optional request ID (generated if not provided)
            metadata: Optional metadata for the request

        Returns:
            AgentResponse with the result
        """
        if not self.is_running:
            raise RuntimeError("Agent Coordinator is not running")

        if not request_id:
            request_id = f"req_{int(time.time() * 1000)}_{hash(str(input_data)) % 10000}"

        request = AgentRequest(
            request_id=request_id,
            agent_type=agent_type,
            input_data=input_data,
            timestamp=time.time(),
            metadata=metadata or {}
        )

        # Put request in queue
        await self.request_queue.put(request)

        # Wait for response
        return await self._wait_for_response(request_id)

    async def _process_requests(self) -> None:
        """Main processing loop for handling agent requests."""
        while self.is_running:
            try:
                # Get next request from queue
                request = await self.request_queue.get()

                self.logger.info(
                    "Processing agent request",
                    request_id=request.request_id,
                    agent_type=request.agent_type.value
                )

                # Process the request
                response = await self._execute_agent_request(request)

                # Cache the response
                self.response_cache[request.request_id] = response

                # Mark queue task as done
                self.request_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error processing agent request", error=str(e))
                # Continue processing other requests

    async def _execute_agent_request(self, request: AgentRequest) -> AgentResponse:
        """Execute a request on the appropriate agent."""
        start_time = time.time()

        try:
            agent = self.agents.get(request.agent_type)
            if not agent:
                raise ValueError(f"Agent {request.agent_type.value} not available")

            # Execute the agent
            result = await agent.run(request.input_data)

            processing_time = time.time() - start_time

            return AgentResponse(
                request_id=request.request_id,
                agent_type=request.agent_type,
                response=result,
                processing_time=processing_time,
                success=True,
                metadata={"agent_name": agent.name}
            )

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)

            self.logger.error(
                "Agent execution failed",
                request_id=request.request_id,
                agent_type=request.agent_type.value,
                error=error_msg
            )

            return AgentResponse(
                request_id=request.request_id,
                agent_type=request.agent_type,
                response=None,
                processing_time=processing_time,
                success=False,
                error_message=error_msg
            )

    async def _wait_for_response(self, request_id: str, timeout: float = 30.0) -> AgentResponse:
        """Wait for a response to be available in the cache."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if request_id in self.response_cache:
                response = self.response_cache.pop(request_id)
                return response
            await asyncio.sleep(0.1)

        # Timeout - return error response
        return AgentResponse(
            request_id=request_id,
            agent_type=AgentType.DATABASE,  # Default
            response=None,
            processing_time=timeout,
            success=False,
            error_message=f"Request timeout after {timeout} seconds"
        )

    def get_agent_status(self) -> Dict[str, Any]:
        """Get the status of all agents."""
        status = {
            "coordinator_running": self.is_running,
            "agents": {},
            "queue_size": self.request_queue.qsize()
        }

        for agent_type, agent in self.agents.items():
            status["agents"][agent_type.value] = agent.get_status()

        return status

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the coordinator and all agents."""
        health = {
            "coordinator": {
                "status": "healthy" if self.is_running else "unhealthy",
                "queue_size": self.request_queue.qsize()
            },
            "agents": {}
        }

        for agent_type, agent in self.agents.items():
            try:
                agent_status = agent.get_status()
                health["agents"][agent_type.value] = {
                    "status": "healthy" if agent_status.get("is_running") else "unhealthy",
                    "name": agent_status.get("name")
                }
            except Exception as e:
                health["agents"][agent_type.value] = {
                    "status": "error",
                    "error": str(e)
                }

        return health</content>
<parameter name="filePath">d:\Chanakya-CareCloud\agent-project\agents\agent_coordinator.py
