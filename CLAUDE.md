## ⚠️ ENVIRONMENT SEPARATION — READ BEFORE ANYTHING ELSE

> **There are TWO completely separate HA environments. NEVER mix them.**

| | **E2E** | **Staging** |
|---|---|---|
| **Purpose** | Deterministic automated tests | Agent navigation + real-user verification |
| **Port** | `:8123` | `:8124` |
| **HA starts via** | `hass` direct (Python venv, NO Docker) | Docker Compose (persistent container) |
| **Config dir** | `/tmp/ha-e2e-config/` (ephemeral) | `~/staging-ha-config/` (persistent) |
| **Agents use** | NO — only automated Playwright tests | YES — Playwright MCP to navigate UI |
| **Tests** | `tests/e2e/` (`.spec.ts` files) | **NONE** — staging has zero tests |
| **Command** | `make e2e` | `make staging-up` |

**RULES:**
1. **E2E tests NEVER use Docker.** If you see `docker compose` in E2E context, it's wrong.
2. **Staging NEVER has tests.** If you see `.spec.ts` files in staging, it's wrong.
3. **Agents navigate staging with Playwright MCP** — never run `npx playwright test` on staging.
4. **E2E tests run against `hass` directly** — never connect to staging's Docker container.

See [`docs/staging-vs-e2e-separation.md`](docs/staging-vs-e2e-separation.md) for full rules.

## MANDATORY OPEN AND APPLY .github/copilot-instructions.md and _ai/CODEGUIDELINESia.md
- Load `.github/copilot-instructions.md` as project context

## BMAD-METHOD Integration

Use `/bmalph` to navigate phases. Use `/bmad-help` to discover all commands. Use `/bmalph-status` for a quick overview. See `_bmad/COMMANDS.md` for a full command reference.

## 📚 DOMINIO Y REGLAS DE NEGOCIO — COLD MEMORY

> **IMPORTANTE:** Este proyecto tiene un documento de dominio específico para agentes IA.

Cuando necesites entender las reglas de negocio, cálculos, o comportamiento del sistema:
- **Consulta [`docs/REGLAS_DE_NEGOCIO.md`](docs/REGLAS_DE_NEGOCIO.md)**
- Es **cold memory** — cargar bajo demanda cuando se necesitan detalles de dominio
- Contiene: glossary, SOC cap dinámico, propagación de déficit, ventanas de carga, parámetros EMHASS, casos de uso reales

Este documento es la **fuente de verdad** para el dominio del EV Trip Planner. Todos los agentes deben referenciarlo antes de tomar decisiones sobre reglas de negocio.

## 🔄 HARNESS SELF-IMPROVEMENT — Hook System

### Hook: PRE-TASK
**ANTES de cualquier tarea**, leer `.harness/agent-feedback/` si existe feedback previo.

### Hook: POST-TASK
**DESPUÉS de tarea >30 min o con errores significativos**, crear archivo en `sessions/` y actualizar `patterns.md` si hay patrón nuevo.

### Indicadores de tarea compleja
- Duró >30 min, errores inesperados, múltiples intentos, frustración del usuario

### Archivos
| Archivo | Propósito |
|---------|-----------|
| [`.harness/agent-feedback/README.md`](.harness/agent-feedback/README.md) | Plantilla feedback |
| [`.harness/agent-feedback/patterns.md`](.harness/agent-feedback/patterns.md) | Plantilla patrones |

## ⚡ AUTO-ROUTING — Skills, Commands & Agents

> **IMPORTANT:** This project uses an **Auto-Router System**. Before responding to ANY user prompt, you MUST:

1. **Load Auto-Router Rules**: Read `_bmad/_config/auto-router-rules.md`
2. **Match Keywords**: Check if the user's prompt matches any keywords in the rules
3. **Auto-Load Elements**: If matched, automatically load the appropriate:
   - **Agent** (via agent skill invocation)
   - **Skill** (via `skill:skill-name`)
   - **Command** (via slash command or workflow)
4. **Delegate to Subagents**: When rules specify subagents, invoke them for parallel execution

