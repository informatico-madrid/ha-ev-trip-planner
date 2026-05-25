# 🔍 Informe de Auditoría de Documentación y Organización de Archivos

**Fecha:** 2026-05-24  
**Proyecto:** ha-ev-trip-planner  
**Rama activa:** `mutation-score-ramp`  
**Archivos en git:** 1,268 trackeados (22 MB)  
**Tamaño en disco:** ~960 MB (excluyendo `.git` y `node_modules`)  
**Tamaño `.git`:** 49 MB  

---

## 1. Resumen Ejecutivo

El repositorio sufre de **inflación severa de archivos auxiliares**: directorios de herramientas de IA (`.claude/`, `.qwen/`, `.roo/`, `.cursor/`, `.gemini/`, `.cline/`), frameworks de metodología (`_bmad/` con 352 archivos), outputs de workflows (`_bmad-output/`, `specs/` con 290 archivos), y artefactos temporales de testing/debug ocupan **más del 95% del espacio en disco** y **más del 70% de los archivos trackeados en git**. La documentación del proyecto está fragmentada entre 4 ubicaciones diferentes (`docs/`, `doc/`, `_ai/`, raíz) con solapamiento significativo.

---

## 2. Mapa de Directorios — Estado en Git vs Disco

### 2.1 Directorios EN GIT que no deberían estar

| Directorio | Archivos trackeados | Tamaño | Problema |
|---|---|---|---|
| `_bmad/` | 352 | 2.8 MB | Framework de metodología BMad completo. Debería ser dependencia externa, no embebido |
| `.agents/skills/` | 136 | 2.4 MB | Skills de IA copiados íntegramente. Origen canónico, pero 130 dirs es excesivo |
| `.claude/` | 24 | 22 MB | Config de Claude Code con skills duplicados (symlinks rotos trackeados como dirs) |
| `.qwen/` | 14 | 13 MB | Config de Qwen con skills duplicados vía symlinks |
| `.ralph/` | 26 | 1.1 MB | Scripts de orquestación Ralph. Herramienta interna, no código del proyecto |
| `.specify/` | 12 | 112 KB | Templates de SpecKit. Herramienta interna |
| `.research/` | 12 | 456 KB | Investigación de PR35 y bugs. Histórico, condensable |
| `.serena/` | 4 | 58 MB | Solo 4 trackeados pero 58 MB en disco (cache `.pkl` no trackeada) |
| `.harness/` | 2 | 8 KB | Mínimo, pero innecesario en git |
| `.gito/` | 1 | 8 KB | Config de herramienta gito |
| `_bmad-output/` | 35 | 10 MB | Outputs de workflows BMad: reviews, quality-gate baselines, research. **Histórico puro** |
| `specs/` | 290 | 7.8 MB | 40 subdirectorios de specs, muchos completados. Incluye `.progress.md`, `chat.md`, `task_review.md`, `.ralph-state.json` |
| `_ai/` | 12 | 264 KB | Documentación de IA: metodologías, case studies. Solapamiento con `docs/` |
| `doc/` | 4 | 20 KB | Borradores YAML y gaps analysis. Debería integrarse en `docs/` |
| `bmalph/` | 2 | 8 KB | Estado de fase de BMad Alpha. Archivo de estado temporal |

### 2.2 Directorios FUERA DE GIT (solo en disco) — Basura a limpiar

