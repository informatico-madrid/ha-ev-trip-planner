# Auditoría de consumo, SOH y cadena energética — 2026-10-09

> Registro previo a la implementación. La corrección y su verificación posterior
> están en `2026-10-09-trip-chain-reserve-fix.md` y
> `2026-10-09-physical-window-restoration.md`.

## Alcance y estado

Investigación del código y del estado real tras la actualización del selector SOH.
No se ha implementado aún la corrección energética descrita al final. Durante
esta investigación no se han cambiado viajes, automatizaciones ni parámetros
OVMS. Los únicos archivos nuevos/modificados son estas notas y los patrones.

## Consumo: contrato e implementación actuales

- `calculations/windows.py:calculate_energy_needed` prioriza la **presencia**
  de `kwh`. Con `km=120, kwh=24`, usa 24 kWh, no `120 × 0.18`.
- Un `kwh=0` también tiene prioridad: no activa el cálculo por distancia.
- Solo sin la clave `kwh` se usa distancia por consumo. La función admite
  `consumption_kwh_per_km`, pero las rutas principales de publicación no lo
  pasan y utilizan el default 0.15. La opción `kwh_per_km=0.18` no está conectada
  a esas rutas.
- Los servicios normales de creación exigen `km` y `kwh`; los viajes guardados
  actuales tienen ambos campos. Cambiar los km no recalcula automáticamente
  unos kWh explícitos existentes.

## SOH

La entrada `01KPZZQ6ADWTBNPKCCE5K88VN3` está cargada y sus opciones conservan
`soh_sensor=sensor.chispitas_instrument_soh_nissan_leaf`, con lectura 84 %.
Capacidad nominal 28 kWh, potencia 3.4 kW, reserva 10 % y `t_base=6`.

Se ejecutó el código **desplegado**, montado en solo lectura, en un contenedor
aislado con HA 2026.9.4, sin red ni puertos y con `python3 -B`. Al construir el
adaptador con la configuración comprobada y una instantánea SOH=84, selecciona
el sensor nuevo y su proveedor calcula **23.52 kWh**. Esto comprueba la ruta de
configuración/cálculo; los diagnósticos actuales no exponen directamente el
valor interno del proveedor del proceso HA que está ejecutándose.

## Límite OVMS y SOC dinámico

Consulta de solo lectura al propio vehículo: servicio `ovms.send_command`,
`command="config list"`, `parameters="xnl"`:

```text
autocharge: no
canwrite: yes
suffsoc: 60
```

El sensor `sensor.chispitas_charge_soc_limit` publica `v/c/limit/soc`. El módulo
Nissan Leaf toma esa métrica de `xnl/suffsoc`. En el código oficial consultado,
`HandleCharging` solicita parar al alcanzar el objetivo si `autocharge` está
activo y no hay climatización encendida/solicitada; el comando requiere
`canwrite`. Por tanto, el 60 % configurado no es una autoparada activa de OVMS
con `autocharge=no`. No confundirlo con el cap calculado por EV Trip Planner.

Fuente: `openvehicles/Open-Vehicle-Monitoring-System-3`,
`vehicle/OVMS.V3/components/vehicle_nissanleaf/src/vehicle_nissanleaf.cpp`,
`ConfigChanged`, `HandleCharging` y `RemoteCommandHandler`. Se consultó master;
no se ha sustituido ni actualizado el firmware del vehículo.

También se comprobó que `automation.chispitas_detener_carga_al_70_soc` y
`automation.control_cargas_aplazables_segun_plan_mpc` están apagadas. El archivo
del control MPC contiene su propia condición SOC >90 %, pero esa automatización
no está activa. No se han activado ni modificado.

## Reanudación del lunes y atributos obsoletos

La referencia del navegador mostraba `rec_1_5q4ih9` pausado. Después del reinicio
lo mostraba activo; IDs y demás campos eran iguales.

El log de HA registra **`Resumed recurring trip rec_1_5q4ih9` a las 10:33:54
locales (08:33:54 UTC)**. El almacenamiento ya contenía `activo=true` con esa
hora. El historial de `trips_list` no publicó el cambio hasta las 11:26:59,
durante el arranque posterior. Por tanto, el reinicio mostró una reanudación
anterior, no una activación creada por actualizar SOH. No se atribuye quién
solicitó la reanudación a partir de ese log.

Posteriormente el usuario confirmó que él retiró la pausa y pidió no continuar
con esa cuestión. No se incluyó una corrección de pausa/reanudación en este trabajo.

Reproducción aislada con el código desplegado:

