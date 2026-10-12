# Recuperar anticipación con t_base y SOC encadenado — 2026-10-12

## Alcance acordado

Recuperar la carga anticipada del planificador manteniendo el balance de una
sola batería, la reserva, capacidad, eficiencia, déficits y ventanas corregidos
el 9 de octubre. Preparar y verificar los datos publicados; no modificar el
optimizador EMHASS ni añadir parámetros, helpers o interfaz.

Solo cambian dos módulos de ejecución: `calculations/energy_chain.py` y
`calculations/window_pipeline.py`. Las pruebas y esta documentación acompañan
la corrección. La implementación se prepara en un worktree temporal y se prueba
aisladamente; se aplica primero a producción y se sincroniza el repositorio
principal después de verificarla.

## Causa y corrección

El commit `73378d0` sustituyó la ruta cap -> déficit por `plan_energy_chain`
para las ventanas resueltas. Corrigió la reutilización del SOC inicial, pero
el nuevo `EnergyChainContext` no recibía `t_base` y solo solicitaba el mínimo.

- Se conecta `t_base` desde el contexto del pipeline.
- Se conserva intacto el cálculo hacia atrás de necesidades mínimas.
- Se limita la energía anticipable a la demanda restante más una reserva y a
  la capacidad física. La rampa de holgura utiliza ese presupuesto.
- Las horas opcionales completas se redondean hacia abajo; no pueden superar
  demanda pendiente, espacio disponible ni límite de salud.
- El cap post-viaje usa el SOC proyectado con la carga de esa etapa.
- Las horas imprescindibles mantienen su redondeo hacia arriba y prioridad.
- La carga adicional pasa por el mismo balance hacia delante, reduciendo
  la necesidad de las etapas siguientes; no cambia la ventana física.

## Verificación aislada

- Las pruebas nuevas fallaron primero en la anticipación, el efecto de
  `t_base` y los arrays publicados sobre el código anterior.
- Suite completa: **2759 pruebas correctas**, Python 3.14.8 / HA 2026.9.4,
  en contenedor temporal sin red ni acceso al HA de producción.
- `energy_chain.py`: **100 % de líneas y ramas** (102 sentencias, 22 ramas).
- Pyright: 0 errores / 0 avisos. Ruff, Black y `git diff --check` correctos.
- Las regresiones del 9 de octubre pasan sin modificar sus expectativas.

Simulación reproducible desde lunes 12 de octubre a las 10:00 de Madrid,
capacidad 23.24 kWh, SOC 43 %, potencia 3.4 kW, eficiencia 85 %, espera 0.02
puntos SOC/h, viajes explícitos 6 / 26 / 26 kWh:

| t_base | Horas martes / miércoles / jueves | SOC salida martes |
|---|---|---|
| 6 | 1 / 6 / 9 | 55.01 % |
| 15 | 2 / 5 / 9 | 67.46 % |
| 24 | 2 / 5 / 9 | 67.46 % |
| 48 | 3 / 4 / 9 | 79.92 % |

Se conservan los déficits de 5.084 kWh para los viajes de 26 kWh con batería de
23.24 kWh y reserva de 10 %. En la cadena factible 6 / 18 / 18 kWh, las horas
pasan de 0 / 6 / 6 a 2 / 4 / 6: misma energía total, adelantada y contabilizada.

## Producción

Copia previa exacta de los dos módulos:
`/tmp/opencode/ev-anticipation-before-20261012.tar`.
Se comprobó igualdad con la versión probada antes del reinicio normal de HA.
No se utilizó la recarga de entrada que puede borrar viajes.

Verificación posterior al arranque:

- Core 2026.10.0 **RUNNING**, integración **loaded**, opciones intactas:
  batería 28 kWh, potencia 3.4 kW, consumo 0.18 kWh/km, reserva 10 %, SOH
  instrumentado y `t_base=15`. Los tres viajes permanecen iguales y activos.
- El SOC real pasó de 57 a **58 %** durante el despliegue; no se confunde con
  la simulación congelada al 43 %. SOH=83 %, capacidad publicada **23.24 kWh**.
- Sensor agregado: **[1, 5, 9] horas**, potencia **[3400, 3400, 3400] W**,
  kWh de red **[3.4, 17.0, 30.6]**. El martes ya no publica cero.
- SOC previsto de salida del martes **70.0761 %**; tras el viaje **44.2586 %**.
- Sobre `planning_reference=2026-10-12T12:00:00+00:00`, las ventanas publicadas
  son **[0, 23, 46] -> [18, 41, 65]**. Una consulta derivada del estado real
  confirma 1 / 5 / 9 posiciones activas y ninguna fuera de esos límites.
- Se mantienen los déficits de 5.084 kWh de los dos viajes de 26 kWh.
- No aparecen excepciones de cálculo; los avisos de arranque sin SOC se
  resuelven al llegar el dato MQTT y republicarse la cadena.
