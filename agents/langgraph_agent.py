"""
Simplified LangGraph Agent for Natural Language to SQL Query Processing.
"""
import re 
import asyncio
import logging
from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

from agents.base_agent import BaseAgent
from services.db_service import DBService
from services.prisma_service import PrismaService


class GraphState(TypedDict):
    """Simplified state for the LangGraph workflow."""
    messages: List[BaseMessage]
    user_query: str
    needs_db_access: Optional[bool]
    sql_query: Optional[str]
    query_results: Optional[List[Dict[str, Any]]]
    final_response: Optional[str]
    error: Optional[str]


class LangGraphAgent(BaseAgent):
    """
    Simplified LangGraph Agent that converts natural language to SQL,
    executes queries, and returns natural language responses.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        db_service: DBService,
        prisma_service: PrismaService,
    ):
        super().__init__("langgraph_agent", config)
        self.db_service = db_service
        self.prisma_service = prisma_service
        self.llm = ChatGoogleGenerativeAI(
            model=config.get("model_name", "gemini-1.5-flash"),
            temperature=config.get("temperature", 0.1),
            api_key=config.get("gemini_api_key"),
        )

        # Build the simplified workflow
        self.graph = self._build_graph()

    async def initialize(self) -> None:
        """Initialize the LangGraph agent."""
        pass

    async def cleanup(self) -> None:
        """Cleanup LangGraph agent resources."""
        pass

    async def start(self) -> None:
        """Start the LangGraph agent."""
        self.logger.info("Starting LangGraph agent")
        self.is_running = True
        self.logger.info("LangGraph agent started successfully")

    async def stop(self) -> None:
        """Stop the LangGraph agent."""
        self.logger.info("Stopping LangGraph agent")
        self.is_running = False
        self.logger.info("LangGraph agent stopped successfully")

    def _build_graph(self) -> StateGraph:
        """Build a simplified LangGraph workflow."""
        workflow = StateGraph(GraphState)

        # Add nodes
        workflow.add_node("analyze_query", self._analyze_query)
        workflow.add_node("generate_sql", self._generate_sql)
        workflow.add_node("execute_sql", self._execute_sql)
        workflow.add_node("format_response", self._format_response)
        workflow.add_node("handle_error", self._handle_error)

        # Set entry point
        workflow.set_entry_point("analyze_query")

        # Add edges
        workflow.add_conditional_edges(
            "analyze_query",
            self._route_after_analysis,
            {
                "generate_sql": "generate_sql",
                "format_response": "format_response",
                "error": "handle_error",
            }
        )

        workflow.add_edge("generate_sql", "execute_sql")
        workflow.add_edge("execute_sql", "format_response")
        workflow.add_edge("format_response", END)
        workflow.add_edge("handle_error", END)

        return workflow.compile()

    def _analyze_query(self, state: GraphState) -> GraphState:
        """Analyze if the query needs database access."""
        try:
            user_query = state["user_query"].lower()

            # Simple keyword-based analysis
            db_keywords = [
                'show', 'list', 'get', 'find', 'search', 'query', 'select',
                'table', 'database', 'data', 'record', 'count', 'how many',
                'what are', 'display', 'retrieve'
            ]

            needs_db = any(keyword in user_query for keyword in db_keywords)

            if not needs_db:
                # General response for non-database queries
                response = f"I understand you're asking about '{state['user_query']}'. This appears to be a general question. For database queries, please ask about data, tables, or records."
                return {
                    **state,
                    "needs_db_access": False,
                    "final_response": response
                }

            return {
                **state,
                "needs_db_access": True
            }

        except Exception as e:
            return {
                **state,
                "error": f"Analysis failed: {str(e)}"
            }

    def _generate_sql(self, state: GraphState) -> GraphState:
        """Generate SQL query from natural language."""
        try:
            user_query = state["user_query"]

            # Get available tables
            try:
                tables_result = self.db_service.execute_query_sync(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                )
                available_tables = [row['tablename'] for row in tables_result]
            except Exception:
                available_tables = ["agent_sessions", "agent_queries", "documents"]

            # Create SQL generation prompt
            sql_prompt = f"""
            Generate a PostgreSQL SELECT query for this request:

            User Query: {user_query}
            Available tables: {', '.join(available_tables)}

            Return only the SQL query, no explanations.
            """

            response = self.llm.invoke([HumanMessage(content=sql_prompt)])
            sql_query = response.content.strip()

            # Clean up SQL
            if sql_query.startswith("```sql"):
                sql_query = sql_query[6:]
            if sql_query.endswith("```"):
                sql_query = sql_query[:-3]
            sql_query = sql_query.strip()

            # Validate it's a SELECT query
            if not sql_query.upper().startswith("SELECT"):
                return {
                    **state,
                    "error": "Generated query is not a SELECT statement"
                }

            return {**state, "sql_query": sql_query}

        except Exception as e:
            return {**state, "error": f"SQL generation failed: {str(e)}"}

    def _execute_sql(self, state: GraphState) -> GraphState:
        """Execute the generated SQL query."""
        try:
            sql_query = state.get("sql_query")
            if not sql_query:
                return {**state, "error": "No SQL query to execute"}

            # Execute the query using Prisma service
            results = asyncio.run(self.prisma_service.execute_raw_query(sql_query))

            return {**state, "query_results": results}

        except Exception as e:
            return {**state, "error": f"Query execution failed: {str(e)}"}

    def _format_response(self, state: GraphState) -> GraphState:
        """Format query results into natural language response."""
        try:
            user_query = state["user_query"]
            query_results = state.get("query_results", [])
            sql_query = state.get("sql_query", "")

            if not query_results:
                response = f"I executed the query for '{user_query}' but found no results."
            else:
                # Simple formatting
                result_count = len(query_results)
                if result_count == 1:
                    response = f"Found 1 result for '{user_query}': {query_results[0]}"
                else:
                    response = f"Found {result_count} results for '{user_query}'. Here are the first few:\n"
                    for i, row in enumerate(query_results[:5]):
                        response += f"{i+1}. {row}\n"
                    if result_count > 5:
                        response += f"... and {result_count - 5} more results"

            return {**state, "final_response": response}

        except Exception as e:
            return {**state, "error": f"Response formatting failed: {str(e)}"}

    def _handle_error(self, state: GraphState) -> GraphState:
        """Handle errors in the workflow."""
        error = state.get("error", "Unknown error occurred")
        self.logger.error(f"Workflow error: {error}")

        return {
            **state,
            "final_response": f"I apologize, but I encountered an error: {error}"
        }

    def _route_after_analysis(self, state: GraphState) -> str:
        """Route after query analysis."""
        if state.get("error"):
            return "error"
        elif state.get("needs_db_access"):
            return "generate_sql"
        else:
            return "format_response"

    async def run(self, query: str) -> str:
        """Run the LangGraph workflow for a natural language query."""
        try:
            if not self.is_running:
                raise RuntimeError("LangGraph agent is not running")

            # Initialize state
            initial_state: GraphState = {
                "messages": [HumanMessage(content=query)],
                "user_query": query,
                "needs_db_access": None,
                "sql_query": None,
                "query_results": None,
                "final_response": None,
                "error": None,
            }

            # Run the graph
            final_state = await self.graph.ainvoke(initial_state)

            # Return the final response
            if final_state.get("error"):
                return f"Error: {final_state['error']}"

            return final_state.get("final_response", "No response generated")

        except Exception as e:
            self.logger.error(f"Error running LangGraph agent: {str(e)}")
            return f"An error occurred while processing your query: {str(e)}"

    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "name": "langgraph_agent",
            "running": self.is_running,
            "type": "natural_language_to_sql",
            "capabilities": ["natural_language_queries", "sql_generation", "result_formatting"]
        }
