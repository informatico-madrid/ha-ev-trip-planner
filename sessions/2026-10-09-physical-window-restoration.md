# Restaurar disponibilidad física para EMHASS — 2026-10-09

## Observación del usuario y causa

Tras corregir la reserva, desapareció gran parte de la ventana con puntitos del
panel nativo. El usuario aclaró que EMHASS debe poder usar todo el intervalo entre
regreso y siguiente salida, aunque la matriz proponga la carga al final.

Se confirmó que no era solo una representación: `_apply_energy_chain_result`
reescribía `def_start_timestep` y `window_start` con el inicio de las últimas
`max(t_base, horas_necesarias)` horas. El lunes quedaba desde las 07:00 del lunes,
en vez de desde el regreso estimado del sábado a las 12:00.

Los comandos de optimización en `configuration.yaml` leen directamente
`def_start_timestep_array` / `def_end_timestep_array` del sensor. Por tanto,
el recorte también limitaba el payload enviado a EMHASS.

## Corrección

- Conservar los límites físicos resueltos originalmente por las ventanas.
- No modificar el inicio de disponibilidad al aplicar el balance energético.
- Separar `suggested_charging_start_timestep` de `def_start_timestep`.
- Mantener horas de carga y reserva corregidas. La matriz continúa compactada
  al final, pero EMHASS puede adelantar su posición dentro de la ventana amplia.
- No requiere cambios en el frontend: el panel representa los límites publicados.

## Verificación

La prueba del lunes falló primero con el inicio recortado. Después comprueba:

- Ventana física del sábado 12:00 al lunes 13:30, con 49 slots completos.
- 4 horas necesarias, sugeridas en 09:00–13:00 del lunes.
- Reserva de al menos 10 % después del viaje.
- Arrays reales del sensor y matriz, no solo diccionarios internos.

Se corrigió también el reloj de esa fixture para que `dt_util.now()` devuelva
hora local de Madrid, como en HA, en lugar de UTC.

688 pruebas Python, 25 del panel, Pyright, Black/isort y `git diff --check`
correctos. Se aplicaron los tres módulos afectados, se comprobó igualdad con
el clon y se realizó un reinicio normal de HA.

## Verificación final en producción

- Core **RUNNING**, comprobado con una lectura nueva de `get_config`.
- Lunes: `window_start=2026-10-10T10:00:00+00:00` (sábado 12:00 local), salida
  `2026-10-12T11:30:00+00:00` (lunes 13:30 local).
- Con origen de rejilla viernes 15:00 local: límites **21–70**, 49 pasos
  completos; cantidad **4 horas**. La matriz sugiere solo **66–70**, lunes
  **09:00–13:00**.
- Se renderizaron los mismos arrays que leen los comandos EMHASS:
  `def_start_timestep=[0,21,75,120]`, `def_end_timestep=[17,70,115,165]`,
  `def_total_hours=[6,4,7,3]`.
- En el DOM del panel, la banda de disponibilidad del lunes abarca **49.5 h**
  (29.4643 % de 168 h) y la banda de carga **4 h** (2.38095 %). Captura revisada:
  puntitos extendidos por toda la ventana y carga compactada al final.
- La reserva corregida se conserva: SOC previsto tras el lunes aproximadamente
  **15.32 %** con los datos actuales (capacidad útil 23.24 kWh).
- Consola del panel sin errores. No fue necesaria una modificación del frontend.
