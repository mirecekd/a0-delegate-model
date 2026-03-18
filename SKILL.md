---
name: "a0-model-delegation"
description: "Delegate prompts from Agent Zero to alternative models exposed by the existing LiteLLM/OpenAI-compatible endpoint without changing Agent Zero core configuration. Use when the user wants a different model, wants to see available models, or wants prompt routing to another LiteLLM-backed model."
version: "1.0.0"
author: "Agent Zero"
tags: ["agent-zero", "litellm", "routing", "delegation", "models", "openai-compatible", "bridge"]
trigger_patterns:
  - "use another model"
  - "delegate to another model"
  - "list litellm models"
  - "show available models"
  - "pick a different model"
  - "send this to claude"
  - "send this to gemini"
  - "send this to codex"
  - "route to another llm"
allowed_tools:
  - "code_execution_tool"
  - "filesystem.read_text_file"
  - "filesystem.read_multiple_files"
  - "filesystem.list_directory"
---

# A0 Model Delegation

## Purpose

This skill lets the agent keep running on its normal chat model while delegating selected prompts or conversations to a different model available behind the existing LiteLLM endpoint.

This is specifically designed for setups where:

- Agent Zero already uses a LiteLLM or OpenAI-compatible endpoint
- multiple models are available behind that endpoint
- the user wants to occasionally use a different model
- the user does **not** want to modify Agent Zero core configuration each time

The skill is designed to be reusable and mostly framework-agnostic, but it includes project-specific defaults that work with the current setup.

## Current project defaults

For this project, the skill should assume:

- Agent Zero settings file: `/a0/usr/settings.json`
- current chat model is read from `chat_model_name`
- current provider is read from `chat_model_provider`
- current API base is read from `chat_model_api_base`
- API key should be read from environment variable `API_KEY_OTHER`
- if environment variables are needed and not already present in process env, helper scripts may try common `.env` locations such as:
  - `/a0/.env`
  - `/a0/usr/.env`
  - `/root/.env`
  - project-local `.env`

## Security rules

### Never reveal secrets

The agent and scripts may internally use:

- API keys
- auth headers
- base URLs if sensitive in another environment
- provider-specific internal details

But the agent must **not** expose secret values to the user.

Allowed to reveal:

- model IDs
- the fact that a given model is currently used for chat
- non-secret configuration concepts like provider name or that the endpoint is OpenAI-compatible

Not allowed to reveal:

- raw API keys
- bearer tokens
- `.env` contents
- secret headers

## When to use this skill

Use this skill when the user asks for any of the following:

- a different model than the current chat model
- a list of available models behind LiteLLM
- delegation of one prompt to another model
- model selection before doing a task
- a specific family of models like Claude, Gemini, Codex, OSS, Nova, etc.
- side-by-side experimentation with alternative models

Typical examples:

- "Use Claude for this"
- "Show me what models are available"
- "Send this coding task to Codex"
- "Pick a better model for reasoning"
- "Use a cheaper faster model"
- "Try Gemini instead"

## High-level workflow

When this skill is used, follow this workflow:

1. Read `/a0/usr/settings.json`
2. Determine:
   - current chat model name
   - current provider
   - current API base
3. Use the helper script to list available models from LiteLLM `/models`
4. Present the model list to the user if selection is needed
5. Put the **current chat model at the end of the list**
6. Mark the current chat model clearly as:
   - `CURRENTLY USING FOR CHAT`
7. If the user chooses a model, send the prompt to that model using the helper script
8. Return the delegated result to the user

## UX rule for model listing

### Important requirement

Do **not** hide the current chat model.

Instead:

- include it in the list
- move it to the end of the list
- annotate it with:
  - `CURRENTLY USING FOR CHAT`

### Example

Preferred output shape:

| Model | Note |
|---|---|
| `gpt-5.2-codex` | coding-focused alternative |
| `global.anthropic.claude-sonnet-4-6` | strong general alternative |
| `gemini/gemini-3.1-pro-preview` | alternative reasoning model |
| `gpt-5.4` | **CURRENTLY USING FOR CHAT** |

## Selection guidance

When the user asks for recommendations, use heuristics like these.

### General reasoning

Prefer candidates such as:

- `gpt-5.2`
- `global.anthropic.claude-sonnet-4-6`
- `global.anthropic.claude-opus-4-6-v1`
- `gemini/gemini-3.1-pro-preview`

### Coding

Prefer candidates such as:

