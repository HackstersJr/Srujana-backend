"""
LangGraph Agent Coordinator for managing multi-agent communication and routing.
"""
import re
import asyncio
import logging
from typing import Any, Dict, List, Optional, TypedDict, Literal
from enum import Enum

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

from agents.base_agent import BaseAgent
from agents.database_agent import DatabaseAgent
from agents.medicine_agent import MedicineAgent
from agents.patient_monitoring_agent import PatientMonitoringAgent
from agents.stock_management_agent import StockManagementAgent
from agents.appointment_agent import AppointmentAgent
from services.db_service import DBService
from services.prisma_service import PrismaService


class AgentType(Enum):
    """Enumeration of available agent types."""
    MEDICINE = "medicine"
    PATIENT_MONITORING = "patient_monitoring"
    STOCK_MANAGEMENT = "stock_management"
    APPOINTMENT = "appointment"
    DATABASE = "database"
    COORDINATOR = "coordinator"


class CoordinatorState(TypedDict):
    """State for the LangGraph agent coordinator workflow."""
    messages: List[BaseMessage]
    user_query: str
    agent_type: Optional[AgentType]
    current_agent: Optional[str]
    agent_responses: Dict[str, Any]
    final_response: Optional[str]
    error: Optional[str]
    retry_count: int
    max_retries: int


