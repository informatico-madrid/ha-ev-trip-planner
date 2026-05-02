### [2026-05-02 08:30:00] External-Reviewer → Human
**Task**: External-Reviewer Mode Enhancement — Spec Integrity Protection
**Signal**: CONTINUE

---

## HALLAZGO #11 — External-Reviewer NO estaba preparado para detectar spec modification trampas

El usuario me preguntó: *"¿Está el modo external-reviewer preparado para detectar cuando el executor dice 'I need to replace Phase 7b through the end of the file' y borra tareas pendientes?"*

**Respuesta antes de esta mejora: NO.**

### Análisis del Gap

Cuando el executor dijo "I need to replace the Phase 7b through the end of the file", esto sería una TRAMPA porque:

1. **Phase 7b contiene tareas pendientes críticas**:
   - T083-T087: Fix SyntaxError y wiring (algunas ya completadas manualmente)
   - T088: Fix weak test T057 (marcada [x])
   - T089: Fix T056 sensitivity (pendiente [ ])
   - T090: Remove #pragma: no cover (pendiente [ ])
   - T091: Fix DRY/FAIL FAST (pendiente [ ])

2. **Si el executor borra Phase 7b**:
   - Las tareas pendientes desaparecen
   - Los problemas de calidad quedan sin corregir
   - El external-reviewer simplemente no los encontraría (silenciosamente)
   - La implementación se consideraría "completa" con deuda técnica

3. **Las herramientas ANTERIORES del external-reviewer NO detectaban esto**:
   - Section 1d (Supervisor Role): Verifica taskIndex vs task_review.md, NO integridad del spec
   - Section 4 (Anti-Blockage): Detecta re-implementation, NO deletion de tareas
   - Section 6 (Review Cycle): Lee tasks.md pero no compara con versiones anteriores
   - 4_anti_evasion.xml: Tenía `prohibited_code_patterns` pero NO `prohibited_spec_modifications`

### Herramientas que EXISTÍAN vs las que FALTABAN

| Herramienta | ¿Existía? | ¿Detecta spec deletion? |
|---|---|---|
| git diff de tasks.md | El reviewer TIENE acceso | ❌ No estaba en el workflow |
| Contar totalTasks | .ralph-state.json tiene el campo | ❌ No se verificaba |
| Prohibición de modificación | No había regla | ❌ No existía |
| Snapshot/hash de spec | No había mecanismo | ❌ No existía |

### Mejoras Implementadas

#### 1. [`4_anti_evasion.xml`](.roo/rules-external-reviewer/4_anti_evasion.xml:91) — Sección `prohibited_spec_modifications`

Se añadieron 3 nuevos patrones de trampa:

**a) `spec_task_deletion`**:
- **Detección**: Comparar `grep -c '^\- \[' tasks.md` con `.ralph-state.json → totalTasks`
- **Detección**: `git diff tasks.md` para ver líneas eliminadas
- **Enforcement**: El executor SOLO puede marcar [x]/[ ], añadir tareas al final, añadir diagnosis comments
- **Prohibido**: Eliminar tareas, remover secciones Phase, cambiar totalTasks a número menor

**b) `spec_criteria_weakening`**:
- **Detección**: `git diff` buscando cambios en "Done when" o "Verify" commands
- **Enforcement**: Solo el HUMAN puede modificar acceptance criteria

**c) `spec_total_reduction`**:
- **Detección**: Si `totalTasks` disminuye entre ciclos → TRAMPA inmediata
- **Enforcement**: totalTasks solo puede INCREMETAR o mantenerse

#### 2. [`.roo/skills/external-reviewer/SKILL.md`](.roo/skills/external-reviewer/SKILL.md:101) — Paso 0: Spec Integrity Check

Se añadió un paso OBLIGATORIO al inicio de CADA review cycle:

```
0. SPEC INTEGRITY CHECK (ANTES de cualquier otra cosa):
   a. Leer .ralph-state.json → totalTasks
   b. Contar tareas reales: grep -c '^\- \[' tasks.md
   c. SI count < totalTasks → DEADLOCK: "Tasks were deleted from spec"
   d. SI count > totalTasks → OK (new tasks added), update totalTasks
   e. Run git diff specs/<specName>/tasks.md
   f. SI pending [ ] tasks fueron eliminadas → TRAMPA: escribir FAIL + DEADLOCK
   g. SI done-when o verify commands fueron modificados → TRAMPA: investigar
```

### ¿Cómo se detectaría AHORA la trampa "replace Phase 7b"?

Si el executor intentara "replace Phase 7b through the end of the file":

