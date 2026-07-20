# Project Overview: AIOps System Using Mixture-of-Agents (MoA)

## 1. System Vision

This project builds an Automated Incident Response system (AIOps). The system ingests real-time logs and alerts from Microservices infrastructure, uses a Multi-Agent council architecture to perform Root Cause Analysis (RCA), and then applies an LLM-as-a-Judge mechanism to make the final decision.

## 2. Agent Architecture

* **Candidate Proposers**: 5 instances of the tini-cybersec-8b-a1b model running on a local LM Studio server (OpenAI compatible). These agents operate in parallel using varied hyperparameters (temperature, top_k, top_p, repeat_penalty) to analyze logs and generate multiple independent RCA reports.
* **Oracle Aggregator**: A premium model (DeepSeek-V4-Flash, gpt-5.4, gpt-5.4-mini, or Gemini 3.1 Pro). Its task is not to analyze from scratch, but to evaluate and synthesize the Proposers' reports, producing the optimal remediation plan.
* **Executor Agent**: Translates the Judge's recommended actions into structured executable tasks, applies the Human-in-the-Loop CLI approval gating, and runs them.
* **Orchestrator**: The entire workflow is managed by LangGraph, maintaining a global State shared across all agents.

## 3. Source Code Structure (Monorepo)

* `/agents`: Defines the workflows for Candidate LLMs, Oracle LLM, and Executor Agent.
* `/orchestrator`: LangGraph Graph structure, Router, and States.
* `/prompts`: Collection of specialized prompt templates designed to counter bias.
* `/infrastructure`: Docker Compose configuration for deploying vLLM, ELK Stack, and API Gateway.
* `/evals`: Toolkit for running offline tests and scoring the system.

## 4. LLM Models Used

### Proposer Models (Candidate LLMs)
1. **tini-cybersec-8b-a1b (x5 with varied parameters)**

### Judge Model (Oracle LLM)
1. **DeepSeek-V4-Flash** - Default Oracle Judge
2. **gpt-5.4** - Alternative Judge
3. **gpt-5.4-mini** - Fallback Judge
4. **Gemini 3.1 Pro** - Alternative Judge

### Executor Model
1. **DeepSeek-V4-Flash** - Default Executor Model
2. **gpt-5.4-nano** - Alternative Executor Model

See `MODELS.md` for more details.

## 5. Core Programming Rules

* All LLM interactions must use LangChain's LCEL syntax.
* All error messages must be logged using the standard `logging` library. Never use `print()`.
* Strictly adhere to least privilege: All AI-generated code that affects the system must go through a Human-in-the-Loop approval mechanism.