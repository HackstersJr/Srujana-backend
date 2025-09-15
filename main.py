"""
Main entry point for the CareCloud AI Agent system.
"""

import asyncio
import signal
import sys
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, root_validator
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

from agents.langchain_agent import LangChainAgent
from agents.langgraph_agent import LangGraphAgentCoordinator
from agents.toolbox_agent import ToolboxAgent
from configs.logging_config import get_logger, setup_agent_logging
# Import our modules
from configs.settings import get_settings
from retrievers.embedchain_retriever import EmbedChainRetriever
from retrievers.nanopq_retriever import NanoPQRetriever
from services.db_service import DBService
from services.toolbox_service import ToolboxService
from services.prisma_service import PrismaService

# Global variables
app = FastAPI()
agent_system: Optional["AgentSystem"] = None
logger = get_logger(__name__)


class QueryRequest(BaseModel):
    """Request model for agent queries.

    Backwards-compatible: accept either `query` (current) or `message` (older clients).
    If `query` is missing but `message` is provided, copy `message` into `query`.
    """

    # We treat `message` as the canonical field. For backwards compatibility
    # accept `query` and copy into message when provided.
    message: Optional[str] = None
    query: Optional[str] = None
    agent_type: Optional[str] = None  # if omitted, backend will decide

    @root_validator(pre=True)
    def ensure_query(cls, values):
        # If message missing but query provided (old clients), copy query->message
        if not values.get("message") and values.get("query"):
            values["message"] = values.get("query")
        return values


class QueryResponse(BaseModel):
    """Response model for agent queries."""

    response: str
    agent_type: str
    processing_time: float


class AgentSystem:
    """Main agent system coordinator."""

    def __init__(self, settings):
        """Initialize the agent system."""
        self.settings = settings
        self.logger = get_logger(__name__)

        # Services
        self.db_service = None
        self.toolbox_service = None
        self.prisma_service = None

        # Retrievers
        self.nanopq_retriever = None
        self.embedchain_retriever = None

        # Legacy agents (for backward compatibility)
        self.langchain_agent = None
        self.toolbox_agent = None
        self.langgraph_agent = None
        self.langchain_agent_secondary = None

        # New LangGraph coordinator system
        self.agent_coordinator = None

        self.is_running = False

    async def initialize(self):
        """Initialize all components."""
        try:
            self.logger.info("Initializing agent system")

            # Ensure directories exist
            self.settings.ensure_directories()

            # Initialize database service
            self.logger.info("Initializing database service")
            self.db_service = DBService(self.settings.get_database_config())
            await self.db_service.initialize()

            # Initialize toolbox service
            self.logger.info("Initializing toolbox service")
            self.toolbox_service = ToolboxService(self.settings.get_toolbox_config())
            await self.toolbox_service.initialize()

            # Initialize Prisma service
            self.logger.info("Initializing Prisma service")
            self.prisma_service = PrismaService()
            await self.prisma_service.connect()

            # Run database migrations
            self.logger.info("Running database migrations")
            from setup_prisma import migrate_database
            migration_success = await migrate_database()
            if not migration_success:
                self.logger.warning("Database migration failed, but continuing with initialization")

            # Initialize retrievers
            self.logger.info("Initializing retrievers")
            self.nanopq_retriever = NanoPQRetriever(
                config=self.settings.get_nanopq_config()
            )
            await self.nanopq_retriever.start()

            self.embedchain_retriever = EmbedChainRetriever(
                config=self.settings.get_embedchain_config()
            )
            await self.embedchain_retriever.start()

            # Initialize LangGraph coordinator with all agents
            self.logger.info("Initializing LangGraph agent coordinator")
            self.agent_coordinator = LangGraphAgentCoordinator(
                config=self.settings.get_llm_config(),
                db_service=self.db_service,
                prisma_service=self.prisma_service,
            )
            await self.agent_coordinator.start()

            # Initialize legacy agents for backward compatibility
            self.logger.info("Initializing legacy agents for backward compatibility")

            # LangChain agent
            self.langchain_agent = LangChainAgent(
                config=self.settings.get_llm_config(),
                retrievers=[self.nanopq_retriever, self.embedchain_retriever],
                db_service=self.db_service,
                toolbox_service=self.toolbox_service,
            )
            await self.langchain_agent.start()

            # Secondary LangChain agent (different LLM config)
            llm_configs = self.settings.get_llm_configs()
            secondary_config = llm_configs.get("secondary", llm_configs.get("primary"))
            self.langchain_agent_secondary = LangChainAgent(
                config=secondary_config,
                retrievers=[self.nanopq_retriever, self.embedchain_retriever],
                db_service=self.db_service,
                toolbox_service=self.toolbox_service,
            )
            await self.langchain_agent_secondary.start()

            # Toolbox agent
            self.toolbox_agent = ToolboxAgent(
                config=self.settings.get_llm_config(),
                toolbox_service=self.toolbox_service,
                db_service=self.db_service
            )
            await self.toolbox_agent.start()

            # LangGraph coordinator (replaces individual agents)
            self.agent_coordinator = LangGraphAgentCoordinator(
                config=self.settings.get_llm_config(),
                db_service=self.db_service,
                prisma_service=self.prisma_service,
            )
            await self.agent_coordinator.start()

            self.is_running = True
            self.logger.info("Agent system initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize agent system: {str(e)}")
            raise

    async def shutdown(self):
        """Shutdown all components."""
        try:
            self.logger.info("Shutting down agent system")

            # Shutdown agent coordinator
            if self.agent_coordinator:
                await self.agent_coordinator.stop()

            # Shutdown legacy agents
            if self.langchain_agent:
                await self.langchain_agent.stop()

            if self.toolbox_agent:
                await self.toolbox_agent.stop()

            if self.langchain_agent_secondary:
                await self.langchain_agent_secondary.stop()

            # Shutdown coordinator
            if self.agent_coordinator:
                await self.agent_coordinator.stop()

            # Shutdown retrievers
            if self.nanopq_retriever:
                await self.nanopq_retriever.stop()

            if self.embedchain_retriever:
                await self.embedchain_retriever.stop()

            # Shutdown services
            if self.toolbox_service:
                await self.toolbox_service.cleanup()

            if self.db_service:
                await self.db_service.cleanup()

            self.is_running = False
            self.logger.info("Agent system shutdown completed")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")

    async def process_query(self, message: str, agent_type: Optional[str] = None) -> tuple:
        """Process a message using the LangGraph coordinator."""
        if not self.is_running:
            raise RuntimeError("Agent system is not running")

        try:
            # If client specified agent_type, pass it through
            if agent_type:
                # For now, just route everything through the coordinator
                # The coordinator will handle the routing internally
                pass

            # Use the LangGraph coordinator for all requests
            if self.agent_coordinator:
                response = await self.agent_coordinator.run(message)
                return response, "coordinator"

            # Fallback to legacy agents if coordinator is not available
            lower = (message or "").lower()
            if any(k in lower for k in ["run", "shell", "file", "open", "read", "write"]):
                if self.toolbox_agent:
                    resp = await self.toolbox_agent.run(message)
                    return resp, "toolbox"

            # Otherwise choose between primary and secondary LLM
            if len(message or "") < 200:
                if self.langchain_agent:
                    resp = await self.langchain_agent.run(message)
                    return resp, "langchain"
            else:
                if self.langchain_agent_secondary:
                    resp = await self.langchain_agent_secondary.run(message)
                    return resp, "langchain_secondary"

            # Fallback to primary
            if self.langchain_agent:
                resp = await self.langchain_agent.run(message)
                return resp, "langchain"

            # If nothing available
            raise RuntimeError("No agent available to process the request")

        except Exception as e:
            self.logger.error(f"Failed to process query: {str(e)}")
            raise


