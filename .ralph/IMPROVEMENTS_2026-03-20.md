# Ralph Loop Improvements - 2026-03-20

## Problem Analysis

El loop de Ralph tenía varios problemas:

1. **Múltiples tareas completadas por iteración**: El agente completaba T001-T005 en 3 iteraciones en lugar de 1 tarea por iteración
2. **Detección débil de señales**: No detectaba correctamente TASK_COMPLETE cuando el agente usaba variantes como "done", "TASK_COMPLETE!", etc.
3. **Sin verificación de una tarea por iteración**: No había control para prevenir que el agente completara múltiples tareas
4. **Estado desincronizado**: El JSON de estado mostraba "completed: 3" cuando en realidad había 5 tareas marcadas

## Changes Made

### 1. Prompt Mejorado - ONE TASK PER ITERATION RULE

**File**: [`.ralph/ralph-loop.sh:621-627`](.ralph/ralph-loop.sh:621)

Se añadió una sección CRÍTICA al prompt que enfatiza que el agente debe completar EXACTAMENTE UNA tarea por iteración:

```
## ⚠ CRITICAL: ONE TASK PER ITERATION RULE ⚠
**YOU MUST COMPLETE EXACTLY ONE TASK PER ITERATION.**
- This is a HARD CONSTRAINT, not a suggestion.
- The loop expects exactly ONE task to be marked [x] after each iteration.
- If you mark multiple tasks [x], the loop will detect a mismatch and retry.
- Do NOT skip ahead to T006 if T005 is not complete.
- Do NOT attempt to complete multiple tasks in one go.
```

### 2. Detección de Señales Mejorada

**File**: [`.ralph/ralph-loop.sh:397-406`](.ralph/ralph-loop.sh:397)

`check_completion_signal()`:
- Acepta: `task_complete`, `task_completions`, `TASK_COMPLETE`, `TASK_COMPLETIONS`
- Acepta: `done`, `done!`, `DONE`, `DONE!`
- Acepta: `<promise>done</promise>`, `<promise>DONE</promise>`, `<promise>done!</promise>`
- Uso de `grep -qiE` para matching case-insensitive

**File**: [`.ralph/ralph-loop.sh:408-416`](.ralph/ralph-loop.sh:408)

`check_all_complete_signal()`:
- Acepta: `all_tasks_complete`, `all-tasks-complete`, `ALL_TASKS_COMPLETE`
- Acepta: `all_done`, `all-done`, `ALL_DONE`, `all_tasks_complete`
- Uso de `grep -qiE` para matching case-insensitive

### 3. Verificación de Múltiples Tareas

**File**: [`.ralph/ralph-loop.sh:1500-1512`](.ralph/ralph-loop.sh:1500)

Se añadió verificación para detectar cuando el agente completa más de una tarea:

```bash
# Check if more than one task was completed (agent completed multiple tasks)
local tasks_completed=$((new_completed - completed))
if (( tasks_completed > 1 )); then
    log_warn "MULTIPLE TASKS COMPLETED IN ONE ITERATION: $tasks_completed tasks marked [x]"
    log_warn "Agent must complete EXACTLY ONE task per iteration"
    log_warn "Resetting taskIteration to force retry"
    update_state --set "taskIteration=$((task_iter + 1))"
    update_state --set "taskIndex=$next_idx"  # Stay on same task
    consecutive_failures=$((consecutive_failures + 1))
    log_progress "$next_idx" "$task_desc" "MULTIPLE_TASKS_COMPLETED (retry $((task_iter + 1)))" "$global_iter"
    sleep 2
    continue
fi
```

### 4. Verificación de Cero Tareas

**File**: [`.ralph/ralph-loop.sh:1513-1525`](.ralph/ralph-loop.sh:1513)

Se añadió verificación para detectar cuando el agente no completa ninguna tarea:

```bash
elif (( tasks_completed == 0 )); then
    log_warn "ZERO TASKS COMPLETED IN ONE ITERATION"
    log_warn "Agent did not mark the current task as [x]"
    log_warn "Resetting taskIteration to force retry"
    update_state --set "taskIteration=$((task_iter + 1))"
    update_state --set "taskIndex=$next_idx"  # Stay on same task
    consecutive_failures=$((consecutive_failures + 1))
    log_progress "$next_idx" "$task_desc" "ZERO_TASKS_COMPLETED (retry $((task_iter + 1)))" "$global_iter"
    sleep 2
    continue
fi
```

### 5. Script de Reset de Estado

**File**: [`.ralph/scripts/reset_state.py`](.ralph/scripts/reset_state.py)

Nuevo script para resetear el estado de un spec:

```bash
python .ralph/scripts/reset_state.py specs/010-fix-sensor-errors-dashboard-issues --confirm
```

### 6. Comando --reset en ralph-loop.sh

**File**: [`.ralph/ralph-loop.sh:144`](.ralph/ralph-loop.sh:144)

Se añadió el flag `--reset` para resetear el estado:

```bash
.ralph/ralph-loop.sh specs/010-fix-sensor-errors-dashboard-issues --reset
```

### 7. RALPH_MAX_RETRIES Aumentado

**File**: [`.ralph/ralph-loop.sh:44`](.ralph/ralph-loop.sh:44)

Aumentado de 5 a 30 intentos por tarea.

## Usage

### Resetear estado antes de re-ejecutar:

```bash
# Opción 1: Usar el flag --reset
.ralph/ralph-loop.sh specs/010-fix-sensor-errors-dashboard-issues --reset

# Opción 2: Usar el script directamente
python .ralph/scripts/reset_state.py specs/010-fix-sensor-errors-dashboard-issues --confirm
```

### Verificar estado actual:

```bash
cat .ralph/state-010-fix-sensor-errors-dashboard-issues.json
```

### Ejecutar loop:

```bash
.ralph/ralph-loop.sh specs/010-fix-sensor-errors-dashboard-issues
```

## Expected Behavior

Con estas mejoras, el loop ahora:

1. **Enfrenta al agente** con instrucciones claras de completar solo UNA tarea por iteración
2. **Detecta señales** de completación con mayor flexibilidad (case-insensitive, múltiples variantes)
3. **Verifica** que se completó exactamente UNA tarea (ni más, ni menos)
4. **Rechaza** iteraciones donde el agente completa múltiples tareas o ninguna tarea
5. **Permite** resetear el estado si es necesario para empezar de cero

## Files Modified

- `.ralph/ralph-loop.sh` - Main loop script with all improvements
- `.ralph/scripts/reset_state.py` - New script for resetting state
- `.ralph/scripts/count_completed.py` - New script for counting completed tasks
