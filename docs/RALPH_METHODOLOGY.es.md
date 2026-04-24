# Metodología de Desarrollo — Smart Ralph Fork

> **TL;DR**: Este plugin se desarrolló usando [**`informatico-madrid/smart-ralph`**](https://github.com/informatico-madrid/smart-ralph),
> un fork de [tzachbon/smart-ralph](https://github.com/tzachbon/smart-ralph) que extiende el loop de
> desarrollo spec-driven con verificación agéntica en tiempo real. El proyecto es deliberadamente
> un **laboratorio de pruebas del propio plugin** — y a la vez un plugin funcional y en producción.

---

## Índice

- [El proyecto como laboratorio](#el-proyecto-como-laboratorio)
- [Qué es Smart Ralph](#qué-es-smart-ralph)
- [El fork: informatico-madrid/smart-ralph](#el-fork-informatico-madridsmartralph)
- [Cómo se desarrolló este proyecto](#cómo-se-desarrolló-este-proyecto)
- [Historial de specs](#historial-de-specs)
- [Configuración de agentes](#configuración-de-agentes)
- [El revisor en tiempo real](#el-revisor-en-tiempo-real)
- [Verificación E2E](#verificación-e2e)
- [Nota histórica: ralph-speckit](#nota-histórica-ralph-speckit)
- [Agradecimientos](#agradecimientos)

---

## El proyecto como laboratorio

Este plugin nació con un doble propósito, explícito y sin disculpas:

1. **Laboratorio deliberado** para probar el loop spec-driven con agentes IA en condiciones reales,
   sobre un dominio con complejidad genuina (Home Assistant, EMHASS, vehículos eléctricos).
2. **Plugin funcional y útil** — que resuelve un problema real y está en uso en producción.

Ambos objetivos son compatibles. El hecho de que el entorno de desarrollo sea un experimento
no hace el resultado menos válido. Al contrario: las specs que guiaron cada feature fueron
revisadas y ejecutadas por agentes especializados, lo que eleva la calidad de la implementación
por encima de lo que una sesión de pair-programming ad hoc produciría.

Si encuentras que algo está sobrediseñado, bien documentado o tiene más cobertura de tests
de la esperada para un proyecto de este tamaño — ahora sabes por qué.

---

## Qué es Smart Ralph

[Smart Ralph](https://github.com/tzachbon/smart-ralph) es un plugin para Claude Code y Codex
que convierte una idea de feature en un conjunto de specs estructuradas y las ejecuta tarea a tarea,
con contexto fresco por tarea y agentes especializados por fase.

El flujo estándar tiene 4 fases de ejecución tras la planificación:

```
Research → Requirements → Design → Tasks → Implement
  │           │             │        │         │
  ↓           ↓             ↓        ↓         ↓
research.md  requirements  design  tasks.md  ejecución
              .md           .md              tarea a tarea
```

Cada fase usa un sub-agente especializado: `research-analyst`, `product-manager`,
`architect-reviewer`, `task-planner`, `spec-executor`, `qa-engineer`.

El patrón está basado en el [Ralph agentic loop](https://ghuntley.com/ralph/) de Geoffrey Huntley.

---

## El fork: informatico-madrid/smart-ralph

**Repositorio:** [`informatico-madrid/smart-ralph`](https://github.com/informatico-madrid/smart-ralph)
**Upstream:** [`tzachbon/smart-ralph`](https://github.com/tzachbon/smart-ralph) (v3.x)

El upstream para en **Phase 4: Quality Gates** (lint, tipos, CI). Este fork añade una
**Phase 5: Agentic Verification Loop** que no existe en el upstream:

| Fase | Upstream | Fork |
|------|----------|------|
| Phase 1: Make It Work | ✅ | ✅ |
| Phase 2: Refactoring | ✅ | ✅ |
| Phase 3: Testing | ✅ | ✅ |
| Phase 4: Quality Gates | ✅ | ✅ |
| Phase 5: Verification | ❌ | ✅ |

La Fase 5 introduce:
- **VE Tasks** (`[VE]`) — tareas de verificación generadas automáticamente por `task-planner`
- **Verification Contract** — bloque estructurado en `requirements.md` con entry points,
  señales observables, invariantes y seed data
- **Señales estructuradas** — `VERIFICATION_PASS`, `VERIFICATION_FAIL`, `VERIFICATION_DEGRADED`, `ESCALATE`
- **Loop de reparación** — cuando `VERIFICATION_FAIL`: clasifica el fallo, corrige, reintenta;
  si falla 2 veces, escala al humano
- **Barrido de regresión** — basado en el `Dependency map` del Verification Contract,
  no en la suite completa

El fork también soporta `@playwright/mcp` como capa de señal de browser, aunque en este
proyecto la verificación browser se ejecuta en modo degradado (ver sección [Verificación E2E](#verificación-e2e)).

> **Estado del PR upstream:** El fork tiene divergencias sustanciales respecto al upstream.
> Existe un PR en draft con las contribuciones para Phase 5, pero la magnitud de los cambios
> requiere un proceso de contribución más cuidadoso antes de abrirlo formalmente.

---

## Cómo se desarrolló este proyecto

Cada feature, fix o refactor de este plugin siguió este proceso:

1. **Idea o bug** → se lanza `/ralph-specum:start` (o `/ralph-specum:triage` para epics grandes)
2. **Research** → el agente `research-analyst` analiza el codebase existente y el dominio HA
3. **Requirements** → `product-manager` genera user stories + Verification Contract
4. **Design** → `architect-reviewer` decide patrones, estructura, estrategia de tests
5. **Tasks** → `task-planner` descompone en tareas atómicas, inyecta `[VE]` tasks, marca `[P]` para tareas paralelas
6. **Implement** → `spec-executor` ejecuta tarea a tarea con contexto fresco
7. **Verificación continua** → `qa-engineer` revisa la implementación en tiempo real y corrige al agente si se desvía

Las 12 skills de dominio en `.agents/skills/` se cargan según la fase:
`homeassistant-skill`, `homeassistant-best-practices`, `homeassistant-ops`,
`homeassistant-config`, `homeassistant-dashboard-designer`,
`e2e-testing-patterns`, `playwright-best-practices`,
`python-testing-patterns`, `python-performance-optimization`,
`python-security-scanner`, `python-cybersecurity-tool-development`,
`github-actions-docs`.

Esto garantiza que los agentes tienen contexto específico del ecosistema HA y no solo
conocimiento genérico de Python.

---

## Historial de specs

Todo el historial de specs está en `specs/`. A lo largo del proyecto se generaron
**más de 20 specs**, cubriendo desde la creación de viajes hasta el refactor SOLID actual.

### Specs principales (época smart-ralph)

| Spec | Qué resolvió |
|------|--------------|
| `trip-creation` | Sistema base de creación y gestión de viajes |
| `charging-window-calculation` | Algoritmo de ventanas de carga y perfil binario |
| `soc-integration-baseline` | Integración baseline del estado de carga (SOC) |
| `soc-milestone-algorithm` | Algoritmo SOC-aware con margen de seguridad |
| `emhass-integration-with-fixes` | Integración EMHASS con correcciones de compatibilidad |
| `emhass-sensor-enhancement` | Mejora de sensores EMHASS con atributos extendidos |
| `emhass-sensor-entity-lifecycle` | Ciclo de vida correcto de entidades sensor |
| `duplicate-emhass-sensor-fix` | Fix de sensores duplicados tras recarga |
| `e2e-trip-crud` | Verificación E2E de operaciones CRUD de viajes |
| `trip-card-enhancement` | Mejoras en la card de viaje del dashboard |
| `regression-orphaned-sensors-ha-core-investigation` | Investigación de sensores huérfanos en HA core |
| `automation-template` | Templates de automatización para carga |
| `solid-refactor-coverage` | Refactor SOLID + cobertura de tests (spec activa) |
| `_epics/` | Epics de triage para features cross-cutting |

### Evolución del naming

El naming de las specs refleja la madurez del proceso. Las specs de la época speckit
(ver [Nota histórica](#nota-histórica-ralph-speckit)) usaban prefijos numéricos (`001-`, `007-`...).
Con el cambio a smart-ralph el naming pasó a ser descriptivo y libre, más fácil de navegar
y buscar.

---

## Configuración de agentes

```
.agents/
└── skills/                          # Skills de dominio cargadas por los agentes
    ├── homeassistant-skill/         # Core HA — entities, states, services
    ├── homeassistant-best-practices/ # Patrones recomendados HA
    ├── homeassistant-config/        # Configuración yaml / config entries
    ├── homeassistant-ops/           # Operaciones: restart, logs, debugging
    ├── homeassistant-dashboard-designer/ # Lovelace / dashboards
    ├── e2e-testing-patterns/        # Patrones E2E genéricos
    ├── playwright-best-practices/   # Playwright selectors, waits, assertions
    ├── python-testing-patterns/     # pytest, mocks, fixtures
    ├── python-performance-optimization/ # Optimización Python
    ├── python-security-scanner/     # Análisis de seguridad estático
    ├── python-cybersecurity-tool-development/ # Herramientas de seguridad
    └── github-actions-docs/         # CI/CD workflows

CLAUDE.md                            # → .github/copilot-instructions.md
                                     #   + docs/CODEGUIDELINESia.md
```

Las guías de código están centralizadas en `docs/CODEGUIDELINESia.md` y
`.github/copilot-instructions.md`. Todos los agentes las reciben como contexto obligatorio
al arrancar, lo que asegura consistencia de estilo y patrones entre specs.

---

## El revisor en tiempo real

Una de las capacidades más valiosas probadas en este proyecto es el **revisor en tiempo real**:
el agente `qa-engineer` opera en paralelo al `spec-executor` y revisa la implementación
mientras se produce, no después.

Esto significa que si el agente se desvía del diseño, introduce un anti-pattern o rompe
un invariante definido en el Verification Contract, el `qa-engineer` interviene en la misma
sesión de implementación — antes de que el error se propague a tareas posteriores.

En la práctica, esto se tradujo en:
- Correcciones de arquitectura detectadas durante la implementación de `emhass-sensor-entity-lifecycle`
- Detección temprana de violaciones SOLID en el refactor actual (`solid-refactor-coverage`)
- Prevención de regresiones en sensores cuando se añadió el soporte de múltiples vehículos

---

## Verificación E2E

La verificación E2E en este proyecto opera en **modo multi-señal**, adaptado al entorno
de Home Assistant donde un browser controlado por el agente no es el canal principal:

| Capa de señal | Qué verifica |
|---------------|--------------|
| **pytest + HA test framework** | Lógica de negocio, ciclo de vida de entidades, servicios |
| **CLI / logs** | Errores de integración, registros en `.storage/`, arranque limpio |
| **HTTP / API** | Contratos de servicios HA, respuestas de endpoints |
| **Browser (MCP Playwright)** | Flujos reales de usuario en el dashboard Lovelace |

La capa browser se gestiona via `@playwright/mcp` y las skills en `.agents/skills/playwright-best-practices/`
y `.agents/skills/e2e-testing-patterns/`. La integración completa del loop de verificación
browser con chat en tiempo real está en proceso de evaluación en el entorno HA específico de este proyecto.

Cuando la capa browser no está disponible, los agentes emiten `VERIFICATION_DEGRADED`
y continúan con las capas CLI, HTTP y pytest — el loop no se detiene.

---

## Nota histórica: ralph-speckit

Antes de migrar a smart-ralph, las primeras specs de este proyecto se generaron con
**`ralph-speckit`** — el plugin alternativo de Smart Ralph que implementa la
[metodología spec-kit de GitHub](https://github.com/github/spec-kit) con gobernanza
basada en constitución.

Esas specs se reconocen por su prefijo numérico (`001-`, `007-`... `020-`) y están
documentadas en `docs/SPECKIT_SDD_FLOW_INTEGRATION_MAP.md`.

El cambio a smart-ralph (fork) permitió naming más libre, epics via triage, y la
Fase 5 de verificación agéntica. Los aprendizajes de la época speckit informaron
directamente el diseño de las specs posteriores.

---

## Agradecimientos

Este proyecto no existiría en su forma actual sin el trabajo de:

- **[Tzach Bonfil](https://github.com/tzachbon)** — autor y mantenedor de
  [`tzachbon/smart-ralph`](https://github.com/tzachbon/smart-ralph), el upstream
  del fork. Un plugin extraordinariamente bien diseñado que convierte el desarrollo
  agentico en algo practicable y reproducible. Muchas gracias por compartirlo.

- **[Geoffrey Huntley](https://ghuntley.com/ralph/)** — creador del patrón
  [Ralph agentic loop](https://ghuntley.com/ralph/) en el que se basa todo el sistema.
  La idea de "Ralph no piensa demasiado, Ralph hace la siguiente tarea" es
  deceptivamente poderosa.

> El fork [`informatico-madrid/smart-ralph`](https://github.com/informatico-madrid/smart-ralph)
> tiene un PR en draft hacia upstream con las contribuciones de Phase 5. Cuando las
> divergencias se estabilicen, la intención es contribuir de vuelta lo que sea
> generalizable — especialmente las VE tasks y el Verification Contract.

---

*Documento mantenido por [@informatico-madrid](https://github.com/informatico-madrid).*
*Última revisión: abril 2026.*