class LangGraphAgentCoordinator(BaseAgent):
    """
    LangGraph-based Agent Coordinator that routes requests to appropriate agents,
    manages agent communication, and ensures proper response flow.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        db_service: DBService,
        prisma_service: PrismaService,
    ):
        super().__init__("langgraph_coordinator", config)
        self.db_service = db_service
        self.prisma_service = prisma_service
        self.llm = ChatGoogleGenerativeAI(
            model=config.get("model_name", "gemini-1.5-flash"),
            temperature=config.get("temperature", 0.1),
            api_key=config.get("gemini_api_key"),
        )

        # Agent instances
        self.database_agent = None
        self.medicine_agent = None
        self.patient_monitoring_agent = None
        self.stock_management_agent = None
        self.appointment_agent = None

        # Build the coordinator workflow
        self.graph = self._build_coordinator_graph()

    async def initialize(self) -> None:
        """Initialize the coordinator and all agents."""
        # Initialize database agent first
        self.database_agent = DatabaseAgent(
            config=self.config,
            prisma_service=self.prisma_service
        )
        await self.database_agent.start()

        # Initialize specialized agents
        self.medicine_agent = MedicineAgent(
            config=self.config,
            database_agent=self.database_agent
        )
        await self.medicine_agent.start()

        self.patient_monitoring_agent = PatientMonitoringAgent(
            config=self.config,
            database_agent=self.database_agent
        )
        await self.patient_monitoring_agent.start()

        self.stock_management_agent = StockManagementAgent(
            config=self.config,
            database_agent=self.database_agent
        )
        await self.stock_management_agent.start()

        self.appointment_agent = AppointmentAgent(
            config=self.config,
            database_agent=self.database_agent
        )
        await self.appointment_agent.start()

    async def cleanup(self) -> None:
        """Cleanup coordinator and all agents."""
        agents = [
            self.appointment_agent,
            self.stock_management_agent,
            self.patient_monitoring_agent,
            self.medicine_agent,
            self.database_agent
        ]

        for agent in agents:
            if agent:
                try:
                    await agent.stop()
                except Exception as e:
                    self.logger.error(f"Error stopping agent: {str(e)}")

    async def start(self) -> None:
        """Start the coordinator."""
        self.logger.info("Starting LangGraph Agent Coordinator")
        await self.initialize()
        self.is_running = True
        self.logger.info("LangGraph Agent Coordinator started successfully")

    async def stop(self) -> None:
        """Stop the coordinator."""
        self.logger.info("Stopping LangGraph Agent Coordinator")
        await self.cleanup()
        self.is_running = False
        self.logger.info("LangGraph Agent Coordinator stopped successfully")

    def _build_coordinator_graph(self) -> StateGraph:
        """Build the LangGraph coordinator workflow."""
        workflow = StateGraph(CoordinatorState)

        # Add nodes
        workflow.add_node("analyze_request", self._analyze_request)
        workflow.add_node("route_to_agent", self._route_to_agent)
        workflow.add_node("execute_medicine_agent", self._execute_medicine_agent)
        workflow.add_node("execute_patient_monitoring", self._execute_patient_monitoring)
        workflow.add_node("execute_stock_management", self._execute_stock_management)
        workflow.add_node("execute_appointment_agent", self._execute_appointment_agent)
        workflow.add_node("execute_database_agent", self._execute_database_agent)
        workflow.add_node("format_final_response", self._format_final_response)
        workflow.add_node("handle_error", self._handle_error)

        # Set entry point
        workflow.set_entry_point("analyze_request")

        # Add edges
        workflow.add_edge("analyze_request", "route_to_agent")

        workflow.add_conditional_edges(
            "route_to_agent",
            self._route_to_specific_agent,
            {
                "medicine": "execute_medicine_agent",
                "patient_monitoring": "execute_patient_monitoring",
                "stock_management": "execute_stock_management",
                "appointment": "execute_appointment_agent",
                "database": "execute_database_agent",
                "error": "handle_error",
            }
        )

        # All agent execution nodes lead to final response
        workflow.add_edge("execute_medicine_agent", "format_final_response")
        workflow.add_edge("execute_patient_monitoring", "format_final_response")
        workflow.add_edge("execute_stock_management", "format_final_response")
        workflow.add_edge("execute_appointment_agent", "format_final_response")
        workflow.add_edge("execute_database_agent", "format_final_response")
        workflow.add_edge("format_final_response", END)
        workflow.add_edge("handle_error", END)

        return workflow.compile()

    def _analyze_request(self, state: CoordinatorState) -> CoordinatorState:
        """Analyze the user request to determine intent and routing."""
        try:
            user_query = state["user_query"].lower()

            # Initialize state
            new_state = {
                **state,
                "agent_responses": {},
                "retry_count": 0,
                "max_retries": 3
            }

            # Use LLM to classify the request
            classification_prompt = f"""
            Classify this healthcare request into one of these categories:
            - medicine: medicine inventory, expiry, drugs, pharmacy
            - patient_monitoring: patient vitals, medical records, monitoring
            - stock_management: inventory levels, stock alerts, procurement
            - appointment: scheduling, booking, appointments, calendar
            - database: direct database queries, SQL-like requests

            Request: {state['user_query']}

            Return only the category name, no explanation.
            """

            response = self.llm.invoke([HumanMessage(content=classification_prompt)])
            category = response.content.strip().lower()

            # Map to agent type
            category_map = {
                "medicine": AgentType.MEDICINE,
                "patient_monitoring": AgentType.PATIENT_MONITORING,
                "stock_management": AgentType.STOCK_MANAGEMENT,
                "appointment": AgentType.APPOINTMENT,
                "database": AgentType.DATABASE
            }

            agent_type = category_map.get(category, AgentType.DATABASE)  # Default to database

            # Create proper return state
            result_state: CoordinatorState = {
                "messages": state["messages"] + [AIMessage(content=f"Request classified as: {agent_type.value}")],
                "user_query": state["user_query"],
                "agent_type": agent_type,
                "current_agent": None,
                "agent_responses": new_state["agent_responses"],
                "final_response": None,
                "error": None,
                "retry_count": new_state["retry_count"],
                "max_retries": new_state["max_retries"]
            }
            return result_state

        except Exception as e:
            return {
                **state,
                "error": f"Request analysis failed: {str(e)}"
            }

    def _route_to_agent(self, state: CoordinatorState) -> CoordinatorState:
        """Route to the appropriate agent based on classification."""
        return state

    def _route_to_specific_agent(self, state: CoordinatorState) -> str:
        """Determine which agent node to route to."""
        if state.get("error"):
            return "error"

        agent_type = state.get("agent_type")
        if not agent_type:
            return "error"

        return agent_type.value

    async def _execute_agent_with_retry(self, agent, agent_name: str, query: str, max_retries: int = 3) -> Dict[str, Any]:
        """Execute an agent with retry logic."""
        last_error = None

        for attempt in range(max_retries):
            try:
                self.logger.info(f"Executing {agent_name} agent (attempt {attempt + 1}/{max_retries})")
                result = await agent.run(query)
                return {"success": True, "result": result, "attempts": attempt + 1}
            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"{agent_name} agent attempt {attempt + 1} failed: {last_error}")

                if attempt < max_retries - 1:
                    # Wait before retry
                    await asyncio.sleep(1)

        return {"success": False, "error": last_error, "attempts": max_retries}

    def _execute_medicine_agent(self, state: CoordinatorState) -> CoordinatorState:
        """Execute medicine agent."""
        if not self.medicine_agent:
            return {**state, "error": "Medicine agent not initialized"}

        # Note: In a real implementation, this would be async
        # For now, we'll simulate the async execution
        async def execute():
            result = await self._execute_agent_with_retry(
                self.medicine_agent, "medicine", state["user_query"]
            )
            return result

        # Since LangGraph nodes should be synchronous, we'll handle this differently
        # In practice, you'd want to make the entire graph async
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(execute())
        finally:
            loop.close()

        if result["success"]:
            return {
                **state,
                "agent_responses": {**state["agent_responses"], "medicine": result["result"]},
                "current_agent": "medicine"
            }
        else:
            return {
                **state,
                "error": f"Medicine agent failed: {result['error']}"
            }

    def _execute_patient_monitoring(self, state: CoordinatorState) -> CoordinatorState:
        """Execute patient monitoring agent."""
        if not self.patient_monitoring_agent:
            return {**state, "error": "Patient monitoring agent not initialized"}

        async def execute():
            result = await self._execute_agent_with_retry(
                self.patient_monitoring_agent, "patient_monitoring", state["user_query"]
            )
            return result

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(execute())
        finally:
            loop.close()

        if result["success"]:
            return {
                **state,
                "agent_responses": {**state["agent_responses"], "patient_monitoring": result["result"]},
                "current_agent": "patient_monitoring"
            }
        else:
            return {
                **state,
                "error": f"Patient monitoring agent failed: {result['error']}"
            }

    def _execute_stock_management(self, state: CoordinatorState) -> CoordinatorState:
        """Execute stock management agent."""
        if not self.stock_management_agent:
            return {**state, "error": "Stock management agent not initialized"}

        async def execute():
            result = await self._execute_agent_with_retry(
                self.stock_management_agent, "stock_management", state["user_query"]
            )
            return result

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(execute())
        finally:
            loop.close()

        if result["success"]:
            return {
                **state,
                "agent_responses": {**state["agent_responses"], "stock_management": result["result"]},
                "current_agent": "stock_management"
            }
        else:
            return {
                **state,
                "error": f"Stock management agent failed: {result['error']}"
            }

    def _execute_appointment_agent(self, state: CoordinatorState) -> CoordinatorState:
        """Execute appointment agent."""
        if not self.appointment_agent:
            return {**state, "error": "Appointment agent not initialized"}

        async def execute():
            result = await self._execute_agent_with_retry(
                self.appointment_agent, "appointment", state["user_query"]
            )
            return result

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(execute())
        finally:
            loop.close()

        if result["success"]:
            return {
                **state,
                "agent_responses": {**state["agent_responses"], "appointment": result["result"]},
                "current_agent": "appointment"
            }
        else:
            return {
                **state,
                "error": f"Appointment agent failed: {result['error']}"
            }

    def _execute_database_agent(self, state: CoordinatorState) -> CoordinatorState:
        """Execute database agent."""
        if not self.database_agent:
            return {**state, "error": "Database agent not initialized"}

        async def execute():
            result = await self._execute_agent_with_retry(
                self.database_agent, "database", state["user_query"]
            )
            return result

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(execute())
        finally:
            loop.close()

        if result["success"]:
            return {
                **state,
                "agent_responses": {**state["agent_responses"], "database": result["result"]},
                "current_agent": "database"
            }
        else:
            return {
                **state,
                "error": f"Database agent failed: {result['error']}"
            }

    def _format_final_response(self, state: CoordinatorState) -> CoordinatorState:
        """Format the final response from agent execution."""
        try:
            agent_responses = state.get("agent_responses", {})
            current_agent = state.get("current_agent")

            if not agent_responses:
                return {
                    **state,
                    "final_response": "No response received from agents."
                }

            # Get the response from the current agent
            if current_agent:
                response = agent_responses.get(current_agent, "No response available")
                # Add agent context to the response
                formatted_response = f"[{current_agent.upper()}] {response}"
            else:
                response = list(agent_responses.values())[0] if agent_responses else "No response available"
                formatted_response = f"[COORDINATOR] {response}"

            return {
                **state,
                "final_response": formatted_response
            }

        except Exception as e:
            return {
                **state,
                "error": f"Response formatting failed: {str(e)}"
            }

    def _handle_error(self, state: CoordinatorState) -> CoordinatorState:
        """Handle errors in the coordinator workflow."""
        error = state.get("error", "Unknown error")
        return {
            **state,
            "final_response": f"I apologize, but I encountered an error while processing your request: {error}"
        }

    async def run(self, input_data: Any) -> str:
        """Run the LangGraph coordinator."""
        try:
            if not isinstance(input_data, str):
                input_data = str(input_data)

            # Initialize state
            initial_state = {
                "messages": [HumanMessage(content=input_data)],
                "user_query": input_data,
                "agent_type": None,
                "current_agent": None,
                "agent_responses": {},
                "final_response": None,
                "error": None,
                "retry_count": 0,
                "max_retries": 3
            }

            # Execute the graph
            result = self.graph.invoke(initial_state)

            # Return the final response
            if result.get("error"):
                return f"Error: {result['error']}"
            elif result.get("final_response"):
                return result["final_response"]
            else:
                return "No response generated."

        except Exception as e:
            self.logger.error(f"Coordinator execution failed: {str(e)}")
            return f"An error occurred while coordinating agents: {str(e)}"

    def get_status(self) -> Dict[str, Any]:
        """Get coordinator status."""
        return {
            "name": "langgraph_coordinator",
            "running": self.is_running,
            "type": "multi_agent_coordinator",
            "capabilities": ["agent_routing", "request_coordination", "response_formatting"],
            "agents": {
                "database_agent": self.database_agent is not None,
                "medicine_agent": self.medicine_agent is not None,
                "patient_monitoring_agent": self.patient_monitoring_agent is not None,
                "stock_management_agent": self.stock_management_agent is not None,
                "appointment_agent": self.appointment_agent is not None
            }
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the coordinator and all agents."""
        health = {
            "coordinator": {
                "status": "healthy" if self.is_running else "unhealthy",
                "name": "langgraph_coordinator"
            },
            "agents": {}
        }

        agents_to_check = [
            ("database_agent", self.database_agent),
            ("medicine_agent", self.medicine_agent),
            ("patient_monitoring_agent", self.patient_monitoring_agent),
            ("stock_management_agent", self.stock_management_agent),
            ("appointment_agent", self.appointment_agent)
        ]

        for agent_name, agent in agents_to_check:
            if agent:
                try:
                    status = agent.get_status()
                    health["agents"][agent_name] = {
                        "status": "healthy" if status.get("is_running") else "unhealthy",
                        "name": status.get("name")
                    }
                except Exception as e:
                    health["agents"][agent_name] = {
                        "status": "error",
                        "error": str(e)
                    }
            else:
                health["agents"][agent_name] = {"status": "not_initialized"}

        return health