| Directorio | Archivos | Tamaño | Tipo | Acción |
|---|---|---|---|---|
| `.venv/` | 178,465 | 2.8 GB | Virtualenv Python 3.12.3 | ✅ Ya en `.gitignore` — mantener |
| `.venv-314-clean/` | 73,262 | 806 MB | Virtualenv Python 3.14.3 con `mutmut` | ⚠️ **Mantener** — único venv con mutmut instalado (`.venv` principal no lo tiene) |
| `node_modules/` | — | 151 MB | Deps JS | ✅ Ya en `.gitignore` — mantener |
| `e2e-diagnosis/` | 179 | 372 MB | Diagnóstico E2E temporal | 🗑️ **Borrar** — artefacto de debugging |
| `test-results1/` | 50 | 104 MB | Resultados de test antiguos | 🗑️ **Borrar** — residual |
| `mutants/` | 1,009 | 80 MB | Mutantes de mutmut | 🗑️ **Borrar** — artefacto de mutation testing |
| `MagicMock/` | 20,028 | 81 MB | Artefacto corrupto de mocking | 🗑️ **Borrar** — basura de debugging |
| `plans/` | 33 | 440 KB | Planes de arquitectura, investigación, RFCs, reviews | ⚠️ **Condensar** — contenido valioso, no borrar (ver §4.6) |
| `.playwright-mcp/` | 484 | 3.8 MB | Cache de Playwright MCP | 🗑️ **Borrar** — cache temporal |
| `.remember/` | 97 | 8.9 MB | Memoria de sesión de Roo Code (`now.md`, `recent.md`, `archive.md`, `today-*.done.md`, logs) | ⚠️ **Mantener** — usado activamente por Roo Code como memoria entre sesiones |
| `.roo/` | 2,080 | 21 MB | Skills + config de Roo Code | ⚠️ Evaluar — 130 dirs de skills duplicados |
| `.cline/` | 1,043 | 13 MB | Config de Cline AI | 🗑️ **Borrar** — herramienta no usada |
| `.cursor/` | 2,011 | 20 MB | Config de Cursor AI | 🗑️ **Borrar** — herramienta no usada |
| `.gemini/` | 1,043 | 13 MB | Config de Gemini AI | 🗑️ **Borrar** — herramienta no usada |
| `.claude/` (no trackeado) | 2,142 | 22 MB | Cache/sessions de Claude | ⚠️ **No tocar** — el usuario mantiene archivos adrede en `.claude/` |
| `.qwen/` (no trackeado) | 1,047 | 13 MB | Cache de Qwen | 🗑️ **Borrar cache** — mantener solo trackeados |
| `htmlcov/` | 89 | 7.4 MB | Coverage HTML | 🗑️ **Borrar** — regenerable |
| `coverage_html_report/` | 73 | 4.2 MB | Coverage HTML alternativo | 🗑️ **Borrar** — regenerable |
| `debug/` | 3 | 792 KB | Screenshots de debug | 🗑️ **Borrar** — no trackeados, basura |
| `qa/` | 47 | 1.5 MB | Screenshots de QA manual | 🗑️ **Borrar** — no trackeados, basura |
| `playwright-report/` | 1 | 588 KB | Reporte Playwright | 🗑️ **Borrar** — regenerable |
| `test-results/` | 1 | 4 KB | Resultados de test | 🗑️ **Borrar** — regenerable |
| `.pytest_cache/` | 7 | 312 KB | Cache pytest | 🗑️ **Borrar** — regenerable |
| `.ruff_cache/` | 45 | 236 KB | Cache ruff | 🗑️ **Borrar** — regenerable |
| `.import_linter_cache/` | 4 | 40 KB | Cache import linter | 🗑️ **Borrar** — regenerable |
| `.vscode/` | 2 | 8 KB | Config VS Code | ✅ **Mantener** — config del editor activo |

**Total recuperable en disco: ~-26 MB** (corregido: excluyendo `.venv-314-clean/` (806 MB), `plans/` (440 KB), `.remember/` (8.9 MB), y `.claude/` cache que no se toca)

> **Nota:** El total real recuperable es ~-26 MB si se borran solo los directorios marcados 🗑️. Los directorios `.venv-314-clean/`, `plans/`, `.remember/`, `.claude/` y `.vscode/` se mantienen por decisión del usuario.

---

## 3. Archivos Sueltos en Raíz — Clasificación

### 3.1 Archivos en git — Evaluación

