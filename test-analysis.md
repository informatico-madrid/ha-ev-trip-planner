# Análisis de Tests E2E para Detectar Bugs de Persistencia y Limpieza

## Resumen Ejecutivo

He creado dos tests E2E que detectarán los problemas reportados:

1. **[ha-restart-persistence.spec.ts](tests/e2e/ha-restart-persistence.spec.ts)** - Verifica que los viajes persistan tras reiniciar HA
2. **[integration-deletion-cleanup.spec.ts](tests/e2e/integration-deletion-cleanup.spec.ts)** - Verifica que los viajes se borren al eliminar la integración

## Test 1: Persistencia tras Reinicio de HA

### Problema Detectado
- **Síntoma**: Los viajes desaparecen del panel frontend y de la plantilla EMHASS tras reiniciar HA
- **Causa Raíz**: La relación vehículo-viajes se pierde aunque los sensores de viajes siguen existiendo en `developer-tools/state`
- **Commit Relacionado**: `98d60e0` supuestamente arregló esto pero no funciona

### Casos de Prueba

#### Test Principal: `should persist all trips after HA restart`
**Flujo:**
1. Crea 3 viajes (2 puntuales, 1 recurrente)
2. Verifica que existen en el panel
3. Verifica que el sensor EMHASS contiene los datos de los viajes
4. Reinicia HA vía Configuration → Server Management → Restart
5. Espera a que HA reinicie y reconecte
6. Navega de vuelta al panel
7. **VERIFICA**: Los viajes siguen existiendo en el panel ❌ (FALLARÁ)
8. **VERIFICA**: El sensor EMHASS todavía contiene los datos ❌ (FALLARÁ)

#### Test Secundario: `should maintain vehicle-trip relationship after HA restart`
**Flujo:**
1. Crea un viaje
2. Verifica que se puede editar (relación vehículo-viaje intacta)
3. Reinicia HA
4. **VERIFICA**: El viaje sigue siendo editable ❌ (FALLARÁ)

### Por Qué Fallarán los Tests

Según tu reporte:
> "desaparecen en su panel frontend y desaparecen del fragmento... pero siguen existiendo en developers-tools-state"

Los tests fallarán en:
- **Línea 120**: `await expect(page.getByText('Persistence Test Trip 1')).toBeVisible()` - Los viajes no estarán visibles
- **Línea 120**: `await expect(page.getByText('Persistence Test Trip 2')).toBeVisible()` - Los viajes no estarán visibles
- **Línea 120**: `await expect(page.getByText('Persistence Test Trip 3')).toBeVisible()` - Los viajes no estarán visibles
- **Línea 158**: `expect(stateAfter).not.toContain('[]')` - Los arrays estarán vacíos aunque los sensores existan

---

## Test 2: Limpieza al Borrar Integración

### Problema Detectado
- **Síntoma**: Al borrar la integración, los viajes no se eliminan
- **Causa Raíz**: Los viajes permanecen en almacenamiento y siguen siendo visibles en `developer-tools/state` y en la plantilla EMHASS
- **Impacto**: Crea datos huérfanos que contaminan el sistema

### Casos de Prueba

#### Test Principal: `should delete all trips when integration is deleted`
**Flujo:**
1. Crea 3 viajes
2. Verifica que existen en el panel
3. Verifica que el sensor EMHASS contiene los datos
4. Navega a Settings → Devices & Services → Integrations
5. Encuentra la integración EV Trip Planner
6. Borra la integración
7. **VERIFICA**: El sensor EMHASS ya no existe o tiene arrays vacíos ❌ (FALLARÁ)
8. **VERIFICA**: No hay sensores de viajes huérfanos en developer-tools ❌ (FALLARÁ)

#### Test Secundario: `should not leave orphaned trip sensors in developer tools after deletion`
**Flujo:**
1. Crea un viaje
2. Cuenta los sensores de viajes antes del borrado
3. Borra la integración
4. **VERIFICA**: No quedan sensores de viajes ❌ (FALLARÁ)

