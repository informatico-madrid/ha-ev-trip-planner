# Límite de carga antes de la salida — 2026-10-09

## Diagnóstico

Viaje semanal del viernes con salida local a las 12:35. El sensor publicaba un
fin de ventana de cinco pasos, calculado a las 08:05 sin una referencia explícita.
EMHASS iniciaba su siguiente optimización a las 09:00: esos cinco pasos permitían
carga hasta las 14:00. Se confirmó `Europe/Madrid` en HA y EMHASS, pasos de 60 min
y `method_ts_round=nearest`; el error de este viaje era de referencia y redondeo,
no una resta GMT fija. Además, los viajes puntuales sin offset sí se interpretaban
incorrectamente como UTC, desplazando su salida una o dos horas.

## Corrección

- Referencia explícita, redondeada en UTC como la rejilla de EMHASS.
- Límite exclusivo con `floor`, conservando separadamente la salida exacta.
- Proyección de parámetros cacheados a la rejilla actual sin mutar el cálculo.
- Carga limitada a la capacidad de los pasos disponibles. Si no cabe, se publica
  la energía pendiente. Un fin 0 lleva duración y potencia 0 para no desactivar
  accidentalmente la restricción temporal en EMHASS.
- Actualización alineada con las fronteras de redondeo `:00` y `:30` UTC.
- Fechas puntuales locales interpretadas en la zona de HA; offsets explícitos
  conservados y siguiente ocurrencia semanal comprobada también por minutos.
- Sensor y panel incluyen referencia y fechas exactas; frontend 4.1.0 muestra
  la hora de salida y el fin de los pasos completos como datos diferentes.

## Pruebas

208 pruebas Python correctas en un contenedor aislado con HA 2026.9.4 / Python
3.14, sin red ni puertos de HA. 25 pruebas Node correctas. Comprobaciones de
sintaxis, formato Black e imports isort correctas. Regresiones de verano/invierno,
cambio DST de otoño, cambio de origen entre cálculos y ausencia de pasos completos.

Se despliega en producción mediante archivos concretos y reinicio normal de HA,
sin utilizar la recarga de entrada que contiene el borrado de viajes.

## Verificación en producción

HA terminó de arrancar en estado `RUNNING`. En una pestaña normal se cargó el
frontend 4.1.0. La referencia publicada es las 10:00 locales; el primer viaje
mantiene salida 12:35, fin exclusivo 2 y última carga a las 12:00. Todos los
tramos publicados terminan antes de su salida. Comparación de los cuatro viajes
con la referencia anterior al reinicio: mismos datos y estados.

Se ejecutó la automatización habitual de optimización. La llamada inicial dio
timeout mientras la automatización seguía trabajando; se verificó su traza y no
se repitió la ejecución. Terminó correctamente a las 10:11:54 con resultado
`Optimal` y mutex liberado. El sensor de salida `p_deferrable0` contiene carga
únicamente en los pasos 10:00 y 11:00, que terminan a las 12:00.

El usuario validó el resultado en producción y autorizó el commit y el push.