# FastAPI routes
@app.on_event("startup")
async def startup_event():
    """FastAPI startup event."""
    global agent_system

    try:
        # Setup logging
        setup_agent_logging()

        logger.info("Starting CareCloud AI Agent system")

        # Load settings
        settings = get_settings()

        # Initialize agent system
        agent_system = AgentSystem(settings)
        await agent_system.initialize()

        logger.info("FastAPI application started successfully")

    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        sys.exit(1)


@app.on_event("shutdown")
async def shutdown_event():
    """FastAPI shutdown event."""
    global agent_system

    if agent_system:
        await agent_system.shutdown()

    if logger:
        logger.info("FastAPI application shutdown completed")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "CareCloud AI Agent API", "status": "running"}


@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint for Docker and monitoring."""
    global agent_system

    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {},
        "agents": {},
        "coordinator": {}
    }

    try:
        # Check agent system
        if not agent_system:
            health_status["status"] = "unhealthy"
            health_status["services"]["agent_system"] = "not_initialized"
            return health_status

        health_status["services"]["agent_system"] = "running" if agent_system.is_running else "stopped"

        # Check agent coordinator
        if agent_system.agent_coordinator:
            try:
                coordinator_health = await agent_system.agent_coordinator.health_check()
                health_status["coordinator"] = coordinator_health

                # If coordinator is unhealthy, mark overall status as degraded
                if coordinator_health.get("coordinator", {}).get("status") != "healthy":
                    health_status["status"] = "degraded"
            except Exception as e:
                health_status["coordinator"] = {"status": "error", "error": str(e)}
                health_status["status"] = "degraded"
        else:
            health_status["coordinator"] = {"status": "not_initialized"}

        # Check legacy agents
        agent_checks = {
            "langchain_agent": agent_system.langchain_agent,
            "toolbox_agent": agent_system.toolbox_agent,
            "langgraph_agent": agent_system.langgraph_agent,
            "langchain_agent_secondary": agent_system.langchain_agent_secondary
        }

        for agent_name, agent in agent_checks.items():
            if agent:
                try:
                    status = agent.get_status()
                    health_status["agents"][agent_name] = {
                        "status": "healthy" if status.get("is_running") else "unhealthy",
                        "name": status.get("name")
                    }
                except Exception as e:
                    health_status["agents"][agent_name] = {"status": "error", "error": str(e)}
                    health_status["status"] = "degraded"
            else:
                health_status["agents"][agent_name] = {"status": "not_initialized"}

        # Check services
        service_checks = {
            "db_service": agent_system.db_service,
            "prisma_service": agent_system.prisma_service,
            "toolbox_service": agent_system.toolbox_service
        }

        for service_name, service in service_checks.items():
            if service:
                health_status["services"][service_name] = "running"
            else:
                health_status["services"][service_name] = "not_initialized"
                health_status["status"] = "degraded"

        # Check retrievers
        retriever_checks = {
            "nanopq_retriever": agent_system.nanopq_retriever,
            "embedchain_retriever": agent_system.embedchain_retriever
        }

        for retriever_name, retriever in retriever_checks.items():
            if retriever:
                try:
                    status = retriever.get_status()
                    health_status["services"][retriever_name] = "running" if status.get("is_running") else "stopped"
                except Exception as e:
                    health_status["services"][retriever_name] = "error"
                    health_status["status"] = "degraded"
            else:
                health_status["services"][retriever_name] = "not_initialized"

        return health_status

    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
        return health_status


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a query using the agent system."""
    global agent_system

    if not agent_system or not agent_system.is_running:
        raise HTTPException(status_code=503, detail="Agent system not ready")

    try:
        import time

        start_time = time.time()

        # Process the message (message is canonical)
        if not request.message:
            raise HTTPException(status_code=422, detail="Request must include a 'message' field")

        response, used_agent = await agent_system.process_query(request.message, request.agent_type)

        processing_time = time.time() - start_time

        return QueryResponse(
            response=response,
            agent_type=used_agent,
            processing_time=processing_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Query processing failed: {str(e)}"
        )


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def handle_signal(signum, frame):
    """Handle shutdown signals."""
    if logger:
        logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


