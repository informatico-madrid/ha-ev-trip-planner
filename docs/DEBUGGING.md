# 🔍 Debugging de Tests E2E

## 🔧 Herramientas de Debugging

### 1. Trace Viewer

El Trace Viewer muestra el DOM completo para cada acción del test.

```bash
# Ver trace de test fallido
npx playwright show-trace playwright/trace.zip
```

**Ventajas del Trace Viewer:**
- Ver DOM completo en cada paso
- Ver requests de network
- Ver console logs
- Ver timeline de interacciones
- Ver screenshots automáticos

### 2. Screenshots Automáticos

Playwright toma screenshots automáticos cuando un test falla.

```bash
# Los screenshots están en test-results/
ls test-results/
```

### 3. DOM Snapshots

Los snapshots del DOM están en los archivos de error.

```bash
# Ver snapshot del error
cat test-results/auth.setup.ts-*/error-context.md | head -200
```

### 4. Scripts de Debugging

#### check_session.js

```bash
# Valida si la sesión es válida
node ~/.agents/skills/ha-e2e-testing/scripts/check_session.js

# OUTPUT:
{
  "valid": true,
  "reason": "Session is valid"
}
```

**CUÁNDO usarlo:**
- Cuando un test falla con 401/403
- Para validar si el problema es de autenticación

#### inspect_dom.js

```bash
# Inspecciona DOM real para ver roles de elementos
node ~/.agents/skills/ha-e2e-testing/scripts/inspect_dom.js http://127.0.0.1:8271/config/integrations

# OUTPUT:
# 🔒 Elementos con Shadow DOM (150):
#    • <ha-list-item> role="listitem"
#    • <generic> role="generic" (no listitem!)
#    • <generic> role="generic" (dentro de <list>)
```

**CUÁNDO usarlo:**
- Cuando un selector falla (locator timeout)
- Para ver roles reales en DOM
- Para verificar si getByRole('listitem') existe o no

#### validate_selector.js

```bash
# Valida selector antes de usarlo en tests
node ~/.agents/skills/ha-e2e-testing/scripts/validate_selector.js "getByRole('button', { name: /Save/i })"
```

**CUÁNDO usarlo:**
- Antes de usar un selector en tests
- Para validar que el selector es correcto
- Para prevenir errores antes de escribir tests

#### extract_report.js

```bash
# Ver resumen estructurado de tests
node ~/.agents/skills/ha-e2e-testing/scripts/extract_report.js

# OUTPUT:
# ✅ 2/2 tests pasados
# ⏱️ 2.4s ejecución total
```

**CUÁNDO usarlo:**
- Después de ejecutar tests con run_playwright_test.sh
- Para ver resumen estructurado
- Para identificar tests que fallaron

#### run_playwright_test.sh

```bash
# Ejecuta tests con reporte estructurado
bash ~/.agents/skills/ha-e2e-testing/scripts/run_playwright_test.sh tests/e2e/panel.spec.ts
```

**Ventajas:**
- Genera playwright-results.json automáticamente
- Mejor que `npx playwright test` directo
- Incluye reporte estructurado

## 🐛 Escenarios Comunes de Debugging

### Escenario 1: Locator Timeout en getByRole('listitem')

**Síntoma:**
```
Error: locator.waitFor: Timeout 5000ms exceeded.
```

**Pasos de Debugging:**

1. **Verificar error en test-results:**
   ```bash
   cat test-results/auth.setup.ts-*/error-context.md | head -100
   ```

2. **Inspeccionar DOM real:**
   ```bash
   node ~/.agents/skills/ha-e2e-testing/scripts/inspect_dom.js http://127.0.0.1:8271/config/integrations
   ```

3. **Buscar el elemento en el output:**
   ```bash
   grep -A 10 "EV Trip Planner" test-results/auth.setup.ts-*/error-context.md
   ```

4. **Ver output del script:**
   ```bash
   # OUTPUT:
   # 🔒 Elementos con Shadow DOM (150):
   #    • <ha-list-item> role="listitem"
   #    • <generic> role="generic" (no listitem!)
   #    • <generic> role="generic" (dentro de <list>)
   ```

5. **Corregir selector:**
   ```typescript
   // ❌ Falla
   await expect(page.getByRole('listitem', { name: /EV Trip Planner/i }))
     .toBeVisible()

   // ✅ Funciona
   await expect(page.getByText('EV Trip Planner'))
     .toBeVisible()
   ```

**Documentado en:** `.claude/agent-memory-local/ha-e2e-test-architect/feedback_selectors.md`

### Escenario 2: 404 Not Found al Cargar Panel

**Síntoma:**
```
Error: 404 Not Found: /ev_trip_planner
```

