---
name: forgeflow-discipline
description: Load this skill before acting in Gemini CLI so ForgeFlow keeps the operational discipline.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must ensure ForgeFlow maintains operational discipline in Gemini CLI.
  Must prioritize tool execution over intent description.
  Must verify work before reporting completion.
---

# forgeflow-discipline

## Purpose

Load this skill before acting in Gemini CLI so ForgeFlow keeps the operational discipline: discover relevant skills first, use the repo tools directly, and verify work before reporting completion.

## Trigger

Use at the start of every ForgeFlow Gemini session, especially when the user asks Gemini to run `/forgeflow`, `/init`, `/clarify`, `/plan`, `/execute`, `/review`, `/ship`, or `/finish`-style work.

## Required behavior

1. Read the ForgeFlow root context and the referenced workflow skill before acting.
2. Prefer concrete tool execution over describing intent.
3. Keep work bounded to the requested task and preserve the user's existing dirty working tree.
4. Write or update the expected ForgeFlow artifacts when running a workflow stage.
5. Verify with the narrowest relevant checks first, then broader validation when changes touch shared contracts.
6. Report only what was changed and how it was verified.

## Gemini-specific tool notes

See `references/gemini-tools.md` for Gemini CLI command and tool-use constraints.
