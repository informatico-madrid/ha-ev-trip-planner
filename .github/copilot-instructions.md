# GitHub Copilot Instructions - EV Trip Planner

## 🎯 PROJECT CONTEXT
This is a **Home Assistant custom integration** for managing Electric Vehicle trip planning and charging optimization.
- **Repository**: https://github.com/informatico-madrid/ha-ev-trip-planner
- **Framework**: Home Assistant Core

## 🏛️ HOME ASSISTANT ARCHITECTURE - STRICT RULES

4. **Async First:** Home Assistant is completely asynchronous. ALWAYS use `async`/`await` for I/O and use non-blocking HTTP clients like `aiohttp`.

## 🏠 HOME ASSISTANT INSTANCES - PRODUCTION VS TEST

### Production Instance
- **Credentials and Access**: In `/home/malka/.env`
- **Usage**: See real usage examples - DO NOT make direct changes

### Test Instance (test-ha)
- **URL**: http://localhost:18124 (mapped internally to 8123)
- **Docker**: `test-ha/docker-compose.yml`
- **Credentials and Access**: In `/home/malka/ha-ev-trip-planner/.env`
- **Purpose**: E2E tests, verifications during development

**IMPORTANT**:
- For **[VERIFY:BROWSER]** and **[VERIFY:API]** verifications during Ralph Loop, use test-ha
- DO NOT use production credentials in tests - use `.env` with test tokens
- **NO SUPERVISOR API:** Use REST API skills at `/home/malka/.agents/skills/home-assistant-rest-api` instead.

### Difference: [VERIFY:BROWSER] vs E2E Tests

| Aspect | [VERIFY:BROWSER] (in tasks.md) | E2E Tests (tests/e2e/) |
|--------|--------------------------------|------------------------|
| **Purpose** | Ad-hoc verification of a specific task | Formal complete test suite |
| **Execution** | Once per task during implementation | Run independently |
| **Tool** | mcp-playwright (browser) | Playwright (playwright.config.ts) |
| **Signal** | Requires `STATE_MATCH` | Test suite results |
| **Example** | "Verify that the panel renders and js error" | "Complete vehicle CRUD" |

**To start test-ha before Ralph Loop:**
```bash
.ralph/scripts/start_test_ha.sh start
```

## 📋 PYTHON CODING STANDARDS
- **Formatting & Linting:** Code must comply with `black` (88 chars), `isort`, `pylint`, and `mypy`.
- **Typing & Docs:** Type hints and Google-style docstrings are REQUIRED for all public functions and classes.
- **Logging:** ALWAYS use `%s` format for logging (e.g., `_LOGGER.debug("Data: %s", data)`). DO NOT use f-strings or string concatenation in log payloads.
- **File Naming & Conventions:**
  - Modules & Functions: `snake_case` (e.g., `trip_manager.py`, `async_setup_entry`)
  - Classes: `PascalCase` (e.g., `EVTripPlannerCoordinator`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_CONSUMPTION`)
  - Private methods/vars: Must have a leading underscore (e.g., `_calculate_internal`)

## 🧪 TESTING REQUIREMENTS
- Write tests for EVERY new feature with >80% coverage target.
- **Mandatory HA Tools:** Always use the `pytest-homeassistant-custom-component` library.
- **Fixtures:** You MUST include the `enable_custom_integrations` fixture in the test suite to prevent core blocking.
- **API Mocking:** Never make real network requests. Use `aioclient_mock` to simulate and mocking all HTTP/API responses (both 200 successes and errors like 401/404).
- **Playwright for UI:** Use Playwright for e2e testing. 

## 📝 COMMIT MESSAGES
When asked to generate a commit message, strictly use Conventional Commits format:
`feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`

## TOOL USAGE FOR MAKING CHANGES

- Read the entire file before attempting to make changes
- Ensure the text to replace exactly matches the file content
- Use read_file to verify content before making changes