# Most Efficient and Latest LLM Models (2026)

## Overview

The Multi-Agent AIOps system uses a Mixture-of-Agents (MoA) architecture combined with an LLM-as-a-Judge mechanism to optimize incident analysis performance. Below is the list of LLM models used in the system, synchronized with the latest `config.py`.

## Proposer Models (Candidate LLMs)

### 1. Qwen 3.6 27B
- **Developer**: Alibaba Cloud
- **Size**: 27 billion parameters
- **Strengths**: Superior performance in reasoning tasks, optimized for complex log analysis.
- **Application in the system**: Incident log analysis, solution recommendations.

### 2. GPT OSS 20B
- **Size**: 20 billion parameters
- **Strengths**: Fast inference, solid benchmark performance for logs and traces.
- **Application in the system**: Log extraction and reasoning.

### 3. SaoLa4-medium
- **Size**: Medium
- **Strengths**: High performance in language and technical text parsing.
- **Application in the system**: Incident log analysis.

### 4. Gemma 4 26B A4B IT
- **Developer**: Google
- **Size**: 26 billion parameters
- **Strengths**: Strong instruction-tuning, excellent log extraction.
- **Application in the system**: Complex incident log analysis.

### 5. Qwen3-32B
- **Developer**: Alibaba Cloud
- **Size**: 32 billion parameters
- **Strengths**: Large model capable of highly detailed technical analysis.
- **Application in the system**: Root cause analysis and detailed solution generation.

## Judge Model (Oracle LLM)

### 1. GPT-5.5 (Default)
- **Developer**: OpenAI
- **Strengths**: The most powerful model currently integrated. Acts as the default Judge.
- **Configuration**: Temperature=0.0, Max Tokens=8192

### 2. GPT-5.4-mini (Fallback)
- **Developer**: OpenAI
- **Strengths**: Faster, highly capable fallback model for the Judge role.
- **Configuration**: Temperature=0.0, Max Tokens=8192

### 3. Gemini 3.1 Pro (Alternative)
- **Developer**: Google
- **Strengths**: Superior multimodal capabilities and massive context window.
- **Configuration**: Temperature=0.0, Max Tokens=8192

## Executor Model

### GPT-4o Mini
- **Developer**: OpenAI
- **Strengths**: High performance at low cost.
- **Application in the system**: Executing incident remediation actions.
- **Configuration**: Temperature=0.3, Max Tokens=2048