"""

EmbedChain Retriever implementation for advanced RAG capabilities.
"""

import os
from typing import Any, Dict, List, Optional

from .base_retriever import BaseRetriever

try:
    from embedchain import App
    from embedchain.config import BaseLlmConfig
except ImportError:
    App = None
    BaseLlmConfig = None


class EmbedChainRetriever(BaseRetriever):
    """
    Retriever implementation using EmbedChain for RAG capabilities.
    """

    def __init__(
        self,
        name: str = "embedchain_retriever",
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the EmbedChain retriever.

        Args:
            name: Name of the retriever
            config: Configuration dictionary
        """
        super().__init__(name, config)
        self.app = None
        self.db_path = self.config.get("db_path", "data/embedchain_db")

    async def initialize(self) -> None:
        """Initialize the EmbedChain retriever."""
        try:
            self.logger.info("Initializing EmbedChain retriever")

            if App is None:
                raise ImportError(
                    "EmbedChain is not installed. Please install it with: pip install embedchain"
                )

            # Set the Google API key environment variable for EmbedChain
            os.environ["GOOGLE_API_KEY"] = self.config.get("gemini_api_key", "")
            # Set a dummy OpenAI API key to avoid embedder initialization issues
            os.environ["OPENAI_API_KEY"] = "dummy-key-for-embedchain"

            # Create data directory if it doesn't exist
            os.makedirs(self.db_path, exist_ok=True)

            # Configure EmbedChain app
            app_config = {
                "vectordb": {
                    "provider": "chroma",
                    "config": {"collection_name": "embedchain_store", "dir": self.db_path}
                }
            }

            # Add LLM config if provided
            if "llm" in self.config:
                app_config["llm"] = self.config["llm"]

            # Initialize EmbedChain app
            self.app = App.from_config(config=app_config)

            self.logger.info("EmbedChain retriever initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize EmbedChain retriever: {str(e)}")
            raise

    async def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using EmbedChain.

        Args:
            query: Search query
            top_k: Number of top results to return

        Returns:
            List of relevant documents
        """
        try:
            if self.app is None:
                self.logger.error("EmbedChain app not initialized")
                return []

            # Search using EmbedChain
            results = self.app.search(query, num_documents=top_k)

            # Format results
            formatted_results = []
            for i, result in enumerate(results):
                formatted_result = {
                    "content": result.get("content", ""),
                    "metadata": result.get("metadata", {}),
                    "score": result.get("score", 0.0),
                    "rank": i + 1,
                }
                formatted_results.append(formatted_result)

            self.logger.info(f"Found {len(formatted_results)} results for query")
            return formatted_results

        except Exception as e:
            self.logger.error(f"Failed to search: {str(e)}")
            return []

    async def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Add documents to the EmbedChain index.

        Args:
            documents: List of documents to add
        """
        try:
            if self.app is None:
                self.logger.error("EmbedChain app not initialized")
                return

            self.logger.info(f"Adding {len(documents)} documents to EmbedChain")

            for doc in documents:
                # Extract content and metadata
                content = doc.get("content", doc.get("text", ""))
                metadata = doc.get("metadata", {})

                # Add document based on type
                doc_type = doc.get("type", "text")

                if doc_type == "text":
                    self.app.add(content, data_type="text", metadata=metadata)
                elif doc_type == "pdf":
                    file_path = doc.get("file_path")
                    if file_path and os.path.exists(file_path):
                        self.app.add(file_path, data_type="pdf_file", metadata=metadata)
                elif doc_type == "web":
                    url = doc.get("url")
                    if url:
                        self.app.add(url, data_type="web_page", metadata=metadata)
                elif doc_type == "youtube":
                    video_url = doc.get("video_url")
                    if video_url:
                        self.app.add(
                            video_url, data_type="youtube_video", metadata=metadata
                        )
                else:
                    # Default to text
                    self.app.add(content, data_type="text", metadata=metadata)

            self.logger.info(
                f"Successfully added {len(documents)} documents to EmbedChain"
            )

        except Exception as e:
            self.logger.error(f"Failed to add documents: {str(e)}")
            raise

    async def add_data_source(
        self, source_type: str, source_path: str, **kwargs
    ) -> None:
        """
        Add a data source to EmbedChain.

        Args:
            source_type: Type of data source (pdf, web, youtube, etc.)
            source_path: Path or URL to the data source
            **kwargs: Additional metadata
        """
        try:
            if self.app is None:
                self.logger.error("EmbedChain app not initialized")
                return

            self.logger.info(f"Adding {source_type} data source: {source_path}")

            metadata = kwargs.get("metadata", {})

            if source_type == "pdf":
                self.app.add(source_path, data_type="pdf_file", metadata=metadata)
            elif source_type == "web":
                self.app.add(source_path, data_type="web_page", metadata=metadata)
            elif source_type == "youtube":
                self.app.add(source_path, data_type="youtube_video", metadata=metadata)
            elif source_type == "text":
                self.app.add(source_path, data_type="text", metadata=metadata)
            else:
                self.logger.warning(f"Unknown source type: {source_type}")

            self.logger.info(f"Successfully added {source_type} data source")

        except Exception as e:
            self.logger.error(f"Failed to add data source: {str(e)}")
            raise

    async def query_with_context(self, query: str) -> str:
        """
        Query EmbedChain and get a contextual response.

        Args:
            query: Query string

        Returns:
            Contextual response
        """
        try:
            if self.app is None:
                self.logger.error("EmbedChain app not initialized")
                return ""

            # Query EmbedChain for a response
            response = self.app.query(query)

            self.logger.info("Generated contextual response")
            return response

        except Exception as e:
            self.logger.error(f"Failed to query with context: {str(e)}")
            return ""

    async def reset_database(self) -> None:
        """Reset the EmbedChain database."""
        try:
            if self.app is None:
                self.logger.error("EmbedChain app not initialized")
                return

            self.app.reset()
            self.logger.info("EmbedChain database reset successfully")

        except Exception as e:
            self.logger.error(f"Failed to reset database: {str(e)}")
            raise

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the EmbedChain database.

        Returns:
            Database statistics
        """
        try:
            if self.app is None:
                return {"error": "EmbedChain app not initialized"}

            # Get basic stats (this might vary based on EmbedChain version)
            stats = {
                "db_path": self.db_path,
                "status": "initialized" if self.app else "not_initialized",
            }

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get database stats: {str(e)}")
            return {"error": str(e)}

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            self.logger.info("Cleaning up EmbedChain retriever")

            # No specific cleanup needed for EmbedChain
            # The database is persisted to disk

            self.app = None

            self.logger.info("EmbedChain retriever cleanup completed")

        except Exception as e:
            self.logger.error(f"Failed to cleanup EmbedChain retriever: {str(e)}")
            raise
