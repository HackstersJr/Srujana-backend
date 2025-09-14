"""
Simplified LangGraph Agent for Natural Language to SQL Query Processing.
Single-node approach that handles everything in one step.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, TypedDict, Annotated
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph, add_messages

from agents.base_agent import BaseAgent
from services.db_service import DBService
from services.toolbox_service import ToolboxService


class SimpleGraphState(TypedDict):
    """Simplified state with minimal fields."""
    messages: Annotated[List[BaseMessage], add_messages]
    user_query: str
    final_response: str


class ToolboxAgent(BaseAgent):
    """
    Simplified LangGraph Agent that processes queries in a single node.
    Handles both database queries and general questions efficiently.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        db_service: DBService,
        toolbox_service: ToolboxService,
    ):
        """Initialize the simplified LangGraph agent."""
        super().__init__("langgraph_agent", config)
        self.db_service = db_service
        self.toolbox_service = toolbox_service
        self.max_results = config.get("max_results", 100)
        self.max_retries = config.get("max_retries", 2)
        
        self.llm = ChatGoogleGenerativeAI(
            model=config.get("model_name", "gemini-1.5-flash"),
            temperature=config.get("temperature", 0.1),
            api_key=config.get("gemini_api_key"),
        )

        # Build the simple graph
        self.graph = self._build_graph()
        self._table_cache = None
        self._cache_timestamp = None

    async def initialize(self) -> None:
        """Initialize the agent."""
        await self._refresh_table_cache()

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._table_cache = None

    async def start(self) -> None:
        """Start the agent."""
        self.logger.info("Starting simplified LangGraph agent")
        await self.initialize()
        self.is_running = True
        self.logger.info("LangGraph agent started successfully")

    async def stop(self) -> None:
        """Stop the agent."""
        self.logger.info("Stopping simplified LangGraph agent")
        self.is_running = False
        await self.cleanup()

    def _build_graph(self) -> StateGraph:
        """Build the simple single-node graph."""
        workflow = StateGraph(SimpleGraphState)
        
        # Single node that handles everything
        workflow.add_node("process_query", self._process_query)
        
        # Simple linear flow
        workflow.set_entry_point("process_query")
        workflow.add_edge("process_query", END)
        
        return workflow.compile()

    async def _refresh_table_cache(self) -> None:
        """Refresh the table cache for better SQL generation."""
        try:
            # Get table and column information
            schema_query = """
                SELECT 
                    t.table_name,
                    string_agg(c.column_name || ' (' || c.data_type || ')', ', ') as columns
                FROM information_schema.tables t
                LEFT JOIN information_schema.columns c ON t.table_name = c.table_name
                WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
                GROUP BY t.table_name
                ORDER BY t.table_name
                LIMIT 20;
            """
            
            results = await self.db_service.execute_query(schema_query)
            
            self._table_cache = {}
            for row in results:
                table_name = row['table_name']
                columns = row.get('columns', 'No column info')
                self._table_cache[table_name] = columns
            
            self._cache_timestamp = datetime.now()
            self.logger.info(f"Table cache refreshed: {len(self._table_cache)} tables")
            
        except Exception as e:
            self.logger.warning(f"Could not refresh table cache: {str(e)}")
            # Fallback cache
            self._table_cache = {
                'agent_sessions': 'id (integer), created_at (timestamp)',
                'agent_queries': 'id (integer), query (text), response (text)',
                'documents': 'id (integer), title (text), content (text)'
            }

    def _get_table_info(self) -> str:
        """Get formatted table information for the prompt."""
        if not self._table_cache:
            return "Database connection available (table info not loaded)"
        
        table_info = []
        for table, columns in list(self._table_cache.items())[:10]:  # Limit to 10 tables
            table_info.append(f"• {table}: {columns}")
        
        return "Available tables:\n" + "\n".join(table_info)

    async def _process_query(self, state: SimpleGraphState) -> SimpleGraphState:
        """
        Single method that processes the entire query workflow.
        Analyzes, executes (if needed), and formats the response.
        """
        try:
            user_query = state["user_query"]
            
            # Refresh cache if needed (every 30 minutes)
            if (self._cache_timestamp is None or 
                (datetime.now() - self._cache_timestamp).seconds > 1800):
                await self._refresh_table_cache()

            table_info = self._get_table_info()

            # Comprehensive analysis prompt
            analysis_prompt = f"""
You are an AI assistant with database access capabilities. Analyze this user query and provide the appropriate response.

User Query: "{user_query}"

{table_info}

DECISION LOGIC:
1. If the query asks for specific data, records, counts, lists, or database information:
   - Respond with: ACTION: DATABASE_QUERY
   - Then provide a safe PostgreSQL SELECT query

2. If the query is a general question, explanation, or doesn't need database data:
   - Respond with: ACTION: GENERAL_RESPONSE
   - Then provide a helpful answer or suggest using the 'langchain' agent

EXAMPLES:
- "Show me all users" → ACTION: DATABASE_QUERY
- "How many records are there?" → ACTION: DATABASE_QUERY  
- "What is machine learning?" → ACTION: GENERAL_RESPONSE
- "How do I code in Python?" → ACTION: GENERAL_RESPONSE

RULES FOR SQL:
- Only SELECT queries allowed
- Include LIMIT clause for safety
- Use proper PostgreSQL syntax
- Reference only existing tables/columns shown above

Your response format:
ACTION: [DATABASE_QUERY or GENERAL_RESPONSE]
CONTENT: [Your SQL query or general response]
            """

            # Get LLM decision
            llm_response = self.llm.invoke([HumanMessage(content=analysis_prompt)])
            llm_output = llm_response.content.strip()

            # Parse the LLM response
            final_response = await self._handle_llm_response(llm_output, user_query)

            # Ensure we always have a valid response
            if not final_response or len(final_response.strip()) == 0:
                final_response = "I apologize, but I couldn't process your request. Please try rephrasing your question."

            return {
                **state,
                "final_response": final_response,
                "messages": state["messages"] + [AIMessage(content=final_response)]
            }

        except Exception as e:
            error_msg = f"I encountered an error while processing your request: {str(e)}"
            self.logger.error(f"Process query error: {str(e)}")
            
            return {
                **state,
                "final_response": error_msg,
                "messages": state["messages"] + [AIMessage(content=error_msg)]
            }

    async def _handle_llm_response(self, llm_output: str, user_query: str) -> str:
        """Handle the LLM response and execute appropriate action."""
        try:
            if "ACTION: DATABASE_QUERY" in llm_output:
                return await self._handle_database_query(llm_output, user_query)
            elif "ACTION: GENERAL_RESPONSE" in llm_output:
                return self._handle_general_response(llm_output)
            else:
                # Fallback: treat as general response
                return llm_output if llm_output else "I couldn't understand your request. Please try again."
                
        except Exception as e:
            self.logger.error(f"Error handling LLM response: {str(e)}")
            return "I encountered an error while processing your request. Please try again."

    async def _handle_database_query(self, llm_output: str, user_query: str) -> str:
        """Handle database query execution with retry logic."""
        # Extract SQL query
        content_start = llm_output.find("CONTENT:") + 8
        if content_start < 8:
            return "I couldn't generate a proper database query. Please rephrase your request."
        
        sql_query = llm_output[content_start:].strip()
        sql_query = self._clean_sql_query(sql_query)

        # Validate SQL
        if not sql_query or not sql_query.upper().startswith('SELECT'):
            return "I can only execute safe SELECT queries. Please rephrase your database request."

        # Try to execute with retries
        for attempt in range(self.max_retries + 1):
            try:
                # Add LIMIT if not present
                if 'LIMIT' not in sql_query.upper():
                    sql_query += f' LIMIT {self.max_results}'

                # Execute query
                results = await self.db_service.execute_query(sql_query)
                
                # Format results
                return self._format_query_results(results, user_query)
                
            except Exception as db_error:
                error_msg = str(db_error)
                self.logger.warning(f"SQL execution attempt {attempt + 1} failed: {error_msg}")
                
                # If it's the last attempt, return error
                if attempt == self.max_retries:
                    return f"I tried to execute your database query but encountered an error: {error_msg}. Please try rephrasing your question."
                
                # Try to fix the query for next attempt
                sql_query = await self._fix_sql_query(sql_query, error_msg)

        return "I couldn't execute your database query after multiple attempts. Please try rephrasing your request."

    def _handle_general_response(self, llm_output: str) -> str:
        """Handle general response."""
        content_start = llm_output.find("CONTENT:") + 8
        if content_start > 7:
            response = llm_output[content_start:].strip()
            return response if response else "For general questions, I recommend using the 'langchain' agent type."
        else:
            return llm_output

    def _clean_sql_query(self, sql_query: str) -> str:
        """Clean and validate SQL query."""
        # Remove markdown formatting
        sql_query = sql_query.strip()
        if sql_query.startswith("```sql"):
            sql_query = sql_query[6:]
        elif sql_query.startswith("```"):
            sql_query = sql_query[3:]
        if sql_query.endswith("```"):
            sql_query = sql_query[:-3]
        
        # Remove extra whitespace and semicolons
        sql_query = sql_query.strip().rstrip(';')
        
        return sql_query

    async def _fix_sql_query(self, original_query: str, error_msg: str) -> str:
        """Attempt to fix SQL query based on error message."""
        fix_prompt = f"""
The following SQL query failed with an error. Please provide a corrected version:

Original Query: {original_query}
Error: {error_msg}

Available tables: {self._get_table_info()}

Provide only the corrected SQL query without explanation:
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=fix_prompt)])
            fixed_query = self._clean_sql_query(response.content)
            return fixed_query if fixed_query else original_query
        except Exception:
            return original_query

    def _format_query_results(self, results: List[Dict[str, Any]], user_query: str) -> str:
        """Format query results into a user-friendly response."""
        if not results:
            return f"I executed your query '{user_query}' but found no matching results in the database."
        
        if len(results) == 1:
            # Single result
            result_str = ", ".join([f"{k}: {v}" for k, v in results[0].items()])
            return f"Here's what I found for '{user_query}':\n{result_str}"
        
        # Multiple results
        response = f"I found {len(results)} results for '{user_query}':\n\n"
        
        # Show first few results
        display_count = min(5, len(results))
        for i, row in enumerate(results[:display_count], 1):
            result_str = ", ".join([f"{k}: {v}" for k, v in row.items()])
            response += f"{i}. {result_str}\n"
        
        if len(results) > display_count:
            response += f"\n... and {len(results) - display_count} more results."
        
        return response

    async def run(self, query: str) -> str:
        """Run the simplified workflow for any query."""
        try:
            if not self.is_running:
                return "The agent is not running. Please start the agent first."

            # Initialize simple state
            initial_state: SimpleGraphState = {
                "messages": [HumanMessage(content=query)],
                "user_query": query,
                "final_response": ""
            }

            # Execute the single-node workflow
            final_state = await self.graph.ainvoke(initial_state)
            
            # Return the final response
            response = final_state.get("final_response", "No response was generated.")
            return response if response else "I apologize, but I couldn't process your request."

        except Exception as e:
            error_msg = f"An error occurred while processing your query: {str(e)}"
            self.logger.error(f"Run method error: {str(e)}")
            return error_msg

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status."""
        return {
            "name": "langgraph_agent",
            "running": self.is_running,
            "type": "simplified_nl_to_sql",
            "approach": "single_node_processing",
            "capabilities": [
                "natural_language_to_sql",
                "general_query_routing",
                "automatic_error_recovery",
                "result_formatting"
            ],
            "cache_info": {
                "tables_cached": len(self._table_cache) if self._table_cache else 0,
                "last_cache_update": self._cache_timestamp.isoformat() if self._cache_timestamp else None
            },
            "limits": {
                "max_results": self.max_results,
                "max_retries": self.max_retries
            }
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive health check."""
        health_status = {
            "agent_running": self.is_running,
            "llm_configured": self.llm is not None,
            "table_cache_loaded": bool(self._table_cache),
            "database_healthy": False,
            "last_error": None
        }
        
        try:
            # Test database connection
            test_result = await self.db_service.execute_query("SELECT 1 as health_test")
            health_status["database_healthy"] = len(test_result) == 1 and test_result[0].get("health_test") == 1
        except Exception as e:
            health_status["last_error"] = str(e)
        
        return health_status
