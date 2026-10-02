

<!-- AGENTHANDOFF:BEGIN -->
## AgentHandoff — Autonomous Context Transfer

This project has an **agenthandoff** MCP server that auto-starts with your session. It contains context from previous agent sessions (Claude Code, Cursor, Gemini, etc.).

### On session start — read incoming handoff

At the start of every session, call these MCP tools from the agenthandoff server:

1. `get_task_state` — what was being worked on, current step, next action (~50 tokens)
2. `get_decisions` — architectural decisions already made (~150 tokens)
3. `get_warnings` — constraints and things to avoid (~100 tokens)

If a handoff packet exists, acknowledge the context and continue from where the previous agent left off. If no packet exists, proceed normally.

### During your session — push context automatically

As you work, call the MCP tools to build up context for the next agent:

- `push_decision` — record architectural decisions as you make them (statement, reason, related files)
- `push_warning` — record constraints or dangers discovered
- `push_failed_attempt` — record approaches that failed and why (prevents the next agent from repeating mistakes)
- `set_task_state` — update the current goal, step, and next action
- `add_note` — record anything else worth preserving

### When the user says "handoff" or "switch to X"

When the user says any of: "handoff to X", "switch to X", "hand off", "transfer to X", or similar — generate the complete handoff packet by writing these two files:

**`.agenthandoff/current-handoff.json`** — structured packet:
```json
{
  "schema_version": "1.0",
  "project_id": "unknown",
  "project_path": "<absolute path of this project>",
  "created_at": "<ISO timestamp>",
  "source_agent": "codex",
  "target_agent": "<target from user's message, default 'generic'>",
  "task_state": {
    "goal": "<specific goal>",
    "current_step": "<what you were doing>",
    "next_action": "<EXACT next action with file:line>",
    "blocked_on": null
  },
  "decisions": [{"statement": "", "reason": "", "related_files": [], "confidence": 0.95}],
  "facts": [{"statement": "", "source": "codex-session", "related_files": []}],
  "warnings": [{"statement": "", "source": "codex-session"}],
  "failed_attempts": [{"what": "", "why_failed": "", "recommendation": ""}],
  "related_files": [],
  "open_questions": [],
  "manual_notes": [],
  "provenance": {
    "capture_method": "agent-self-reported",
    "sources_used": ["codex-session-context"],
    "review_status": "approved"
  }
}
```

**`.agenthandoff/current-handoff.md`** — human-readable markdown with sections: Task State, Decisions, Warnings, Failed Attempts, Related Files, Next Action.

Rules for the packet:
- Be specific. "worked on auth" is useless. "Added JWT refresh at src/auth/routes.ts:45" is good.
- Every failed_attempt MUST include why_failed.
- next_action must be exact enough that the next agent starts immediately.
- Include ALL decisions and warnings from the session, not just recent ones.
- After writing, confirm: "Handoff ready. The target agent will pick up context automatically via MCP."
<!-- AGENTHANDOFF:END -->
