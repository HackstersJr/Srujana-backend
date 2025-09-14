"""
Toolbox Service for managing LangChain tools and utilities.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain.tools import Tool
from langchain_community.tools import (
    ShellTool,
    ReadFileTool,
    WriteFileTool,
    ListDirectoryTool,
    CopyFileTool,
    DeleteFileTool,
    MoveFileTool
)


class ToolboxService:
    """
    Service for managing and providing LangChain tools.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the toolbox service.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.tools = {}
        self.logger = logging.getLogger(__name__)

    async def initialize(self) -> None:
        """Initialize the toolbox service."""
        try:
            self.logger.info("Initializing toolbox service")

            # Initialize built-in tools
            await self._load_builtin_tools()

            # Initialize custom tools
            await self._load_custom_tools()

            self.logger.info(
                f"Toolbox service initialized with {len(self.tools)} tools"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize toolbox service: {str(e)}")
            raise

    async def _load_builtin_tools(self) -> None:
        """Load built-in LangChain tools."""
        try:
            tool_config = self.config.get("builtin_tools", {})

            # Shell tool
            if tool_config.get("shell", False):
                shell_tool = ShellTool()
                self.tools["shell"] = shell_tool
                self.logger.info("Loaded shell tool")

            # File management tools
            if tool_config.get("file_management", False):
                file_tools = [
                    ReadFileTool(),
                    WriteFileTool(),
                    ListDirectoryTool(),
                    CopyFileTool(),
                    DeleteFileTool(),
                    MoveFileTool()
                ]
                self.tools["file_management"] = file_tools
                self.logger.info("Loaded file management tools")

            # Calculator tool
            if tool_config.get("calculator", False):
                calculator_tool = Tool(
                    name="calculator",
                    description="Useful for when you need to answer questions about math",
                    func=self._calculator_func,
                )
                self.tools["calculator"] = calculator_tool
                self.logger.info("Loaded calculator tool")

            # Database tool will be added later when db_service is available

        except Exception as e:
            self.logger.error(f"Failed to load builtin tools: {str(e)}")
            raise

    async def _load_custom_tools(self) -> None:
        """Load custom tools defined in configuration."""
        try:
            custom_tools_config = self.config.get("custom_tools", [])

            for tool_config in custom_tools_config:
                tool_name = tool_config.get("name")
                tool_description = tool_config.get("description")
                tool_function = tool_config.get("function")

                if tool_name and tool_description and tool_function:
                    # Create tool from configuration
                    custom_tool = Tool(
                        name=tool_name, description=tool_description, func=tool_function
                    )
                    self.tools[tool_name] = custom_tool
                    self.logger.info(f"Loaded custom tool: {tool_name}")

        except Exception as e:
            self.logger.error(f"Failed to load custom tools: {str(e)}")
            raise

    def _calculator_func(self, expression: str) -> str:
        """
        Simple calculator function.

        Args:
            expression: Mathematical expression to evaluate

        Returns:
            Result of the calculation
        """
        try:
            # Basic safety check
            allowed_chars = set("0123456789+-*/().= ")
            if not all(c in allowed_chars for c in expression):
                return "Error: Invalid characters in expression"

            # Evaluate the expression
            result = eval(expression)
            return str(result)

        except Exception as e:
            return f"Error: {str(e)}"

    async def get_tools(self) -> List:
        """
        Get all available tools.

        Returns:
            List of tools
        """
        tools = []
        for tool in self.tools.values():
            if isinstance(tool, list):
                tools.extend(tool)
            else:
                tools.append(tool)
        return tools

    async def get_tool(self, tool_name: str) -> Optional[Tool]:
        """
        Get a specific tool by name.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool instance or None if not found
        """
        return self.tools.get(tool_name)

    async def add_tool(self, tool_name: str, tool: Tool) -> None:
        """
        Add a tool to the toolbox.

        Args:
            tool_name: Name of the tool
            tool: Tool instance
        """
        try:
            self.tools[tool_name] = tool
            self.logger.info(f"Added tool: {tool_name}")

        except Exception as e:
            self.logger.error(f"Failed to add tool {tool_name}: {str(e)}")
            raise

    async def remove_tool(self, tool_name: str) -> bool:
        """
        Remove a tool from the toolbox.

        Args:
            tool_name: Name of the tool to remove

        Returns:
            True if tool was removed, False if not found
        """
        try:
            if tool_name in self.tools:
                del self.tools[tool_name]
                self.logger.info(f"Removed tool: {tool_name}")
                return True
            else:
                self.logger.warning(f"Tool not found: {tool_name}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to remove tool {tool_name}: {str(e)}")
            raise

    async def initialize_database_tool(self, db_service) -> None:
        """
        Initialize database tool with the provided database service.

        Args:
            db_service: Database service instance
        """
        try:
            tool_config = self.config.get("builtin_tools", {})

            if tool_config.get("database", False) and db_service:
                db_tool = await self.create_database_tool(db_service)
                await self.add_tool("database_query", db_tool)
                self.logger.info("Loaded database tool")

        except Exception as e:
            self.logger.error(f"Failed to initialize database tool: {str(e)}")
            raise

    async def create_database_tool(self, db_service) -> Tool:
        """
        Create a database query tool.

        Args:
            db_service: Database service instance

        Returns:
            Database tool
        """
        try:

            def db_query_func(query: str) -> str:
                """Execute a database query."""
                try:
                    # Use synchronous database execution
                    results = db_service.execute_query_sync(query)

                    if not results:
                        return "Query executed successfully, but returned no results."

                    # Format results nicely
                    if len(results) == 1:
                        return f"Result: {results[0]}"
                    else:
                        formatted_results = "\n".join([str(row) for row in results[:5]])
                        if len(results) > 5:
                            formatted_results += f"\n... and {len(results) - 5} more results"
                        return f"Found {len(results)} results:\n{formatted_results}"

                except Exception as e:
                    return f"Database error: {str(e)}"

            db_tool = Tool(
                name="database_query",
                description="Execute SQL queries on the database. Input should be a valid SQL query string.",
                func=db_query_func,
            )

            self.logger.info("Created database tool")
            return db_tool

        except Exception as e:
            self.logger.error(f"Failed to create database tool: {str(e)}")
            raise

    async def create_web_search_tool(self) -> Tool:
        """
        Create a web search tool.

        Returns:
            Web search tool
        """
        try:

            def web_search_func(query: str) -> str:
                """Search the web for information."""
                try:
                    # Placeholder implementation
                    # In a real implementation, you would use a search API
                    return f"Web search results for: {query}"
                except Exception as e:
                    return f"Web search error: {str(e)}"

            web_tool = Tool(
                name="web_search",
                description="Search the web for information. Input should be a search query string.",
                func=web_search_func,
            )

            self.logger.info("Created web search tool")
            return web_tool

        except Exception as e:
            self.logger.error(f"Failed to create web search tool: {str(e)}")
            raise

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools with their information.

        Returns:
            List of tool information
        """
        tools_info = []
        for name, tool in self.tools.items():
            tools_info.append(
                {
                    "name": name,
                    "description": getattr(tool, "description", "No description"),
                    "type": type(tool).__name__,
                }
            )
        return tools_info

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            self.logger.info("Cleaning up toolbox service")

            # Cleanup tools if they have cleanup methods
            for tool in self.tools.values():
                if hasattr(tool, "cleanup"):
                    await tool.cleanup()

            self.tools.clear()

            self.logger.info("Toolbox service cleanup completed")

        except Exception as e:
            self.logger.error(f"Failed to cleanup toolbox service: {str(e)}")
            raise
