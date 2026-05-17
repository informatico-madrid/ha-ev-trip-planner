# Auto-Router Rules para BMAD en Claude Code

> Este archivo define el mapeo sistemático de keywords → Agent + Skill + Command + Subagents.
> Cargado automáticamente en cada sesión.

## Fase 1: Analysis

| Keywords | Agent | Skill | Command | Subagents |
|----------|-------|-------|---------|-----------|
| "brainstorm", "ideate", "ideas", "nuevas features" | Carson (CIS Brainstorming Coach) | bmad-brainstorming | /brainstorm-project | Mary para research de mercado |
| "market research", "competitors", "landscape" | Mary (Analyst) | bmad-market-research | /market-research | Subagentes paralelos para análisis |
| "domain", "industry", "expertise" | Mary (Analyst) | bmad-domain-research | /domain-research | - |
| "technical research", "feasibility", "stack" | Winston (Architect) | bmad-technical-research | /technical-research | - |
| "brief", "product brief", "resumen" | Mary (Analyst) | bmad-product-brief | /create-brief | - |
| "prfaq", "working backwards", "press release" | Mary (Analyst) | bmad-prfaq | /prfaq | - |

## Fase 2: Planning

| Keywords | Agent | Skill | Command | Subagents |
|----------|-------|-------|---------|-----------|
| "prd", "product requirements", "requirements" | John (PM) | bmad-create-prd | /create-prd | Sally para UX, Winston para arquitectura |
| "edit prd", "improve prd", "update prd" | John (PM) | bmad-edit-prd | /edit-prd | - |
| "validate prd", "validar prd" | John (PM) | bmad-validate-prd | /validate-prd | - |
| "ux", "user experience", "interface", "wireframe" | Sally (UX Designer) | bmad-create-ux-design | /create-ux | - |
| "validate ux", "validar ux" | Sally (UX Designer) | bmad-validate-ux | /validate-ux | - |

## Fase 3: Solutioning

| Keywords | Agent | Skill | Command | Subagents |
|----------|-------|-------|---------|-----------|
| "architecture", "architect", "technical design" | Winston (Architect) | bmad-create-architecture | /create-architecture | John para FRs, Sally para UX |
| "validate architecture", "validar arquitectura" | Winston (Architect) | bmad-validate-architecture | /validate-architecture | - |
| "epics", "stories", "user stories" | John (PM) | bmad-create-epics-stories | /create-epics-stories | Winston para technical feasibility |
| "validate epics", "validar epics" | John (PM) | bmad-validate-epics-stories | /validate-epics-stories | - |
| "implementation readiness", "check readiness" | Winston (Architect) | bmad-check-implementation-readiness | /implementation-readiness | - |
| "generate project context", "project context" | Mary (Analyst) | bmad-generate-project-context | /generate-project-context | - |

## Fase 4: Implementation

| Keywords | Agent | Skill | Command | Subagents |
|----------|-------|-------|---------|-----------|
| "implement", "code", "build", "develop" | Amelia (Dev) | bmad-dev-story | /dev-story | Winston para arquitectura si se necesita |
| "quick", "small change", "fix", "bug" | Amelia (Dev) | bmad-quick-dev | /quick-dev | - |
| "story", "sprint story", "next story" | SM (Scrum Master) | bmad-create-story | /create-story | Amelia para development |
| "validate story", "validar story" | SM (Scrum Master) | bmad-validate-story | /validate-story | - |
| "sprint planning", "plan sprint" | SM (Scrum Master) | bmad-sprint-planning | /sprint-planning | John para priorities |
| "sprint status", "status" | SM (Scrum Master) | bmad-sprint-status | /sprint-status | - |
| "retrospective", "retro" | SM (Scrum Master) | bmad-retrospective | /retrospective | - |
| "correct course", "change direction", "pivote" | SM (Scrum Master) | bmad-correct-course | /correct-course | Winston, John |

## QA & Testing

| Keywords | Agent | Skill | Command | Subagents |
|----------|-------|-------|---------|-----------|
| "test", "tests", "coverage", "e2e" | Murat (TEA) | bmad-qa-generate-e2e-tests | /qa-automate | Amelia para unit tests |
| "test framework", "setup tests" | Murat (TEA) | bmad-testarch-framework | /testarch-framework | - |
| "test design", "plan tests" | Murat (TEA) | bmad-testarch-test-design | /testarch-test-design | - |
| "atdd", "acceptance tests" | Murat (TEA) | bmad-testarch-atdd | /testarch-atdd | - |
| "test review", "review tests" | Murat (TEA) | bmad-testarch-test-review | /testarch-test-review | - |
| "ci", "pipeline", "quality gates" | Murat (TEA) | bmad-testarch-ci | /testarch-ci | - |
| "traceability", "coverage matrix" | Murat (TEA) | bmad-testarch-trace | /testarch-trace | - |
| "nfr", "performance", "security" | Murat (TEA) | bmad-testarch-nfr | /testarch-nfr | - |
| "teach me testing", "learn testing" | Murat (TEA) | bmad-teach-me-testing | /teach-me-testing | - |

## Core Utilities

