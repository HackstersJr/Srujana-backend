"""
Base Agent module providing common functionality for all agents.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable

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
        self.request_handlers: Dict[str, Callable] = {}
        self.response_callbacks: Dict[str, Callable] = {}
        self.metrics = {
            "requests_processed": 0,
            "errors": 0,
            "avg_processing_time": 0.0,
            "last_request_time": None
        }

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
        return {
            "name": self.name,
            "is_running": self.is_running,
            "config": self.config,
            "metrics": self.metrics.copy()
        }

    def register_request_handler(self, request_type: str, handler: Callable) -> None:
        """Register a handler for a specific request type."""
        self.request_handlers[request_type] = handler
        self.logger.info(f"Registered handler for {request_type}", agent=self.name)

    def register_response_callback(self, callback_id: str, callback: Callable) -> None:
        """Register a callback for response handling."""
        self.response_callbacks[callback_id] = callback
        self.logger.info(f"Registered response callback {callback_id}", agent=self.name)

    async def handle_request(self, request_type: str, data: Any) -> Any:
        """Handle a request using registered handlers."""
        if request_type in self.request_handlers:
            start_time = time.time()
            try:
                result = await self.request_handlers[request_type](data)
                processing_time = time.time() - start_time

                # Update metrics
                self.metrics["requests_processed"] += 1
                self.metrics["last_request_time"] = time.time()
                if self.metrics["requests_processed"] == 1:
                    self.metrics["avg_processing_time"] = processing_time
                else:
                    self.metrics["avg_processing_time"] = (
                        (self.metrics["avg_processing_time"] * (self.metrics["requests_processed"] - 1)) +
                        processing_time
                    ) / self.metrics["requests_processed"]

                return result
            except Exception as e:
                self.metrics["errors"] += 1
                self.logger.error(f"Error handling {request_type} request", error=str(e))
                raise
        else:
            raise ValueError(f"No handler registered for request type: {request_type}")

    async def send_response(self, callback_id: str, response: Any) -> None:
        """Send a response using registered callbacks."""
        if callback_id in self.response_callbacks:
            try:
                await self.response_callbacks[callback_id](response)
            except Exception as e:
                self.logger.error(f"Error sending response for {callback_id}", error=str(e))
        else:
            self.logger.warning(f"No callback registered for {callback_id}", agent=self.name)

    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics."""
        return self.metrics.copy()

    def reset_metrics(self) -> None:
        """Reset agent metrics."""
        self.metrics = {
            "requests_processed": 0,
            "errors": 0,
            "avg_processing_time": 0.0,
            "last_request_time": None
        }
        self.logger.info("Metrics reset", agent=self.name)
