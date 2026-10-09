# CI esencial y reparación de la ejecución GitHub — 2026-10-09

## Causa inicial

La ejecución `37936261146` del commit `73378d0` falló antes de los tests:
Ruff 0.16 amplió sus reglas predeterminadas de 59 a 413. El proyecto dependía
de defaults y una versión abierta, por lo que aparecieron 588 incidencias nuevas.

La política anterior se declaró explícitamente y se fijó Ruff 0.16.10. Las
regresiones de configuración comprueban que se siguen rechazando nombres
indefinidos e imports sin uso; no se ignoran errores funcionales para pasar CI.

## Decisión del usuario

La CI debe ser proporcionada al producto. Los análisis costosos, frágiles o de
bajo valor en cada push permanecen en local: SOLID/principios/antipatrones,
seguridad extensiva, mutación, BMAD y E2E. GitHub mantiene lint/formato básico,
tipos de integración, toda la suite funcional Python y las pruebas del panel.

## Cambios

- Dependencias esenciales en `requirements_ci.txt`, sin las herramientas
  avanzadas. Desarrollo local incluye esa base y sus herramientas adicionales.
- `make quality-gate-ci` no llama a los layers avanzados. Los targets locales,
  scripts y pruebas se conservan, con rutas actualizadas a `.agents`.
- Workflow con caché pip, Node.js 22, límite de 15 minutos e informe JUnit.
- Entorno de pruebas fijado a HA 2026.9.4 y su plugin pytest compatible.
- Compatibilidad de metadata del dispositivo padre y de la configuración HTTP
  sin ignorar los errores de tipos ni cambiar IDs de entidades.
- Limpieza de zona horaria de fixtures antes del verificador de HA; aserciones
  basadas en la rejilla real y en los contratos actuales de reserva/consumo.
- Sincronización de los aliases `total_hours` y `def_total_hours` en la caché.

## Validación

En un entorno nuevo Python 3.14.8, instalado únicamente con
`requirements_ci.txt`, pasaron **2734 pruebas Python** y **25 del panel**.
Ruff y Pyright correctos, dependencias sin conflictos. Se comprobó que no estaban
instalados Pylint, Semgrep, Bandit, pip-audit, Refurb, Vulture ni import-linter.
Se añade una regresión del routing de Make para mantener esta separación.

La validación final de GitHub se realiza después del commit y push; el resultado
local no se presenta como una ejecución remota ya completada.