| Archivo | Tamaño | En git | Veredicto |
|---|---|---|---|
| `.git-commit.lock` | 0 | ✅ | 🗑️ **Quitar de git** — lock file, no debería trackearse |
| `.progress.md` | 8 KB | ✅ | 🗑️ **Quitar de git** — estado temporal de agente |
| `.jscpd.json` | 4 KB | ✅ | ⚠️ Mantener — config de copy-paste detector |
| `.semgrep.yml` | 8 KB | ✅ | ⚠️ Mantener — config de security scanner |
| `skills-lock.json` | 8 KB | ✅ | 🗑️ **Quitar de git** — lock de skills de agente |
| `globalTeardown.ts` | 4 KB | ✅ | ⚠️ Mantener — teardown de Playwright |
| `auth.setup.ts` | 20 KB | ✅ | ⚠️ Mantener — auth setup de Playwright |
| `auth.setup.soc.ts` | 20 KB | ✅ | ⚠️ Mantener — auth setup SOC de Playwright |
| `configuration.yaml` | 4 KB | ✅ | 🗑️ **Quitar de git** — config de HA de desarrollo, no del componente |
| `docker-compose.staging.yml` | 4 KB | ✅ | ⚠️ Mantener — infra de staging |
| `Dockerfile.custom` | 4 KB | ✅ | ⚠️ Mantener — infra de staging |
| `requirements_dev.txt` | 4 KB | ✅ | ⚠️ Mantener — deps Python dev |
| `jest.config.js` | 4 KB | ✅ | 🗑️ **Quitar de git** — Jest no se usa (proyecto usa pytest + Playwright) |
| `tsconfig.e2e.json` | 4 KB | ✅ | ⚠️ Mantener — config TS para E2E |
| `playwright.soc.config.ts` | 4 KB | ✅ | ⚠️ Mantener — config Playwright SOC |
| `RELEASE_NOTES_v0.5.9.md` | — | ✅ | 🗑️ **Condensar** en CHANGELOG.md |
| `RELEASE_NOTES_v0.5.16.md` | — | ✅ | 🗑️ **Condensar** en CHANGELOG.md |
| `RELEASE_NOTES_v0.5.17.md` | — | ✅ | 🗑️ **Condensar** en CHANGELOG.md |
| `QWEN.md` | — | ✅ | 🗑️ **Quitar de git** — symlink roto a path absoluto |
| `CLAUDE.md` | 166 L | ✅ | ⚠️ Mantener — instrucciones para Claude Code |
| `CLAUDE.es.md` | 92 L | ✅ | ⚠️ Evaluar — versión española de CLAUDE.md |
| `TODO.md` | 169 L | ✅ | 🗑️ **Condensar** en ROADMAP.md o issues |
| `ROADMAP.md` | 576 L | ✅ | ⚠️ Mantener — roadmap del proyecto |
| `CHANGELOG.md` | 605 L | ✅ | ✅ Mantener — changelog del proyecto |
| `CONTRIBUTING.md` | 667 L | ✅ | ✅ Mantener — guía de contribución |
| `README.md` | 907 L | ✅ | ✅ Mantener — readme del proyecto |
| `LICENSE` | — | ✅ | ✅ Mantener — licencia |

### 3.2 Archivos fuera de git en raíz — Basura

| Archivo | Tamaño | Veredicto |
|---|---|---|
| `code-review-report.json` | 76 KB | 🗑️ **Borrar** — reporte temporal |
| `quality-gate-checkpoint.json` | 8 KB | 🗑️ **Borrar** — checkpoint temporal |
| `ui-map.local.md` | 12 KB | 🗑️ **Borrar** — mapa UI local |
| `playwright-env.local.md` | 4 KB | 🗑️ **Borrar** — env local |
| `.coverage` | 68 KB | 🗑️ **Borrar** — regenerable |
| `*.png` (16 screenshots) | ~560 KB | 🗑️ **Borrar** — screenshots de staging/debug, no trackeados |

---

## 4. Documentación — Análisis de Redundancia

### 4.1 Distribución actual (4 ubicaciones fragmentadas)