- `gpt-5.2-codex`
- `gpt-5.2`
- `global.anthropic.claude-sonnet-4-6`

### Fast / cheaper feeling option

Prefer candidates such as:

- `global.anthropic.claude-haiku-4-5-20251001-v1:0`
- `gemini-3.1-flash-lite-preview`
- `gemini/gemini-3-flash-preview`

### Open-weight experimentation

Prefer candidates such as:

- `openai.gpt-oss-120b-1:0`
- `openai.gpt-oss-20b-1:0`

## Expected scripts

This skill expects these helper scripts:

- `scripts/list_models.py`
- `scripts/delegate_prompt.py`

## Script responsibilities

### `list_models.py`

Responsibilities:

- read `/a0/usr/settings.json`
- detect current chat model
- detect LiteLLM base URL
- read `API_KEY_OTHER` from environment or common `.env` files
- call `GET /models`
- collect model IDs
- move current model to the end if present
- annotate current model in human-readable mode
- optionally emit JSON for machine use

### `delegate_prompt.py`

Responsibilities:

- read `/a0/usr/settings.json`
- use current API base unless explicitly overridden
- read `API_KEY_OTHER`
- call OpenAI-compatible chat completions endpoint
- accept:
  - target model
  - system prompt
  - user prompt
  - optional message history file
- return response text
- optionally return raw JSON

## Recommended terminal usage

### List models (table-like text)

```bash
python /a0/usr/projects/private/a0-model-delegation/scripts/list_models.py
```

### List models as JSON

```bash
python /a0/usr/projects/private/a0-model-delegation/scripts/list_models.py --json
```

### Delegate one prompt

```bash
python /a0/usr/projects/private/a0-model-delegation/scripts/delegate_prompt.py \
  --model global.anthropic.claude-sonnet-4-6 \
  --prompt "Summarize this architecture and point out weaknesses."
```

### Delegate with system prompt

```bash
python /a0/usr/projects/private/a0-model-delegation/scripts/delegate_prompt.py \
  --model gpt-5.2-codex \
  --system "You are a senior software engineer." \
  --prompt "Refactor this Python function for clarity and safety."
```

## Agent usage procedure

When performing actual delegation:

1. Determine whether the user already specified a target model
2. If no target model was specified, list models first
3. If recommending a model, explain briefly why
4. If the user wants a one-off answer, use `delegate_prompt.py`
5. If the user later wants multi-turn delegation, extend this skill with a session script rather than overloading the simple prompt script

## Output style guidance

### When showing model choices

Prefer compact grouped output with clear categories if there are many models.

Always include:

- model ID
- short note if useful
- current model label for current chat model

### When returning delegated output

The agent should state that the answer came from the delegated model, for example:

- "Delegated to `global.anthropic.claude-sonnet-4-6`"
- "Result from `gpt-5.2-codex`"

Do not imply the delegated output came from the main chat model.

## Failure handling

If listing models fails:

1. verify `/a0/usr/settings.json` exists
2. verify `chat_model_api_base` is set
3. verify `API_KEY_OTHER` is available
4. verify LiteLLM endpoint responds to `/models`
5. report a concise operational error without revealing secrets

If delegation fails:

1. verify the requested model exists in `/models`
2. verify the endpoint supports `/chat/completions`
3. retry once if the failure looks transient
4. return concise failure context

## Reusability guidance

This skill is intentionally built so the scripts can be reused outside Agent Zero.

To adapt it to another environment:

- replace the settings file path if needed
- replace the API key env var if needed
- keep the OpenAI-compatible contract the same

## Minimal extension roadmap

Possible future additions:

- session-based delegated chat script
- cost-aware routing
- automatic routing by task type
- side-by-side comparison mode
- model alias presets like `--preset coding`

## Checklist for agent

Before using this skill:

- [ ] Confirm whether the user wants model listing or direct delegation
- [ ] Read current chat model from settings
- [ ] Keep current chat model visible but last
- [ ] Mark current model as `CURRENTLY USING FOR CHAT`
- [ ] Never reveal API secrets
- [ ] Clearly indicate which model produced delegated output

## Files in this skill

- `SKILL.md` — main instructions and policy
- `scripts/list_models.py` — list and label available models
- `scripts/delegate_prompt.py` — send delegated chat completions

## Notes specific to this project

At time of creation, the current Agent Zero chat model is `gpt-5.4` via provider `other` and base `http://playpi4.local:4000`.

This should not be hardcoded in agent behavior. Scripts should read the live settings file so the skill stays accurate if configuration changes later.
