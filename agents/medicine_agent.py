"""
Medicine Agent implementation.
"""

import asyncio
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .base_agent import BaseAgent


class MedicineAgent(BaseAgent):
    """
    Medicine Agent that tracks medicine inflow, outflow, expiry dates, and usage.
    Delegates database queries to the DatabaseAgent.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        database_agent: Optional["DatabaseAgent"] = None,
    ):
        super().__init__("medicine_agent", config)
        self.database_agent = database_agent
        self.llm = ChatGoogleGenerativeAI(
            model=config.get("model_name", "gemini-1.5-flash"),
            temperature=config.get("temperature", 0.1),
            api_key=config.get("gemini_api_key"),
        )

    async def initialize(self) -> None:
        """Initialize the Medicine Agent."""
        pass

    async def start(self) -> None:
        """Start the Medicine Agent."""
        self.logger.info("Starting Medicine Agent")
        self.is_running = True
        self.logger.info("Medicine Agent started successfully")

    async def cleanup(self) -> None:
        """Cleanup Medicine Agent resources."""
        pass

    async def run(self, input_data: Any) -> str:
        """
        Run the Medicine Agent with input data.

        Args:
            input_data: Input data for the agent

        Returns:
            Agent response
        """
        try:
            self.logger.info("Running Medicine Agent", input_data=str(input_data))

            if not isinstance(input_data, str):
                input_data = str(input_data)

            # Classify the medicine operation
            operation = await self._classify_operation(input_data)

            if operation == "inflow":
                return await self._handle_inflow(input_data)
            elif operation == "outflow":
                return await self._handle_outflow(input_data)
            elif operation == "expiry":
                return await self._handle_expiry_check(input_data)
            elif operation == "usage":
                return await self._handle_usage_tracking(input_data)
            elif operation == "query":
                return await self._handle_query(input_data)
            else:
                return f"I understand you're asking about medicine operations: {input_data}. Please specify if you want to track inflow, outflow, check expiry, or query usage."

        except Exception as e:
            self.logger.error("Failed to run Medicine Agent", error=str(e))
            return f"An error occurred while processing your medicine request: {str(e)}"

    async def _classify_operation(self, query: str) -> str:
        """Classify the medicine operation using LLM."""
        prompt = (
            "Classify the following medicine-related request into one of: inflow, outflow, expiry, usage, query. "
            "Return ONLY the classification word, no explanation.\n\n"
            f"Request: {query}\n"
            "- inflow: adding new medicine stock, receiving deliveries, restocking inventory\n"
            "- outflow: dispensing medicine, selling medicine, removing from inventory\n"
            "- expiry: checking expiry dates, expiration alerts, medicines about to expire\n"
            "- usage: tracking medicine usage patterns, consumption statistics, prescription frequency\n"
            "- query: asking for information, listing data, showing inventory, general questions about medicines"
        )

        response = self.llm.invoke([HumanMessage(content=prompt)])
        classification = response.content.strip().lower()

        valid_ops = ["inflow", "outflow", "expiry", "usage", "query"]
        if classification in valid_ops:
            return classification
        else:
            return "query"

    async def _handle_inflow(self, query: str) -> str:
        """Handle medicine inflow operations."""
        # For now, return a placeholder response
        # In a real implementation, this would parse the query and create transactions
        return f"Medicine inflow operation detected: {query}. This would add new stock to inventory."

    async def _handle_outflow(self, query: str) -> str:
        """Handle medicine outflow operations."""
        return f"Medicine outflow operation detected: {query}. This would record medicine dispensing."

    async def _handle_expiry_check(self, query: str) -> str:
        """Handle expiry date monitoring."""
        if not self.database_agent:
            return "Database agent not available for expiry check."

        # Query for medicines expiring soon
        db_query = "SELECT m.productName, i.expiryDate, i.quantity FROM medicines m JOIN inventory i ON m.id = i.medicineId WHERE i.expiryDate < NOW() + INTERVAL '30 days' ORDER BY i.expiryDate"
        result = await self.database_agent.query_database(db_query)

        if not result:
            return "No medicines expiring within the next 30 days."

        response = "Medicines expiring soon:\n"
        for row in result[:10]:  # Limit to 10 results
            response += f"- {row['productName']}: expires {row['expiryDate']}, quantity: {row['quantity']}\n"

        return response

    async def _handle_usage_tracking(self, query: str) -> str:
        """Handle usage tracking."""
        if not self.database_agent:
            return "Database agent not available for usage tracking."

        # Query for medicine usage patterns
        db_query = "SELECT m.productName, COUNT(pi.id) as usage_count FROM medicines m JOIN prescription_items pi ON m.id = pi.medicineId GROUP BY m.productName ORDER BY usage_count DESC LIMIT 10"
        result = await self.database_agent.query_database(db_query)

        if not result:
            return "No usage data available."

        response = "Top 10 medicines by usage:\n"
        for row in result:
            response += f"- {row['productName']}: {row['usage_count']} prescriptions\n"

        return response

    async def _handle_query(self, query: str) -> str:
        """Handle general medicine queries with multi-layered search and summarization."""
        if not self.database_agent:
            return "Database agent not available for queries."

        # Layer 1: Try database agent's SQL generation
        db_result = await self.database_agent.run(query)
        db_success = not ("No results found" in db_result or "no results" in db_result.lower())

        # Layer 2: Try flexible keyword search
        keyword_results = await self._perform_keyword_search(query)

        # Layer 3: Combine and summarize results
        return await self._combine_and_summarize_results(query, db_result, db_success, keyword_results)

    def _extract_medicine_keywords(self, query: str) -> List[str]:
        """Extract relevant keywords from medicine queries."""
        # Common medicine-related keywords to filter out
        stop_words = {'medicines', 'medicine', 'drugs', 'drug', 'show', 'me', 'available', 'for', 'what', 'are', 'the', 'list', 'find', 'search', 'get', 'display', 'give'}

        # Split query into words and filter
        words = query.lower().split()
        keywords = [word for word in words if word not in stop_words and len(word) > 2]

        return keywords

    async def _perform_keyword_search(self, query: str) -> List[Dict[str, Any]]:
        """Perform flexible keyword search across medicine data."""
        keywords = self._extract_medicine_keywords(query)

        if not keywords:
            return []

        # Search in medicine names, descriptions, and categories
        search_conditions = []
        for keyword in keywords:
            search_conditions.extend([
                f"\"productName\" ILIKE '%{keyword}%'",
                f"\"subCategory\" ILIKE '%{keyword}%'",
                f"\"medicineDesc\" ILIKE '%{keyword}%'"
            ])

        if search_conditions:
            where_clause = " OR ".join(search_conditions)
            search_query = f"SELECT \"productName\", \"subCategory\", \"medicineDesc\" FROM medicines WHERE {where_clause} LIMIT 15"
            return await self.database_agent.query_database(search_query)

        return []

    async def _combine_and_summarize_results(self, query: str, db_result: str, db_success: bool, keyword_results: List[Dict[str, Any]]) -> str:
        """Combine results from different layers and provide a summarized response."""
        try:
            # Collect all medicines found
            all_medicines = []
            medicine_details = {}

            # Process database agent results
            if db_success and "Found" in db_result:
                # Extract medicine names from the formatted response
                lines = db_result.split('\n')
                for line in lines:
                    if line.strip().startswith('•') or line.strip().startswith('-'):
                        medicine_name = line.strip().lstrip('•- ').split('(')[0].strip()
                        if medicine_name and medicine_name != "Unknown":
                            all_medicines.append(medicine_name)

            # Process keyword search results
            for row in keyword_results:
                medicine_name = row.get('productName', '')
                if medicine_name and medicine_name not in all_medicines:
                    all_medicines.append(medicine_name)
                    medicine_details[medicine_name] = {
                        'category': row.get('subCategory', ''),
                        'description': row.get('medicineDesc', '')[:150] + '...' if row.get('medicineDesc', '') else ''
                    }

            # If we have results, create a summarized response
            if all_medicines:
                # Group by category for better organization
                category_groups = {}
                for medicine in all_medicines[:10]:  # Limit to top 10
                    category = medicine_details.get(medicine, {}).get('category', 'General Medicines')
                    if category not in category_groups:
                        category_groups[category] = []
                    category_groups[category].append(medicine)

                # Create summarized response
                response = f"📋 **Medicine Search Results for '{query}'**\n\n"

                for category, medicines in category_groups.items():
                    response += f"**{category}:**\n"
                    for medicine in medicines[:5]:  # Limit per category
                        response += f"• {medicine}\n"
                    if len(medicines) > 5:
                        response += f"• ... and {len(medicines) - 5} more\n"
                    response += "\n"

                total_found = len(all_medicines)
                if total_found > 10:
                    response += f"💡 Found {total_found} medicines total. Showing top results by category.\n"

                return response

            # If no results found, provide helpful fallback
            fallback_query = "SELECT \"subCategory\", COUNT(*) as count FROM medicines GROUP BY \"subCategory\" ORDER BY count DESC LIMIT 5"
            category_stats = await self.database_agent.query_database(fallback_query)

            if category_stats:
                response = f"I couldn't find specific medicines for '{query}', but here are the main medicine categories available:\n\n"
                for row in category_stats:
                    response += f"• {row['subCategory']}: {row['count']} medicines\n"
                response += f"\n💡 Try searching for specific categories or medicine names."
                return response

            return f"No medicines found matching '{query}' in the database."

        except Exception as e:
            self.logger.error(f"Error combining results: {str(e)}")
            # Fallback to original db_result if combination fails
            return db_result if db_success else f"Error processing query '{query}': {str(e)}"