### Por Qué Fallarán los Tests

Según tu reporte:
> "si voy a config integraciones... y borro el vechiculo... los viajes realmente no se estan borrando"

Los tests fallarán en:
- **Línea 128**: `expect(stateAfter).toMatch(/def_total_hours.*\[\]/)` - Los arrays NO estarán vacíos
- **Línea 150-157**: Los sensores individuales de viajes seguirán existiendo en `developer-tools/state`

---

## Importancia de estos Tests

### 1. **Prevención de Regresiones**
Una vez arreglados, estos tests impedirán que los problemas regresen en el futuro.

### 2. **Documentación del Bug**
Los tests sirven como documentación viva del comportamiento esperado vs. real.

### 3. **Validación del Fix**
Antes de declarar que el fix funciona, los tests deben pasar exitosamente.

---

## Siguientes Pasos (TDD Estricto)

### ✅ Fase Roja: Completada
- [x] Escribir tests que fallen por el motivo correcto
- [x] Documentar por qué fallarán
- [x] Crear casos de prueba comprehensivos

### 🔲 Fase Verde: Próxima
Los tests deben pasar. Necesito investigar:

1. **Para el Bug de Persistencia:**
   - ¿Cómo se carga la relación vehículo-viajes al iniciar?
   - ¿Dónde se almacena esta relación?
   - ¿Por qué se pierde tras el reinicio?

2. **Para el Bug de Limpieza:**
   - ¿Qué código se ejecuta al borrar la integración?
   - ¿Por qué no se están borrando los viajes?
   - ¿Qué falta en el flujo de limpieza?

### 🔲 Fase Refactor: Final
Una vez los tests pasen, refactorizar para mejorar el código sin romper los tests.

---

## Notas de Ejecución

### Test de Reinicio
- **Duración**: ~2-3 minutos (HA tarda en reiniciar)
- **Marcado como `test.slow()`**: Playwright extenderá el timeout
- **Aislamiento**: Debe ejecutarse solo o al final

### Test de Borrado
- **Impacto**: Borra la integración, otros tests fallarán después
- **Ejecución**: Debe ejecutarse último o en aislamiento
- **Reconfiguración**: Necesitará recrear la integración para ejecutar again

### Configuración Recomendada
```json
{
  "projects": [
    {
      "name": "e2e-critical",
      "testMatch": "**/*.spec.ts",
      "testIgnore": "**/integration-deletion-cleanup.spec.ts"
    },
    {
      "name": "e2e-cleanup",
      "testMatch": "**/integration-deletion-cleanup.spec.ts"
    }
  ]
}
```

---

## Análisis de Commits Relacionados

### Commit `98d60e0`: "fix: ensure publish_deferrable_loads is called after EMHASS adapter setup"
**Intento**: Arreglar persistencia de viajes tras reinicio
**Resultado**: No funcionó según tu reporte
**Análisis**: El fix aborda `publish_deferrable_loads` pero el problema parece ser la relación vehículo-viajes, no la publicación de sensores

### Commit `dd24a76`: "fix: add missing disconnectedCallback() to prevent blank screen on tab switching"
**Intento**: Arreglar blank screen en panel
**Resultado**: Probablemente funcionó
**Análisis**: No relacionado con persistencia de viajes

### Commit `ae267af`: "fix: publish loaded trips to EMHASS after HA restart (#31)"
**Intento**: Publicar viajes tras reinicio de HA
**Resultado**: No funcionó completamente
**Análisis**: El fix publica viajes pero algo en la relación vehículo-viajes se pierde

---

## Conclusión

Los tests están listos para fallar por los motivos correctos. Según TDD estricto, ahora debo:
1. Ejecutar los tests y confirmar que fallan como esperado
2. Investigar el código para entender la causa raíz
3. Implementar los fixes
4. Verificar que los tests pasen
5. Refactorizar si es necesario

¿Quieres que ejecute los tests ahora para confirmar que fallan como esperado, o prefieres que proceda directamente a investigar y arreglar los problemas?
