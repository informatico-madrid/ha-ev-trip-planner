# 🎨 Patrones de Selectores Playwright

## ✅ Web-First Locators (Recomendado)

### getByRole - Para elementos con role semántico

```typescript
// Botones
await page.getByRole('button', { name: /Save/i }).click()
await page.getByRole('button', { name: /Add Integration/i }).click()

// Links
await page.getByRole('link', { name: /Settings/i }).click()
await page.getByRole('link', { name: /EV Trip Planner/i }).click()

// Dialogs
await page.getByRole('dialog', { name: /EV Trip Planner/i })
await expect(page.getByRole('dialog', { name: /Add Trip/i })).toBeVisible()

// Form inputs
await page.getByRole('textbox', { name: /vehicle_name/i }).fill('Mi Tesla')
await page.getByRole('combobox', { name: /Charging Power/i }).selectOption('11')
```

### getByText - Para elementos sin role específico

```typescript
// Textos simples
await expect(page.getByText('EV Trip Planner')).toBeVisible()
await expect(page.getByText('Morning Commute')).toBeVisible()

// Textos dentro de dialogs
await page.getByRole('dialog', { name: /EV Trip Planner/i })
  .getByText(/battery capacity/i)
  .fill('75')
```

### getByLabel - Para formularios

```typescript
await page.getByLabel(/Trip Name/i).fill('Morning Commute')
await page.getByLabel(/Departure Time/i).fill('08:00')
await page.getByLabel(/Description/i).fill('Work commute')
```

### getByPlaceholder - Para campos vacíos

```typescript
await page.getByPlaceholder(/Search/i).fill('EV Trip Planner')
await page.getByPlaceholder(/Enter value/i).fill('75')
```

## ❌ Anti-patrones a Evitar

### waitForTimeout

```typescript
// ❌ NO USAR - WaitForTimeout es frágil
await page.waitForTimeout(1000)
await page.waitForTimeout(2000)

// ✅ USAR - Auto-waiting de Playwright
await expect(page.getByRole('button', { name: /Save/i }))
  .toBeVisible({ timeout: 10000 })
```

**Por qué:** Playwright tiene auto-waiting por defecto. Las esperas artificiales solo ralentizan el test sin mejorar la estabilidad.

### XPath

```typescript
// ❌ NO USAR - XPath es innecesario
await page.locator('xpath=ancestor-or-self::*[@role="dialog" or @role="alertdialog"]')

// ✅ USAR - getByRole directo
await page.getByRole('dialog', { name: /EV Trip Planner/i })
```

**Por qué:** getByRole es más semántico y no requiere navegación manual del DOM.

### CSS Classes

```typescript
// ❌ NO USAR - CSS classes son frágiles
await page.click('.clase-css-random')
await page.locator('.mdc-button')

// ✅ USAR - getByRole semántico
await page.getByRole('button', { name: /Save/i }).click()
```

**Por qué:** Las CSS classes pueden cambiar sin avisar. Los roles semánticos son más estables.

### :has-text()

```typescript
// ❌ NO USAR - :has-text() no es estándar
await page.click('button:has-text("Add integration")')

// ✅ USAR - getByRole
await page.getByRole('button', { name: /Add integration/i }).click()
```

**Por qué:** `:has-text()` no es un selector estándar de Playwright.

### getByRole('listitem') sin verificar DOM

```typescript
// ❌ NO ASUMIR - getByRole('listitem') puede no existir
await expect(page.getByRole('listitem', { name: /EV Trip Planner/i }))
  .toBeVisible()

// ✅ VERIFICAR EL DOM REAL - Usar getByText
await expect(page.getByText('EV Trip Planner'))
  .toBeVisible()
```

**Por qué:** Home Assistant usa Lit Elements que pueden renderizar elementos con roles diferentes a los esperados.

## 🔍 Cómo Verificar el DOM Real

### Paso 1: Ejecutar el test

```bash
bash ~/.agents/skills/ha-e2e-testing/scripts/run_playwright_test.sh tests/e2e/auth.setup.ts
```

### Paso 2: Ver el snapshot del error

```bash
cat test-results/auth.setup.ts-*/error-context.md | head -100
```

### Paso 3: Buscar el elemento en el DOM