### Example Auto-Routing Flow:
```
User: "let's brainstorm the new authentication feature"

1. Load auto-router-rules.md
2. Match: "brainstorm" → Carson agent + bmad-brainstorming skill + /brainstorm-project command
3. Also match: "authentication" → Mary for security research subagent
4. Load bmad-brainstorming skill
5. Invoke Carson (CIS Brainstorming Coach) agent
6. Delegate to Mary subagent for parallel research
```

### Key Agents:
| ID | Name | Role |
|----|------|------|
| bmad-agent-analyst | Mary | Market research, competitive analysis, requirements |
| bmad-agent-pm | John | Product Manager - PRD, requirements discovery |
| bmad-agent-ux-designer | Sally | UX Designer - user research, interaction design |
| bmad-agent-architect | Winston | Architect - distributed systems, API design |
| bmad-agent-dev | Amelia | Developer - story execution, TDD |
| bmad-agent-tech-writer | Paige | Technical Writer - documentation |
| bmad-tea | Murat | Test Architect - risk-based testing |
| bmad-cis-agent-brainstorming-coach | Carson | Brainstorming Specialist |

### When to Delegate:
- **Parallel independent tasks** → Invoke subagents simultaneously
- **Specialization** → Use the clearly best agent for that domain
- **Review/Validation** → Always use a different subagent than the author
- **Research** → Delegate to subagent with web search access
- **Asymmetric review** → Use "blinded" subagent for adversarial review

### Phase Auto-Loading:
| Phase | Primary Agent | Auto-load Skills | Commands |
|-------|--------------|------------------|-----------|
| 1-Analysis | Mary | bmad-brainstorming, bmad-market-research | /brainstorm-project |
| 2-Planning | John | bmad-create-prd, bmad-create-ux-design | /create-prd |
| 3-Solutioning | Winston | bmad-create-architecture | /create-architecture |
| 4-Implementation | Amelia | bmad-dev-story, bmad-qa-generate-e2e-tests | /dev-story |

### Phases

| Phase | Focus | Key Commands |
|-------|-------|-------------|
| 1. Analysis | Understand the problem | `/create-brief`, `/brainstorm-project`, `/market-research` |
| 2. Planning | Define the solution | `/create-prd`, `/create-ux` |
| 3. Solutioning | Design the architecture | `/create-architecture`, `/create-epics-stories`, `/implementation-readiness` |
| 4. Implementation | Build it | `/sprint-planning`, `/create-story`, then `/bmalph-implement` for Ralph |

### Workflow

1. Work through Phases 1-3 using BMAD agents and workflows (interactive, command-driven)
2. Run `/bmalph-implement` to transition planning artifacts into Ralph format, then start Ralph

### Management Commands

| Command | Description |
|---------|-------------|
| `/bmalph-status` | Show current phase, Ralph progress, version info |
| `/bmalph-implement` | Transition planning artifacts → prepare Ralph loop |
| `/bmalph-upgrade` | Update bundled assets to match current bmalph version |
| `/bmalph-doctor` | Check project health and report issues |

### Available Agents

| Command | Agent | Role |
|---------|-------|------|
| `/analyst` | Analyst | Research, briefs, discovery |
| `/architect` | Architect | Technical design, architecture |
| `/pm` | Product Manager | PRDs, epics, stories |
| `/sm` | Scrum Master | Sprint planning, status, coordination |
| `/dev` | Developer | Implementation, coding |
| `/ux-designer` | UX Designer | User experience, wireframes |
| `/qa` | QA Engineer | Test automation, quality assurance |

## STAGING HOME ASSISTANT — Playwright Navigation

> **Breadcrumb:** Si usas `playwright` MCP para navegar `localhost:8124` (HA staging), carga primero `.claude/skills/home-assistant-best-practices.md` — instructions sobre web components, Shadow DOM y formularios de HA. No intentes usar `browser_snapshot`/`browser_click [ref=xxx]` con elementos de HA — web components no aparecen en el árbol de accesibilidad.

- Always run them via the Makefile
- API calls are strictly prohibited
- Must replicate real user behavior. If the test cannot replicate real user behavior, it is invalid, indicating either a flaw in the test design or an error in the application code.