```
docs/          → 23 archivos (364 KB) — Documentación "oficial" del proyecto
_ai/           → 12 archivos (264 KB) — Documentación de IA/metodologías
doc/           →  4 archivos (20 KB)  — Borradores y gaps
raíz (*.md)    → ~10 archivos         — README, CHANGELOG, ROADMAP, etc.
```

### 4.2 Archivos condensables en `docs/`

| Archivo | Líneas | Problema | Acción |
|---|---|---|---|
| `docs/BUG-ANALYSIS-def_total_hours-7-6.md` | 148 | Bug específico ya resuelto | 📦 **Archivar** a `docs/archive/` |
| `docs/e2e-date-diagnosis-final.md` | 225 | Diagnóstico E2E puntual | 📦 **Archivar** a `docs/archive/` |
| `docs/staging-manual-verification.md` | 191 | Verificación manual de staging | 📦 **Archivar** a `docs/archive/` |
| `docs/staging-vehicle-5-trips-snapshot.md` | 189 | Snapshot de staging | 📦 **Archivar** a `docs/archive/` |
| `docs/staging-vs-e2e-separation.md` | 109 | Nota de separación staging/E2E | 📦 **Condensar** en `docs/development-guide.md` |
| `docs/source-tree-analysis.md` | 360 | Análisis del árbol de código | 📦 **Archivar** — ya no es actual |
| `docs/project-scan-report.json` | 107 | Reporte JSON de scan | 🗑️ **Borrar** — regenerable, dato temporal |
| `docs/simulation_trace_def_total_hours.py` | 357 | Script de simulación | 🗑️ **Mover** a `scripts/` o borrar |
| `docs/DOCS_DEEP_AUDIT.md` | 177 | Meta-auditoría de docs | 📦 **Archivar** — ya se está haciendo esta auditoría |
| `docs/MILESTONE_4_1_PLANNING.md` | — | Planning de milestone | 📦 **Archivar** si milestone completado |
| `docs/MILESTONE_4_POWER_PROFILE.md` | — | Spec de power profile | 📦 **Archivar** si milestone completado |
| `docs/staging-qa-results.md` | — | Resultados QA de staging | 🗑️ **Borrar** — en `.gitignore` pero aún referenciado |

### 4.3 Archivos condensables en `_ai/`

| Archivo | Líneas | Problema | Acción |
|---|---|---|---|
| `_ai/DEBUGGING-CASE-STUDY-def_total_hours-7-6.md` | 123 | Duplica `docs/BUG-ANALYSIS-def_total_hours-7-6.md` | 🗑️ **Condensar** — mantener solo en `docs/` |
| `_ai/IMPLEMENTATION_REVIEW.md` | 682 | Review de implementación | 📦 **Archivar** — histórico |
| `_ai/ai-development-lab.md` | 717 | Lab de desarrollo IA | 📦 **Archivar** — histórico |
| `_ai/SPECKIT_SDD_FLOW_INTEGRATION_MAP.md` | 418 | Mapa de flujo SpecKit | 📦 **Archivar** — referencia de herramienta |
| `_ai/TDD_METHODOLOGY.md` | 530 | Metodología TDD | ⚠️ **Mantener** — referencia activa para tests |
| `_ai/TESTING_E2E.md` | 438 | Guía E2E testing | ⚠️ **Mantener** — referencia activa |
| `_ai/CODEGUIDELINESia.md` | 591 | Guías de código IA | ⚠️ **Evaluar** — solapamiento con `docs/development-guide.md` |
| `_ai/PORTFOLIO.md` | 334 | Portfolio del proyecto | 🗑️ **Borrar** — auto-promoción, no doc técnica |
| `_ai/RALPH_METHODOLOGY.md` | 264 | Metodología Ralph | 📦 **Archivar** — referencia de herramienta |
| `_ai/SOLID_REFACTORING_CASE_STUDY.md` | 268 | Case study SOLID | 📦 **Archivar** — histórico |
| `_ai/charging-planning-functional-analysis.md` | 394 | Análisis funcional | ⚠️ **Mantener** — referencia de dominio |
| `_ai/index.md` | 198 | Índice de `_ai/` | ⚠️ **Mantener** — navegación |

