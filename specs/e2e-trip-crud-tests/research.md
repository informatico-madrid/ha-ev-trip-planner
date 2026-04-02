# Research: E2E Trip CRUD Tests — Investigation Plan

## ⚠️ Methodology Note

This document distinguishes between **confirmed facts** (verified by reading code or test output) and **hypotheses** (working theories pending confirmation). Nothing in the Hypotheses section should be treated as a fix until confirmed.

---

## 🟢 ROOT CAUSE — CONFIRMED

### RC-1: `baseURL` se evalúa en el momento de cargar el config, NO cuando corren los tests

**Evidencia directa** de `playwright.config.ts` (SHA: `03f470f75460aa7b9ffd53c6b1c7c700fa1a83c9`):

```typescript
// playwright.config.ts — líneas ~50-62
baseURL: (() => {
  const serverInfoPath = path.join(authDir, 'server-info.json');
  try {
    const serverInfo = JSON.parse(fs.readFileSync(serverInfoPath, 'utf-8'));
    return new URL(serverInfo.link).origin;  // ← lee el fichero AQUÍ
  } catch (error) {
    console.warn('Could not read server-info.json, using default localhost:8123');
    return 'http://localhost:8123';           // ← FALLBACK cuando no existe
  }
})()
```

Esta IIFE (función autoejecutable) se ejecuta **cuando Node.js carga `playwright.config.ts`**.
En ese momento, `globalSetup` todavía NO ha corrido — `server-info.json` no existe o tiene datos de una ejecución anterior.

**Resultado:**
- El `baseURL` que ven todos los tests es `http://localhost:8123` (o el puerto de un run anterior)
- `global.setup.ts` crea el servidor efimero en, por ejemplo, el puerto `8528`
- `auth.setup.ts` guarda tokens válidos para el puerto `8528`
- Todos los tests navegan a `http://localhost:8123/dashboard` → **404**
- El sidebar de HA nunca aparece → `waitFor({ state: 'visible' })` lanza timeout

**Evidencia de los tests:**
```
Could not read server-info.json, using default localhost:8123   ← log de la IIFE
...
[GlobalTeardown] Cleaning up server at: http://127.0.0.1:8528/...  ← puerto real
31 failed                                                           ← resultado
```

El puerto real era `8528`. El `baseURL` usó `localhost:8123`. Diferencia = causa de todos los 404.

---

### RC-2: `navigateViaSidebar()` hace `page.goto(baseURL + '/dashboard')` — hereda el bug de RC-1

**Evidencia de `trips.page.ts`** (SHA: `55b569f7bfd03076ac70390f674442ceecb45039`):

```typescript
// trips.page.ts — líneas ~187-193
async navigateViaSidebar(): Promise<void> {
  await this.page.goto(`${baseUrl}/dashboard`, { waitUntil: 'domcontentloaded' });
  await this.sidebar.waitFor({ state: 'visible', timeout: 10000 });
  await this.evTripPlannerMenuItem.click();
}
```

Donde `baseUrl` viene del `baseURL` del config — que es `localhost:8123` por RC-1.
Por esto **TODOS los tests fallan** en `navigateViaSidebar()`, incluyendo los de US-1 que antes pasaban.

---

## Hechos Confirmados

| ID | Hecho | Fuente |
|----|-------|--------|
| F1 | `baseURL` es una IIFE que corre al cargar el config, antes de `globalSetup` | `playwright.config.ts` SHA `03f470f7` |
| F2 | `global.setup.ts` crea el servidor en un puerto aleatorio y guarda `server-info.json` | `global.setup.ts` SHA `5f11a856` |
| F3 | `globalTeardown` limpia el servidor al final de toda la sesión | Output de tests: `[GlobalTeardown] Cleaning up server at: http://127.0.0.1:8528/` |
| F4 | `baseURL` reportó `Could not read server-info.json, using default localhost:8123` | Output de tests: primera línea del log |
| F5 | El servidor real corría en el puerto `8528` | GlobalTeardown log |
| F6 | 31 tests fallaron en `navigateViaSidebar()` por 404 en `localhost:8123/dashboard` | Stack trace: `trips.page.ts:190` |
| F7 | `global.setup.ts` es global y diseñado para correr UNA vez (no hay un `globalSetup` por proyecto) | `playwright.config.ts`: `globalSetup: './tests/global.setup.ts'` (campo global, no por proyecto) |
| F8 | La hipótesis de "dos instancias HA" del agente era INCORRECTA | F7 lo desmiente: hay un solo `globalSetup`. El problema es de timing de lectura del fichero. |
| F9 | `navigateViaSidebar()` usa `${baseUrl}/dashboard` que hereda el `baseURL` roto | `trips.page.ts` SHA `55b569f7`, línea 188 |

