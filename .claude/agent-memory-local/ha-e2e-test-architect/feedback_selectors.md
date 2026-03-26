---
name: feedback_selectors
description: Lecciones aprendidas sobre selectores de Playwright y Shadow DOM en HA
type: feedback
---

# Lecciones sobre Selectores Playwright en Home Assistant E2E

## 1. waitForTimeout() NO es crítico cuando hay auto-waiting de Playwright

**Regla:** `await page.waitForTimeout()` no es un anti-patrón crítico si el test pasa, pero debe reemplazarse con `expect().toBeVisible()` para mejor estabilidad.

**Por qué:** Playwright tiene auto-waiting por defecto. Las esperas artificiales solo ralentizan el test sin mejorar la estabilidad.

**Cómo aplicar:**
- Reemplazar `waitForTimeout(1000)` con `expect(locator).toBeVisible({ timeout: 5000 })`
- Reemplazar `waitForTimeout(2000)` con `expect(locator).toBeVisible({ timeout: 10000 })`
- El test seguirá pasando e incluso puede ser más rápido (2.4s vs 7.2s en mi caso)

## 2. getByRole('listitem') NO funciona siempre para elementos del Shadow DOM

**Regla:** Verifica el DOM real antes de asumir el role correcto.

**Por qué:** Home Assistant usa Lit Elements que pueden renderizar elementos con roles diferentes a los esperados. El snapshot mostró que "EV Trip Planner" estaba dentro de un elemento `generic` dentro de una `list`, no como `listitem`.

**Cómo aplicar:**
- Usar `getByText('EV Trip Planner')` cuando `getByRole('listitem')` falla
- Verificar el snapshot del DOM con `test-results/*/error-context.md` para ver la estructura real
- Preferir selectores más simples: `getByText` > `getByRole('listitem')` > `getByRole('generic')`

## 3. XPath selectors son innecesarios y frágiles

**Regla:** Evitar XPath. Usar `getByRole('dialog', { name: /.../i })` en su lugar.

**Por qué:** El XPath `.locator('xpath=ancestor-or-self::*[@role="dialog" or @role="alertdialog"]')` es innecesariamente complejo cuando se puede acceder directamente al role del dialog.

**Cómo aplicar:**
- Reemplazar XPath con `getByRole('dialog', { name: /.../i })`
- No navegar el Shadow DOM manualmente
- Usar roles semánticos directamente

## 4. CSS :has-text() no es estándar de Playwright

**Regla:** Evitar selectores CSS no estándar como `button:has-text()`. Usar `getByRole('button', { name: /.../i })`.

**Por qué:** `button:has-text("Add integration")` no es un selector estándar de Playwright. Debe reemplazarse con selectores semánticos.

**Cómo aplicar:**
- Reemplazar `page.click('button:has-text("Add integration")')` con:
- `await page.getByRole('button', { name: /Add integration/i }).click()`
- Preferir siempre `getByRole` sobre selectores CSS complejos

## Patrón de verificación recomendado:

```typescript
// ✅ CORRECTO - Verificar selector antes de usarlo
await page.getByRole('textbox', { name: /Search/i }).fill('EV Trip Planner');
await expect(page.getByText('EV Trip Planner')).toBeVisible({ timeout: 5000 });

// ❌ INCORRECTO - Asumir que getByRole('listitem') funciona
await expect(page.getByRole('listitem', { name: /EV Trip Planner/i })).toBeVisible();

// ❌ INCORRECTO - XPath innecesario
const dialogBox = page.getByRole('heading', { name: /EV Trip Planner/i })
  .locator('xpath=ancestor-or-self::*[@role="dialog" or @role="alertdialog"]');

// ❌ INCORRECTO - CSS :has-text() no estándar
await page.click('button:has-text("Add integration")');

// ✅ CORRECTO - Usar getByRole para botones
await page.getByRole('button', { name: /Add integration/i }).click();

// ✅ CORRECTO - Verificar estructura del DOM en snapshots
// Usar test-results/*/error-context.md para ver la estructura real antes de elegir selector
```

## Herramienta de debugging:

Cuando un selector falla:
1. Revisar `test-results/*/error-context.md` para ver el DOM real
2. Buscar el texto del elemento en el snapshot
3. Elegir selector basado en la estructura real, no la asumida
4. Preferir selectores simples: `getByText` > `getByRole` > XPath
