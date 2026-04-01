# Skill: E2E Verify Integration para Ralph Loop

> Cómo Ralph lanza, verifica y usa los tests E2E Playwright dentro del ciclo `ralph-loop.sh`.
> Este skill conecta `selector-map.skill.md` con el motor de verificación de Ralph.

---

## Cómo funciona el [VERIFY:TEST] en Ralph

Cuando una tarea en `tasks.md` contiene `[VERIFY:TEST]` o una línea `- **Verify**: npx playwright test ...`, Ralph entra en la **fase de verificación de 3 capas**:

```
Layer 1: Contradiction detection   → ¿el agente genera salida contradictoria?
Layer 2: Signal check              → ¿el agente emite TASK_COMPLETE / state_match?
Layer 3: Artifact review           → cada RALPH_REVIEW_EVERY tareas (default: 5)
```

El flujo exacto de `ralph-loop.sh` es:

```
1. pick_next_task()         → lee tasks.md, extrae task_index actual
2. run_work_phase()         → lanza claude/goose con el prompt de trabajo
3. run_verification()       → el agente ejecuta [VERIFY:TEST]
   └→ check_task_complete_signal()   → busca TASK_COMPLETE en stdout
   └→ check_state_match_signal()     → busca state_match/verification_passed
4. update_state_json()      → actualiza .ralph/state.json
5. mark_task_done()         → tilda el checkbox en tasks.md
6. ¿ALL_TASKS_COMPLETE?     → termina o sigue al task_index+1
```

---

## Cómo se lanzan los tests E2E desde Ralph

Ralph ejecuta los tests E2E directamente como subproceso del agente Claude/Goose. El agente recibe en su prompt las instrucciones de la tarea + los skills cargados, y usa `Bash` tool para lanzar:

```bash
# Comando que el agente ejecuta via Bash tool
npx playwright test [archivo.spec.ts] --reporter=line

# O el suite completo
npx playwright test --reporter=line

# O un proyecto específico
npx playwright test --project=chromium
```

Ralph controla la concurrencia con `RALPH_TEST_CONCURRENCY=5` (máximo 5 procesos playwright/pytest simultáneos). Si se supera, el loop espera.

---

## Integración del Selector Map en el flujo

### Opción A: Via skill cargado en el prompt del agente (recomendado)

Añade el selector map como skill de contexto que Ralph inyecta automáticamente al agente cuando trabaja en tareas E2E. El agente lo lee antes de generar o modificar tests.

En la tarea del `tasks.md` añade la referencia:

```markdown
### Task X: Crear test de [funcionalidad]
- [ ] **Do**: Implementar test Playwright para [funcionalidad]
- [ ] **Skills**: `tests/e2e/skills/selector-map.skill.md`
- [ ] **Files**: `tests/e2e/test-[nombre].spec.ts`
- [ ] **Done when**: Test pasa en verde
- [ ] **Verify**: `npx playwright test test-[nombre].spec.ts --reporter=line`
- [ ] **Commit**: `test(e2e): add [nombre] test`
```

El agente Claude interpreta el campo `**Skills**` como instruccion para leer ese archivo antes de empezar. Esto le da el mapa de selectores completo sin tener que explorar el DOM.

### Opción B: Via prompt system del agente (para nuevas specs)

En el archivo de spec (`.md` o `requirements.md`) referencia el skill al inicio:

```markdown
## Skills requeridos

- `tests/e2e/skills/selector-map.skill.md` — mapa de selectores validados
- `tests/e2e/skills/ha-core-frontend.skill.md` — cómo HA sirve el panel JS
```

Ralph pasa estos archivos como contexto adicional al agente en el prompt de trabajo.

### Opción C: Via quickstart.md de la spec (forma actual del repo)

Si la spec tiene `quickstart.md`, añade una sección:

```markdown
## Selectores UI Validados

Antes de crear o modificar tests, leer:
- `tests/e2e/skills/selector-map.skill.md`

Este archivo contiene los selectores extraídos de los tests en verde.
No explorar el DOM desde cero. Usar los selectores documentados directamente.
```

---

## Patrón de tarea tasks.md para nuevos tests E2E

Usa este patrón exacto para que Ralph lo procese correctamente:

