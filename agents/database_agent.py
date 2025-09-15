"""
Database Agent implementation.
"""

import asyncio
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .base_agent import BaseAgent
from services.prisma_service import PrismaService


class DatabaseAgent(BaseAgent):
    """
    Database Agent that analyzes requests, plans SQL queries, generates SQL statements,
    and executes them via MCP (PrismaService).
    """

    def __init__(
        self,
        config: Dict[str, Any],
        prisma_service: PrismaService,
    ):
        super().__init__("database_agent", config)
        self.prisma_service = prisma_service
        self.llm = ChatGoogleGenerativeAI(
            model=config.get("model_name", "gemini-1.5-flash"),
            temperature=config.get("temperature", 0.1),
            api_key=config.get("gemini_api_key"),
        )

    async def initialize(self) -> None:
        """Initialize the Database Agent."""
        pass

    async def start(self) -> None:
        """Start the Database Agent."""
        self.logger.info("Starting Database Agent")
        self.is_running = True
        self.logger.info("Database Agent started successfully")

    async def cleanup(self) -> None:
        """Cleanup Database Agent resources."""
        pass

    async def run(self, input_data: Any) -> str:
        """
        Run the Database Agent with input data and retry logic.

        Args:
            input_data: Input data for the agent

        Returns:
            Agent response
        """
        try:
            self.logger.info("Running Database Agent", input_data=str(input_data))

            if not isinstance(input_data, str):
                input_data = str(input_data)

            # Try up to 5 times with schema inspection on failures
            max_retries = 5
            last_error = None

            for attempt in range(max_retries):
                try:
                    self.logger.info(f"Attempt {attempt + 1}/{max_retries} for query: {input_data}")

                    # On retry attempts, include schema inspection
                    if attempt > 0:
                        schema_info = await self._inspect_database_schema()
                        self.logger.info(f"Schema inspection for retry: {schema_info[:500]}...")

                    # Analyze the request and generate SQL
                    sql_query = await self._generate_sql(input_data)

                    if not sql_query:
                        if attempt == max_retries - 1:
                            return f"Could not generate SQL query for: {input_data}"
                        continue

                    # Execute the query
                    result = await self._execute_sql(sql_query)

                    # Format the response
                    return await self._format_response(input_data, sql_query, result)

                except Exception as e:
                    last_error = str(e)
                    self.logger.warning(f"Attempt {attempt + 1} failed: {last_error}")

                    # If this is not the last attempt, continue to try again
                    if attempt < max_retries - 1:
                        continue
                    else:
                        # Last attempt failed, return error
                        return f"Query failed after {max_retries} attempts. Last error: {last_error}"

        except Exception as e:
            self.logger.error("Failed to run Database Agent", error=str(e))
            return f"An error occurred while processing your database request: {str(e)}"

    async def query_database(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results.

        Args:
            sql_query: The SQL query to execute

        Returns:
            Query results
        """
        try:
            self.logger.info(f"Executing SQL query: {sql_query}")
            result = await self.prisma_service.execute_raw_query(sql_query)
            return result or []
        except Exception as e:
            self.logger.error(f"Failed to execute query: {str(e)}")
            return []

    async def _get_table_schema(self, table_name: str) -> str:
        """Get the schema information for a specific table."""
        try:
            # Query to get column information
            schema_query = f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
            """

            result = await self.prisma_service.execute_raw_query(schema_query)

            if not result:
                return f"No schema information found for table '{table_name}'"

            schema_info = f"TABLE: {table_name}\nCOLUMNS:\n"
            for row in result:
                nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
                schema_info += f"- {row['column_name']} ({row['data_type']}, {nullable})\n"

            return schema_info

        except Exception as e:
            self.logger.error(f"Failed to get schema for table {table_name}: {str(e)}")
            return f"Error getting schema for table '{table_name}': {str(e)}"

    async def _inspect_database_schema(self) -> str:
        """Inspect the database schema and return information about all tables."""
        try:
            # Get all table names
            tables_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """

            tables_result = await self.prisma_service.execute_raw_query(tables_query)

            if not tables_result:
                return "No tables found in database"

            schema_info = "DATABASE SCHEMA INSPECTION:\n\n"

            for table_row in tables_result:
                table_name = table_row['table_name']
                table_schema = await self._get_table_schema(table_name)
                schema_info += table_schema + "\n"

            return schema_info

        except Exception as e:
            self.logger.error(f"Failed to inspect database schema: {str(e)}")
            return f"Error inspecting database schema: {str(e)}"

    async def _generate_sql(self, request: str) -> Optional[str]:
        """Generate SQL query from natural language request."""
        try:
            # Get schema information for better SQL generation
            schema_info = await self._inspect_database_schema()

            prompt = (
                "Generate a PostgreSQL query for this request. Return only the SQL query, no explanations.\n\n"
                f"Request: {request}\n\n"
                f"DATABASE SCHEMA:\n{schema_info}\n\n"
                "CRITICAL RULES - FOLLOW THESE EXACTLY:\n"
                "1. ALWAYS use double quotes around camelCase column names: \"medicineId\", \"productName\", \"expiryDate\", \"firstName\", \"lastName\", etc.\n"
                "2. NEVER use unquoted camelCase - PostgreSQL will treat them as lowercase and fail\n"
                "3. Use lowercase WITHOUT quotes for: id, quantity, status, gender, phone, email, address, notes, reason, supplier\n"
                "4. For JOINs, always use the correct foreign key relationships\n"
                "5. Use table aliases (m, i, p, d, etc.) for readability\n\n"
                "EXAMPLES OF CORRECT QUERIES:\n"
                "SELECT m.\"productName\", i.\"expiryDate\", i.quantity FROM medicines m JOIN inventory i ON m.id = i.\"medicineId\" WHERE i.\"expiryDate\" < NOW()\n"
                "SELECT p.\"firstName\", p.\"lastName\", COUNT(pr.id) as prescription_count FROM patients p LEFT JOIN prescriptions pr ON p.id = pr.\"patientId\" GROUP BY p.id, p.\"firstName\", p.\"lastName\"\n"
                "SELECT d.\"firstName\", d.\"lastName\", d.specialization FROM doctors d\n\n"
                "EXAMPLES OF INCORRECT QUERIES (will fail):\n"
                "SELECT m.productName FROM medicines m  (missing quotes on productName)\n"
                "SELECT p.name FROM patients p  (wrong column name, should be firstName/lastName)\n"
                "SELECT m.id, medicineId FROM inventory i  (missing table alias and quotes)\n"
            )

            response = self.llm.invoke([HumanMessage(content=prompt)])
            sql_query = response.content.strip()

            # Clean up the SQL
            if sql_query.startswith("```sql"):
                sql_query = sql_query[6:]
            if sql_query.endswith("```"):
                sql_query = sql_query[:-3]
            sql_query = sql_query.strip()

            # Post-process SQL to ensure camelCase columns are quoted
            sql_query = self._fix_column_quoting(sql_query)

            # Basic validation
            if not sql_query.upper().startswith(("SELECT", "INSERT", "UPDATE", "DELETE")):
                self.logger.warning(f"Generated invalid SQL: {sql_query}")
                return None

            return sql_query

        except Exception as e:
            self.logger.error(f"Failed to generate SQL: {str(e)}")
            return None

    def _fix_column_quoting(self, sql_query: str) -> str:
        """Fix SQL query to ensure camelCase columns are properly quoted."""
        import re

        # Define the camelCase columns that need quoting
        camelcase_columns = [
            'medicineId', 'subCategory', 'productName', 'saltComposition', 'productPrice',
            'productManufactured', 'medicineDesc', 'sideEffects', 'drugInteractions',
            'batchNumber', 'expiryDate', 'unitPrice', 'inventoryId', 'transactionType',
            'transactionDate', 'performedBy', 'currentQuantity', 'alertSent', 'alertDate',
            'patientId', 'doctorId', 'prescriptionDate', 'prescriptionId', 'firstName',
            'lastName', 'dateOfBirth', 'emergencyContact', 'licenseNumber', 'yearsOfExperience'
        ]

        # Create a pattern to match these columns when they're not quoted
        # This matches word boundaries and the column name not preceded by a quote
        for column in camelcase_columns:
            # Pattern to match column name not already quoted
            pattern = r'(?<!")(\b' + re.escape(column) + r'\b)(?!")'
            sql_query = re.sub(pattern, r'"\1"', sql_query)

        return sql_query

    async def _execute_sql(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute the SQL query."""
        return await self.query_database(sql_query)

    async def _format_response(self, original_request: str, sql_query: str, results: List[Dict[str, Any]]) -> str:
        """Format query results into natural language response."""
        if not results:
            return f"No results found for your request: {original_request}"

        try:
            # Use LLM to format the results
            format_prompt = (
                "Format these database query results into a natural language response for a medical AI assistant.\n\n"
                f"Original request: {original_request}\n"
                f"SQL query executed: {sql_query}\n"
                f"Results: {results[:10]}\n"  # Limit to first 10 results
                "\nProvide a clear, concise, and user-friendly summary of the results. "
                "Focus on the key information and present it in a natural way that would be helpful for medical professionals."
            )

            response = self.llm.invoke([HumanMessage(content=format_prompt)])

            if response and response.content:
                formatted_response = response.content.strip()
                # Ensure we don't return empty or invalid responses
                if len(formatted_response) > 10:  # Basic check for meaningful response
                    return formatted_response

            # Fallback formatting if LLM fails
            return self._fallback_format_response(original_request, results)

        except Exception as e:
            self.logger.error(f"Failed to format response with LLM: {str(e)}")
            # Fallback to basic formatting
            return self._fallback_format_response(original_request, results)

    def _fallback_format_response(self, original_request: str, results: List[Dict[str, Any]]) -> str:
        """Fallback formatting when LLM fails."""
        try:
            num_results = len(results)

            if num_results == 1:
                # Single result - provide detailed info
                result = results[0]
                if 'productName' in result:
                    # Medicine result
                    response = f"Found medicine: {result['productName']}\n"
                    if 'subCategory' in result:
                        response += f"Category: {result['subCategory']}\n"
                    if 'productPrice' in result:
                        response += f"Price: ${result['productPrice']}\n"
                    if 'medicineDesc' in result:
                        response += f"Description: {result['medicineDesc']}\n"
                    if 'sideEffects' in result:
                        response += f"Side effects: {result['sideEffects']}\n"
                    return response.strip()
                else:
                    # Generic single result
                    return f"Found result: {result}"

            else:
                # Multiple results - provide summary
                if 'productName' in results[0]:
                    # Medicine results
                    medicine_names = [r.get('productName', 'Unknown') for r in results[:5]]
                    response = f"Found {num_results} medicines in the database"
                    if num_results <= 5:
                        response += f": {', '.join(medicine_names)}"
                    else:
                        response += f". First few: {', '.join(medicine_names[:3])}..."
                    return response
                else:
                    # Generic multiple results
                    return f"Found {num_results} results for your query."

        except Exception as e:
            self.logger.error(f"Failed to format response with fallback: {str(e)}")
            return f"Found {len(results)} results for your request, but couldn't format them properly."