### 4.4 Archivos en `doc/` — Integrar o archivar

| Archivo | Veredicto |
|---|---|
| `doc/borrador/perfildiferible.yml` | 📦 **Archivar** — borrador YAML de ejemplo EMHASS |
| `doc/borrador/perfildiferibletemplateejemplo.yml` | 📦 **Archivar** — template de ejemplo |
| `doc/gaps/EXECUTIVE_SUMMARY.md` | 📦 **Condensar** en `docs/architecture.md` o archivar |
| `doc/gaps/promptspecrfactor.md` | 📦 **Archivar** — prompt de spec, no doc de proyecto |

### 4.5 Solapamiento `RELEASE_NOTES_*.md` ↔ `CHANGELOG.md`

Los 3 archivos `RELEASE_NOTES_v0.5.*.md` (138 líneas totales) contienen información que **debería estar consolidada en** [`CHANGELOG.md`](CHANGELOG.md) (605 líneas). Son redundantes y fragmentan el historial de releases.

---

## 5. Archivos Basura Trackeados en Git

### 5.1 Archivos de backup/residual en código fuente

| Archivo | Problema |
|---|---|
| `custom_components/ev_trip_planner/frontend/panel.js.bak` | 🗑️ Backup de JS — **quitar de git** |
| `custom_components/ev_trip_planner/frontend/panel.js.fixed` | 🗑️ Versión fixed residual — **quitar de git** |
| `custom_components/ev_trip_planner/frontend/panel.js.old` | 🗑️ Versión old residual — **quitar de git** |
| `tests/conftest.py.bak` | 🗑️ Backup de conftest — **quitar de git** |

### 5.2 Archivos de estado temporal de agentes en `specs/`

Dentro de los 290 archivos trackeados en `specs/`, hay **55 archivos de estado temporal** que no deberían estar en git:

- **17× `.progress.md`** — Estado de progreso de cada spec
- **4× `.ralph-state.json`** — Estado del loop Ralph
- **14× `chat.md`** — Transcripciones de chat con agentes
- **14× `task_review.md`** — Reviews de tareas completadas

### 5.3 Symlinks rotos trackeados

| Archivo | Problema |
|---|---|
| `QWEN.md` | Symlink a path absoluto `/home/malka/...` — **roto en otros clones** |
| `.claude/skills/*` (28 dirs) | Symlinks a `.agents/skills/` trackeados como directorios — git los convirtió en copias |
| `.qwen/skills/*` (22 dirs) | Symlinks a `.agents/skills/` — mismo problema |

### 5.4 Outputs de quality-gate en `_bmad-output/`

El directorio `_bmad-output/quality-gate/baseline/20260509-092405/` contiene **20 archivos de texto/JSON** con outputs crudos de herramientas (ruff, pyright, pytest, mutation, etc.). El archivo `antipatterns-tier-a.txt` tiene **25,015 líneas**. Estos son artefactos regenerables, no documentación.

---

## 6. Directorios de Skills de IA — Triplicación

Los skills de agentes están **triplicados** en el repositorio:

| Ubicación | Tipo | Tamaño | Trackeado |
|---|---|---|---|
| `.agents/skills/` (32 skills) | **Origen canónico** (archivos reales) | 2.4 MB | ✅ 136 archivos |
| `.claude/skills/` (28 skills) | Symlinks → `.agents/skills/` | 22 MB (cache) | ✅ 24 trackeados |
| `.qwen/skills/` (22 skills) | Symlinks → `.agents/skills/` | 13 MB (cache) | ✅ 14 trackeados |
| `.roo/skills/` (130 dirs) | **Copias completas** (no symlinks) | 21 MB | ❌ No trackeado |

