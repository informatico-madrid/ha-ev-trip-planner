## 🎯 PROJECT CONTEXT
This is a **Home Assistant custom integration** for managing Electric Vehicle trip planning and charging optimization.
- **Repository**: https://github.com/informatico-madrid/ha-ev-trip-planner
- **Framework**: Home Assistant Core

## 🏛️ HOME ASSISTANT ARCHITECTURE - STRICT RULES

4. **Async First:** Home Assistant is completely asynchronous. ALWAYS use `async`/`await` for I/O and use non-blocking HTTP clients like `aiohttp`. Every `async` call **must** be `await`ed — never fire-and-forget, as unawaited coroutines are silently skipped.

## 🏠 HOME ASSISTANT INSTANCES - PRODUCTION VS TEST

### Production Instance
- **Usage**: See real usage examples - DO NOT make direct changes


## 📋 PYTHON CODING STANDARDS
- **Formatting & Linting:** Code must comply with `black` (88 chars), `isort`, `pylint`, and `pyright`.
- **Typing & Docs:** Type hints and Google-style docstrings are REQUIRED for all public functions and classes.
- **Logging:** ALWAYS use `%s` format for logging (e.g., `_LOGGER.debug("Data: %s", data)`). DO NOT use f-strings or string concatenation in log payloads.
- **File Naming & Conventions:**
  - Modules & Functions: `snake_case` (e.g., `trip_manager.py`, `async_setup_entry`)
  - Classes: `PascalCase` (e.g., `EVTripPlannerCoordinator`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_CONSUMPTION`)
  - Private methods/vars: Must have a leading underscore (e.g., `_calculate_internal`)

## 🧹 CLEAN CODE RULES (MANDATORY)

### TDD Workflow (Red-Green-Refactor)
- **RED:** Always start with a failing test for a micro-feature
- **GREEN:** Write minimal code to pass the test
- **REFACTOR:** Optimize for DRY/SOLID only after tests pass
- **Never proceed to GREEN without a failing test**

### DRY Enforcement
- Extract repeated logic immediately
- Flag duplicate code for refactoring
- Create shared utilities after second repetition

### SOLID Compliance
- **Single Responsibility:** One purpose per function/class
- **Open/Closed:** Extend via interfaces/abstractions
- **Liskov Substitution:** Interchangeable subtypes
- **Interface Segregation:** Split large interfaces
- **Dependency Inversion:** Depend on abstractions, not concretions

### Workflow Rules
1. Break features into micro-tasks (max 5-10 lines of code per task)
2. For each micro-task follow RED → GREEN → REFACTOR cycle
3. Propose design patterns (Strategy, Factory, etc.) early
4. Isolate concerns — no mixing of UI, business logic, and I/O
5. **KISS + YAGNI:** No speculative implementation, simplest solution that works

### Legacy Code Rules
- Create adapter layers for external services
- Wrap legacy components with facade pattern

### Architecture Rules
- Code against interfaces when complexity warrants it
- No class > 200 lines


## 📝 COMMIT MESSAGES
When asked to generate a commit message, strictly use Conventional Commits format:
`feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`

## TOOL USAGE FOR MAKING CHANGES

- Use read_file to verify content before making changes
- If you are implementing tasks, always read docs/IMPLEMENTATION_REVIEW.md for any important notes left by the reviewer that may help you in your task.

## ⚠️ TWO HA ENVIRONMENTS — NEVER MIX

> E2E and Staging are completely separate. See CLAUDE.md section "ENVIRONMENT SEPARATION".

- **E2E** = `hass` direct (no Docker), port 8123, deterministic tests in `tests/e2e/`
- **Staging** = Docker container, port 8124, persistent, for agent navigation (NO tests)

## Stuck State Protocol

<mandatory>

Los tests e2e se ejecutan con make e2e. tiene un script de lipmieza de carpetas y procesos antes de cada ejecución. 
**If the same task fails 3+ times with different errors each time, you are stuck.**
Do NOT make another edit. Entering stuck state is mandatory.

**Stuck ≠ "try harder". Stuck = the model of the problem is wrong.**

### Step 1: Stop and diagnose

Write a one-paragraph diagnosis before touching any file:
- What exactly is failing (smallest failing unit, not the symptom)
- What assumption each previous fix was based on
- Which assumption was wrong

### Step 2: Investigate — breadth first, not depth first

Investigate in this order, stopping when you find the root cause:

1. **Source code** — read the actual implementation being tested/called, not just the interface. The real behavior often differs from the expected behavior.
2. **Existing tests** — find passing tests for similar components. They show the exact mocking pattern that works in this codebase.
3. **Library/framework docs** — WebSearch `"<library> <class/method> testing" site:docs.<lib>.io` or `"<library> <error text> pytest"`. Docs reveal constraints invisible from the source.
4. **Error message verbatim** — WebSearch the exact error text. Someone has hit this before.
5. **Redesign** — if investigation reveals the test is testing at the wrong abstraction level, redesign: extract the logic into a standalone function and test that instead.

### Step 3: Re-plan before re-executing

After investigation, write one sentence: "The root cause is X, so the fix is Y."
If you can't write that sentence clearly, investigate more.
Only then make the next edit.
</mandatory>

## Test Writing Rules (MANDATORY)

1. AWAIT ALL ASYNC: Every test calling an async function MUST use `await`.
   Never call async functions without await — pytest won't fail loudly,
   it will silently skip the coroutine.

2. FIXTURES FIRST: Before writing test methods that use parameters, define
   ALL fixtures at the top of the file with @pytest.fixture.
   Run the file with `pytest -x <file>` before moving on.

3. DO NOT SELF-MARK VERIFY TASKS: Never mark V0/V1/V5/VF tasks as [x]
   yourself. Verify tasks are marked [x] ONLY after running the full suite
   (`pytest --cov`) and confirming **100% coverage**. Show the output in your
   commit message.

4. **100% COVERAGE IS THE TARGET**: Every module, function, and branch must be
   covered. No exceptions. If a line is hard to test, refactor it — don't skip it.

Cuándo usan pragma: no cover
Los patrones aceptados en home-assistant/core son muy concretos:

Ramas imposibles de alcanzar en test — Por ejemplo, código que solo se ejecuta si falla algo del sistema operativo, o ramas else de un TYPE_CHECKING block (que solo existe en tiempo de análisis estático, no de ejecución)

Overloads de typing — Funciones decoradas con @overload que son solo para type checkers como pyright, nunca se ejecutan realmente

Bloques if TYPE_CHECKING: — Todo lo que está dentro de este bloque se excluye porque no se ejecuta en runtime

Métodos abstractos triviales — raise NotImplementedError en clases base que se prueban a través de sus subclases

Un ejemplo real de mqtt/entity.py en el repo oficial:

python
if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.core import HomeAssistant
Lo que los revisores humanos saben (y el agente no)
Esta es la clave de tu pregunta. Los revisores humanos de HA (o tú mismo como maintainer) tienen que juzgar si un pragma: no cover está justificado. Un agente de IA o Copilot que genere tests no sabe automáticamente qué líneas son genuinamente intesteables vs. cuáles el desarrollador simplemente no quiso testear. Los revisores necesitan saber:

Uso aceptado	Uso rechazado
if TYPE_CHECKING: blocks	Lógica de negocio compleja
@overload decorators	Manejo de errores reales
raise NotImplementedError en ABC	Ramas de configuración
Imports de plataforma específica (ej. Windows-only)	Cualquier código que podría fallar en producción
El 100% no es obligatorio en todos los niveles
Importante aclarar: el 100% de cobertura solo es requisito Platinum. Gold requiere alta cobertura pero no el 100%. La realidad en los repos más grandes es que llegan a ese número con una combinación de:

Tests muy exhaustivos que cubren casi todo

# pragma: no cover aplicado quirúrgicamente en código genuinamente inaccesible

Un coveragerc o pyproject.toml que excluye patrones globalmente (por ejemplo, todos los if TYPE_CHECKING: bloques del repositorio entero)

El archivo .coveragerc de home-assistant/core define exclusiones globales de patrones como if TYPE_CHECKING:, @overload, y raise NotImplementedError, por lo que los contributors individuales ni siquiera tienen que poner el pragma en esos casos.

## E2E Testing Rules — Home Assistant + Lit Web Components

> **CRITICAL**: Home Assistant uses Lit Web Components with `mode: "open"` Shadow DOM.
> Playwright auto-pierces open shadow DOM with ALL locators EXCEPT XPath.

### Selector Priority (use in this order)
1. `getByRole()` — most robust, accessibility-native, auto-pierces shadow DOM
2. `getByLabel()` / `getByPlaceholder()` — semantic form elements
3. `getByText()` — text-based matching
4. `getByTestId()` — data attributes (if available)
5. CSS selector — auto-pierces open shadow DOM (no special syntax)
6. **XPath PROHIBITED** — does NOT pierce shadow roots

### Forbidden Patterns
- `page.goto('/ev_trip_planner')` — NOT allowed in HA Container; use authenticated navigation via `window.location` or click-through HA UI
- XPath selectors inside shadow trees — will NOT find elements
- `>>` syntax — NOT a pierce syntax; not valid CSS (use `>` for child combinator)

### Shadow DOM Architecture
```text
<home-assistant> (open shadow root)
  └── <home-assistant-panel> (open shadow root)
       └── ev-trip-planner-panel (open shadow root)
            └── Trip UI: buttons, forms, cards
```
Playwright auto-traverses all open shadow roots with web-first locators.

### Dialog Handling
- Native browser dialogs (alert/confirm): set up `page.on('dialog', ...)` BEFORE triggering action
- Use `setupDialogHandler()` from `tests/e2e/trips-helpers.ts`
- Use `setupAlertHandler()` from `trips-helpers.ts` for alerts

### Debug
- `npx playwright test --debug` — opens Playwright inspector
- `await page.pause()` — pauses execution, opens browser inspector for shadow DOM inspection
- `npx playwright show-trace` — analyze test traces

### Skills
When writing E2E tests, invoke `playwright-best-practices` from `.agents/skills/playwright-best-practices/`. Key file: `core/locators.md` lines 177-203 for Shadow DOM patterns.

### Run E2E Tests
```bash
make e2e          # Full E2E test suite
npx playwright test --debug  # Debug mode
```