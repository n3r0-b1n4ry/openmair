#!/usr/bin/env python3
"""
Benchmark and Evaluation Script for Multi-Agent AIOps System
"""
import asyncio
import json
import os
import argparse
import logging
from typing import List, Dict, Any
from orchestrator.graph import graph
from orchestrator.state import AIOpsState
from config import config
from infrastructure.elasticsearch_integration import ElasticsearchManager, LogEntry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("benchmark")

# Initialize ES Manager
es_manager = None
try:
    es_manager = ElasticsearchManager(config.get_elasticsearch_config())
except Exception as e:
    logger.warning(f"Could not connect to Elasticsearch. Visualization data will not be recorded: {e}")

def load_scenarios(scenarios_dir: str = "scenarios") -> List[Dict[str, Any]]:
    """Load all scenario JSON files from the scenarios directory"""
    scenarios = []
    if not os.path.exists(scenarios_dir):
        logger.error(f"Scenarios directory '{scenarios_dir}' not found.")
        return scenarios
        
    for filename in sorted(os.listdir(scenarios_dir)):
        if filename.endswith(".json"):
            filepath = os.path.join(scenarios_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    scenario = json.load(f)
                    scenarios.append(scenario)
            except Exception as e:
                logger.error(f"Failed to load {filename}: {e}")
                
    return scenarios

async def evaluate_scenario(scenario: Dict[str, Any]):
    """Run a single scenario through the AIOps system"""
    logger.info(f"\n{'='*50}\nEvaluating Scenario: {scenario.get('name')} ({scenario.get('id')})\n{'='*50}")
    logger.info(f"Description: {scenario.get('description')}")
    
    incident_logs = scenario.get("logs", "")
    
    initial_state: AIOpsState = {
        "incident_id": scenario.get("id"),
        "incident_logs": incident_logs,
        "messages": [],
    }
    
    # Set current incident ID in env so the log handler picks it up
    os.environ["CURRENT_INCIDENT_ID"] = scenario.get("id")
    
    # Setup real-time ES log handler
    es_handler = None
    if es_manager:
        try:
            from infrastructure.elasticsearch_integration import ElasticsearchLogHandler
            index_name = f"{config.ELASTICSEARCH_INDEX_PREFIX}-reports"
            es_handler = ElasticsearchLogHandler(es_manager.es_client, index_name)
            # Use same formatter as basicConfig
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            es_handler.setFormatter(formatter)
            logging.getLogger().addHandler(es_handler)
        except Exception as e:
            logger.warning(f"Failed to setup real-time Elasticsearch log handler: {e}")
            
    try:
        if es_manager:
            # Push the original logs to Elasticsearch for dashboard visualization and proposer fetching
            es_manager.log_pipeline.ingest_incident_logs(
                incident_logs=incident_logs,
                incident_id=scenario.get("id"),
                service="aiops-benchmark"
            )
            # Ensure the logs are instantly searchable
            try:
                es_manager.es_client.client.indices.refresh(index="incident_logs")
            except Exception as e:
                logger.warning(f"Failed to refresh Elasticsearch index: {e}")

        # Run the system
        logger.info("Starting incident analysis...")
        final_state = await graph.ainvoke(initial_state)
        
        final_report = final_state.get("final_report")
        
        if es_manager:
            # Push individual proposer reports with Judge scores
            proposals = final_state.get("proposals", [])
            evaluations = final_state.get("evaluations", [])
            judge_scores = evaluations[0].scores if (evaluations and len(evaluations) > 0) else []
            
            for i, proposal in enumerate(proposals):
                try:
                    from datetime import datetime
                    judge_score = judge_scores[i] if i < len(judge_scores) else None
                    metadata = {
                        "confidence_score": proposal.report.confidence_score,
                        "root_cause": proposal.report.root_cause,
                        "solution": proposal.report.solution,
                        "is_proposal": True,
                        "model_name": proposal.model_name
                    }
                    if judge_score is not None:
                        metadata["judge_score"] = judge_score
                        
                    proposer_log = LogEntry(
                        timestamp=datetime.now().isoformat(),
                        level="INFO",
                        service=f"aiops-{proposal.proposer_id}",
                        message=f"Proposal from {proposal.proposer_id}: {proposal.report.root_cause}",
                        incident_id=scenario.get("id"),
                        metadata=metadata
                    )
                    es_manager.es_client.index_log(f"{config.ELASTICSEARCH_INDEX_PREFIX}-reports", proposer_log)
                except Exception as e:
                    logger.warning(f"Failed to log proposal to ES: {e}")

        if final_report:
            print("\n--- AIOPS GENERATED REPORT ---")
            print(f"Root Cause: {final_report.root_cause}")
            print(f"Solution: {final_report.solution}")
            print(f"Judge Confidence Score: {final_report.confidence_score}")
            print("------------------------------\n")
            
            if es_manager:
                from datetime import datetime
                report_log = LogEntry(
                    timestamp=datetime.now().isoformat(),
                    level="INFO",
                    service="aiops-judge",
                    message=f"Generated Final Incident Report by Judge",
                    incident_id=scenario.get("id"),
                    metadata={
                        "confidence_score": final_report.confidence_score,
                        "root_cause": final_report.root_cause,
                        "solution": final_report.solution,
                        "is_final_report": True
                    }
                )
                es_manager.es_client.index_log(f"{config.ELASTICSEARCH_INDEX_PREFIX}-reports", report_log)
        else:
            logger.warning("No final report was generated.")

        # Log executed actions to console and ES
        executed_actions = final_state.get("executed_actions", [])
        if executed_actions:
            print("\n--- EXECUTOR ACTION REPORT ---")
            for action in executed_actions:
                print(f"- {action}")
            print("------------------------------\n")
            
            if es_manager:
                from datetime import datetime
                for action in executed_actions:
                    try:
                        action_log = LogEntry(
                            timestamp=datetime.now().isoformat(),
                            level="INFO",
                            service="aiops-executor",
                            message=f"Action result: {action}",
                            incident_id=scenario.get("id"),
                            metadata={
                                "action_detail": action,
                                "is_executed_action": True
                            }
                        )
                        es_manager.es_client.index_log(f"{config.ELASTICSEARCH_INDEX_PREFIX}-reports", action_log)
                    except Exception as e:
                        logger.warning(f"Failed to log executed action to ES: {e}")
        else:
            logger.warning("No executor actions were executed.")
            
    except Exception as e:
        logger.error(f"Error evaluating scenario {scenario.get('id')}: {str(e)}")
    finally:
        if es_handler:
            try:
                logging.getLogger().removeHandler(es_handler)
            except Exception:
                pass
        os.environ.pop("CURRENT_INCIDENT_ID", None)

async def main():
    parser = argparse.ArgumentParser(description="Evaluate AIOps System with Scenarios")
    parser.add_argument("--all", action="store_true", help="Run all available scenarios")
    parser.add_argument("--scenario", type=str, help="Run a specific scenario by ID or Name (e.g., ddos_attack)")
    parser.add_argument("--list", action="store_true", help="List all available scenarios")
    
    args = parser.parse_args()
    
    scenarios = load_scenarios()
    if not scenarios:
        return
        
    if args.list:
        print("\nAvailable Scenarios:")
        for s in scenarios:
            filename = s.get('id', 'Unknown')
            name = s.get('name', 'Unknown')
            print(f"- {name} (ID: {filename})")
        return
        
    if args.scenario:
        # Find the specific scenario
        target = args.scenario.lower()
        matched_scenarios = [
            s for s in scenarios 
            if target in s.get('id', '').lower() or target in s.get('name', '').lower()
        ]
        
        if not matched_scenarios:
            logger.error(f"No scenario found matching '{args.scenario}'")
            return
            
        await evaluate_scenario(matched_scenarios[0])
        
    elif args.all:
        for scenario in scenarios:
            await evaluate_scenario(scenario)
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
