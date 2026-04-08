Crea una nueva spec en `specs/solid-refactor-coverage/` para refactorizar
la arquitectura del código fuente y alcanzar 100% de cobertura de tests.


## Contexto


La spec anterior (`regression-orphaned-sensors-ha-core-investigation`) resolvió
el bug de sensores huérfanos. La cobertura quedó en ~85% porque los módulos
`trip_manager.py` (~224 líneas sin cubrir) y `emhass_adapter.py` tienen lógica
de negocio mezclada con I/O y dependencias externas (EMHASS, HA APIs), lo que
hace imposible testearlos sin dobles de test profundamente anidados.


## Fuente de verdad para test doubles


**ANTES de decidir qué tipo de doble usar en cualquier test, consultar
`docs/TDD_METHODOLOGY.md` sección `## Layered Test Doubles Strategy` y
`## Test Doubles Reference Table`.**
Esas dos secciones son la fuente de verdad del proyecto. No el criterio del
momento, no la intuición, no "usar Mock porque es fácil".

La estrategia tiene 3 capas obligatorias:
- **Capa 1** — `tests/__init__.py`: Fakes y Stubs compartidos (datos de test,
  `create_mock_*`, helpers de setup). Nunca en `conftest.py`.
- **Capa 2** — Stubs por método: sobreescribir solo el método concreto que
  necesita respuesta diferente en ese test.
- **Capa 3** — Patch en el boundary: `patch()` exclusivamente en factories
  o dependencias inyectadas por HA, nunca dentro del código propio.

La tabla distingue: Fake, Stub, Spy, Mock, Fixture, Patch — cada uno con
su caso de uso. Un test difícil de escribir es señal de mal diseño en el
código fuente, no señal de añadir más dobles.

Regla de oro HA (ESTRICTO): `MagicMock(spec=ClaseReal)` obligatorio para
clases propias. Nunca `MagicMock()` sin `spec`.


## Diagnóstico previo conocido


- `trip_manager.py`: Clase God Object. Mezcla persistencia, cálculos de
  energía, optimización EMHASS y gestión de estado. Las ~224 líneas sin
  cubrir son paths de EMHASS que requieren dobles profundamente anidados
  para alcanzarlos — señal clara de que el código necesita refactor, no
  más tests.
- `emhass_adapter.py`: Adaptador con lógica de negocio embebida. Llama
  directamente a APIs externas sin interfaz inyectable. Imposible testear
  paths de error sin Patch profundo.
- `services.py`: Handlers que, aunque delgados tras el refactor anterior,
  aún acceden a `trip_manager` sin abstracción de interfaz formal.


## Objetivo


Refactorizar el código fuente aplicando principios SOLID de forma que los
tests sean fáciles de escribir usando el doble apropiado según la tabla.
La cobertura 100% debe ser consecuencia del buen diseño, no el objetivo
directo.

Donde ya existan tests que usen `MagicMock()` sin `spec`, o Patches
innecesariamente profundos, o Fakes/Stubs definidos en `conftest.py` en vez
de `tests/__init__.py` — refactorizarlos también para alinearlos con la
Layered Test Doubles Strategy. Solo donde merezca la pena: si el test pasa
y el doble es correcto para su capa, no tocarlo.


## Restricciones obligatorias SUGERIDAS MEJORALO SI PUEDES


1. Consultar `docs/TDD_METHODOLOGY.md` secciones `## Layered Test Doubles
   Strategy` y `## Test Doubles Reference Table` antes de elegir cualquier
   doble de test en cualquier task.
2. Si un test necesita más de 2 niveles de anidación de dobles, la señal
   es PARAR y refactorizar el código fuente primero — no añadir más dobles.
3. NO usar `# pragma: no cover` salvo en código estructuralmente inalcanzable
   documentado con razón explícita y revisión humana.
4. Cada refactor debe ir precedido de su test RED antes de tocar el código
   fuente (TDD estricto RED → GREEN → REFACTOR).
5. Las clases `TripManager` y `EmhassAdapter` NO son SOLID hoy — no escribas
   tests de cobertura sobre ellas sin refactorizarlas primero.
6. Mantener todos los tests E2E pasando en cada checkpoint de fase.
7. `MagicMock(spec=ClaseReal)` obligatorio. Nunca `MagicMock()` sin `spec`
   para clases propias.
8. Fakes/Stubs compartidos viven en `tests/__init__.py`, no en `conftest.py`.


## Fases sugeridas (la spec debe desarrollarlas con tasks detalladas) ES SOLO SUGERENCIA MEJORALO SI PUEDES


### Fase A: Extracción de lógica pura
Identificar y extraer funciones puras de `trip_manager.py`:
- Cálculos de energía (kWh, horas)
- Validación de trips
- Ordenación y filtrado de trips
Mover a módulos puros (`calculations.py` ya existe — ampliar si necesario).
Doble apropiado según tabla: ninguno — son funciones puras, test directo.
Resultado: estas funciones son 100% testeables sin ningún doble.


### Fase B: Protocolo para EmhassAdapter
Definir `EmhassAdapterProtocol` usando `typing.Protocol`.
`EmhassAdapter` implementa el protocolo (sin cambiar su interfaz pública).
`TripManager` recibe el protocolo por inyección en `__init__`.
Doble apropiado según tabla: Fake (clase real con implementación en memoria,
definida en `tests/__init__.py`).
Resultado: tests de TripManager usan `FakeEmhassAdapter` — clase real,
sin MagicMock, sin Patch.


### Fase C: Protocolo para Storage
Definir `StorageProtocol` para operaciones de persistencia de trips.
`TripManager` recibe storage por inyección.
Doble apropiado según tabla: Fake (`InMemoryTripStorage`) — clase real
con dict en memoria, sin tocar ficheros ni HA Store, definida en
`tests/__init__.py`.
Resultado: tests de TripManager son síncronos, rápidos, sin fixtures de HA.


### Fase D: Cobertura consecuente + limpieza de tests existentes
Con Fases A-C completas, los paths antes inalcanzables son testeables con
dobles simples según la tabla.
Escribir los tests que faltan eligiendo el doble según la tabla en cada caso.
Revisar tests existentes en busca de:
  - `MagicMock()` sin `spec` → reemplazar con `MagicMock(spec=ClaseReal)`
  - Fakes/Stubs en `conftest.py` que deberían estar en `tests/__init__.py`
  - Patches dentro del código propio (no en boundaries) → refactorizar
Solo corregir donde el doble actual es incorrecto para su capa. No tocar
tests que ya son correctos aunque pudieran escribirse diferente.
Target: 100% en `trip_manager.py`, `emhass_adapter.py`, `services.py`.
Anti-patrón prohibido: no crear ficheros `*_coverage.py` o `*_coverage2.py`.
Todos los tests nuevos van a los ficheros canónicos correspondientes.


### Fase E: Checkpoint final
- `ruff check` limpio
- `mypy` sin errores nuevos
- `pytest --randomly-seed=1/2/3` sin flaky (3 runs obligatorias)
- `make e2e` pasa
- `quality_scale.yaml` actualizado con `test-coverage: done`