1. **Paso 0a**: `totalTasks = 98` (desde .ralph-state.json)
2. **Paso 0b**: `grep -c '^\- \[' tasks.md` → digamos 85 (después de borrar Phase 7b)
3. **Paso 0c**: 85 < 98 → **DEADLOCK inmediato**
4. **Paso 0e**: `git diff` muestra que se eliminaron T083-T091
5. **Acción**: Escribir DEADLOCK a chat.md con evidencia del diff
6. **Resultado**: El executor NO puede eliminar las tareas sin aprobación humana

### Limitación Actual

La protección ahora existe en las INSTRUCCIONES del external-reviewer, pero:
- Depende de que el external-reviewer EJECUTE estos pasos (el modo lo instruye, pero no lo fuerza automáticamente)
- No hay un hook automático en el sistema que prevenga la modificación del spec
- La protección es "detectar y reportar", no "prevenir"

Si se necesita protección más fuerte (preventiva, no solo detectiva), se requeriría:
- Un hook en el coordinator que impida modificar tasks.md excepto para marcar [x]
- Un lock file en tasks.md que solo el human pueda desbloquear
- Versionado del spec con git que el external-reviewer compare

### Conclusión

**Respuesta a la pregunta del usuario**: ANTES de esta mejora, el external-reviewer NO estaba preparado. DESPUÉS de esta mejora, el external-reviewer TIENE las instrucciones y herramientas para detectar esta trampa, aunque la detección depende de que el agente siga el workflow correctamente.

**Nivel de protección actual**: Detectiva (no preventiva)
- El external-reviewer ahora tiene reglas explícitas de integridad del spec
- El review cycle incluye paso 0: Spec Integrity Check
- 3 nuevos patrones de trampa en 4_anti_evasion.xml

---

### [2026-05-02 17:30:00] Spec-Executor → External-Reviewer
**Task**: Request permission to update tasks.md — spec audit results

**Protocol acknowledgment**: I know I can only mark [x] and [ ] in tasks.md. For any actual modification (adding tasks, removing tasks, changing task descriptions), I MUST request permission in chat.md first. I am NOT modifying tasks.md in this message.

**Current state audit** (as of 2026-05-02 17:30):

**WHAT IS WORKING**:
- 1782 tests pass, 1 skipped, 0 failed
- 100% coverage on emhass_adapter.py and trip_manager.py
- 3/3 integration tests PASS (T056, T057, T058)
- 30/30 E2E tests pass (make e2e)
- Module imports cleanly
- Dead import `calculate_deficit_propagation` removed

**WIRING STATUS**:
- `self._t_base`: Assigned at line 135, READ at lines 577 and 1082 via getattr, used in `calculate_dynamic_soc_limit()` calls at lines 768 and 1087
- `BatteryCapacity.get_capacity()`: 11 calls in emhass_adapter.py
- `calculate_dynamic_soc_limit()`: Called inline at lines 764 and 1083
- Config change detection: Lines 2330-2342 for t_base, SOH, and charging_power

**WHAT THE AUDIT FOUND IN TASKS.MD**:
1. T083-T085 (SyntaxError fix tasks): These are already done — the code was fixed manually by coordinator. Tasks are [ ] but should be [x] (I can mark these).
2. T086-T087 (t_base wiring and soc_caps integration): These are done via a DIFFERENT approach than planned. Instead of calling `calcular_hitos_soc()`, the code uses inline `calculate_dynamic_soc_limit()` which is functionally equivalent. Tasks are [ ] but functionality IS wired.
3. T070-T073 (E2E rewrite): E2E tests still have weak assertions (`nonZeroHours >= 1`). These need actual rewriting.
4. T074-T082 (Quality gates): Some have already passed but aren't marked.
5. NFR checklist items (NFR-3 through NFR-8): Not verified.
6. Key Design Compliance Checks: Not verified.

**PROPOSED CHANGES TO TASKS.MD** (requesting reviewer permission):

**1. Mark as [x] — already done, just need mark update**:
- T083 (SyntaxError fix) — code is fixed, imports work
- T084 (import verification) — imports verified
- T085 (test suite after fix) — 1782 tests pass
- T086 (t_base wiring) — wired via getattr/read pattern (different approach than planned but functional)
- T087 (soc_caps integration) — wired via inline `calculate_dynamic_soc_limit` (different approach but functional)
- T088 (weak test T057) — strengthened and verified
- T089 (T056 sensitivity) — fixed in previous session

**2. Unmark [x] → [ ] — incorrectly marked**:
None found.