**Problema:** `.roo/skills/` contiene **130 directorios** con copias completas de skills BMad que ya están en `_bmad/` (352 archivos trackeados). Esto es una **cuadruplicación** de contenido de skills.

---

## 7. Plan de Acción Recomendado

### 🔴 Prioridad Alta — Limpieza de basura en disco

```bash
# 1. Borrar directorios basura fuera de git
#    NOTA: NO borrar .venv-314-clean/ (Python 3.14 + mutmut, necesario)
#    NOTA: NO borrar plans/ (condensar, ver §4.6)
#    NOTA: NO borrar .remember/ (memoria activa de Roo Code)
#    NOTA: NO borrar .claude/ (archivos mantenidos adrede por el usuario)
#    NOTA: NO borrar .vscode/ (config del editor activo)
rm -rf e2e-diagnosis/ test-results1/ mutants/ MagicMock/
rm -rf .playwright-mcp/ .cline/ .cursor/ .gemini/
rm -rf htmlcov/ coverage_html_report/ debug/ qa/ playwright-report/ test-results/
rm -rf .pytest_cache/ .ruff_cache/ .import_linter_cache/

# 2. Borrar archivos basura en raíz
rm -f code-review-report.json quality-gate-checkpoint.json ui-map.local.md
rm -f playwright-env.local.md .coverage *.png
```

### 🟠 Prioridad Alta — Quitar archivos basura de git

```bash
# 3. Quitar del tracking archivos que no deben estar en git
git rm --cached .git-commit.lock .progress.md skills-lock.json
git rm --cached configuration.yaml  # config de desarrollo local
git rm --cached jest.config.js       # Jest no se usa
git rm --cached QWEN.md              # symlink roto
git rm --cached custom_components/ev_trip_planner/frontend/panel.js.bak
git rm --cached custom_components/ev_trip_planner/frontend/panel.js.fixed
git rm --cached custom_components/ev_trip_planner/frontend/panel.js.old
git rm --cached tests/conftest.py.bak

# 4. Quitar del tracking archivos de estado temporal en specs/
git rm --cached "specs/*/.progress.md" "specs/*/.ralph-state.json"
git rm --cached "specs/*/chat.md" "specs/*/task_review.md"
```

### 🟡 Prioridad Media — Condensar documentación

| Acción | Detalle |
|---|---|
| **Condensar RELEASE_NOTES** | Mover contenido de los 3 `RELEASE_NOTES_*.md` a `CHANGELOG.md` y borrar los archivos |
| **Condensar TODO.md** | Migrar items a GitHub Issues o integrar en `ROADMAP.md` |
| **Integrar `doc/`** | Mover contenido útil a `docs/` y borrar `doc/` |
| **Condensar `_ai/`** | Mover `_ai/DEBUGGING-CASE-STUDY-*` a `docs/archive/` (duplica `docs/BUG-ANALYSIS-*`), archivar históricos |
| **Mover script** | `docs/simulation_trace_def_total_hours.py` → `scripts/` |
| **Borrar `_ai/PORTFOLIO.md`** | No es documentación técnica |
| **Condensar `plans/`** | Ver §4.6 — 33 archivos condensables en ~10 temáticos |

### 4.6 Análisis de `plans/` — Condensación

El directorio `plans/` (33 archivos, 440 KB, **no trackeado en git**) contiene documentación valiosa de arquitectura, investigación y RFCs. No es basura, pero está fragmentado y puede condensarse:

