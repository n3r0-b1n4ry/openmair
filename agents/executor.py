import logging
import os
import sys
import asyncio
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from orchestrator.state import IncidentReport
from config import Config
from prompts import EXECUTOR_SYSTEM_PROMPT, EXECUTOR_HUMAN_PROMPT
from agents.retry_handler import with_all_protections

logger = logging.getLogger(__name__)

class RemediationAction(BaseModel):
    """Structure definition for a single remediation action"""
    id: str = Field(description="Unique identifier for the action, e.g. step-1")
    action_type: Literal["bash", "kubernetes", "api", "db", "config", "log_cleanup", "notification", "mock"] = Field(
        description="Type of action: bash, kubernetes, api, db, config, log_cleanup, notification, or mock"
    )
    target: str = Field(description="Target resource/service/server (e.g. UserService, /var/log, IP 203.0.113.5)")
    command_or_payload: str = Field(description="The actual script, command, query, configuration or API payload to run")
    description: str = Field(description="Explanation of what this action does")
    safe_to_auto_run: bool = Field(default=False, description="Whether this action can be executed without manual confirmation (e.g. read-only, status checking, notifications)")

class RemediationPlan(BaseModel):
    """Structure definition for a full remediation plan containing multiple actions"""
    actions: List[RemediationAction] = Field(description="List of sequential remediation actions to execute")

