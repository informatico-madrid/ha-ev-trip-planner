# Panel de planificación de carga — 2026-10-09

## Objetivo y resultado

Sustituir el inventario general de sensores del panel nativo por una interfaz
centrada en el perfil enviado a EMHASS y la gestión de viajes. Implementación
realizada directamente; la única delegación fue una investigación de lectura
del esquema del backend.

## Cambios

- Resumen de energía, tiempo, potencia y próximo viaje activo.
- Gráfica del perfil publicado y ventanas independientes por fila de la matriz.
- Selección de 48 horas o del horizonte completo; desplazamiento sincronizado
  de las gráficas en móvil.
- Viajes activos/pausados, nombres de días y formularios accesibles.
- Lectura de viajes desde estados enviados por HA, evitando consultas periódicas
  del servicio por cambios de sensores ajenos al planificador.
- CSS compatible con el tema de HA y navegación lateral en móvil.

## Comprobación

- 22 pruebas del módulo frontend con Node: transformación, límites, aislamiento
  por vehículo y contratos simulados de guardado.
- Sintaxis JavaScript y `git diff --check` correctos.
- Navegación real en el panel de producción, escritorio y móvil (390 px), tema
  claro/oscuro, filtros, selección de horizonte y apertura/cierre de formularios.
- Teclado: foco dentro del diálogo y cierre con Escape.
- Confirmada la existencia de los servicios usados en el frontend instalado.
- No se guardaron, pausaron ni eliminaron viajes reales durante la comprobación.

Se desplegaron solo `panel.js` y `panel.css`, sin reiniciar HA. Los cambios de Git
quedan pendientes de validación del usuario antes de commit/push.

## Seguimiento: el navegador del usuario conserva el panel anterior

La primera validación visual había desactivado la caché del navegador. HA aún
anunciaba la URL de JavaScript registrada el 6 de octubre. Se añadió
`PANEL_FRONTEND_VERSION = "4.0.0"` al registro del panel y una comprobación de
coherencia con la versión del JavaScript. Resultados: 23 pruebas de frontend y
7 de construcción de URL correctas; las pruebas Python locales requieren
compatibilidad de configuración con su versión antigua de pytest-asyncio.

No se utilizó la recarga de la integración: se comprobó que su rutina de descarga
borra y guarda los viajes. Se aplicó un reinicio normal de HA y se esperó al
estado `RUNNING`. El nuevo registro anuncia `panel.js?t=4.0.0-…`.

Verificación en una pestaña normal, con caché habilitada: interfaz 4.0.0, perfil
disponible y tres cargas publicadas. Comparación en memoria de los cuatro viajes
antes y después del reinicio: mismos datos y estados, tres activos y uno pausado.

## Hallazgos para futuras iteraciones

El sensor no publica una fecha base absoluta. `last_updated` es hora de
publicación, no una garantía del origen temporal del perfil. Las filas de matriz
y `deferrables_schedule` pueden tener diferente orden. Un HTTP 200 del navegador
puede corresponder a una copia cacheada anterior del JavaScript: revisar versión
y metadatos del recurso, y recargar sin caché para comprobar un despliegue.

## Validación del usuario

El usuario confirmó que recibe el nuevo panel en su navegador y dio su visto
bueno al resultado en producción. Autorizó el commit y el push de estos cambios
a `main`.
