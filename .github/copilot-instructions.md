# GitHub Copilot Instructions - EV Trip Planner

## 🎯 PROJECT CONTEXT
This is a **Home Assistant custom integration** for managing Electric Vehicle trip planning and charging optimization.
- **Repository**: https://github.com/informatico-madrid/ha-ev-trip-planner
- **Framework**: Home Assistant Core

## 🏛️ HOME ASSISTANT ARCHITECTURE - STRICT RULES

4. **Async First:** Home Assistant is completely asynchronous. ALWAYS use `async`/`await` for I/O and use non-blocking HTTP clients like `aiohttp`.

## 🏠 HOME ASSISTANT INSTANCES - PRODUCTION VS TEST

### Production Instance
- **Usage**: See real usage examples - DO NOT make direct changes

### Test Instance (test-ha)
- **URL**: http://localhost:18123 (mapped internally to 8123)
- **Docker**: `test-ha/docker-compose.yml`
- **Credentials and Access**: In `/home/malka/ha-ev-trip-planner/.env`
- **Purpose**: E2E tests, verifications during development

#### TESTS E2E
un Test E2E Funcional e Interactivo real usando Playwright para el flujo de "Crear un viaje".
Reglas obligatorias:
Prohibido el testeo estático superficial: No me sirve que solo compruebes que el panel está visible. Tienes que simular a un usuario real.
Interacción a través del Shadow DOM: Debes localizar los campos de entrada (input, select) y los botones de guardado que están dentro del panel utilizando el combinador de Shadow DOM de Playwright (ej. page.locator('ev-trip-planner-panel >> #campo-destino').fill('Madrid')).
Flujo completo: El test debe hacer lo siguiente:
Hacer clic en el botón de "Crear / Añadir Viaje" (penetrando el Shadow DOM).
Rellenar el formulario del viaje simulando escritura.
Hacer clic en el botón de guardar/enviar.
Validación dinámica del resultado: Después de enviar el formulario, el test debe esperar y validar que la tarjeta o el texto del nuevo viaje ha aparecido dinámicamente en la interfaz de la lista de viajes dentro del Shadow DOM.


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