| Categoría | Archivos | Propuesta |
|---|---|---|
| **LangGraph/BMad Engine** | `langgraph-bmad-execution-engine-plan.md`, `langgraph-bmad-hello-world-plan.md`, `langgraph-bmad-integration-research.md`, `INTEGRATED_PLAN.md` | 📦 Condensar en `docs/archive/langgraph-bmad-engine.md` |
| **Harness Quality Gate** | `harness-implementation-plan.md`, `harness-quality-gate-architect-review.md`, `harness-quality-gate-dev-review.md`, `harness-quality-gate-research.md`, `harness-quality-gate-test-review.md` | 📦 Condensar en `docs/archive/harness-quality-gate.md` |
| **Spec3 Reviews** | `spec3-design-review.md`, `spec3-requirements-review.md`, `spec3-tasks-review.md`, `spec3-doc-update-plan.md` | 📦 Condensar en `specs/3-solid-refactor/reviews.md` |
| **EMHASS Comunidad** | `emhass-discussion-integration.md`, `emhass-response-github.md`, `emhass-response-github-cookbook.md`, `emhass-stateful-context-rfc-contribution.md` | 📦 Condensar en `docs/archive/emhass-community-contributions.md` |
| **Mutation Testing** | `mutation-quality-gate.md`, `mutation-testing-guide.md` | 📦 Mover a `docs/` como docs de referencia activa |
| **Quality Gate** | `quality-gate-iterative-architecture.md`, `makefile-parallel-optimization.md` | 📦 Condensar en `docs/archive/quality-gate-architecture.md` |
| **Staging Docker** | `entorno-docker-local-stagging/` (6 archivos) | 📦 Condensar en `docs/staging-docker-setup.md` |
| **Varios** | `auto-skill-loading-plan.md`, `doc-update-mutation-score-ramp.md`, `impact-analysis-fixing-critical-1-2.md`, `linkedin-article-ai-development-lab.md`, `tooling-foundation-verification.md`, `index.md`, `research/` | 📦 Archivar individualmente o condensar |

**Resultado esperado:** 33 archivos → ~10 documentos condensados + `index.md` actualizado.

### 🟢 Prioridad Media — Archivar specs completados

```bash
# 5. Mover specs completados a archivo
mkdir -p specs/archive/
# Mover specs de milestones completados (001, 007-013, 017, 020, etc.)
```

Evaluar cada subdirectorio de `specs/`: los que tengan todas sus tareas completadas deberían moverse a `specs/archive/`.

### 🔵 Prioridad Baja — Reestructuración de skills de IA

| Acción | Detalle |
|---|---|
| **Evaluar `_bmad/`** | 352 archivos trackeados de framework BMad. Considerar si puede ser submodule o dependencia externa |
| **Limpiar `.roo/skills/`** | 130 dirs con copias completas (21 MB no trackeados). Borrar y recrear como symlinks a `.agents/skills/` |
| **`.claude/skills/`** | ⚠️ **No tocar** — el usuario mantiene archivos adrede en `.claude/` |
| **Revisar `.qwen/skills/`** | Mismo problema que `.claude/skills/` — evaluar con el usuario antes de modificar |

### ⚪ Prioridad Baja — Actualizar `.gitignore`

Agregar entradas faltantes:

```gitignore
# Archivos de estado temporal de agentes
**/.progress.md
**/.ralph-state.json
specs/*/chat.md
specs/*/task_review.md

# Lock files
.git-commit.lock
skills-lock.json

# Symlinks de skills de agentes (se recrean localmente)
# NOTA: .claude/skills/ NO tocar — el usuario mantiene archivos adrede
.qwen/skills/

# Config de desarrollo local
configuration.yaml

# Jest (no se usa)
jest.config.js

# Symlinks rotos
QWEN.md
```

---

## 8. Métricas Resumen

| Métrica | Valor |
|---|---|
| Archivos trackeados en git | 1,268 |
| Archivos de documentación trackeados | ~80 (docs + _ai + doc + specs + _bmad-output) |
| Archivos de framework/metodología trackeados | ~490 (_bmad + .agents + .claude + .qwen + .ralph + .specify) |
| Archivos de specs trackeados | 290 |
| Archivos basura en git | ~25 (backups, locks, symlinks rotos, estado temporal) |
| Espacio recuperable en disco (solo 🗑️) | ~660 MB (excluyendo `.venv-314-clean/`, `plans/`, `.remember/`, `.claude/`, `.vscode/`) |
| Directorios de agente fuera de git (borrables) | 5 (~127 MB: `.cline/`, `.cursor/`, `.gemini/`, `.playwright-mcp/`) |
| Screenshots basura en raíz | 16 (~560 KB) |
| Documentación condensable | ~48 archivos (15 en docs/ + 33 en plans/) |
| Specs archivables | ~20 subdirectorios (estimado) |

