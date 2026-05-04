---
name: bmad-consensus-party
description: 'Iterative consensus-building skill that runs BMAD Party Mode in loops until agents reach consensus. Each iteration enriches context with previous round findings, project domain knowledge, and relevant evidence. Use when you need multi-agent validation, architectural decisions, technical debates, or any situation where consensus is the goal and isolated opinions are insufficient.'
---

# BMAD Consensus Party

Run BMAD Party Mode iteratively — with **context enrichment between rounds** — until the agents reach consensus. This is not a single-round discussion. It's a **convergent process** where each party builds on the last, agents respond to prior arguments with evidence, and consensus emerges naturally from accumulated understanding.

## Core Philosophy

Most multi-agent discussions are one-shot: agents give opinions, the user picks one, done. This skill treats consensus as a **process**, not an event. The same question asked after 3 rounds of evidence-backed debate is fundamentally different from the same question asked cold — agents have refined their understanding, challenged each other's assumptions, and converged on the truth.

## When to Use

- Architectural decisions that affect multiple components
- Technical debates where multiple valid approaches exist
- Validation of complex features before implementation
- Security or safety-critical decisions
- Any question where "it depends" is unsatisfying and you need a definitive answer

## Consensus Criteria

Consensus is reached when ANY of these conditions is met:

| Type | Definition |
|------|------------|
| **Full consensus** | All participating agents agree on the same conclusion |
| **Majoritarian** | ≥ N-1 agents agree (e.g., 3 of 4), remaining agents don't object |
| **Evidential** | All agents agree the evidence supports the conclusion, even if they frame it differently |
| **Timeout** | Max rounds reached — present accumulated findings as best effort |

## Iterations and Rounds

```
Iteration N
├── Round 1: Agents A, B debate question Q
│   └── Output: Positions P_A1, P_B1
├── Round 2: Agents A, B respond to each other's positions with NEW evidence
│   └── Output: Positions P_A2, P_B2 (enriched)
├── ...
└── Consensus check → If not reached → Next Iteration
```

Each **iteration** is a full Party Mode cycle. Each iteration **enriches** the context fed to the next by injecting:

1. A summary of all previous rounds and positions
2. The strongest evidence each agent cited
3. Key disagreements and why they persist
4. Relevant domain knowledge or project context discovered mid-debate

## Context Enrichment Pipeline

After each round, before moving to the next:

### Step 1: Extract Round Findings
For each agent response, identify:
- **Stated position**: What the agent believes
- **Supporting evidence**: What facts, code, or logic the agent cited
- **Concession**: What the agent acknowledged from other agents
- **Outstanding disagreement**: What the agent still disputes and why

### Step 2: Build Iteration Summary
Create a structured summary (keep under 500 words):

```markdown
## Iteration N — Round Summary

### Question Under Debate
{original question}

### Agent Positions (Round N)
- **Agent A**: {position}, evidence: {evidence cited}, concessions: {what A conceded}
- **Agent B**: {position}, evidence: {evidence cited}, concessions: {what B conceded}

### Key Disagreements
1. { disagreement 1 } — reason it persists
2. { disagreement 2 } — reason it persists

### Convergence Signals
- {any partial agreement detected}
- {any evidence that shifted an agent's position}

### New Context for Next Round
- {domain knowledge discovered this round}
- {project-specific context that applies}
- {code or architecture that is relevant}
```

### Step 3: Inject Enriched Context
For the next round, prepend to each agent's prompt:

```markdown
## Previous Rounds Summary

{round summary from Step 2}

## Instructions for This Round
- You are responding to Round {N+1} of this debate.
- Your fellow agent(s) have already given their positions (see above).
- You MUST engage with their specific arguments — not just repeat your prior position.
- If you were wrong in a previous round, acknowledge it and update your position.
- Cite NEW evidence if you are changing your stance.
- Be precise about what you agree and disagree with.
```

## Consensus Detection

After each round, analyze agent responses for:

### Signals of Consensus
- Agents use similar language to describe the solution
- Agents cite the same evidence
- An agent explicitly says "I agree with X's analysis"
- No agent raises new objections in 2 consecutive rounds

### Signals of Stalemate
- Agents repeating the same arguments without new evidence
- The disagreement is semantic, not technical
- Agents agree on facts but not on values/priorities

### Signals to Stop (Timeout)
- Max rounds reached (default: 5 iterations, 3 rounds each)
- A Round N+1 response is identical to Round N (no movement)
- User interrupts

## Agent Selection Strategy

### First Iteration
Pick agents based on the domain of the question:
- Technical architecture → Winston (Architect) + Amelia (Developer)
- Testing/quality → Murat (Test Architect)
- Product/UX → Sally (UX Designer) + John (PM)
- Requirements → Mary (Business Analyst)

### Subsequent Iterations
After seeing where agents disagree, bring in agents that can adjudicate the specific dispute:
- If the disagreement is about data integrity → Amelia with data analysis
- If the disagreement is about user impact → Sally with UX evidence
- If the disagreement is about implementation risk → Winston with technical review

Rotate agents to avoid groupthink. If 3 iterations use Winston + Amelia + John, switch to Winston + Murat + Mary in iteration 4.

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_iterations` | 5 | Stop after N iterations even without consensus |
| `rounds_per_iteration` | 3 | Party Mode rounds before consensus check |
| `consensus_threshold` | `majoritarian` | `full`, `majoritarian`, `evidential` |
| `context_limit_words` | 400 | Max words per context block per agent |
| `enrichment_summary_words` | 500 | Max words for iteration summary |

## Exit Conditions

### Consensus Reached
When consensus criteria are met, present:

```markdown
## Consensus Reached ✓

**Conclusion**: {the agreed position}

**Confidence**: {high / medium / low} — based on evidence strength and agreement breadth

**Supporting Evidence**:
- {evidence 1}
- {evidence 2}

**Dissenting Notes** (if any agent disagreed):
- {agent}: {remaining concern}
```

### Timeout Reached
When max iterations are exhausted:

```markdown
## Best Effort Conclusion

**After {N} iterations, consensus was not reached.**

**Converged Positions**:
- {what agents agreed on}
- {what remains unresolved}

**Recommendation**: {suggested path forward — more investigation, user decision, A/B test, etc.}
```

## When NOT to Use

- Quick clarifying questions (use normal discussion)
- Questions with a single correct answer (e.g., "what color is the sky")
- When the user just wants a report, not validation (use technical-research skill instead)
- Situations where agents don't have sufficient domain expertise in the project

## Interaction with bmad-party-mode Skill

This skill **extends** `bmad-party-mode`, not replaces it. The consensus loop is built **around** Party Mode calls — each Party Mode invocation is one "round" within an iteration. You MUST invoke the `bmad-party-mode` skill using the skill tool for each round, not simulate it.

## Example Flow

```
User: "Should we use Redis or a file-based store for trip cache?"

→ Iteration 1
  → Round 1: Spawn Winston + Amelia via bmad-party-mode
  → Winston: Redis is faster but adds operational complexity
  → Amelia: File-based is simpler but has concurrency issues at scale
  → No consensus

→ Iteration 2
  → Build enriched context with round 1 findings
  → Spawn Winston + Amelia + Mary (bringing in business context)
  → Round 2: Agents now have prior positions + Mary introduces data volume requirements
  → Winston revises: "Given Mary says <1000 trips, file-based is sufficient"
  → Amelia: "Concurrency is only an issue if multiple HA instances"
  → Mary clarifies: "Single HA instance"
  → Amelia concedes: "Then file-based is fine"
  → Consensus: File-based store is appropriate for single-instance deployment