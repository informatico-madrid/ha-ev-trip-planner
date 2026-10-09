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
