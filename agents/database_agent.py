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
        Run the Database Agent with input data.

        Args:
            input_data: Input data for the agent

        Returns:
            Agent response
        """
        try:
            self.logger.info("Running Database Agent", input_data=str(input_data))

            if not isinstance(input_data, str):
                input_data = str(input_data)

            # Analyze the request and generate SQL
            sql_query = await self._generate_sql(input_data)

            if not sql_query:
                return f"Could not generate SQL query for: {input_data}"

            # Execute the query
            result = await self._execute_sql(sql_query)

            # Format the response
            return await self._format_response(input_data, sql_query, result)

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

    async def _generate_sql(self, request: str) -> Optional[str]:
        """Generate SQL query from natural language request."""
        prompt = (
            "Generate a PostgreSQL query for this request. Return only the SQL query, no explanations.\n\n"
            f"Request: {request}\n"
            "Available tables and columns (CRITICAL: Always use EXACT column names with quotes for camelCase):\n"
            "- medicines: id, \"subCategory\", \"productName\", \"saltComposition\", \"productPrice\", \"productManufactured\", \"medicineDesc\", \"sideEffects\", \"drugInteractions\"\n"
            "- inventory: id, \"medicineId\", \"batchNumber\", \"expiryDate\", quantity, \"unitPrice\", supplier\n"
            "- transactions: id, \"inventoryId\", \"transactionType\", quantity, \"transactionDate\", reason, \"performedBy\"\n"
            "- expiry_tracking: id, \"inventoryId\", \"medicineId\", \"batchNumber\", \"expiryDate\", \"currentQuantity\", status, \"alertSent\", \"alertDate\"\n"
            "- prescriptions: id, \"patientId\", \"doctorId\", \"prescriptionDate\", notes\n"
            "- prescription_items: id, \"prescriptionId\", \"medicineId\", dosage, frequency, duration, instructions\n"
            "- patients: id, \"firstName\", \"lastName\", \"dateOfBirth\", gender, phone, email, address, \"emergencyContact\"\n"
            "- doctors: id, \"firstName\", \"lastName\", specialization, \"licenseNumber\", phone, email, department, \"yearsOfExperience\"\n"
            "\nMANDATORY RULES:\n"
            "1. ALWAYS use double quotes around camelCase column names (e.g., \"medicineId\", \"productName\", \"expiryDate\")\n"
            "2. NEVER use unquoted camelCase column names - this will cause PostgreSQL errors\n"
            "3. Use lowercase column names WITHOUT quotes only for simple names like 'id', 'quantity', 'status'\n"
            "4. Always use proper JOIN syntax with quoted column names in ON clauses\n"
            "5. PostgreSQL requires quoted identifiers for columns with mixed case\n"
            "\nExample of CORRECT syntax:\n"
            "SELECT m.\"productName\", i.\"expiryDate\" FROM medicines m JOIN inventory i ON m.id = i.\"medicineId\"\n"
            "\nExample of INCORRECT syntax (will fail):\n"
            "SELECT m.productName, i.expiryDate FROM medicines m JOIN inventory i ON m.id = i.medicineId"
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