---

## Hipótesis Descartadas

| ID | Hipótesis | Por qué descartada |
|----|-----------|-------------------|
| H-old-1 | Dos instancias HA creadas (una por proyecto) | F7: `globalSetup` es global, corre una sola vez. El agente se confundió analizando los puertos. |
| H-old-2 | URL case mismatch `Coche2` vs `coche2` | F4: el error es anterior a cualquier navegación al panel, ocurre en `/dashboard`. |
| H-old-3 | `ReferenceError: TripsPage is not defined` como causa actual | Los tests ni llegan a ejecutar lógica — fallan en la navegación. |

---

## Hipótesis Activas (pendientes de confirmar)

### H1 — El 1 test que pasa (US-1 empty state) usa una ruta diferente o no navega
**Teoría:** En la última ejecución `31 failed, 1 passed`. El test que pasa probablemente no llama a `navigateViaSidebar()` o tiene una guarda que lo hace pasar aunque el panel no cargue.
**Paso de confirmación:** Paso 2 — leer el test en `trips.spec.ts` que corresponde al único passed.

### H2 — La fix más limpia es leer `server-info.json` en `navigateViaSidebar()` en runtime, no en config load time
**Teoría:** En lugar de arreglar el `baseURL` del config (que se evalúa demasiado pronto), `navigateViaSidebar()` puede leer `server-info.json` directamente en runtime para obtener el puerto correcto. Esto funcionaría porque cuando los tests corren, `globalSetup` ya ha escrito ese fichero.
**Alternativa:** Pasar el `baseURL` como variable de entorno desde `globalSetup` usando `process.env`.
**Paso de confirmación:** Paso 3 — evaluar y elegir la estrategia de fix.

### H3 — `auth.setup.ts` guarda `panel-url.txt` con el puerto correcto y podría usarse como fuente de verdad
**Teoría:** `auth.setup.ts` ya guarda `panel-url.txt` con la URL completa incluyendo el puerto real. Si `navigateViaSidebar()` leyera ese fichero en lugar de usar `baseURL`, tendría el puerto correcto.
**Paso de confirmación:** Paso 2 — verificar que `auth.setup.ts` escribe `panel-url.txt` correctamente.

---

## Pasos de Investigación

Los pasos originales 1-4 quedan **reemplazados** por estos, más focalizados en el root cause confirmado.

### Paso 1 — COMPLETADO ✔ʻ
Identificar el error real en la última ejecución.
**Resultado:** RC-1 y RC-2 confirmados. La causa es `baseURL` evaluado antes de `globalSetup`.

### Paso 2 — Verificar los artefactos de `auth.setup.ts`
**Objetivo:** Confirmar H3 — que `panel-url.txt` existe y tiene el puerto correcto.
**Acción:** Leer `auth.setup.ts` completo y verificar qué escribe en `playwright/.auth/`.
**Criterio de éxito:** Sabemos exactamente qué ficheros escribe `auth.setup.ts` y qué contienen.

### Paso 3 — Elegir la estrategia de fix
**Objetivo:** Decidir cómo hacer que los tests usen el puerto correcto en runtime.

