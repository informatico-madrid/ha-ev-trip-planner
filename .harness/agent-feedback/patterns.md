# Patterns — Detected Feedback Patterns

> Plantilla. El maestro es CLAUDE.md.

## Patrones de Éxito

| Patrón | Descripción | Frecuencia |
|--------|-------------|------------|
| - | - | - |

## Patrones de Error

| Patrón | Descripción | Frecuencia |
|--------|-------------|------------|
| - | - | - |

## Constraints Problemáticos

| Constraint | Problema | Sugerencia |
|------------|----------|------------|
| - | - | - |

## Información Faltante Frecuente

| Missing Info | Impacto | Solución |
|--------------|---------|----------|
| - | - | - |

## Última Actualización

2026-10-09

## Panel nativo y planificación EMHASS (2026-10-09)

- Priorizar código y atributos reales cuando la documentación describe sensores
  o parámetros antiguos.
- No reconstruir el perfil agregado sumando cargas: el backend lo combina con
  el máximo de las filas.
- No asignar filas de matriz a registros de `deferrables_schedule` por posición;
  sus órdenes pueden ser distintos.
- No convertir pasos relativos a fechas del reloj usando `last_updated` como
  supuesto origen del plan cuando el sensor no publica esa base.
- Después de sustituir recursos frontend, comprobar su versión real. El
  navegador puede usar una copia cacheada incluso si la petición aparece con 200.
- En la instancia de producción, comprobar presentación y formularios sin
  enviar operaciones destructivas como parte de una revisión visual.

## Invalidación del recurso tras un despliegue

- Copiar el JavaScript no actualiza el registro del panel que HA mantiene en
  memoria. La versión del recurso registrado debe acompañar a la del frontend.
- Validar la actualización también en una pestaña normal, sin desactivar su
  caché ni saltarse el service worker.
- En esta versión, la descarga de la integración borra viajes persistidos.
  No utilizar `reload_config_entry` para invalidar recursos hasta corregir ese
  comportamiento. El reinicio normal de HA sigue un ciclo de parada distinto.

## Referencia de los índices de tiempo (2026-10-09)

- Una coincidencia aproximada con GMT+2 no demuestra un error de zona: contrastar
  la hora real de salida, la referencia del proveedor y el primer índice de EMHASS.
- El origen de EMHASS con `nearest` se redondea en UTC. Los índices relativos
  cacheados necesitan una referencia explícita y proyección al avanzar la rejilla.
- Redondear hacia arriba la energía/duración no implica redondear hacia arriba
  el límite de salida. Un paso completo no puede terminar después de la salida.
- En EMHASS, un fin 0 significa ausencia de límite. Sin capacidad temporal, poner
  también duración y potencia 0, y mostrar la carga que no cabe.
- El entorno Python local antiguo no tiene todas las APIs de HA actual. Verificar
  cambios del backend con la versión real en un contenedor de pruebas aislado.

## Consumo, cadena energética y snapshots (2026-10-09)

- Un cambio observado después de reiniciar no prueba que el reinicio lo causó:
  contrastar servicios registrados, almacenamiento e historial de atributos.
- Las listas de diccionarios publicadas por entidades necesitan snapshots
  independientes. Compartir objetos mutables con CRUD puede modificar los
  atributos anteriores y ocultar el cambio al comparar estados.
- No confundir el objetivo `xnl/suffsoc` de OVMS con una autoparada habilitada
  ni con el cap dinámico del planificador. Consultar también `xnl/autocharge`.
  En el firmware observado la consulta disponible es `config list`, no
  `config get`; evitar comandos `set` para investigar.
- La factibilidad debe contrastarse con la demanda original. Un déficit cero
  calculado después de reducir esa demanda mediante un cap no garantiza energía
  suficiente ni reserva después de los viajes.
- El SOC inicial pertenece a una batería, no a cada viaje independientemente:
  transportar su energía por la cadena y comprobar capacidad, carga y consumos.
- Verificar la presencia de `kwh` y el cableado del consumo configurado: cero
  explícito no equivale a campo ausente en la implementación actual.

## Reserva y protección de batería (2026-10-09)

- Separar disponibilidad física, cantidad necesaria y posición sugerida de la
  carga. La preferencia de cargar al final no puede recortar los límites enviados
  a EMHASS ni reducir la energía necesaria para viaje y reserva.
- El redondeo por horas puede dejar energía sobrante: transportarla al siguiente
  viaje, limitarla a la capacidad y no solicitar otra vez el mismo consumo.
- Conservar los déficits energéticos al proyectar una caché a otra rejilla;
  limitar horas por tiempo no debe sustituir un déficit físico por cero.
- Mantener la misma convención de potencia nominal, eficiencia y espera en el
  backend y en la gráfica. Publicar capacidad, eficiencia y SOC previstos para
  verificar el resultado directamente en HA.
- El SOC/SOH de MQTT puede llegar después del primer cálculo de arranque:
  invalidar la caché y recalcular cuando lleguen valores reales. No verificar
  únicamente que el selector de sensor esté guardado o la integración cargada.

## Ventana disponible frente a carga sugerida (2026-10-09)

- Al corregir las horas de carga se introdujo un recorte indebido del inicio de
  ventana mediante `t_base`. Lo observó el usuario por los puntitos del panel;
  el mismo recorte llegaba al payload EMHASS. Mantener el inicio físico.
- Comprobar conjuntamente `window_start`, `def_start_timestep`, horas y matriz:
  una ventana amplia debe coexistir con pocos slots sugeridos al final.
- Verificar los arrays publicados por el sensor y consumidos por el optimizador,
  además del dibujo; una gráfica correcta no demuestra por sí sola disponibilidad.

## CI proporcionada al producto (2026-10-09)

- GitHub bloquea errores funcionales, lint/formato básico y tipos. SOLID/KISS,
  antipatrones, seguridad extensiva, mutación y E2E se conservan en local.
- Separar dependencias de CI y desarrollo: no instalar herramientas avanzadas
  que no se van a ejecutar en cada push.
- Declarar reglas y versiones de herramientas; Ruff 0.16 amplió sus defaults
  de 59 a 413 y convirtió una dependencia abierta en cientos de fallos nuevos.
- Validar la suite completa con los plugins y la versión de HA declarados,
  además de las regresiones seleccionadas. Las fixtures deben restaurar su zona
  horaria antes del verificador de limpieza de Home Assistant.