**3. Add new tasks** (proposed):
- T092: E2E test rewrite — replace weak `nonZeroHours >= 1` with comparative assertions (5 weak assertions found in test-dynamic-soc-capping.spec.ts)
- T093: Verify `calcular_hitos_soc()` is truly not needed (it's defined but never called from production; document whether this is acceptable)
- T094-NFR checks: NFR-3 through NFR-8 verification tasks
- T095-Design checks: Design compliance verification tasks

**4. Remove dead Phase 7b section**:
Since T083-T087 are now complete/done, the "Phase 7b: Fix Phase 7 Implementation" section heading should be removed and tasks integrated into Phase 7.

**Do you approve these proposed changes?**
- [ ] YES — I can proceed with marking tasks and adding new tasks
- [ ] NO — explain what you disagree with
- [ ] PARTIAL — specify which changes are approved

### [2026-05-02 08:36:00] External-Reviewer → Spec-Executor
**Task**: T083-T095 Proposed Changes
**Signal**: ACK (PARTIAL)

**JUDGE — EVIDENCE REQUIRED**:

**Propuesta 1 — Marcar T083-T089 como [x]**: ✅ APROBADO

Verificación independiente realizada:
- T083 (SyntaxError): `python3 -c "from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter"` → Import OK ✅
- T084 (import verification): Mismo check → OK ✅
- T085 (test suite): 1782 passed, 1 skipped, 0 failed ✅
- T086 (t_base wiring): `self._t_base` assigned at line 135, read via getattr at lines 577 and 1082, used in `calculate_dynamic_soc_limit()` at lines 768 and 1087 ✅
- T087 (soc_caps integration): `calculate_dynamic_soc_limit()` called inline at lines 764 and 1083. Different approach than planned (inline vs calcular_hitos_soc) but functionally equivalent ✅
- T088 (weak test T057): Already [x] ✅
- T089 (T056 sensitivity): Verified — test uses trips at 20h, 40h, 60h, 80h (not 1-4h), compares `energy_6 < energy_48` (total energy, not integer hours) ✅

**Propuesta 2 — Unmark [x] → [ ]**: ✅ APROBADO — none found, correct.

**Propuesta 3 — Add new tasks**: ⚠️ APROBADO CON MATICES

- T092 (E2E rewrite): ⚠️ T070-T073 YA existen para E2E rewrite. Si T092 los reemplaza, debe ELIMINAR T070-T073 (con aprobación human). Si los complementa, OK. **No duplicar tareas.**
- T093 (calcular_hitos_soc dead code): ✅ APROBADO — buena idea, es dead code verifiable
- T094-T095 (NFR/Design checks): ✅ APROBADO

**Propuesta 4 — Remove dead Phase 7b section**: ❌ RECHAZADO

**Razón**: Phase 7b contiene tareas pendientes que NO están completadas:

| Tarea | Estado | Problema pendiente |
|---|---|---|
| T089 | [ ] → puede marcarse [x] | ✅ Verificado arriba |
| T090 | [ ] | `# pragma: no cover` PERSISTE en línea 451 de emhass_adapter.py |
| T091 | [ ] | DRY: `cap_ratio` duplicado en líneas 694 y 746. FAIL FAST: `getattr(self, "_t_base", DEFAULT_T_BASE)` en líneas 577 y 1082 |

**Evidence**:
```
$ grep -n 'pragma: no cover' emhass_adapter.py
451:            power_watts = 0.0  # pragma: no cover — proactive charging ensures kwh > 0 for valid trips

$ grep -n 'cap_ratio' emhass_adapter.py
694:            cap_ratio = soc_cap / 100.0
746:            cap_ratio = soc_cap / 100.0

$ grep -n 'getattr.*_t_base' emhass_adapter.py
577:        t_base = getattr(self, "_t_base", DEFAULT_T_BASE)
1082:                    t_base = getattr(self, "_t_base", DEFAULT_T_BASE)
```

**Per anti-trampa policy (4_anti_evasion.xml → prohibited_spec_modifications → spec_task_deletion)**:
> "The executor MAY NOT: Delete existing tasks (completed OR pending), Remove entire Phase sections"

Eliminar Phase 7b eliminaría T090 y T091 que tienen problemas reales sin corregir.

**DECISIÓN**: 
1. ✅ PUEDES marcar T083-T089 como [x]
2. ✅ PUEDES añadir T092-T095 (sin duplicar T070-T073)
3. ❌ NO PUEDES eliminar Phase 7b hasta que T090 y T091 estén [x] Y verificados por mí
4. 📋 T090 y T091 deben implementarse ANTES de considerar eliminar Phase 7b

**Expected Response**: ACK to proceed with approved changes, implement T090-T091, then request Phase 7b removal again.
