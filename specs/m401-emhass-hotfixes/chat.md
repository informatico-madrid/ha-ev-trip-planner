# Chat Log — agent-chat-protocol

## Signal Legend

| Signal | Meaning |
|--------|---------|
| OVER | Task/turn complete, no more output |
| ACK | Acknowledged, understood |
| CONTINUE | Work in progress, more to come |
| HOLD | Paused, waiting for input or resource |
| STILL | Still alive/active, no progress but not dead |
| ALIVE | Initial check-in or heartbeat |
| CLOSE | Conversation closing |
| URGENT | Needs immediate attention |
| DEADLOCK | Blocked, cannot proceed |
| INTENT-FAIL | Could not fulfill stated intent |

## Message Format

### [<writer> → <addressee>] <HH:MM:SS> | <task-ID> | <SIGNAL>

Example: `[agent-1 → agent-2] 14:32:05 | task-3.2 | OVER`

## Example Messages

```text
[spec-executor → coordinator] 09:00:00 | task-1.1 | ALIVE
[coordinator → spec-executor] 09:00:01 | task-1.1 | ACK
[spec-executor → coordinator] 09:00:05 | task-1.1 | CONTINUE
[spec-executor → coordinator] 09:01:30 | task-1.1 | OVER
[coordinator → spec-executor] 09:01:31 | task-1.2 | OVER
```

<!-- Messages accumulate here. Append only. Do not edit or delete. -->