1. `TripCRUD.async_get_recurring_trips()` devuelve los mismos diccionarios del
   estado mutable del gestor.
2. El coordinador conserva esas referencias; `definitions.default_attrs_fn`
   vuelve a publicarlas como atributos.
3. Al cambiar `activo` se altera también el objeto de los atributos anteriores.
   El snapshot serializado era `false`, pero los atributos anteriores y nuevos
   pasan a ser iguales (`true`) y comparten la identidad del viaje.

Corrección pendiente: crear snapshots independientes al publicar datos y
atributos, y verificar que pausar/reanudar emite un cambio de estado observable
en otras pestañas, sin depender de reiniciar.

## Reproducción de la cadena

Instantánea reproducible del viernes 2026-10-09 a las **10:00 Europe/Madrid**,
SOC 57 %, capacidad 23.52 kWh, potencia 3.4 kW, reserva 10 %, `t_base=6`.
Incluye los cuatro viajes activos: viernes 5 kWh, sábado 24 kWh, lunes 8 kWh,
miércoles 24 kWh. No representa los índices temporales del panel más tarde.

| Viaje | Energía que pide cargar antes del cap | Horas antes | Horas después |
|---|---:|---:|---:|
| Viernes 12:35 | 5 kWh | 2 | 2 |
| Sábado 08:00 | 12.946 kWh | 4 | 2 |
| Lunes 13:30 | 8 kWh | 3 | 1 |
| Miércoles 10:38 | 12.946 kWh | 4 | 1 |

El pipeline devuelve déficit 0 para todas esas ventanas porque la propagación
usa las horas **ya reducidas** por el cap. No conserva la demanda energética
original como restricción independiente.

Los cálculos de cada viaje reutilizan SOC=57 en lugar de descontar viajes y
acumular carga. Además, `calculate_energy_needed` pide cargar el consumo del
viaje cuando la energía actual ya cubre consumo y reserva: una heurística de
preparación de cadena, no una simulación de esa cadena.

Comprobación energética de las dos primeras ventanas del ejemplo, suponiendo
que se entregan todos los kWh planificados y sin pérdidas:

- Inicio: `23.52 × 0.57 = 13.4064 kWh`.
- Tras 2 h de carga y el viernes: `13.4064 + 6.8 - 5 = 15.2064 kWh`.
- Antes del sábado, con otras 2 h: `15.2064 + 6.8 = 22.0064 kWh`.
- Frente a 24 kWh de consumo faltan **1.9936 kWh**; frente a consumo más reserva
  faltan **4.3456 kWh**. El déficit 0 del pipeline no demuestra factibilidad.
- Incluso lleno, el consumo de 24 kWh supera 23.52 kWh en 0.48 kWh. Ese caso
  exige marcar inviabilidad por capacidad, no propagar energía imposible de
  almacenar ni prometer un regreso con reserva.

## Corrección propuesta, todavía no implementada

1. Resolver el consumo una vez por viaje: conservar kWh explícitos; cuando
   falten, utilizar el consumo configurado. No convertir automáticamente un
   cero explícito en «sin dato» sin definir ese contrato.
2. Usar una instantánea única de SOC, capacidad SOH, potencia, reserva y tiempo
   para todo el cálculo. Conservar demanda necesaria y carga permitida como
   magnitudes diferentes.
3. Calcular necesidades hacia atrás desde las salidas, con reserva y capacidad
   de las ventanas, para anticipar carga cuando después no haya oportunidad.
   Limitar la anticipación a la energía realmente almacenable.
4. Simular hacia delante la energía de una sola batería: sumar carga entregable
   una vez, descontar cada viaje una vez, respetar capacidad y disponibilidad,
   y comprobar la reserva tras cada viaje. Distinguir falta de tiempo, falta
   de capacidad y la dependencia de un viaje anterior inviable.
5. Aplicar la protección dinámica para retrasar/limitar carga temprana sin
   borrar la demanda futura. Si protección y viabilidad entran en conflicto,
   mostrar el conflicto; no etiquetarlo como déficit cero.
6. Publicar un único resultado coherente para EMHASS, SOC proyectado y alertas.
   Respetar la rejilla y los deadlines corregidos; el redondeo de horas no debe
   contar como entregada energía que no cabe en la batería.

Verificaciones propuestas: viaje único ya cubierto, cadena sin recarga entre
salidas, saturación de batería, demanda superior a capacidad, reserva tras cada
viaje, cap dinámico frente a demanda original, precedencia de consumo y eventos
de pausa/reanudación con snapshots independientes.