---

## 9. Nota sobre `.venv-314-clean/`

| Atributo | Valor |
|---|---|
| Python | 3.14.3 |
| Paquete clave | `mutmut` 3.5.0 (NO disponible en `.venv` principal) |
| `.venv` principal | Python 3.12.3, sin `mutmut` |
| Makefile | Usa `.venv/bin/mutmut` (línea 339) pero **mutmut no está instalado** en `.venv` |
| **Conclusión** | `.venv-314-clean/` es el **único venv funcional para mutation testing**. No borrar. Se recomienda instalar `mutmut` en `.venv` principal para unificar. |

---

## 10. Nota sobre `.remember/`

| Atributo | Valor |
|---|---|
| Uso | Memoria de sesión de **Roo Code** (agente de VS Code) |
| Contenido | `now.md` (contexto actual), `recent.md` (resumen reciente), `archive.md` (histórico semanal), `today-*.done.md` (logs diarios), `logs/` (logs de autoguardado), `tmp/` (temporales) |
| En git | ❌ No trackeado (`.gitignore` lo excluye) |
| Tamaño | 8.9 MB (97 archivos) |
| **Conclusión** | **Mantener** — es la memoria activa entre sesiones de Roo Code. Borrarlo causaría pérdida de contexto del agente. Los archivos `today-*.done.md` antiguos podrían purgarse periódicamente. |

---

## 11. Estructura Propuesta de Documentación

```
docs/
├── index.md                    ← Portal de documentación
├── architecture.md             ← Arquitectura (mantener)
├── api-contracts.md            ← Contratos API (mantener)
├── data-models.md              ← Modelos de datos (mantener)
├── development-guide.md        ← Guía de desarrollo (mantener + condensar staging-vs-e2e)
├── project-overview.md         ← Overview (mantener)
├── emhass-setup.md             ← Setup EMHASS (mantener)
├── DASHBOARD.md                ← Dashboard doc (mantener)
├── VEHICLE_CONTROL.md          ← Control vehículo (mantener)
├── REGLAS_DE_NEGOCIO.md        ← Reglas negocio (mantener)
├── SHELL_COMMAND_SETUP.md      ← Shell commands (mantener)
├── mutation-testing.md         ← Mutation testing guide (mantener)
├── ai-guidelines/              ← Nuevo: condensar _ai/ activo
│   ├── code-guidelines.md
│   ├── tdd-methodology.md
│   └── e2e-testing.md
└── archive/                    ← Nuevo: históricos
    ├── BUG-ANALYSIS-def_total_hours-7-6.md
    ├── e2e-date-diagnosis-final.md
    ├── staging-manual-verification.md
    ├── staging-vehicle-5-trips-snapshot.md
    ├── source-tree-analysis.md
    ├── DOCS_DEEP_AUDIT.md
    ├── MILESTONE_4_1_PLANNING.md
    ├── MILESTONE_4_POWER_PROFILE.md
    ├── emhass-community-contributions.md  ← Condensado de plans/
    ├── harness-quality-gate.md            ← Condensado de plans/
    ├── langgraph-bmad-engine.md           ← Condensado de plans/
    └── quality-gate-architecture.md       ← Condensado de plans/

plans/                          ← Condensar (33 → ~10 archivos)
├── index.md                    ← Índice actualizado
├── mutation-testing-guide.md   ← Mover a docs/ como referencia activa
├── mutation-quality-gate.md    ← Mover a docs/ como referencia activa
├── staging-docker-setup.md     ← Condensado de entorno-docker-local-stagging/
└── ... (archivos restantes tras condensación)
```

---

*Este informe es de solo lectura — no se ha modificado ningún archivo del proyecto.*
