"""
Patient Monitoring Agent implementation.
"""

import asyncio
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .base_agent import BaseAgent


class PatientMonitoringAgent(BaseAgent):
    """
    Patient Monitoring Agent that tracks patient vitals, health metrics, and medical history.
    Delegates database queries to the DatabaseAgent.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        database_agent: Optional["DatabaseAgent"] = None,
    ):
        super().__init__("patient_monitoring_agent", config)
        self.database_agent = database_agent
        self.llm = ChatGoogleGenerativeAI(
            model=config.get("model_name", "gemini-1.5-flash"),
            temperature=config.get("temperature", 0.1),
            api_key=config.get("gemini_api_key"),
        )

    async def initialize(self) -> None:
        """Initialize the Patient Monitoring Agent."""
        pass

    async def start(self) -> None:
        """Start the Patient Monitoring Agent."""
        self.logger.info("Starting Patient Monitoring Agent")
        self.is_running = True
        self.logger.info("Patient Monitoring Agent started successfully")

    async def cleanup(self) -> None:
        """Cleanup Patient Monitoring Agent resources."""
        pass

    async def run(self, input_data: Any) -> str:
        """
        Run the Patient Monitoring Agent with input data.

        Args:
            input_data: Input data for the agent

        Returns:
            Agent response
        """
        try:
            self.logger.info("Running Patient Monitoring Agent", input_data=str(input_data))

            if not isinstance(input_data, str):
                input_data = str(input_data)

            # Classify the patient monitoring operation
            operation = await self._classify_operation(input_data)

            if operation == "vitals":
                return await self._handle_vitals_check(input_data)
            elif operation == "history":
                return await self._handle_medical_history(input_data)
            elif operation == "alerts":
                return await self._handle_health_alerts(input_data)
            elif operation == "monitoring":
                return await self._handle_continuous_monitoring(input_data)
            elif operation == "query":
                return await self._handle_query(input_data)
            else:
                return f"I understand you're asking about patient monitoring: {input_data}. Please specify if you want to check vitals, view medical history, monitor alerts, or query patient data."

        except Exception as e:
            self.logger.error("Failed to run Patient Monitoring Agent", error=str(e))
            return f"An error occurred while processing your patient monitoring request: {str(e)}"

    async def _classify_operation(self, query: str) -> str:
        """Classify the patient monitoring operation using LLM."""
        prompt = (
            "Classify the following patient monitoring request into one of: vitals, history, alerts, monitoring, query. "
            "Return ONLY the classification word, no explanation.\n\n"
            f"Request: {query}\n"
            "- vitals: checking blood pressure, heart rate, temperature, oxygen levels\n"
            "- history: viewing medical records, past diagnoses, treatment history\n"
            "- alerts: critical health alerts, abnormal readings, emergency notifications\n"
            "- monitoring: continuous health monitoring, trend analysis, preventive care\n"
            "- query: general patient information, demographics, basic health status"
        )

        response = self.llm.invoke([HumanMessage(content=prompt)])
        classification = response.content.strip().lower()

        valid_ops = ["vitals", "history", "alerts", "monitoring", "query"]
        if classification in valid_ops:
            return classification
        else:
            return "query"

    async def _handle_vitals_check(self, query: str) -> str:
        """Handle patient vitals checking."""
        try:
            patient_id = self._extract_patient_id(query)

            if not self.database_agent:
                return "Database agent not available for vitals check."

            if patient_id:
                # Query specific patient vitals/history
                patient_query = f"SELECT * FROM patients WHERE id = '{patient_id}'"
                patient_data = await self.database_agent.query_database(patient_query)

                medical_query = f"SELECT * FROM medical_records WHERE \"patientId\" = '{patient_id}' AND \"recordType\" = 'vitals' ORDER BY \"recordDate\" DESC LIMIT 5"
                vitals_data = await self.database_agent.query_database(medical_query)

                if patient_data:
                    patient = patient_data[0]
                    response = f"🏥 Patient Vitals for {patient.get('firstName', 'N/A')} {patient.get('lastName', 'N/A')} (ID: {patient_id})\n\n"
                else:
                    response = f"🏥 Patient Vitals for ID: {patient_id}\n\n"

                if vitals_data:
                    response += f"📊 Recent Vitals ({len(vitals_data)} records):\n"
                    for vital in vitals_data:
                        response += f"   • {vital.get('recordDate', 'N/A')}: {vital.get('description', 'N/A')}\n"
                    response += "\n"
                else:
                    response += f"📊 No recent vitals records found for this patient.\n\n"

                response += "💡 Note: Full vitals tracking system integration needed for comprehensive monitoring."
                return response
            else:
                # General vitals overview
                db_query = "SELECT p.\"firstName\", p.\"lastName\", p.id, COUNT(mr.id) as records FROM patients p LEFT JOIN medical_records mr ON p.id = mr.\"patientId\" AND mr.\"recordType\" = 'vitals' GROUP BY p.id, p.\"firstName\", p.\"lastName\" ORDER BY records DESC LIMIT 10"
                result = await self.database_agent.query_database(db_query)

                if not result:
                    return "No patient vitals data available."

                response = "🏥 Patient Vitals Overview:\n"
                for row in result:
                    response += f"   • {row['firstName']} {row['lastName']} (ID: {row['id']}): {row['records']} vitals records\n"

                response += "\n💡 Specify a patient ID for detailed vitals information."
                return response

        except Exception as e:
            self.logger.error(f"Error in vitals check: {str(e)}")
            return f"Error retrieving patient vitals: {str(e)}"

    async def _handle_medical_history(self, query: str) -> str:
        """Handle medical history queries."""
        try:
            patient_id = self._extract_patient_id(query)

            if not self.database_agent:
                return "Database agent not available for medical history."

            if patient_id:
                # Query specific patient medical history
                patient_query = f"SELECT * FROM patients WHERE id = '{patient_id}'"
                patient_data = await self.database_agent.query_database(patient_query)

                history_query = f"SELECT * FROM medical_records WHERE \"patientId\" = '{patient_id}' ORDER BY \"recordDate\" DESC LIMIT 10"
                history_data = await self.database_agent.query_database(history_query)

                prescription_query = f"SELECT COUNT(pi.id) as prescriptions FROM prescriptions pr LEFT JOIN prescription_items pi ON pr.id = pi.\"prescriptionId\" WHERE pr.\"patientId\" = '{patient_id}'"
                prescription_data = await self.database_agent.query_database(prescription_query)

                if patient_data:
                    patient = patient_data[0]
                    response = f"📚 Medical History for {patient.get('firstName', 'N/A')} {patient.get('lastName', 'N/A')} (ID: {patient_id})\n\n"
                    response += f"📋 Patient Info: {patient.get('medicalHistory', 'No history recorded')}\n"
                    response += f"💊 Allergies: {patient.get('allergies', 'None listed')}\n\n"
                else:
                    response = f"📚 Medical History for Patient ID: {patient_id}\n\n"

                if history_data:
                    response += f"📝 Medical Records ({len(history_data)} found):\n"
                    for record in history_data:
                        response += f"   • {record.get('recordDate', 'N/A')}: {record.get('recordType', 'N/A')} - {record.get('description', 'N/A')}\n"
                        if record.get('diagnosis'):
                            response += f"     Diagnosis: {record.get('diagnosis')}\n"
                        if record.get('treatment'):
                            response += f"     Treatment: {record.get('treatment')}\n"
                    response += "\n"
                else:
                    response += f"📝 No medical records found.\n\n"

                if prescription_data:
                    prescription_count = prescription_data[0].get('prescriptions', 0)
                    response += f"💊 Total Prescriptions: {prescription_count}\n\n"

                response += "🏥 Regular monitoring recommended based on medical history."
                return response
            else:
                # General medical history overview
                db_query = "SELECT p.\"firstName\", p.\"lastName\", p.id, COUNT(mr.id) as records, COUNT(pr.id) as prescriptions FROM patients p LEFT JOIN medical_records mr ON p.id = mr.\"patientId\" LEFT JOIN prescriptions pr ON p.id = pr.\"patientId\" GROUP BY p.id, p.\"firstName\", p.\"lastName\" ORDER BY records DESC LIMIT 10"
                result = await self.database_agent.query_database(db_query)

                if not result:
                    return "No medical history data available."

                response = "📚 Patient Medical History Overview:\n"
                for row in result:
                    response += f"   • {row['firstName']} {row['lastName']} (ID: {row['id']}): {row['records']} records, {row['prescriptions']} prescriptions\n"

                response += "\n💡 Specify a patient ID for detailed medical history."
                return response

        except Exception as e:
            self.logger.error(f"Error in medical history: {str(e)}")
            return f"Error retrieving medical history: {str(e)}"

    async def _handle_health_alerts(self, query: str) -> str:
        """Handle health alerts and critical notifications."""
        try:
            patient_id = self._extract_patient_id(query)

            if not self.database_agent:
                return "Database agent not available for health alerts."

            if patient_id:
                # Query specific patient alerts
                patient_query = f"SELECT * FROM patients WHERE id = '{patient_id}'"
                patient_data = await self.database_agent.query_database(patient_query)

                # Look for abnormal lab results
                alerts_query = f"SELECT lr.*, lt.\"testName\" FROM lab_results lr JOIN lab_tests lt ON lr.\"testId\" = lt.id WHERE lr.\"patientId\" = '{patient_id}' AND lr.\"isNormal\" = false ORDER BY lr.\"testDate\" DESC LIMIT 5"
                alerts_data = await self.database_agent.query_database(alerts_query)

                if patient_data:
                    patient = patient_data[0]
                    response = f"🚨 Health Alerts for {patient.get('firstName', 'N/A')} {patient.get('lastName', 'N/A')} (ID: {patient_id})\n\n"
                else:
                    response = f"🚨 Health Alerts for Patient ID: {patient_id}\n\n"

                if alerts_data:
                    response += f"⚠️ Critical Findings ({len(alerts_data)} alerts):\n"
                    for alert in alerts_data:
                        response += f"   • {alert.get('testName', 'Unknown Test')} ({alert.get('testDate', 'N/A')}): {alert.get('result', 'N/A')} - {alert.get('notes', 'Requires attention')}\n"
                    response += "\n"
                else:
                    response += f"✅ No critical health alerts found.\n\n"

                # Check emergency contact
                if patient_data and patient_data[0].get('emergencyContact'):
                    response += f"📞 Emergency Contact: {patient_data[0]['emergencyContact']}\n\n"

                response += "🏥 Immediate medical attention may be required for abnormal results."
                return response
            else:
                # General alerts overview - patients with abnormal results
                db_query = "SELECT p.\"firstName\", p.\"lastName\", p.id, COUNT(lr.id) as abnormal_results FROM patients p LEFT JOIN lab_results lr ON p.id = lr.\"patientId\" AND lr.\"isNormal\" = false GROUP BY p.id, p.\"firstName\", p.\"lastName\" HAVING COUNT(lr.id) > 0 ORDER BY abnormal_results DESC LIMIT 10"
                result = await self.database_agent.query_database(db_query)

                if not result:
                    return "✅ No critical health alerts at this time."

                response = "🚨 Patients with Health Alerts:\n"
                for row in result:
                    response += f"   • {row['firstName']} {row['lastName']} (ID: {row['id']}): {row['abnormal_results']} abnormal results\n"

                response += "\n💡 Specify a patient ID for detailed alert information."
                return response

        except Exception as e:
            self.logger.error(f"Error in health alerts: {str(e)}")
            return f"Error retrieving health alerts: {str(e)}"

    async def _handle_continuous_monitoring(self, query: str) -> str:
        """Handle continuous health monitoring by querying patient data."""
        try:
            # Extract patient ID from query
            patient_id = self._extract_patient_id(query)
            if not patient_id:
                return "Please provide a valid patient ID for monitoring."

            if not self.database_agent:
                return "Database agent not available for patient monitoring."

            # Query for patient basic information
            patient_query = f"SELECT * FROM patients WHERE id = '{patient_id}'"
            patient_data = await self.database_agent.query_database(patient_query)

            # Query for recent medical records
            medical_query = f"SELECT * FROM medical_records WHERE \"patientId\" = '{patient_id}' ORDER BY \"recordDate\" DESC LIMIT 5"
            medical_data = await self.database_agent.query_database(medical_query)

            # Query for recent lab results
            lab_query = f"SELECT lr.*, lt.\"testName\" FROM lab_results lr JOIN lab_tests lt ON lr.\"testId\" = lt.id WHERE lr.\"patientId\" = '{patient_id}' ORDER BY lr.\"testDate\" DESC LIMIT 10"
            lab_data = await self.database_agent.query_database(lab_query)

            # Format the monitoring report
            report = f"📊 Patient Monitoring Report for ID: {patient_id}\n\n"

            if patient_data:
                patient = patient_data[0]
                report += f"👤 Patient Information:\n"
                report += f"   Name: {patient.get('firstName', 'N/A')} {patient.get('lastName', 'N/A')}\n"
                report += f"   DOB: {patient.get('dateOfBirth', 'N/A')}\n"
                report += f"   Blood Type: {patient.get('bloodType', 'N/A')}\n"
                report += f"   Allergies: {patient.get('allergies', 'None listed')}\n\n"
            else:
                report += f"❌ Patient data not found for ID: {patient_id}\n\n"

            if medical_data:
                report += f"📋 Recent Medical Records ({len(medical_data)} found):\n"
                for record in medical_data:
                    report += f"   • {record.get('recordDate', 'N/A')}: {record.get('recordType', 'N/A')} - {record.get('description', 'N/A')}\n"
                report += "\n"
            else:
                report += f"📋 No recent medical records found.\n\n"

            if lab_data:
                report += f"🧪 Recent Lab Results ({len(lab_data)} found):\n"
                for lab in lab_data:
                    status = "✅ Normal" if lab.get('isNormal') else "⚠️ Abnormal"
                    report += f"   • {lab.get('testName', 'Unknown Test')} ({lab.get('testDate', 'N/A')}): {lab.get('result', 'N/A')} {status}\n"
                report += "\n"
            else:
                report += f"🧪 No recent lab results found.\n\n"

            report += "🏥 Health monitoring recommendations: Regular check-ups advised. Monitor vital signs and lab trends."

            return report

        except Exception as e:
            self.logger.error(f"Error in continuous monitoring: {str(e)}")
            return f"Error retrieving patient monitoring data: {str(e)}"

    def _extract_patient_id(self, query: str) -> Optional[str]:
        """Extract patient ID from the query using regex."""
        import re

        # Look for UUID pattern or patient ID mentions
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        match = re.search(uuid_pattern, query, re.IGNORECASE)
        if match:
            return match.group(0)

        # Look for "patient ID" or "patient" followed by ID
        patterns = [
            r'patient\s+(?:id\s+)?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
            r'id\s+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
        ]

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    async def _handle_query(self, query: str) -> str:
        """Handle general patient queries by delegating to database agent."""
        if not self.database_agent:
            return "Database agent not available for queries."

        # Delegate to database agent with the query
        return await self.database_agent.run(query)
