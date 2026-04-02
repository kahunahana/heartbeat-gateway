---
phase: "04-braintrust-adapter"
plan: "01"
subsystem: "adapters"
tags: ["braintrust", "adapter", "tdd", "webhook", "normalization"]
dependency_graph:
  requires: ["heartbeat_gateway/adapters/base.py", "heartbeat_gateway/config/schema.py", "heartbeat_gateway/__init__.py"]
  provides: ["heartbeat_gateway/adapters/braintrust.py"]
  affects: ["tests/adapters/test_braintrust.py"]
tech_stack:
  added: []
  patterns: ["TDD red-green", "permanent-passthrough verify_signature (option-b)", "is_test guard as first normalize line"]
key_files:
  created:
    - heartbeat_gateway/adapters/braintrust.py
    - tests/adapters/test_braintrust.py
    - tests/fixtures/braintrust_logs.json
    - tests/fixtures/braintrust_is_test.json
    - tests/fixtures/braintrust_environment_update.json
  modified: []
decisions:
  - "option-b: verify_signature is permanent passthrough — Braintrust confirmed no webhook signing"
  - "condense() uses automation name not time/count fields to preserve dedup determinism in writer.py"
  - "is_test guard is first executable line in normalize() per BTST-02 constraint"
metrics:
  duration: "~15 minutes"
  completed_date: "2026-04-02"
  tasks_completed: 2
  files_created: 5
  files_modified: 0
---

# Phase 4 Plan 01: BraintrustAdapter Summary

**One-liner:** BraintrustAdapter with permanent-passthrough verify_signature, deterministic condense, and is_test guard — covering logs and environment_update event types across 11 TDD tests.

## What Was Built

`BraintrustAdapter` in `heartbeat_gateway/adapters/braintrust.py` implements the three required `WebhookAdapter` methods:

- `verify_signature` — permanent passthrough (always returns True); docstring documents the no-signing fact and recommends IP allowlisting as mitigation
- `normalize` — first line is the `is_test` guard per BTST-02; dispatches to `logs` and `environment_update` event types; returns None for unknown event types
- `condense` — deterministic 240-char summary using `automation["name"]` as stable identifier (never `details["count"]` or time fields, which break the 5-minute dedup window)

Three fixture JSON files provide realistic Braintrust webhook payloads. `test_braintrust.py` contains 11 test functions structured identically to `test_posthog.py`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 2 | Write failing test stubs (RED) | 977cd6e | tests/adapters/test_braintrust.py, 3 fixture JSON files |
| 3 | Implement BraintrustAdapter (GREEN) | d675900 | heartbeat_gateway/adapters/braintrust.py |

Note: Task 1 (HMAC checkpoint) was resolved by the user before this execution — decision: option-b.

## Test Results

- 11/11 new tests pass
- Full suite: 181 passed, 1 xfailed (up from 170 passed pre-plan)
- ruff: no issues on braintrust.py

## Decisions Made

**1. verify_signature is permanent passthrough (option-b)**
Braintrust does not sign webhook deliveries. Confirmed by checking braintrust.dev/docs/admin/automations/alerts, braintrust.dev/docs/security, and changelog — no HMAC header, no signing secret field in UI. Pattern mirrors AmplitudeAdapter (AMP-01).

**2. condense() uses automation name, not details fields**
`details["count"]` and time fields vary across redeliveries. Using `automation["name"]` (stable identifier) ensures the writer.py 5-minute dedup window works correctly.

**3. is_test guard position enforced**
The very first executable line of `normalize()` is the `is_test` check. No logic runs before it — this is a BTST-02 constraint.

## Deviations from Plan

None — plan executed exactly as written. Task 1 was pre-resolved by the user; Tasks 2 and 3 followed TDD order without deviation.

## Self-Check: PASSED

Files verified:
- heartbeat_gateway/adapters/braintrust.py: FOUND
- tests/adapters/test_braintrust.py: FOUND
- tests/fixtures/braintrust_logs.json: FOUND
- tests/fixtures/braintrust_is_test.json: FOUND
- tests/fixtures/braintrust_environment_update.json: FOUND

Commits verified:
- 977cd6e (test stubs): FOUND
- d675900 (implementation): FOUND
