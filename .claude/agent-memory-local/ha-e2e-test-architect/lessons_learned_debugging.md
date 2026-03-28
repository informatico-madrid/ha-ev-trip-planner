---
name: lessons_learned_debugging
description: Lecciones aprendidas sobre diagnóstico de errores y progreso en tests E2E
type: feedback
---

## Lecciones Aprendidas - Debugging de Tests E2E

### Punto 1: Reconocer Señales de Progreso
**Regla:** Un cambio en el tipo de error indica que estamos avanzando.

**Ejemplo real:**
- Error inicial: `Could not connect to localhost: Connection refused`
- Error después: `TimeoutError: locator.click: Timeout 10000ms exceeded`
- Interpretación: El servidor ahora se conecta (puerto dinámico funciona), pero el elemento no existe
- Conclusión: El problema ya no es de red, es de UI

**Cómo aplicarlo:** Comparar errores antes/después para medir progreso real. Si el error cambia de "no hay conexión" a "elemento no encontrado", estamos avanzando.

### Punto 2: No Sobre-ingenierizar
**Regla:** A veces la solución simple es la correcta.

**Ejemplo real:**
- Solución compleja que intenté: Funciones helper con `import.meta.url`, rutas relativas, try/catch
- Solución simple correcta: Modificar `playwright.config.ts` para leer `server-info.json` directamente en el baseURL

**Por qué fallé:** Me obsesioné con la estructura de rutas y el manejo de errores, mientras ignoraba la solución más simple que ya estaba identificada en mi diagnóstico inicial.

**Cómo aplicarlo:** Cuando identifico una solución simple en el diagnóstico inicial, aplicarla inmediatamente en lugar de buscar complicaciones.

---

## Patrón de Error a Evitar

**Comportamiento problemático:**
1. Identificar correctamente el diagnóstico inicial
2. No confiar en el diagnóstico
3. Buscar problemas en otros lugares del código
4. Crear código complejo innecesario
5. Esperar que el usuario me corrija en lugar de verificar la solución

**Solución:**
1. Identificar correctamente el diagnóstico
2. Confiar en el diagnóstico y aplicar la solución inmediatamente
3. Verificar el resultado contra el diagnóstico
4. Reconocer señales de progreso (cambio en el tipo de error)