| Keywords | Agent | Skill | Command | Subagents |
|----------|-------|-------|---------|-----------|
| "review", "code review", "adversarial" | Winston (Architect) | bmad-review-adversarial-general | /adversarial-review | Amelia (dev), Murat (test) |
| "edge cases", "boundary" | - | bmad-review-edge-case-hunter | /edge-case-hunter | - |
| "party", "multi-agent", "discuss" | - | bmad-party-mode | /party-mode | Todos los agentes relevantes |
| "consensus", "agree", "align" | - | bmad-consensus-party | /consensus-party | Agentes relacionados |
| "document project", "documentar" | Paige (Tech Writer) | bmad-document-project | /document-project | Mary para analysis |
| "index docs", "index" | - | bmad-index-docs | /index-docs | - |
| "shard", "split doc" | - | bmad-shard-doc | /shard-doc | - |
| "distill", "compress", "resumir" | - | bmad-distillator | /distillator | - |
| "editorial", "review prose", "polish text" | Paige (Tech Writer) | bmad-editorial-review-prose | /editorial-prose | - |
| "review structure", "reorganize" | Paige (Tech Writer) | bmad-editorial-review-structure | /editorial-structure | - |

## Creative Intelligence Suite (CIS)

| Keywords | Agent | Skill | Command | Subagents |
|----------|-------|-------|---------|-----------|
| "design thinking", "empathy" | Maya (CIS Design Thinking) | bmad-cis-design-thinking | /cis-design-thinking | - |
| "problem solving", "crack" | Dr. Quinn (CIS Problem Solver) | bmad-cis-problem-solving | /cis-problem-solving | - |
| "innovation", "disrupt" | Victor (CIS Innovation) | bmad-cis-innovation-strategy | /cis-innovation-strategy | - |
| "storytelling", "narrative" | Sophia (CIS Storyteller) | bmad-cis-storytelling | /cis-storytelling | - |
| "presentation", "slides", "deck" | Caravaggio (CIS Presentation) | bmad-cis-agent-presentation-master | /cis-presentation-master | - |

## BMAD Builder Module

| Keywords | Agent | Skill | Command | Subagents |
|----------|-------|-------|---------|-----------|
| "create agent", "new agent" | - | bmad-agent-builder | /agent-builder | - |
| "build workflow", "create workflow" | - | bmad-workflow-builder | /workflow-builder | - |
| "module", "bmad module" | - | bmad-module-builder | /module-builder | - |
| "setup bmb", "install bmb" | - | bmad-bmb-setup | /bmb-setup | - |

## Meta & Help

| Keywords | Agent | Skill | Command | Subagents |
|----------|-------|-------|---------|-----------|
| "help", "bmad help", "que hacer" | - | bmad-help | /bmad-help | - |
| "advanced elicitation", "reconsider", "critique" | - | bmad-advanced-elicitation | /advanced-elicitation | - |
| "checkpoint", "human review", "walk me through" | - | bmad-checkpoint-preview | /checkpoint | - |

---

## Reglas de Delegación a Subagentes

### Siempre delegar a subagentes cuando:
1. **Tareas paralelas independientes** → Invocar subagentes simultáneamente
2. **Especialización clara** → El agente específico es marcadamente mejor
3. **Review/Validation** → Siempre usar subagente diferente al que escribió
4. **Research** → Búsquedas web delegadas a subagente con acceso a search
5. **Asimetría de información** → Para adversarial review, usar subagente "ciego"

### Ejemplo de Delegación:
```
Input: "review del codigo nuevo"
→ Agent: Winston (Architect) para liderar review
→ Skill: bmad-code-review
→ Subagents:
   ├─ Amelia (Dev) para análisis de implementación
   ├─ Murat (TEA) para análisis de coverage/tests
   └─ Subagente "blinded" para adversarial review
```

### Patrones de Delegación:

| Situación | Main Agent | Subagent 1 | Subagent 2 |
|-----------|-----------|------------|------------|
| PRD con UX | John (PM) | Sally (UX) | Winston (Architect) |
| Architecture con UX | Winston | John (FR mapping) | Sally (UX alignment) |
| Code Review | Winston | Amelia (dev) | Murat (test) |
| Market Research | Mary | Subagentes paralelos por sección |
| Sprint Planning | SM | John (priorities) | Amelia (estimation) |
| Party Mode | - | Todos relevantes | - |

---

## Mapeo de Fases BMAD

| Phase | Focus | Auto-load Agent | Skills | Commands |
|-------|-------|----------------|--------|----------|
| 1 | Analysis | Mary (Analyst) | bmad-brainstorming, bmad-domain-research | /brainstorm-project, /market-research |
| 2 | Planning | John (PM) | bmad-create-prd, bmad-create-ux-design | /create-prd, /create-ux |
| 3 | Solutioning | Winston (Architect) | bmad-create-architecture, bmad-check-implementation-readiness | /create-architecture, /implementation-readiness |
| 4 | Implementation | Amelia (Dev) | bmad-dev-story, bmad-sprint-planning | /dev-story, /sprint-planning |
| - | Anytime | SM (Scrum Master) | bmad-sprint-status, bmad-correct-course | /sprint-status, /correct-course |

---

*Generado automáticamente desde agent-manifest.csv, skill-manifest.csv, y bmad-help.csv*
*Última actualización: 2026-05-14*