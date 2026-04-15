v0.5.9 — EMHASS hotfixes & per-trip cache

Resumen
- Correcciones críticas (hotfixes) para la integración EMHASS que arreglan problemas por los que cambios de potencia de carga quedaban ignorados.
- Añadida caché de parámetros por viaje (per-trip EMHASS params) y nuevas APIs/sensores para exponer esos datos por viaje.
- Varios helpers y defensas añadidas (lectura de `entry.options` antes que `entry.data`, guardias cuando `_published_trips` está vacío, manejo robusto de SOC/hora regreso).

Cambios destacados
- Fix: Leer `charging_power_kw` desde `entry.options` primero; usar `is None` para no tratar `0` como falsy.
- Fix: Registrar listener de config entry durante `async_setup_entry` para asegurar updates de potencia.
- Fix: Recarga de viajes cuando `_published_trips` está vacío antes de publicar a EMHASS.
- Feature: Cache por viaje (`per_trip_emhass_params`) con parámetros precalculados (horas, potencias, perfiles de potencia, timestep inicio/fin, kWh necesarios, deadline, emhass_index).
- Feature: Nuevo sensor `TripEmhassSensor` para exponer los 9 atributos por viaje y funciones CRUD (`async_create_trip_emhass_sensor` / `async_remove_trip_emhass_sensor`).
- Fix: `async_publish_deferrable_load` ahora calcula `def_start_timestep` desde las ventanas de carga en vez de usar 0 fijo.

Tests & Calidad
- Se añadieron tests TDD para cada hotfix y feature (tests en `tests/` relacionados con `emhass_adapter` y `TripEmhassSensor`).
- Verificaciones locales: tests relevantes ejecutados; ruff/mypy aplicados en los módulos modificados según la spec.

Notas para integradores
- No hay cambios breaking conocidos para usuarios finales; configure `charging_power_kw` como antes, pero la opción en la entrada (`options`) ahora tiene prioridad.
- Los sensores por viaje (`TripEmhassSensor`) sólo se crean cuando se invoca la API de creación o cuando el manager crea sensores en el ciclo de vida de los viajes.

Referencias
- Especificación: `specs/m401-emhass-hotfixes`
- Commit principal asociado: rama `feat/m401-emhass-per-trip-sensors`
