"""
Base Agent module providing common functionality for all agents.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    Provides common functionality and interface.
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the base agent.

        Args:
            name: Name of the agent
            config: Configuration dictionary
        """
        self.name = name
        self.config = config or {}
        self.is_running = False
        self.logger = logger.bind(agent_name=name)

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the agent. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def run(self, input_data: Any) -> Any:
        """Run the agent. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources. Must be implemented by subclasses."""
        pass

    async def start(self) -> None:
        """Start the agent."""
        try:
            self.logger.info("Starting agent", agent=self.name)
            await self.initialize()
            self.is_running = True
            self.logger.info("Agent started successfully", agent=self.name)
        except Exception as e:
            self.logger.error("Failed to start agent", agent=self.name, error=str(e))
            raise

    async def stop(self) -> None:
        """Stop the agent."""
        try:
            self.logger.info("Stopping agent", agent=self.name)
            await self.cleanup()
            self.is_running = False
            self.logger.info("Agent stopped successfully", agent=self.name)
        except Exception as e:
            self.logger.error("Failed to stop agent", agent=self.name, error=str(e))
            raise

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the agent."""
        return {"name": self.name, "is_running": self.is_running, "config": self.config}
