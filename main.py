#!/usr/bin/env python3
"""
Multi-Agent AIOps System with LLM-As-A-Judge Mechanism
"""
import asyncio
import sys
import logging
from orchestrator.graph import graph
from orchestrator.state import AIOpsState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main function to run the AIOps system"""
    logger.info("Multi-Agent AIOps System with LLM-As-A-Judge Mechanism")
    logger.info("=" * 50)
    
    # Example incident logs
    incident_logs = """
    2026-03-04 10:15:23 ERROR [UserService] - Unable to connect to database
    2026-03-04 10:15:24 WARN  [APIGateway] - Timeout calling UserService
    2026-03-04 10:15:25 ERROR [OrderService] - UserService call failed
    2026-03-04 10:15:26 FATAL [PaymentService] - Unable to process order due to missing user information
    """
    
    # Create initial state
    initial_state: AIOpsState = {
        "incident_logs": incident_logs,
        "messages": [],
    }
    
    try:
        # Run the system
        logger.info("Starting incident analysis...")
        final_state = await graph.ainvoke(initial_state)
        
        # Display results
        logger.info("Analysis results:")
        logger.info("-" * 30)
        
        final_report = final_state.get("final_report")
        if final_report:
            logger.info(f"Incident ID: {final_report.incident_id}")
            logger.info(f"Timestamp: {final_report.timestamp}")
            logger.info(f"Description: {final_report.description}")
            logger.info(f"Root Cause: {final_report.root_cause}")
            logger.info(f"Solution: {final_report.solution}")
            logger.info(f"Confidence Score: {final_report.confidence_score}")
        else:
            logger.warning("No final report was generated.")
        
        executed_actions = final_state.get("executed_actions", [])
        if executed_actions:
            logger.info("Executed actions:")
            for action in executed_actions:
                logger.info(f"- {action}")
        else:
            logger.warning("No actions were executed.")
            
    except Exception as e:
        logger.error(f"Error running the system: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
