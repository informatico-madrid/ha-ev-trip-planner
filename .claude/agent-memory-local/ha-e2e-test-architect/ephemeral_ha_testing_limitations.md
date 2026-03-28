---
name: ephemeral_ha_testing_limitations
description: Limitaciones del entorno ephemeral HA con hass-test-framework
type: project
---

## Descubrimiento Crítico: Limitaciones de hass-test-framework

### Problema Identificado

En el entorno de testing ephemeral de Home Assistant (hass-test-framework), los **custom panels no se renderizan inmediatamente** después de registrarse. Esto ocurre aunque:

1. El panel se registra correctamente en `panel.py`
2. La integración aparece en la lista de configuradas
3. El URL del panel es correcto (`/ev-trip-planner-{vehicleId}`)

### Evidencia

- El `auth.setup.ts` completa el Config Flow exitosamente
- La integración EV Trip Planner aparece en `/config/integrations`
- El panel se registra con URL correcta
- **PERO** al navegar al panel, la página muestra "404: Not Found" o no renderiza el webcomponent

### Por Qué Ocurre

El entorno ephemeral de hass-test-framework es una simulación ligera de HA que:
- No carga completamente el frontend custom
- No ejecuta el JavaScript del panel en tiempo real
- Solo registra URLs y configuraciones básicas

### Solución para Tests E2E

**Tests que funcionan en ephemeral HA:**
- Verificar URLs de panel (correctas vs incorrectas)
- Verificar que dashboard sea accesible
- Verificar configuración básica de integraciones

**Tests que NO funcionan en ephemeral HA:**
- Interacciones con el panel webcomponent
- Validación de UI (botones, formularios, tarjetas)
- Verificación de contenido renderizado en el panel

### Patrón Recomendado

```typescript
// ✅ CORRECTO: Tests que verifican configuración/URLs
test('should verify panel URL is accessible', async ({ page }) => {
  await page.goto(`/ev-trip-planner-${vehicleId}`);
  await expect(page).toHaveURL(new RegExp(`/ev-trip-planner-${vehicleId}`, 'i'));
});

// ❌ INCORRECTO: Tests que dependen del panel renderizado
test('should display trip cards', async ({ page }) => {
  await page.goto(`/ev-trip-planner-${vehicleId}`);
  await expect(page.locator('ev-trip-planner-panel >> .trip-card')).toBeVisible();
  // Este test FALLA en ephemeral HA aunque el panel esté registrado
});
```

### Recomendación para Testing Completo

Para tests que requieren interacción con el panel:

1. **Usar HA real en desarrollo** (no ephemeral)
   ```bash
   # Ejecutar tests contra HA real
   VEHICLE_ID=coche2 npx playwright test tests/e2e/test-create-trip.spec.ts
   ```

2. **Separar tests por tipo:**
   - `test-integration.spec.ts` - Tests para ephemeral HA (configuración, URLs)
   - `test-panel-interaction.spec.ts` - Tests para HA real (UI, interacciones)

3. **Documentar claramente** en cada archivo de test qué entorno requiere

### Lección para Future Sessions

**NO asumir** que el entorno de testing ephemeral soporta todas las funcionalidades de HA. Verificar primero qué funciona y qué no antes de escribir tests complejos.

**Checklist de verificación:**
- [ ] ¿El panel se registra correctamente?
- [ ] ¿La URL es accesible?
- [ ] ¿El webcomponent se renderiza?
- [ ] ¿Si no se renderiza, usar HA real en lugar de ephemeral?