**Diagnóstico:** NO es un problema de autenticación.

**Causas comunes:**
1. Integración no se instaló correctamente en Config Flow
2. URL del panel es incorrecta
3. Frontend del panel no se registró en backend

**Pasos de Debugging:**

1. **Verificar que auth.setup.ts ejecutó Config Flow:**
   ```bash
   npx playwright test auth.setup.ts --reporter=list
   ```

2. **Verificar que storageState fue guardado:**
   ```bash
   node ~/.agents/skills/ha-e2e-testing/scripts/check_session.js
   ```

3. **Revisar logs de HA para errores de instalación:**
   ```bash
   docker logs homeassistant --tail 50 | grep ev_trip_planner
   ```

**Solución:**
- Revisar que auth.setup.ts completó Config Flow exitosamente
- Verificar que el panel fue registrado en backend

### Escenario 3: Elemento no encontrado en Dialog

**Síntoma:**
```
Error: locator.waitFor: Timeout 5000ms exceeded.
```

**Pasos de Debugging:**

1. **Verificar que el dialog existe:**
   ```bash
   await expect(page.getByRole('dialog', { name: /EV Trip Planner/i }))
     .toBeVisible()
   ```

2. **Usar getByRole en vez de XPath:**
   ```typescript
   // ❌ NO USAR - XPath innecesario
   const dialogBox = page.getByRole('heading', { name: /EV Trip Planner/i })
     .locator('xpath=ancestor-or-self::*[@role="dialog" or @role="alertdialog"]')

   // ✅ USAR - getByRole directo
   await page.getByRole('dialog', { name: /EV Trip Planner/i })
   ```

### Escenario 4: Selectores que Fallan con :has-text()

**Síntoma:**
```
Error: Locator expected to be visible but got error
```

**Pasos de Debugging:**

1. **Verificar selector:**
   ```bash
   node ~/.agents/skills/ha-e2e-testing/scripts/validate_selector.js "button:has-text(\"Add integration\")"
   ```

2. **Corregir selector:**
   ```typescript
   // ❌ NO USAR - :has-text() no estándar
   await page.click('button:has-text("Add integration")')

   // ✅ USAR - getByRole
   await page.getByRole('button', { name: /Add integration/i }).click()
   ```

## 📊 Análisis de Trace

### Ver Trace en CI

```bash
# Descargar trace de CI
curl -o trace.zip https://ci.example.com/traces/123.zip

# Ver trace localmente
npx playwright show-trace trace.zip
```

### Información en Trace Viewer

El Trace Viewer muestra:
- **DOM completo** para cada acción
- **Network requests** realizados
- **Console logs** del navegador
- **Timeline** de interacciones
- **Screenshot** de cada paso

## 🎯 Mejores Prácticas de Debugging

### 1. Usar expect().toBeVisible() en vez de waitForTimeout

```typescript
// ❌ NO USAR - waitForTimeout es frágil
await page.waitForTimeout(1000)

// ✅ USAR - Auto-waiting de Playwright
await expect(page.getByRole('button', { name: /Save/i }))
  .toBeVisible({ timeout: 10000 })
```

### 2. Documentar lecciones aprendidas

```markdown
# feedback_selectors.md

## 2. getByRole('listitem') NO funciona siempre para elementos del Shadow DOM

**Regla:** Verificar el DOM real antes de asumir el role correcto.

**Por qué:** Home Assistant usa Lit Elements que pueden renderizar elementos
con roles diferentes a los esperados.

**Cómo aplicar:**
- Usar getByText('EV Trip Planner') cuando getByRole('listitem') falla
- Verificar el snapshot del DOM con test-results/*/error-context.md
- Preferir selectores más simples: getByText > getByRole('listitem') > getByRole('generic')
```

### 3. Usar scripts de debugging

```bash
# Cuando un selector falla
node ~/.agents/skills/ha-e2e-testing/scripts/inspect_dom.js http://127.0.0.1:8271/config/integrations

# Validar selector antes de usarlo
node ~/.agents/skills/ha-e2e-testing/scripts/validate_selector.js "getByRole('button', { name: /Save/i })"
```

### 4. Usar Trace Viewer en vez de screenshots manuales

```bash
# NO USAR - Screenshots manuales son limitados
# SÍ USAR - Trace Viewer es más completo
npx playwright show-trace playwright/trace.zip
```

## 📚 Recursos

- [Playwright Debugging](https://playwright.dev/docs/debug)
- [Playwright Trace Viewer](https://playwright.dev/docs/trace-viewer)
- [SKILL.md](~/.agents/skills/ha-e2e-testing/SKILL.md)
- [Memorias](.claude/agent-memory-local/ha-e2e-test-architect/)
