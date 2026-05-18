MANDATORY OPEN AND APPLY .github/copilot-instructions.md and _ai/CODEGUIDELINESia.md
- Load `.github/copilot-instructions.md` as project context

## BMAD-METHOD Integration

Use `/bmalph` to navigate phases. Use `/bmad-help` to discover all commands. Use `/bmalph-status` for a quick overview. See `_bmad/COMMANDS.md` for a full command reference.

## ⚡ AUTO-ROUTING — Skills, Commands & Agents

> **IMPORTANTE:** Este proyecto usa un **Sistema de Auto-Routing**. ANTES de responder a CUALQUIER prompt del usuario, DEBES:

1. **Cargar Auto-Router Rules**: Lee `_bmad/_config/auto-router-rules.md`
2. **Match Keywords**: Verifica si el prompt del usuario coincide con alguna keyword en las reglas
3. **Auto-Cargar Elementos**: Si hay match, cargar automáticamente:
   - **Agent** (via invocación de agent skill)
   - **Skill** (via `skill:skill-name`)
   - **Command** (via slash command o workflow)
4. **Delegar a Subagentes**: Cuando las reglas especifican subagentes, invocarlos para ejecución paralela

### Ejemplo de Flujo de Auto-Routing:
```
Usuario: "vamos a hacer un brainstorm de la nueva feature de autenticación"

1. Cargar auto-router-rules.md
2. Match: "brainstorm" → Carson agent + bmad-brainstorming skill + /brainstorm-project command
3. También match: "autenticación" → Mary para investigación de seguridad subagent
4. Cargar bmad-brainstorming skill
5. Invocar Carson (CIS Brainstorming Coach) agent
6. Delegar a Mary subagent para investigación paralela
```

### Agentes Principales:
| ID | Nombre | Rol |
|----|--------|-----|
| bmad-agent-analyst | Mary | Investigación de mercado, análisis competitivo |
| bmad-agent-pm | John | Product Manager - PRD, discovery de requisitos |
| bmad-agent-ux-designer | Sally | UX Designer - investigación de usuario, diseño de interacción |
| bmad-agent-architect | Winston | Arquitecto - sistemas distribuidos, diseño de API |
| bmad-agent-dev | Amelia | Developer - ejecución de stories, TDD |
| bmad-agent-tech-writer | Paige | Technical Writer - documentación |
| bmad-tea | Murat | Test Architect - testing basado en riesgo |
| bmad-cis-agent-brainstorming-coach | Carson | Brainstorming Specialist |

### Cuándo Delegar:
- **Tareas paralelas independientes** → Invocar subagentes simultáneamente
- **Especialización** → Usar el agente claramente mejor para ese dominio
- **Review/Validación** → Siempre usar un subagente diferente al autor
- **Research** → Delegar a subagente con acceso a búsqueda web
- **Review asimétrico** → Usar subagente "ciego" para adversarial review

### Auto-Carga por Fase:
| Fase | Agente Principal | Skills Auto-cargar | Commands |
|-------|-----------------|-------------------|----------|
| 1-Análisis | Mary | bmad-brainstorming, bmad-market-research | /brainstorm-project |
| 2-Planificación | John | bmad-create-prd, bmad-create-ux-design | /create-prd |
| 3-Solutioning | Winston | bmad-create-architecture | /create-architecture |
| 4-Implementación | Amelia | bmad-dev-story, bmad-qa-generate-e2e-tests | /dev-story |

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
