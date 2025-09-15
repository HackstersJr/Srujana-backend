#!/usr/bin/env python3
"""
Test script for the healthcare agents system.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.medicine_agent import MedicineAgent
from agents.patient_monitoring_agent import PatientMonitoringAgent
from agents.stock_management_agent import StockManagementAgent
from agents.appointment_agent import AppointmentAgent
from agents.database_agent import DatabaseAgent
from services.prisma_service import PrismaService
from configs.settings import get_settings


async def test_agents():
    """Test all the healthcare agents."""
    print("🩺 Testing Healthcare Agents System")
    print("=" * 50)

    # Initialize settings and services
    settings = get_settings()
    prisma_service = PrismaService()

    # Initialize database agent
    db_config = settings.get_llm_config()
    database_agent = DatabaseAgent(db_config, prisma_service)
    await database_agent.start()

    # Initialize medicine agent
    medicine_config = settings.get_llm_config()
    medicine_agent = MedicineAgent(medicine_config, database_agent)
    await medicine_agent.start()

    # Initialize patient monitoring agent
    patient_config = settings.get_llm_config()
    patient_agent = PatientMonitoringAgent(patient_config, database_agent)
    await patient_agent.start()

    # Initialize stock management agent
    stock_config = settings.get_llm_config()
    stock_agent = StockManagementAgent(stock_config, database_agent)
    await stock_agent.start()

    # Initialize appointment agent
    appointment_config = settings.get_llm_config()
    appointment_agent = AppointmentAgent(appointment_config, database_agent)
    await appointment_agent.start()

    print("✅ All agents initialized successfully!")

    # Test queries
    test_queries = [
        ("Medicine Agent", medicine_agent, "Show me medicine inventory with quantities"),
        ("Patient Monitoring Agent", patient_agent, "Check patient vitals for recent visits"),
        ("Stock Management Agent", stock_agent, "Check inventory levels and reorder alerts"),
        ("Appointment Agent", appointment_agent, "Show today's appointments"),
    ]

    for agent_name, agent, query in test_queries:
        print(f"\n🔍 Testing {agent_name}:")
        print(f"Query: {query}")
        try:
            response = await agent.run(query)
            print(f"Response: {response[:200]}..." if len(response) > 200 else f"Response: {response}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")

    # Cleanup
    await appointment_agent.cleanup()
    await stock_agent.cleanup()
    await patient_agent.cleanup()
    await medicine_agent.cleanup()
    await database_agent.cleanup()

    print("\n🎉 Agent testing completed!")


if __name__ == "__main__":
    asyncio.run(test_agents())