```markdown
### Task N.M: Test E2E de [funcionalidad]
- [ ] **Do**: Crear test Playwright que verifica [descripción del flujo]
- [ ] **Skills**: `tests/e2e/skills/selector-map.skill.md`
- [ ] **Context**:
  - Selectores validados en `tests/e2e/skills/selector-map.skill.md` sección [sección relevante]
  - Usar `[VERIFY:TEST]` tras implementar
- [ ] **Files**: `tests/e2e/test-[nombre].spec.ts`
- [ ] **Done when**: `npx playwright test test-[nombre].spec.ts` pasa en verde sin errores
- [ ] **Verify**: `npx playwright test test-[nombre].spec.ts --reporter=line` [VERIFY:TEST]
- [ ] **Commit**: `test(e2e): add [nombre] E2E test`
```

**El campo `[VERIFY:TEST]` al final de la línea Verify es el trigger** que activa la capa 2 de verificación de Ralph.

---

## Signals que Ralph espera tras los tests E2E

Después de que el agente ejecuta `npx playwright test`, Ralph busca estos signals en stdout:

| Signal | Pattern | Significado |
|---|---|---|
| Task completa | `TASK_COMPLETE` | El agente lo emite explícitamente |
| Verificación OK | `state_match`, `verification_passed`, `verification_ok` | Tests pasaron |
| Todo completo | `ALL_TASKS_COMPLETE`, `ALL_DONE` | Spec terminada |
| Fallo de test | Ninguno de los anteriores | Ralph entra en recovery mode |

El agente debe emitir explícitamente el signal tras confirmar que los tests pasan:

```
npx playwright test test-xxx.spec.ts --reporter=line
# → output con resultados
# → si pasa: emitir TASK_COMPLETE
# → si falla: NO emitir, Ralph generará recovery task automáticamente
```

---

## Recovery Mode de Ralph para tests E2E

Si un `[VERIFY:TEST]` falla (el agente no emite signal positivo), Ralph **automáticamente genera una tarea de fix** con este formato interno:

```
RECOVERY: Test [nombre] faló en iteración N. 
  Error: [output del test]
  Contexto: leer selector-map.skill.md para selectores correctos
  Acción: corregir test sin cambiar el selector, a menos que el DOM haya cambiado
```

Para que el recovery sea efectivo, el agente en modo recovery **debe leer el selector map antes de tocar el test**. Añade esto en el `quickstart.md` de specs con tests E2E:

```markdown
## Recovery de tests E2E

Si un test falla en verificación:
1. Leer `tests/e2e/skills/selector-map.skill.md` antes de modificar nada
2. Verificar sección 10 (Antipatrones) primero
3. Comparar selector usado vs selector validado en el map
4. NO cambiar el selector si el map dice que es correcto—revisar el flujo del test
```

---

## Variables de entorno disponibles en tests E2E

Ralph inyecta estas variables antes de lanzar cualquier test:

```bash
HA_URL="http://localhost:8123"        # URL del HA de pruebas
HA_USER="tests"                       # Usuario E2E
HA_USERNAME="tests"                   # Alias
HA_PASSWORD="tests"                   # Password E2E
```

Los tests Playwright las leen desde `process.env` o desde `playwright/.auth/server-info.json`.

---

## Checklist para añadir un nuevo test al flujo Ralph

```
[ ] 1. Crear tests/e2e/test-[nombre].spec.ts usando selectores de selector-map.skill.md
[ ] 2. Verificar manualmente: npx playwright test test-[nombre].spec.ts
[ ] 3. Añadir tarea en tasks.md con formato de la sección anterior
[ ] 4. El campo **Skills** apunta a selector-map.skill.md
[ ] 5. La línea **Verify** termina con [VERIFY:TEST]
[ ] 6. Si la spec tiene quickstart.md, añadir referencia al skill allí también
[ ] 7. Ejecutar: .ralph/ralph-loop.sh specs/[spec-dir] — Ralph manejará el resto
```

---

## Specs existentes que usan [VERIFY:TEST] en este repo

| Spec | Archivo tasks | Tipo de verify |
|---|---|---|
| `007-complete-milestone-3-verify-1-2` | tasks.md | Verificación de milestone completo |
| `012-dashboard-crud-verify` | tasks.md | CRUD dashboard |
| `018-e2e-playwright-testing` | tasks.md | Setup Playwright |
| `021-e2e-trip-crud-panel-tests` | tasks.md | CRUD trips E2E (todos en verde ✅) |

La spec `021` es la referencia de cómo deben quedar las tasks.md de tests E2E en este repo.
