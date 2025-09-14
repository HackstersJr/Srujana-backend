"""
Base Retriever module providing common functionality for all retrievers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseRetriever(ABC):
    """
    Abstract base class for all retrievers in the system.
    Provides common functionality and interface.
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the base retriever.

        Args:
            name: Name of the retriever
            config: Configuration dictionary
        """
        self.name = name
        self.config = config or {}
        self.is_initialized = False
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the retriever. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search for relevant documents. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Add documents to the retriever. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources. Must be implemented by subclasses."""
        pass

    async def start(self) -> None:
        """Start the retriever."""
        try:
            self.logger.info(f"Starting retriever: {self.name}")
            await self.initialize()
            self.is_initialized = True
            self.logger.info(f"Retriever started successfully: {self.name}")
        except Exception as e:
            self.logger.error(f"Failed to start retriever {self.name}: {str(e)}")
            raise

    async def stop(self) -> None:
        """Stop the retriever."""
        try:
            self.logger.info(f"Stopping retriever: {self.name}")
            await self.cleanup()
            self.is_initialized = False
            self.logger.info(f"Retriever stopped successfully: {self.name}")
        except Exception as e:
            self.logger.error(f"Failed to stop retriever {self.name}: {str(e)}")
            raise

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the retriever."""
        return {
            "name": self.name,
            "is_initialized": self.is_initialized,
            "config": self.config,
        }
