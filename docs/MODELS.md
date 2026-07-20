# Most Efficient and Latest LLM Models (2026)

## Overview

The Multi-Agent AIOps system uses a Mixture-of-Agents (MoA) architecture combined with an LLM-as-a-Judge mechanism to optimize incident analysis performance. Below is the list of LLM models used in the system, synchronized with the latest `config.py`.

## Proposer Models (Candidate LLMs)

All 5 proposers use the **tini-cybersec-8b-a1b** model hosted on a local LLM server (LM Studio), configured with different parameters (temperature, top_k, top_p, and repeat_penalty) to diversify the proposed solutions:

### 1. tini-cybersec-8b-a1b (Proposer 1)
- **Parameters**: Temperature=0.2, Top K=40, Top P=0.85, Repeat Penalty=1.1
- **Role**: Highly deterministic security and incident analysis.

### 2. tini-cybersec-8b-a1b (Proposer 2)
- **Parameters**: Temperature=0.3, Top K=42, Top P=0.90, Repeat Penalty=1.12
- **Role**: Balanced and standard incident analysis.

### 3. tini-cybersec-8b-a1b (Proposer 3)
- **Parameters**: Temperature=0.4, Top K=45, Top P=0.92, Repeat Penalty=1.15
- **Role**: Creative but focused root cause analysis.

### 4. tini-cybersec-8b-a1b (Proposer 4)
- **Parameters**: Temperature=0.5, Top K=48, Top P=0.95, Repeat Penalty=1.18
- **Role**: High variance alternative resolution options.

### 5. tini-cybersec-8b-a1b (Proposer 5)
- **Parameters**: Temperature=0.6, Top K=50, Top P=0.98, Repeat Penalty=1.20
- **Role**: Maximum exploration configuration for corner cases.

## Judge Model (Oracle LLM)

### 1. DeepSeek-V4-Flash (Default)
- **Developer**: DeepSeek
- **Strengths**: High speed, optimized for quick and efficient text reasoning, suitable for evaluation.
- **Configuration**: Temperature=0.0, Max Tokens=8192

### 2. gpt-5.4 (Alternative)
- **Developer**: OpenAI
- **Strengths**: Premium reasoning and evaluation capabilities.
- **Configuration**: Temperature=0.0, Max Tokens=8192

### 3. gpt-5.4-mini (Fallback)
- **Developer**: OpenAI
- **Strengths**: Faster, highly capable fallback model for the Judge role.
- **Configuration**: Temperature=0.0, Max Tokens=8192

### 4. Gemini 3.1 Pro (Alternative)
- **Developer**: Google
- **Strengths**: Superior multimodal capabilities and massive context window.
- **Configuration**: Temperature=0.0, Max Tokens=8192

## Executor Model

### 1. DeepSeek-V4-Flash (Default)
- **Developer**: DeepSeek
- **Strengths**: Lightweight model optimized for low-latency command parsing.
- **Application in the system**: Translating Judge recommendations into structured execution actions.
- **Configuration**: Temperature=0.3, Max Tokens=2048

### 2. gpt-5.4-nano (Alternative)
- **Developer**: OpenAI
- **Strengths**: Ultra-lightweight model optimized for low-latency command parsing.
- **Application in the system**: Translating Judge recommendations into structured execution actions.
- **Configuration**: Temperature=0.3, Max Tokens=2048