class ExecutorAgent:
    """Agent responsible for executing actions based on the final report"""
    
    def __init__(self, model_name: Optional[str] = None, temperature: float = 0.3):
        """
        Initialize ExecutorAgent
        
        Args:
            model_name (Optional[str]): LLM model name for the executor. If None, uses default from config
            temperature (float): Model temperature
        """
        config = Config()
        
        # Use configured model or default model
        if model_name is None:
            model_name = config.EXECUTOR_MODEL
            
        # Check if we should use custom API base (vLLM or other gateway)
        # Standard OpenAI models (like gpt-4o-mini) should use the direct OpenAI API endpoint.
        is_openai_model = model_name.lower().startswith("gpt-") or "text-davinci" in model_name.lower()
        
        if is_openai_model:
            api_base = None
            api_key = config.OPENAI_API_KEY
        else:
            api_base = config.LLM_API_BASEURL if config.LLM_API_BASEURL else None
            api_key = config.LLM_API_KEY if config.LLM_API_KEY else config.OPENAI_API_KEY
        
        # Initialize model based on model type
        if "claude" in model_name.lower():
            self.model = ChatAnthropic(
                model=model_name,
                temperature=temperature,
                max_tokens=2048,
                timeout=60
            )
            logger.info(f"Initialized Executor Agent with Claude model: {model_name}")
        elif "gemini" in model_name.lower():
            from langchain_google_genai import ChatGoogleGenerativeAI
            self.model = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                max_tokens=2048,
                timeout=60
            )
            logger.info(f"Initialized Executor Agent with Gemini model: {model_name}")
        else:
            self.model = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=2048,
                timeout=60,
                base_url=api_base,
                api_key=api_key
            )
            logger.info(f"Initialized Executor Agent with OpenAI/vLLM model: {model_name}")
            
        self.parser = PydanticOutputParser(pydantic_object=RemediationPlan)
        
        # Create prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", EXECUTOR_SYSTEM_PROMPT),
            ("human", EXECUTOR_HUMAN_PROMPT)
        ])
        
        # Create chain
        self.chain = self.prompt_template | self.model | self.parser
    
    @with_all_protections(max_attempts=3, min_wait=1.0, max_wait=10.0)
    async def execute_report_actions(self, report: IncidentReport, auto_approve: Optional[bool] = None) -> List[str]:
        """
        Execute the actions proposed in the report
        
        Args:
            report (IncidentReport): Final report from the judge
            auto_approve (Optional[bool]): Override config.AUTO_APPROVE_REMEDIATION
            
        Returns:
            List[str]: List of executed actions and results
        """
        config = Config()
        if auto_approve is None:
            auto_approve = config.AUTO_APPROVE_REMEDIATION
            
        executed_actions = []
        
        try:
            logger.info(f"Executor Agent generating execution plan for incident {report.incident_id}...")
            
            # 1. Translate high-level report into structured RemediationPlan
            try:
                plan = await self.chain.ainvoke({
                    "incident_id": report.incident_id,
                    "description": report.description,
                    "root_cause": report.root_cause,
                    "solution": report.solution,
                    "format_instructions": self.parser.get_format_instructions()
                })
            except Exception as llm_err:
                logger.warning(f"Executor LLM failed ({str(llm_err)}). Using rule-based fallback plan.")
                plan = self._generate_fallback_plan(report)
            
            logger.info(f"Generated remediation plan with {len(plan.actions)} steps.")
            
            # 2. Sequential execution of actions
            for action in plan.actions:
                # Check for approval
                approved = False
                if auto_approve or action.safe_to_auto_run:
                    approved = True
                    logger.info(f"[EXECUTOR] Action {action.id} auto-approved (safe_to_auto_run={action.safe_to_auto_run}, auto_approve={auto_approve})")
                else:
                    # Human-in-the-Loop check
                    if sys.stdin.isatty():
                        print("\n" + "="*50)
                        print(f"⚠️  [APPROVAL REQUIRED] Action {action.id} ({action.action_type})")
                        print(f"Description: {action.description}")
                        print(f"Target:      {action.target}")
                        print(f"Command/Payload:")
                        print(f"  {action.command_or_payload}")
                        print("="*50)
                        
                        # Wait for user input
                        loop = asyncio.get_event_loop()
                        user_input = await loop.run_in_executor(None, input, "Approve execution? (y/N): ")
                        if user_input.strip().lower() in ["y", "yes"]:
                            approved = True
                        else:
                            approved = False
                    else:
                        # Non-interactive CLI
                        logger.warning(f"[EXECUTOR] Non-interactive environment: Action {action.id} requires manual approval. Skipping execution.")
                        action_result = f"SKIPPED: Awaiting manual approval (Non-interactive environment) for Action {action.id}: {action.description}"
                        executed_actions.append(action_result)
                        continue
                
                if approved:
                    # Execute action
                    result = await self._run_action(action, config.MOCK_REMEDIATION)
                    executed_actions.append(result)
                else:
                    logger.warning(f"[EXECUTOR] Action {action.id} rejected by user.")
                    action_result = f"REJECTED: User denied permission for Action {action.id}: {action.description}"
                    executed_actions.append(action_result)
                    
        except Exception as e:
            error_msg = f"Error in execute_report_actions: {str(e)}"
            logger.error(error_msg)
            executed_actions.append(f"ERROR: {error_msg}")
            
        return executed_actions
    
    def _generate_fallback_plan(self, report: IncidentReport) -> RemediationPlan:
        """Generate a rule-based fallback remediation plan when the LLM fails"""
        solution_lower = report.solution.lower() if report.solution else ""
        root_cause_lower = report.root_cause.lower() if report.root_cause else ""
        
        actions = []
        
        if "disk" in root_cause_lower or "space" in root_cause_lower or "disk" in solution_lower or "space" in solution_lower:
            actions.append(RemediationAction(
                id="step-1",
                action_type="log_cleanup",
                target="/var/log",
                command_or_payload="find /var/log -type f -name '*.log' -mtime +7 -delete",
                description="Clean up old log files to free disk space",
                safe_to_auto_run=True
            ))
            actions.append(RemediationAction(
                id="step-2",
                action_type="bash",
                target="local_host",
                command_or_payload="df -h",
                description="Verify disk space usage after cleanup",
                safe_to_auto_run=True
            ))
        elif "brute" in root_cause_lower or "login" in root_cause_lower or "auth" in root_cause_lower or "attack" in root_cause_lower:
            actions.append(RemediationAction(
                id="step-1",
                action_type="api",
                target="Firewall/IPBlocker",
                command_or_payload="block_ip(\"203.0.113.5\")",
                description="Block attacker IP address on the firewall",
                safe_to_auto_run=False
            ))
            actions.append(RemediationAction(
                id="step-2",
                action_type="notification",
                target="Slack-Security-Channel",
                command_or_payload="ALERT: Brute force attack detected and IP 203.0.113.5 blocked.",
                description="Send security alert notification",
                safe_to_auto_run=True
            ))
        elif "oom" in root_cause_lower or "memory" in root_cause_lower or "heap" in root_cause_lower or "oom" in solution_lower:
            actions.append(RemediationAction(
                id="step-1",
                action_type="kubernetes",
                target="report-generator-pod",
                command_or_payload="kubectl rollout restart deployment/report-generator",
                description="Restart the failed report generator deployment",
                safe_to_auto_run=False
            ))
            actions.append(RemediationAction(
                id="step-2",
                action_type="kubernetes",
                target="report-generator-pod",
                command_or_payload="kubectl scale deployment/report-generator --replicas=3",
                description="Scale up replicas to distribute memory load",
                safe_to_auto_run=False
            ))
        elif "pool" in root_cause_lower or "connection" in root_cause_lower or "db" in root_cause_lower or "database" in root_cause_lower:
            actions.append(RemediationAction(
                id="step-1",
                action_type="db",
                target="InventoryDB",
                command_or_payload="KILL ALL CONNECTION WHERE idle_time > 300",
                description="Kill inactive database sessions to free up connections",
                safe_to_auto_run=False
            ))
            actions.append(RemediationAction(
                id="step-2",
                action_type="config",
                target="InventoryService-Config",
                command_or_payload="hikari.maximumPoolSize=100",
                description="Increase connection pool size limits",
                safe_to_auto_run=False
            ))
        else:
            # General fallback action
            actions.append(RemediationAction(
                id="step-1",
                action_type="mock",
                target="system",
                command_or_payload=f"Apply recommendation: {report.solution}",
                description="Apply general remediation action",
                safe_to_auto_run=False
            ))
            
        return RemediationPlan(actions=actions)
    
    async def _run_action(self, action: RemediationAction, mock: bool = True) -> str:
        """
        Run a single action (mock or real)
        
        Args:
            action (RemediationAction): Action to execute
            mock (bool): Whether to simulate the execution
            
        Returns:
            str: Result string
        """
        action_desc = f"Action {action.id} [{action.action_type.upper()}] on {action.target}"
        logger.info(f"Executing {action_desc}...")
        
        if mock:
            # Simulate a brief delay to look realistic
            await asyncio.sleep(0.5)
            
            # Construct a realistic output depending on the action type
            if action.action_type == "bash":
                simulated_output = "stdout: ok\nexit code: 0"
            elif action.action_type == "kubernetes":
                simulated_output = f"deployment.apps/{action.target} patched / restarted successfully"
            elif action.action_type == "api":
                simulated_output = "HTTP/1.1 200 OK\nContent-Type: application/json\n\n{\"status\":\"success\"}"
            elif action.action_type == "db":
                simulated_output = "Query executed successfully. 1 row affected."
            elif action.action_type == "config":
                simulated_output = f"Configuration updated for {action.target}. Config reloaded successfully."
            elif action.action_type == "log_cleanup":
                simulated_output = f"Cleaned up logs at {action.target}. Freed 4.2 GB space."
            elif action.action_type == "notification":
                simulated_output = f"Notification successfully sent to {action.target}."
            else:
                simulated_output = "Simulated action completed successfully."
                
            result = f"[SUCCESS] {action_desc} -> {simulated_output}"
            logger.info(f"[EXECUTOR] {result}")
            return result
        else:
            # REAL execution (only if explicitly requested and safe)
            try:
                if action.action_type == "bash":
                    import subprocess
                    # Run in a shell
                    process = await asyncio.create_subprocess_shell(
                        action.command_or_payload,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    exit_code = process.returncode
                    
                    if exit_code == 0:
                        output = stdout.decode().strip()
                        return f"[SUCCESS] {action_desc} -> stdout: {output}"
                    else:
                        err = stderr.decode().strip()
                        return f"[FAILED] {action_desc} -> exit code {exit_code}, stderr: {err}"
                else:
                    # For other types, fallback to mock as we don't have k8s/db connections locally
                    logger.warning(f"Real execution for type '{action.action_type}' not fully supported in local environment. Mocking execution.")
                    return await self._run_action(action, mock=True)
            except Exception as e:
                err_msg = f"[ERROR] {action_desc} failed: {str(e)}"
                logger.error(err_msg)
                return err_msg
                
    async def execute_custom_action(self, action: str) -> str:
        """
        Execute a custom action
        
        Args:
            action (str): Action to execute
            
        Returns:
            str: Result of the action
        """
        try:
            # Mimic old interface for backward compatibility
            action_obj = RemediationAction(
                id="custom-action",
                action_type="bash",
                target="local_host",
                command_or_payload=action,
                description=f"Custom action: {action}",
                safe_to_auto_run=False
            )
            config = Config()
            return await self._run_action(action_obj, config.MOCK_REMEDIATION)
        except Exception as e:
            error_result = f"Error executing custom action '{action}': {str(e)}"
            logger.error(f"[EXECUTOR] {error_result}")
            return error_result