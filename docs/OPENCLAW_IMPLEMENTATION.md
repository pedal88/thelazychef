# OpenClaw Architecture & Implementation

**Status**: Active  
**Version**: 1.0.0  
**Last Updated**: 2026-02-20

This document serves as the **Source of Truth** for the local autonomous agent runtime governing this project. It details the system architecture, configuration, implementation history, and memory structure of the OpenClaw agent integrated into the `thelazychef` workspace.

---

## 1. System Architecture

The local agent operates a persistent runtime that autonomously manages code, documentation, and system health.

- **Runtime Environment**: [OpenClaw v2026.2.17](https://github.com/openclaw/core) (Node.js Gateway Process)
- **Primary LLM Engine**: **Google Gemini 2.0 Flash** 
  - Selected for high-speed reasoning and code generation capabilities.
  - Default model for all agent operations.
- **Human Interface**: Telegram Gateway via `@antigravity_whisperer_bot`
  - Allows remote command execution and status updates via encrypted messaging.
- **Workspace Root**: `/Users/pad/Projects/thelazychef`
  - The agent has full read/write access to this directory and its subdirectories.

---

## 2. Configuration & Security

Configuration is managed via the local `openclaw.json` manifest.

### Authentication Strategy
- **Method**: Hardcoded `GEMINI_API_KEY` directly within `openclaw.json`.
- **Rationale**: While environment variable substitution (`${env:GEMINI_API_KEY}`) is standard practice, persistent resolution errors in the underlying Node.js runtime necessitated a direct inclusion strategy to ensure prompt stability.
- **Security Note**: This `openclaw.json` must **NEVER** be committed to public repositories. It is strictly excluded via `.gitignore`.

### Critical Schema Definition
To prevent "Unrecognized Key" initialization errors, the model definition enforces start-up nesting:

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "google/gemini-2.0-flash-exp"
      }
    }
  }
}
```

*Note: Previous flat configurations (e.g., `model: "gemini..."` at root) are deprecated and will cause boot failures.*

---

## 3. Implementation History & Troubleshooting (Post-Mortem)

A comprehensive log of the migration and stabilization process for the autonomous agent.

### Migration Logic
- **Transition**: Shifted from **Anthropic Claude 3.5 Sonnet** to **Google Gemini 2.0 Flash**.
- **Driver**: Need for lower latency responses and higher context window utilization for large codebase refactoring.

### Resolved Incidents & Fixes

| Incident | Root Cause | Resolution |
| :--- | :--- | :--- |
| **Boot Failure: "Unrecognized key"** | Configuration schema mismatch in `openclaw.json`. | Applied strict nesting under `agents.defaults.model.primary` to align with v2026 spec. |
| **API Error: "404/Invalid Key"** | Deprecated model string identifier (`gemini-1.5-pro`). | Updated model target to `gemini-2.0-flash-exp` and verified key permissions. |
| **Port Locked: 18789 (Gateway)** | Orphaned process from previous crash holding the port. | Terminated ghost PIDs (e.g., `70848`) via `lsof -i :18789` and `kill -9`. |

---

## 4. Agent Memory Structure

The agent utilizes a structured markdown file system to maintain persona, context, and operational rules across sessions.

| Filename | Purpose |
| :--- | :--- |
| **`AGENTS.md`** | **Master Instructions.** The primary directive file. Defines high-level goals, behavioral constraints, and workflow priorities. |
| **`SOUL.md`** | **Persona Definition.** Defines the agent's personality, tone (e.g., "Professional & Witty"), and ethical boundaries. |
| **`MEMORY.md`** | **Long-Term Memory.** A curated log of major architectural decisions, user preferences, and project milestones. Unlike chat logs, this is permanent context. |
| **`HEARTBEAT.md`** | **Background Tasks.** Defines autonomous health checks (e.g., "Check for uncommitted git changes every hour") executed without user prompt. |

---

## 5. Capabilities Manifest

The agent is equipped with the following toolsets ("Skills") to perform its duties:

- **`coding-agent`**: Full file system manipulation. Can read, write, specific line-edit, and delete files within the workspace.
- **`github`**: Git plumbing and GitHub API integration. Capable of checking out branches, creating pull requests, and managing issues.
- **`healthcheck`**: System diagnostics. Monitors disk usage, memory consumption, and process health for self-healing.
- **`shell`**: Terminal execution. Allows running arbitrary shell commands (e.g., `npm test`, `python app.py`) directly from the Telegram interface.

---

> *This document is automatically generated and maintained by the Lead DevOps Agent. Manual edits should be verified against the running configuration.*
