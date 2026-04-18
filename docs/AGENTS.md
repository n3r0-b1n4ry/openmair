# Project Overview: AIOps System Using Mixture-of-Agents (MoA)

## 1. System Vision

This project builds an Automated Incident Response system (AIOps). The system ingests real-time logs and alerts from Microservices infrastructure, uses a Multi-Agent council architecture to perform Root Cause Analysis (RCA), and then applies an LLM-as-a-Judge mechanism to make the final decision.

## 2. Agent Architecture

* **Candidate Proposers:** State-of-the-art open-source LLMs (Qwen 3.5 27B, Llama 4 17B, Devstral Small 2 24B, Gemma 4 27B) deployed locally via vLLM. These agents operate in parallel to analyze logs and generate multiple independent RCA reports.
* **Oracle Aggregator:** A premium model (GPT-4o, Claude Opus 4.7, or Gemini 3.1 Pro). Its task is not to analyze from scratch, but to synthesize, compare, and evaluate the Proposers' reports, thereby filtering out hallucinations and producing the optimal remediation action.
* **Orchestrator:** The entire workflow is managed by LangGraph, maintaining a global State shared across all agents.

## 3. Source Code Structure (Monorepo)

* `/agents`: Defines the workflows for Candidate LLMs and Oracle LLM.
* `/orchestrator`: LangGraph Graph structure, Router, and States.
* `/prompts`: Collection of specialized prompt templates designed to counter bias.
* `/infrastructure`: Docker Compose configuration for deploying vLLM, ELK Stack, and API Gateway.
* `/evals`: Toolkit for running offline tests and scoring the system.

## 4. LLM Models Used

### Proposer Models (Candidate LLMs)
1. **Qwen 3.5 27B** - Currently the most powerful open-source model
2. **Llama 4 17B** - The most popular open-source model (upgraded from Llama 3.1)
3. **Devstral Small 2 24B** - Chain-of-thought reasoning model (replacing Mistral Large 2)
4. **Gemma 4 27B** - The latest open-source model
5. **DeepSeek R1 Distill Llama 70B** - Powerful reasoning model

### Judge Model (Oracle LLM)
1. **GPT-4o** - The most powerful model from OpenAI
2. **Claude Opus 4.7** - The best model for reasoning
3. **Gemini 3.1 Pro** - The latest model from Google

See `MODELS.md` for more details.

## 5. Core Programming Rules

* All LLM interactions must use LangChain's LCEL syntax.
* All error messages must be logged using the standard `logging` library. Never use `print()`.
* Strictly adhere to least privilege: All AI-generated code that affects the system must go through a Human-in-the-Loop approval mechanism.