```bash
grep -A 10 "EV Trip Planner" test-results/auth.setup.ts-*/error-context.md
```

### Paso 4: Inspeccionar DOM real

```bash
node ~/.agents/skills/ha-e2e-testing/scripts/inspect_dom.js http://127.0.0.1:8271/config/integrations
```

### Paso 5: Elegir selector basado en DOM real

```bash
# OUTPUT del script:
# 🔒 Elementos con Shadow DOM (150):
#    • <ha-list-item> role="listitem"
#    • <generic> role="generic" (no listitem!)
#    • <generic> role="generic" (dentro de <list>)

# ✅ SOLUCIÓN: Usar selector basado en DOM real
await expect(page.getByText('EV Trip Planner')).toBeVisible()
```

## 📋 Referencia Rápida

| Elemento | Selector | Ejemplo |
|----------|----------|---------|
| Botón | `getByRole('button')` | `getByRole('button', { name: /Save/i })` |
| Link | `getByRole('link')` | `getByRole('link', { name: /Settings/i })` |
| Dialog | `getByRole('dialog')` | `getByRole('dialog', { name: /Add Trip/i })` |
| Textbox | `getByRole('textbox')` | `getByRole('textbox', { name: /vehicle_name/i })` |
| Label | `getByLabel()` | `getByLabel(/Trip Name/i)` |
| Placeholder | `getByPlaceholder()` | `getByPlaceholder(/Search/i)` |
| Texto | `getByText()` | `getByText('EV Trip Planner')` |
| List Item | `getByRole('listitem')` | `getByRole('listitem', { name: /EV Trip Planner/i })` |

## 🎯 Patrones para Home Assistant

### Config Flow

```typescript
// 1. Navegar a integraciones
await page.goto('/config/integrations')

// 2. Agregar integración
await page.getByRole('button', { name: /Add Integration/i }).click()

// 3. Buscar integración
await page.getByPlaceholder(/Search/i).fill('EV Trip Planner')

// 4. Seleccionar integración
await page.getByRole('listitem', { name: /EV Trip Planner/i }).click()

// 5. Rellenar campos
await page.getByRole('textbox', { name: /vehicle_name/i }).fill('Mi Tesla')
await page.getByRole('textbox', { name: /battery_capacity_kwh/i }).fill('75')

// 6. Navegar por el flow
await page.getByRole('button', { name: /Next/i }).click()
await page.getByRole('button', { name: /Submit/i }).click()

// 7. Esperar confirmación
await expect(page.getByText(/EV Trip Planner/i))
  .toBeVisible()
```

### Navegación vía Sidebar

```typescript
// 1. Navegar al dashboard
await page.goto('/dashboard')

// 2. Esperar sidebar
await expect(page.getByRole('navigation', { name: /Navigation/i }))
  .toBeVisible({ timeout: 10000 })

// 3. Clic en link del panel
await page.getByRole('link', { name: /EV Trip Planner/i }).click()

// 4. Verificar que el panel cargó
await expect(page.getByRole('heading', { name: /EV Trip Planner/i }))
  .toBeVisible({ timeout: 10000 })
```

### Crear Viaje

```typescript
// 1. Navegar al panel
await page.goto('/dashboard')
await page.getByRole('link', { name: /EV Trip Planner/i }).click()

// 2. Clic en botón
await page.getByRole('button', { name: /New Trip/i }).click()

// 3. Esperar formulario
await expect(page.getByRole('heading', { name: /New Trip/i }))
  .toBeVisible()

// 4. Rellenar formulario
await page.getByLabel(/Trip Name/i).fill('Morning Commute')
await page.getByLabel(/Departure Time/i).fill('08:00')
await page.getByLabel(/Description/i).fill('Work commute')

// 5. Clic en crear
await page.getByRole('button', { name: /Create|Save/i }).click()

// 6. Verificar creación
await expect(page.getByText(/Morning Commute/i))
  .toBeVisible()
```

## 📚 Recursos

- [Playwright Locators](https://playwright.dev/docs/locators)
- [Playwright Assertions](https://playwright.dev/docs/assertions)
- [Web Accessibility Roles](https://www.w3.org/TR/wai-aria-1.2/#roles)
- [SKILL.md](~/.agents/skills/ha-e2e-testing/SKILL.md)