async def run_console_mode():
    """Run the agent system in console mode."""
    try:
        # Setup logging
        setup_agent_logging()
        logger = get_logger(__name__)

        logger.info("Starting CareCloud AI Agent in console mode")

        # Load settings
        settings = get_settings()

        # Initialize agent system
        agent_system = AgentSystem(settings)
        await agent_system.initialize()

        print("CareCloud AI Agent System")
        print("=" * 40)
        print("Type 'quit' or 'exit' to stop")
        print("Type 'help' for commands")
        print()

        while True:
            try:
                # Get user input
                query = input("Query> ").strip()

                if not query:
                    continue

                if query.lower() in ["quit", "exit"]:
                    break

                if query.lower() == "help":
                    print("Available commands:")
                    print("  help - Show this help message")
                    print("  status - Show system status")
                    print("  langchain <query> - Use LangChain agent")
                    print("  toolbox <query> - Use Toolbox agent")
                    print("  quit/exit - Exit the system")
                    continue

                if query.lower() == "status":
                    status = {
                        "System": "Running" if agent_system.is_running else "Stopped",
                        "LangChain Agent": (
                            "Ready"
                            if agent_system.langchain_agent
                            else "Not initialized"
                        ),
                        "Toolbox Agent": (
                            "Ready" if agent_system.toolbox_agent else "Not initialized"
                        ),
                        "NanoPQ Retriever": (
                            "Ready"
                            if agent_system.nanopq_retriever
                            else "Not initialized"
                        ),
                        "EmbedChain Retriever": (
                            "Ready"
                            if agent_system.embedchain_retriever
                            else "Not initialized"
                        ),
                    }

                    for component, state in status.items():
                        print(f"  {component}: {state}")
                    continue

                # Determine agent type (optional prefix)
                agent_type = None
                if query.startswith("toolbox "):
                    agent_type = "toolbox"
                    query = query[8:]  # Remove "toolbox " prefix
                elif query.startswith("langchain "):
                    agent_type = "langchain"
                    query = query[10:]  # Remove "langchain " prefix

                # Process message
                print(f"Processing with agent_type={agent_type}...")
                response, used_agent = await agent_system.process_query(query, agent_type)
                print(f"Used agent: {used_agent}")
                print(f"Response: {response}")
                print()

            except KeyboardInterrupt:
                print("\nReceived interrupt signal...")
                break
            except Exception as e:
                print(f"Error: {str(e)}")
                continue

        # Shutdown
        await agent_system.shutdown()
        print("Agent system stopped.")

    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="CareCloud AI Agent System")
    parser.add_argument(
        "--mode",
        choices=["server", "console"],
        default="server",
        help="Run mode: server (FastAPI) or console (interactive)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )

    args = parser.parse_args()

    # Setup signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    if args.mode == "console":
        # Run in console mode
        asyncio.run(run_console_mode())
    else:
        # Run FastAPI server
        uvicorn.run(
            "main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info",
        )


if __name__ == "__main__":
    main()
