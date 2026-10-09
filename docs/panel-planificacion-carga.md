# Panel de planificación de carga

El panel nativo `/ev-trip-planner-<vehicle_id>` muestra la planificación del vehículo,
no un inventario general de sus entidades. Su interfaz está en
`custom_components/ev_trip_planner/frontend/panel.js` y `panel.css`.

## Información principal

- Energía, duración y potencia máxima del **perfil publicado**.
- Próximo viaje activo.
- Gráfica del perfil y ventanas disponibles de cada carga.
- Viajes semanales y puntuales, con filtros para activos y pausados.
- Parámetros numéricos de EMHASS en un desplegable secundario.

Los datos de viajes se actualizan desde los atributos del sensor `trips_list`
que Home Assistant envía al frontend. El servicio `trip_list` se utiliza como
alternativa y después de guardar una modificación, no en cada cambio de una
entidad ajena al planificador.

## Cómo interpretar la gráfica

La fuente es el sensor agregado **EMHASS Perfil Diferible** cuyo atributo
`vehicle_id` coincide con el vehículo del panel.

| Atributo | Representación |
| --- | --- |
| `power_profile_watts` | Potencia del perfil agregado, convertida de W a kW |
| `p_deferrable_matrix` | Tramos con potencia distinta de cero de cada fila |
| `def_start_timestep_array` | Inicio de la ventana disponible |
| `def_end_timestep_array` | Límite de la ventana |
| `def_total_hours_array` | Horas solicitadas para cada carga |
| `p_deferrable_nom_array` | Potencia nominal de cada carga |

El backend actual utiliza pasos de **una hora**. La energía del resumen es la
integral del perfil agregado: `sum(power_profile_watts) / 1000` kWh. Las filas
pueden solaparse; no se suman para reconstruir este resumen, porque el backend
combina el perfil usando el máximo de las filas.

Las ventanas disponibles y la carga propuesta son cosas distintas. El panel
representa los valores publicados, sin recalcular ni recortar el perfil.

**Es la entrada propuesta a EMHASS, no la salida de su optimización.** El
sensor actual no publica una fecha base absoluta para los pasos. Por eso el
eje muestra horas relativas (`0 h`, `+24 h`...) y `last_updated` se presenta
únicamente como hora de actualización del sensor, no como origen exacto del eje.

Las filas de la matriz están ordenadas por ventana; `deferrables_schedule`
puede tener otro orden. El índice EMHASS solo se muestra si la ventana permite
identificar un registro sin ambigüedad. No se asignan nombres de viajes a filas
por mera coincidencia de posición.

## Comprobaciones del frontend

Pruebas de transformación de datos y contratos de los formularios, sin levantar
Home Assistant ni modificar viajes reales:

```bash
node --experimental-vm-modules --test tests/panel-planning.test.mjs
node --check custom_components/ev_trip_planner/frontend/panel.js
```

## Despliegue y caché

La versión `VERSION` de `frontend/panel.js` debe coincidir con
`PANEL_FRONTEND_VERSION` en `panel.py`. Las pruebas del frontend comprueban esta
coherencia. La versión forma parte de la URL del JavaScript registrado por HA
y de la URL de CSS.

Copiar archivos no cambia la URL que HA ya tiene registrada en memoria. Al
aplicar una nueva versión, debe reiniciarse HA para registrar la nueva URL.
Verificar después en una sesión normal, sin desactivar la caché de Playwright.
Una prueba con caché desactivada no demuestra que los clientes existentes reciban
el recurso nuevo. Una vez cambiado el registro, recargar la página completa.

**No usar la recarga de la integración como sustituto del reinicio en la versión
actual:** `async_unload_entry_cleanup` llama a `async_delete_all_trips`, que guarda
la eliminación de los viajes. Ese problema del ciclo de vida está pendiente de
corrección y es independiente de la presentación del panel.
