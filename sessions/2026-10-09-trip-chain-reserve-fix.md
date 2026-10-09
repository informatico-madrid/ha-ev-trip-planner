# Cadena de viajes y reserva tras el lunes — 2026-10-09

> Corrección posterior: el recorte del inicio de ventana descrito en este registro
> se retiró tras la observación del usuario. La disponibilidad física permanece
> amplia y la posición al final es solo una sugerencia; ver
> `2026-10-09-physical-window-restoration.md`.

## Petición y reproducción

El usuario pidió corregir el planificador después de confirmar que, con batería
vacía tras el sábado y un viaje de 8 kWh el lunes, el plan publicaba una sola hora.
El gráfico del Centro de Mando se corrigió antes, por separado, para leer los
consumos por ID y las fechas publicadas en lugar del fallback de 7 kWh.

La regresión nueva `test_monday_charges_from_empty_saturday_and_preserves_ten_percent`
se ejecutó primero contra el código anterior: falló con **1 != 4**. Configuración
de la prueba: nominal 28 kWh, SOH 84 %, SOC 57 %, potencia 3.4 kW, reserva 10 %,
`t_base=6`; los cuatro viajes reales con sus IDs y consumos explícitos.

## Corrección

- Nuevo cálculo puro `calculations/energy_chain.py`, activado por el pipeline
  para ventanas que ya contienen viaje, rejilla y salida resueltos.
- Necesidades calculadas hacia atrás cuando no hay oportunidad posterior de
  carga, limitando el transporte de energía a la capacidad física.
- Simulación hacia delante: energía inicial única, carga entregable, consumo
  de cada viaje, reserva y déficits. Se conserva el excedente de redondeo.
- Potencia nominal de red, eficiencia prevista del 85 % y espera de 0.02 puntos
  SOC/h, para usar la misma convención que el gráfico actual. El gráfico lee
  ahora capacidad/eficiencia publicadas cuando están disponibles.
- Salud de batería: limitar el inicio de carga a las últimas
  `max(t_base, horas_necesarias)` horas; conservar las horas necesarias en lugar
  de reducirlas por holgura y después comprobar el déficit sobre esa demanda
  artificialmente reducida.
- Publicar SOC antes/después del viaje, reserva incumplida, capacidad/eficiencia
  y energía no servida. La proyección temporal conserva los déficits originales.
- Los callers antiguos por horas y las transformaciones explícitas mantienen
  su contrato. Se recalcula también la cadena al publicar un viaje individual.

## Pruebas y revisión

- **688 pruebas Python correctas**, con HA 2026.9.4 / Python 3.14.6, en un
  contenedor aislado, sin red/puertos y con el repositorio montado solo lectura.
- **25 pruebas Node del panel** y **5 del gráfico** correctas.
- Pyright: **0 errores / 0 avisos** en los cinco módulos afectados.
- Black, isort y `git diff --check` correctos.
- Se comprobaron carga previa para viajes sin ventana, capacidad insuficiente,
  ventana corta, transporte del redondeo, reserva erosionada por espera,
  precedencia de kWh y consumo configurado, y persistencia de déficits al proyectar.

Tres pruebas antiguas fallaron también en un worktree limpio de `b85a966`:
esperaban un fin calculado con ceil, la hora local sin normalizar a UTC y una
separación de índices sin el ceil/floor de la rejilla. Se corrigieron sus
aserciones para comprobar los límites físicos y el instante real; después,
la selección completa pasó. Las tres regresiones adicionales cubren llegada
de batería tras arranque, descarte de cambios solo de atributos/valores inválidos
y registro/cancelación del listener SOC/SOH.

## Despliegue

Se aplicaron solo los cinco módulos afectados en el componente de producción.
Se comprobó igualdad byte a byte con el clon mediante `git diff --no-index`.
Se inició un reinicio normal de HA después de las pruebas, conservando una
referencia de los cuatro viajes para la comprobación posterior. No se utilizó
la recarga de entrada que borra viajes.

La comprobación del primer arranque detectó el cálculo inicial con capacidad
nominal antes de llegar los datos MQTT. Se añadió un listener SOC/SOH que
invalida la caché SOH y republica el plan al llegar un valor real distinto. Se
reprodujo primero la ausencia del callback; después pasaron las 688 pruebas,
se aplicó el listener y se realizó el reinicio final.

## Verificación final en producción

- Estado del Core comprobado mediante lectura nueva de `get_config`: **RUNNING**.
  Integración `loaded`, opciones conservadas y cuatro viajes iguales a la
  referencia previa al despliegue.
- Al llegar SOH=84, el plan se actualizó inmediatamente: **23.52 kWh**, reserva
  **10 %**, eficiencia prevista **0.85**. Ya no quedó el cálculo inicial nominal.
- Horas por orden cronológico (sábado, lunes, miércoles, viernes siguiente):
  **[4, 4, 7, 3]**.
- Lunes: **4 horas**, perfil compactado **09:00–13:00**, salida **13:30**;
  SOC de salida **49.1497 %**, tras consumo de 8 kWh **15.1361 %**;
  energía no servida y reserva incumplida **0**.
- Gráfico del Centro de Mando, leído de sus puntos Plotly ya renderizados:
  lunes **49.1 % → 15.1 %**, con cuatro tramos de 3400 W (09, 10, 11 y 12 h).
  Consola del navegador sin errores nuevos.
- Sábado y miércoles conservan el aviso por consumo de 24 kWh frente a 23.52
  kWh útiles: salida prevista 100 %, déficit de **2.832 kWh** incluyendo reserva
  (0.48 kWh de consumo y 2.352 kWh de reserva). No se modifican esos datos ni se
  declara factible completar esos viajes con la capacidad indicada.
