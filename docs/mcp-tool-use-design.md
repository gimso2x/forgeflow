# MCP/Tool-Use Abstraction Layer — Design Note

**Status:** Draft
**Date:** 2026-05-12
**Issue:** #125

## Problem

ForgeFlow's `executor.py` dispatches to hardcoded adapter targets (Claude, Codex) via subprocess calls. Each adapter owns its own invocation logic, and there is no shared abstraction for tool capabilities — filesystem access, shell execution, web search, GitHub operations, or artifact I/O.

As MCP (Model Context Protocol) standardizes tool interfaces across agents, ForgeFlow should have a layer that:

1. Names the tool boundaries the runtime cares about.
2. Allows agents to declare capability, not just brand name.
3. Decouples stage execution from "call this CLI binary."

## Current state

```
RunTaskRequest → executor.dispatch() → StubClaude | StubCodex | ClaudeCode | CodexCLI
                                         ↓
                                    subprocess call
```

- `ExecutorAdapter` protocol defines `run_task()` and `estimate_tokens()`.
- Real adapters invoke `claude -p` or `codex exec` as subprocesses.
- Tool access (filesystem, shell, etc.) is implicit — the agent does whatever it wants, and ForgeFlow only checks output artifacts post-execution.

## Proposed interface

### ToolCapability enum

The runtime declares what categories of tool access a stage may need:

```python
class ToolCapability(enum.Enum):
    FILESYSTEM = "filesystem"     # read/write/create files in task dir
    SHELL = "shell"               # execute shell commands
    WEB_SEARCH = "web_search"     # search the web
    GITHUB = "github"             # GitHub API (issues, PR, review)
    ARTIFACT_IO = "artifact_io"   # read/write ForgeFlow artifacts
```

### ToolPolicy

Each stage can declare required and optional capabilities:

```python
@dataclass(frozen=True)
class ToolPolicy:
    required: list[ToolCapability]
    optional: list[ToolCapability]
    constraints: dict[str, str]  # e.g. {"filesystem": "task-dir-only"}
```

### AdapterCapability profile

Instead of hardcoded name→adapter dispatch, adapters declare a capability profile:

```python
@dataclass(frozen=True)
class AdapterCapability:
    name: str
    capabilities: list[ToolCapability]
    max_token_input: int
    max_token_output: int
    supports_streaming: bool
    invocation_style: str  # "subprocess" | "mcp" | "in-process"
```

### Dispatch change

```python
# Before: hardcoded registry
REAL_REGISTRY = {"claude": ClaudeCodeAdapter(), "codex": CodexCLIAdapter()}

# After: capability-matched dispatch
def dispatch(request: RunTaskRequest, *, use_real: bool = False) -> RunTaskResult:
    policy = tool_policy_for_stage(request.stage)
    adapter = match_adapter(policy, request.adapter_target, use_real=use_real)
    ...
```

The `match_adapter()` function:
1. Checks if the named adapter supports all `required` capabilities.
2. Falls back to any adapter that does if the named one doesn't.
3. Returns a structured error if no adapter satisfies the policy.

## Runtime boundaries

### ForgeFlow-owned (this abstraction covers)

| Boundary | What ForgeFlow controls |
|---|---|
| **Artifact I/O** | Schema validation, read/write, gate checks |
| **Stage dispatch** | Which adapter runs which stage, with what capabilities |
| **Tool policy** | What tools a stage is allowed to use |
| **Audit trail** | What the adapter did (capabilities used, artifacts produced) |

### Agent-owned (this abstraction does NOT cover)

| Boundary | What the agent controls |
|---|---|
| **Model selection** | Which LLM actually runs |
| **Auth/Credentials** | API keys, OAuth tokens |
| **Tool implementation** | How a filesystem read or shell exec actually happens |
| **Streaming/chunking** | How output is delivered incrementally |

## Non-goals

- **MCP server implementation.** ForgeFlow does not become an MCP server. It consumes tool capabilities, it doesn't serve them.
- **Replacing subprocess invocation.** The current `claude -p` / `codex exec` paths remain. MCP is an *additional* invocation style, not a replacement.
- **Runtime dependency on MCP libraries.** This remains stdlib-only. MCP integration is optional.
- **Tool execution sandboxing.** ForgeFlow declares policies; it doesn't enforce OS-level sandboxing.

## Migration path

### Phase 1: Declare, don't enforce (this issue)

1. Add `ToolCapability`, `ToolPolicy`, `AdapterCapability` dataclasses to `forgeflow_runtime/tool_policy.py`.
2. Annotate existing adapters with capability profiles (no behavior change).
3. Add `tool_policy_for_stage()` mapping: plan→filesystem+artifact, work→filesystem+shell+artifact, review→filesystem+artifact+github, etc.
4. Tests verify annotations exist and are consistent.

**No existing adapter breaks.** This is purely additive — dataclass declarations and a lookup function.

### Phase 2: Capability-aware dispatch (future)

1. `dispatch()` uses `ToolPolicy` to validate adapter selection.
2. Mismatched capabilities produce structured errors instead of silent failures.
3. MCP invocation style becomes an option in `AdapterCapability.invocation_style`.

### Phase 3: MCP bridge (future)

1. Adapters with `invocation_style="mcp"` use MCP protocol instead of subprocess.
2. ForgeFlow discovers tool capabilities from MCP server metadata.
3. `ToolPolicy` is populated dynamically from MCP server declarations.

## File changes (Phase 1)

```
forgeflow_runtime/tool_policy.py     # NEW: ToolCapability, ToolPolicy, AdapterCapability
forgeflow_runtime/executor.py        # MODIFIED: add capability annotations to existing adapters
tests/runtime/test_tool_policy.py    # NEW: tests for policy dataclasses and lookup
```

## Decision log

- **Why enum, not string?** Enum prevents typos and makes capability sets statically checkable.
- **Why not Protocol for tools?** ForgeFlow doesn't implement tools. It declares what capabilities it expects. The agent implements.
- **Why `invocation_style` as string, not enum?** Keep it open for future styles without enum updates. "subprocess" and "mcp" are the only two today.
