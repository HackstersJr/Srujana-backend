"""
Agent modules for the CareCloud AI system.
"""

from .base_agent import BaseAgent
from .database_agent import DatabaseAgent
from .medicine_agent import MedicineAgent
from .patient_monitoring_agent import PatientMonitoringAgent
from .stock_management_agent import StockManagementAgent
from .appointment_agent import AppointmentAgent
from .langchain_agent import LangChainAgent
from .langgraph_agent import LangGraphAgentCoordinator
from .toolbox_agent import ToolboxAgent

__all__ = [
    "BaseAgent",
    "DatabaseAgent",
    "MedicineAgent",
    "PatientMonitoringAgent",
    "StockManagementAgent",
    "AppointmentAgent",
    "LangChainAgent",
    "LangGraphAgentCoordinator",
    "ToolboxAgent",
]
