"""
LangChain Agent implementation.
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI

from .base_agent import BaseAgent


class LangChainAgent(BaseAgent):
    """
    LangChain-based agent implementation.
    """

    def __init__(
        self,
        name: str = "langchain_agent",
        config: Optional[Dict[str, Any]] = None,
        tools: Optional[List] = None,
        retrievers: Optional[List] = None,
        db_service=None,
        toolbox_service=None,
    ):
        """
        Initialize the LangChain agent.

        Args:
            name: Name of the agent
            config: Configuration dictionary
            tools: List of tools for the agent
            retrievers: List of retrievers for the agent
            db_service: Database service instance
            toolbox_service: Toolbox service instance
        """
        super().__init__(name, config)
        self.tools = tools or []
        self.retrievers = retrievers or []
        self.db_service = db_service
        self.toolbox_service = toolbox_service
        self.llm = None
        self.agent_executor = None

    async def initialize(self) -> None:
        """Initialize the LangChain agent."""
        try:
            self.logger.info("Initializing LangChain agent")

            # Set Google API key environment variable
            api_key = self.config.get("gemini_api_key", "")
            self.logger.info(f"Setting GOOGLE_API_KEY, key length: {len(api_key)}")
            os.environ["GOOGLE_API_KEY"] = api_key

            # Initialize LLM
            self.llm = ChatGoogleGenerativeAI(
                model=self.config.get("model_name", "gemini-1.5-flash"),
                temperature=self.config.get("temperature", 0.7),
                max_tokens=self.config.get("max_tokens", 2048),
            )

            # Initialize tools from toolbox service
            if self.toolbox_service:
                additional_tools = await self.toolbox_service.get_tools()
                self.tools.extend(additional_tools)

            # Create prompt template
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        self.config.get(
                            "system_prompt", "You are a helpful AI assistant."
                        ),
                    ),
                    ("human", "{input}"),
                    ("placeholder", "{agent_scratchpad}"),
                ]
            )

            # Create agent
            if self.tools:
                # Bind tools to the LLM
                llm_with_tools = self.llm.bind_tools(self.tools)
                
                # Create a simple agent using RunnablePassthrough
                agent = (
                    RunnablePassthrough.assign(
                        agent_scratchpad=lambda x: format_to_openai_function_messages(
                            x["intermediate_steps"]
                        )
                    )
                    | prompt
                    | llm_with_tools
                    | OpenAIFunctionsAgentOutputParser()
                )
                
                self.agent_executor = AgentExecutor(
                    agent=agent, tools=self.tools, verbose=True
                )

            self.logger.info("LangChain agent initialized successfully")

        except Exception as e:
            self.logger.error("Failed to initialize LangChain agent", error=str(e))
            raise

    async def run(self, input_data: Any) -> Any:
        """
        Run the LangChain agent with input data.

        Args:
            input_data: Input data for the agent

        Returns:
            Agent response
        """
        try:
            self.logger.info("Running LangChain agent", input_data=str(input_data))

            if not self.agent_executor:
                # If no tools, use LLM directly
                if isinstance(input_data, str):
                    response = await self.llm.ainvoke(input_data)
                    return response.content
                else:
                    return await self.llm.ainvoke(str(input_data))

            # Use agent executor with tools
            result = await self.agent_executor.ainvoke({"input": str(input_data)})

            self.logger.info("LangChain agent completed successfully")
            return result.get("output", result)

        except Exception as e:
            self.logger.error("Failed to run LangChain agent", error=str(e))
            raise

    async def search_and_respond(self, query: str) -> str:
        """
        Search using retrievers and respond with LLM.

        Args:
            query: Search query

        Returns:
            Response from the agent
        """
        try:
            # Collect results from all retrievers
            retrieval_results = []
            for retriever in self.retrievers:
                if hasattr(retriever, "search"):
                    results = await retriever.search(query)
                    retrieval_results.extend(results)

            # Combine query with retrieval context
            context = "\n".join([str(result) for result in retrieval_results])
            enhanced_query = f"Context: {context}\n\nQuery: {query}"

            # Get response from agent
            response = await self.run(enhanced_query)
            return response

        except Exception as e:
            self.logger.error("Failed to search and respond", error=str(e))
            raise

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            self.logger.info("Cleaning up LangChain agent")

            # Cleanup retrievers
            for retriever in self.retrievers:
                if hasattr(retriever, "cleanup"):
                    await retriever.cleanup()

            # Cleanup services
            if self.db_service and hasattr(self.db_service, "cleanup"):
                await self.db_service.cleanup()

            if self.toolbox_service and hasattr(self.toolbox_service, "cleanup"):
                await self.toolbox_service.cleanup()

            self.logger.info("LangChain agent cleanup completed")

        except Exception as e:
            self.logger.error("Failed to cleanup LangChain agent", error=str(e))
            raise