**Opción A — `process.env` desde `globalSetup` (recomendada):**
```typescript
// global.setup.ts — añadir al final
process.env.HA_BASE_URL = new URL(hassInstance.link).origin;
```
```typescript
// playwright.config.ts — cambiar la IIFE por:
baseURL: process.env.HA_BASE_URL || 'http://localhost:8123',
```
Ventaja: un cambio mínimo en 2 ficheros. Funciona porque `globalSetup` escribe `process.env` antes de que el config se use para los tests.
⚠️ **Riesgo:** En Playwright, `globalSetup` corre en el mismo proceso Node.js que el runner, pero `use.baseURL` se evalúa al cargar el config (antes del globalSetup). `process.env` podria no llegar a tiempo. Necesita verificación.

**Opción B — Leer `server-info.json` en runtime dentro de `navigateViaSidebar()`:**
```typescript
// trips.page.ts — navigateViaSidebar()
async navigateViaSidebar(): Promise<void> {
  const serverInfo = JSON.parse(fs.readFileSync('playwright/.auth/server-info.json', 'utf-8'));
  const baseUrl = new URL(serverInfo.link).origin;
  await this.page.goto(`${baseUrl}/dashboard`, ...);
}
```
Ventaja: no toca `playwright.config.ts`. Lee el fichero cuando ya existe.
Desventaja: acopla la Page Object al sistema de ficheros.

**Opción C — Usar `panel-url.txt` (si H3 se confirma en Paso 2):**
```typescript
// trips.page.ts — navigateViaSidebar()
async navigateViaSidebar(): Promise<void> {
  const panelUrl = fs.readFileSync('playwright/.auth/panel-url.txt', 'utf-8').trim();
  const baseUrl = new URL(panelUrl).origin;
  await this.page.goto(`${baseUrl}/dashboard`, ...);
}
```
Ventaja: reutiliza infraestructura ya existente de `auth.setup.ts`.

**Criterio de éxito:** Una opción elegida y aprobada antes de tocar código.

### Paso 4 — Aplicar el fix mínimo
**Objetivo:** Implementar la opción elegida en Paso 3.
**Ficheros a modificar:** Máximo 2 (probablemente solo `trips.page.ts` con Opción B o C).
**Regla:** NO modificar `playwright.config.ts`, `global.setup.ts`, ni `auth.setup.ts` a menos que el Paso 3 indique explicitamente que es necesario.
**Criterio de éxito:** Los diffs están aprobados antes de aplicarse.

### Paso 5 — Correr el suite completo y verificar
**Objetivo:** Confirmar que el fix funciona.
**Acción:** `npx playwright test --project=setup --project=chromium`
**Criterio de éxito:** 32/32 tests pasan. O si falla alguno, identificar cuál y por qué (podria ser un problema distinto ya resuelto RC-1).

---

## Ficheros Clave

| Fichero | SHA actual | Tocar? |
|---------|-----------|--------|
| `playwright.config.ts` | `03f470f7` | Solo si Opción A elegida en Paso 3 |
| `tests/global.setup.ts` | `5f11a856` | Solo si Opción A elegida en Paso 3 |
| `tests/e2e/auth.setup.ts` | `60a774dc` | NO |
| `tests/e2e/pages/trips.page.ts` | `55b569f7` | SÍ — `navigateViaSidebar()` necesita usar el puerto real |
| `tests/e2e/trips.spec.ts` | `efd4f1e1` | Solo si Paso 2 revela que algún `beforeEach` también usa `baseURL` directamente |

---

## Contexto Previo (preservado)

### Por qué los paneles custom devuelven 404 sin sesión WebSocket
`panel_custom.async_register_panel()` registra paneles como paths de ficheros estáticos que evitan el middleware de autenticación del React Router de HA. Este sigue siendo un hecho válido (F5 de la versión anterior) pero es **secundario** al RC-1 actual: los tests ni siquiera llegan a navegar al panel, fallan antes en `/dashboard`.

### Patrón storageState
El patrón de guardar `storageState` después del Config Flow es correcto. Los tokens están ligados al puerto del servidor HA (`8528` en la última ejecución). El problema no está en la autenticación sino en que los tests no navegan al servidor correcto.
