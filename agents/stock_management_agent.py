"""
Stock Management Agent implementation.
"""

import asyncio
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .base_agent import BaseAgent


class StockManagementAgent(BaseAgent):
    """
    Stock Management Agent that handles inventory tracking, stock levels, reordering, and supply chain management.
    Delegates database queries to the DatabaseAgent.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        database_agent: Optional["DatabaseAgent"] = None,
    ):
        super().__init__("stock_management_agent", config)
        self.database_agent = database_agent
        self.llm = ChatGoogleGenerativeAI(
            model=config.get("model_name", "gemini-1.5-flash"),
            temperature=config.get("temperature", 0.1),
            api_key=config.get("gemini_api_key"),
        )

    async def initialize(self) -> None:
        """Initialize the Stock Management Agent."""
        pass

    async def start(self) -> None:
        """Start the Stock Management Agent."""
        self.logger.info("Starting Stock Management Agent")
        self.is_running = True
        self.logger.info("Stock Management Agent started successfully")

    async def cleanup(self) -> None:
        """Cleanup Stock Management Agent resources."""
        pass

    async def run(self, input_data: Any) -> str:
        """
        Run the Stock Management Agent with input data.

        Args:
            input_data: Input data for the agent

        Returns:
            Agent response
        """
        try:
            self.logger.info("Running Stock Management Agent", input_data=str(input_data))

            if not isinstance(input_data, str):
                input_data = str(input_data)

            # Classify the stock management operation
            operation = await self._classify_operation(input_data)

            if operation == "inventory":
                return await self._handle_inventory_check(input_data)
            elif operation == "reorder":
                return await self._handle_reorder_alerts(input_data)
            elif operation == "suppliers":
                return await self._handle_supplier_management(input_data)
            elif operation == "transactions":
                return await self._handle_transaction_tracking(input_data)
            elif operation == "query":
                return await self._handle_query(input_data)
            else:
                return f"I understand you're asking about stock management: {input_data}. Please specify if you want to check inventory, reorder alerts, manage suppliers, or track transactions."

        except Exception as e:
            self.logger.error("Failed to run Stock Management Agent", error=str(e))
            return f"An error occurred while processing your stock management request: {str(e)}"

    async def _classify_operation(self, query: str) -> str:
        """Classify the stock management operation using LLM."""
        prompt = (
            "Classify the following stock management request into one of: inventory, reorder, suppliers, transactions, query. "
            "Return ONLY the classification word, no explanation.\n\n"
            f"Request: {query}\n"
            "- inventory: checking stock levels, current inventory, stock counts\n"
            "- reorder: low stock alerts, reorder points, automatic reordering\n"
            "- suppliers: supplier information, vendor management, procurement\n"
            "- transactions: stock movements, inflow/outflow tracking, transaction history\n"
            "- query: general stock information, reports, analytics"
        )

        response = self.llm.invoke([HumanMessage(content=prompt)])
        classification = response.content.strip().lower()

        valid_ops = ["inventory", "reorder", "suppliers", "transactions", "query"]
        if classification in valid_ops:
            return classification
        else:
            return "query"

    async def _handle_inventory_check(self, query: str) -> str:
        """Handle inventory level checking."""
        if not self.database_agent:
            return "Database agent not available for inventory check."

        # Query for current inventory levels
        db_query = "SELECT m.\"productName\", i.quantity, i.\"unitPrice\", i.\"batchNumber\" FROM medicines m JOIN inventory i ON m.id = i.\"medicineId\" ORDER BY i.quantity ASC LIMIT 20"
        result = await self.database_agent.query_database(db_query)

        if not result:
            return "No inventory data available."

        response = "Current inventory levels (lowest first):\n"
        for row in result:
            status = "LOW STOCK" if row['quantity'] < 10 else "NORMAL"
            response += f"- {row['productName']}: {row['quantity']} units (${row['unitPrice']}) - {status}\n"

        return response

    async def _handle_reorder_alerts(self, query: str) -> str:
        """Handle reorder alerts and low stock notifications."""
        if not self.database_agent:
            return "Database agent not available for reorder alerts."

        # Query for items that need reordering (low stock)
        db_query = "SELECT m.\"productName\", i.quantity, i.\"batchNumber\" FROM medicines m JOIN inventory i ON m.id = i.\"medicineId\" WHERE i.quantity < 10 ORDER BY i.quantity ASC"
        result = await self.database_agent.query_database(db_query)

        if not result:
            return "All items are sufficiently stocked. No reorder alerts."

        response = "⚠️ REORDER ALERTS - Items with low stock:\n"
        for row in result:
            response += f"- {row['productName']}: Only {row['quantity']} units remaining (Batch: {row['batchNumber']})\n"

        response += "\nRecommendation: Reorder these items immediately."
        return response

    async def _handle_supplier_management(self, query: str) -> str:
        """Handle supplier and vendor management."""
        if not self.database_agent:
            return "Database agent not available for supplier management."

        # Query for supplier information from inventory
        db_query = "SELECT DISTINCT i.supplier, COUNT(*) as items_count FROM inventory i WHERE i.supplier IS NOT NULL GROUP BY i.supplier ORDER BY items_count DESC"
        result = await self.database_agent.query_database(db_query)

        if not result:
            return "No supplier information available."

        response = "Supplier management overview:\n"
        for row in result:
            response += f"- {row['supplier']}: {row['items_count']} items supplied\n"

        return response

    async def _handle_transaction_tracking(self, query: str) -> str:
        """Handle transaction tracking and stock movements."""
        if not self.database_agent:
            return "Database agent not available for transaction tracking."

        # Query for recent transactions
        db_query = "SELECT t.\"transactionType\", t.quantity, t.\"transactionDate\", m.\"productName\" FROM transactions t JOIN inventory i ON t.\"inventoryId\" = i.id JOIN medicines m ON i.\"medicineId\" = m.id ORDER BY t.\"transactionDate\" DESC LIMIT 10"
        result = await self.database_agent.query_database(db_query)

        if not result:
            return "No transaction data available."

        response = "Recent stock transactions:\n"
        for row in result:
            response += f"- {row['transactionType']}: {row['quantity']} units of {row['productName']} on {row['transactionDate']}\n"

        return response

    async def _handle_query(self, query: str) -> str:
        """Handle general stock queries by delegating to database agent."""
        if not self.database_agent:
            return "Database agent not available for queries."

        # Delegate to database agent with the query
        return await self.database_agent.run(query)
