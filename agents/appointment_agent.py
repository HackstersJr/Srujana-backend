"""
Appointment Agent implementation.
"""

import asyncio
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .base_agent import BaseAgent


class AppointmentAgent(BaseAgent):
    """
    Appointment Agent that handles scheduling, booking, rescheduling, and managing medical appointments.
    Delegates database queries to the DatabaseAgent.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        database_agent: Optional["DatabaseAgent"] = None,
    ):
        super().__init__("appointment_agent", config)
        self.database_agent = database_agent
        self.llm = ChatGoogleGenerativeAI(
            model=config.get("model_name", "gemini-1.5-flash"),
            temperature=config.get("temperature", 0.1),
            api_key=config.get("gemini_api_key"),
        )

    async def initialize(self) -> None:
        """Initialize the Appointment Agent."""
        pass

    async def start(self) -> None:
        """Start the Appointment Agent."""
        self.logger.info("Starting Appointment Agent")
        self.is_running = True
        self.logger.info("Appointment Agent started successfully")

    async def cleanup(self) -> None:
        """Cleanup Appointment Agent resources."""
        pass

    async def run(self, input_data: Any) -> str:
        """
        Run the Appointment Agent with input data.

        Args:
            input_data: Input data for the agent

        Returns:
            Agent response
        """
        try:
            self.logger.info("Running Appointment Agent", input_data=str(input_data))

            if not isinstance(input_data, str):
                input_data = str(input_data)

            # Classify the appointment operation
            operation = await self._classify_operation(input_data)

            if operation == "schedule":
                return await self._handle_scheduling(input_data)
            elif operation == "reschedule":
                return await self._handle_rescheduling(input_data)
            elif operation == "cancel":
                return await self._handle_cancellation(input_data)
            elif operation == "view":
                return await self._handle_appointment_view(input_data)
            elif operation == "query":
                return await self._handle_query(input_data)
            else:
                return f"I understand you're asking about appointments: {input_data}. Please specify if you want to schedule, reschedule, cancel, or view appointments."

        except Exception as e:
            self.logger.error("Failed to run Appointment Agent", error=str(e))
            return f"An error occurred while processing your appointment request: {str(e)}"

    async def _classify_operation(self, query: str) -> str:
        """Classify the appointment operation using LLM."""
        prompt = (
            "Classify the following appointment request into one of: schedule, reschedule, cancel, view, query. "
            "Return ONLY the classification word, no explanation.\n\n"
            f"Request: {query}\n"
            "- schedule: booking new appointments, making reservations\n"
            "- reschedule: changing appointment times, moving appointments\n"
            "- cancel: canceling appointments, removing bookings\n"
            "- view: checking existing appointments, viewing schedules\n"
            "- query: general appointment information, availability, statistics"
        )

        response = self.llm.invoke([HumanMessage(content=prompt)])
        classification = response.content.strip().lower()

        valid_ops = ["schedule", "reschedule", "cancel", "view", "query"]
        if classification in valid_ops:
            return classification
        else:
            return "query"

    async def _handle_scheduling(self, query: str) -> str:
        """Handle appointment scheduling."""
        return f"Appointment scheduling operation detected: {query}. This would create a new appointment booking."

    async def _handle_rescheduling(self, query: str) -> str:
        """Handle appointment rescheduling."""
        return f"Appointment rescheduling operation detected: {query}. This would modify an existing appointment time."

    async def _handle_cancellation(self, query: str) -> str:
        """Handle appointment cancellation."""
        return f"Appointment cancellation operation detected: {query}. This would cancel an existing appointment."

    async def _handle_appointment_view(self, query: str) -> str:
        """Handle appointment viewing and schedule checking."""
        if not self.database_agent:
            return "Database agent not available for appointment viewing."

        # Query for appointment information (this would need an appointments table)
        # For now, we'll show prescription data as a proxy
        db_query = "SELECT p.\"firstName\", p.\"lastName\", COUNT(pr.id) as appointments FROM patients p LEFT JOIN prescriptions pr ON p.id = pr.\"patientId\" GROUP BY p.id, p.\"firstName\", p.\"lastName\" ORDER BY appointments DESC LIMIT 10"
        result = await self.database_agent.query_database(db_query)

        if not result:
            return "No appointment data available."

        response = "Patient appointment summary (based on prescriptions):\n"
        for row in result:
            response += f"- {row['firstName']} {row['lastName']}: {row['appointments']} visits\n"

        response += "\nNote: Full appointment scheduling system needs to be implemented."
        return response

    async def _handle_query(self, query: str) -> str:
        """Handle general appointment queries by delegating to database agent."""
        if not self.database_agent:
            return "Database agent not available for queries."

        # Delegate to database agent with the query
        return await self.database_agent.run(query)
