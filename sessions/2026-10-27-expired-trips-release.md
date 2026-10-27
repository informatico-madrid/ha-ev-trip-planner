# Corrección de viajes vencidos y publicación 0.8.2

## Problema y corrección

Un viaje puntual pasado seguía pendiente y se descontaba del SOC medido hoy.
Con 78% de SOC, 22,96 kWh útiles y un consumo pasado de 18 kWh, el siguiente
viaje solicitaba ocho horas de carga como si la batería estuviera vacía.

El publicador por lotes de EMHASS excluye las salidas explícitas vencidas antes
de calcular ventanas y energía. Se aplicó el mismo cambio en el repositorio y
en `/home/malka/homeassistant/custom_components/ev_trip_planner/emhass/adapter.py`.
Los registros históricos se conservan. Producción pasó a solicitar dos horas
y el recálculo completo de EMHASS finalizó Optimal.

## Incidencia de CI

El primer push pasó las pruebas locales, pero CI con semilla `2679221485`
detectó siete fallos dependientes del orden: los nuevos tests y su fixture
padre usaban distintos `MonkeyPatch` sobre `dt_util.now`. Un desmontaje podía
reinstalar el reloj de la fixture después de restaurarse el reloj real.

Los nuevos tests usan ahora `patch.object` dentro de `with`, que restaura el
reloj al salir del test, antes del desmontaje de la fixture. Una revisión
independiente confirmó el alcance de los relojes y las aserciones.

## Verificación local

- Suite completa con la semilla de CI y dos workers: 2762 passed, 1 skipped.
- Regresiones: fecha local y UTC, salida exacta, viaje futuro próximo,
  expiración, limpieza de caché y arrays enviados a EMHASS.
- Cambios de producción limitados al filtro de viajes vencidos y metadatos
  de versión; la corrección de aislamiento pertenece únicamente a los tests.
