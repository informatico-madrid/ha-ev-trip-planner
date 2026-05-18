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
