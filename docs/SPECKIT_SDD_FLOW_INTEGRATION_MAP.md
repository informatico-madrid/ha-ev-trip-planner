# Speckit SDD Flow - Complete Integration Map

## 🎯 Overview

Este documento mapea **toda** la integración del flujo Spec-Driven Development (SDD) de Speckit, incluyendo agentes, prompts, comandos y scripts, coordinados con el **Zero-Trust Deployment Protocol v1.0**.

---

## 📋 Arquitectura Completa del Flujo SDD

### Fase 1: Especificación (Specify)
```
User Request → /speckit.specify → Create Feature Structure
```

**Archivos:**
- `.github/agents/speckit.specify.agent.md` - Agente principal
- `.github/prompts/speckit.specify.prompt.md` - Prompt de especificación
- `.roo/commands/speckit.specify.md` - Comando Roo
- `.specify/scripts/bash/create-new-feature.sh` - Script de creación

**Output:**
- `specs/XXX-feature-name/` directory
- `spec.md` - Feature specification
- `plan.md` - Implementation plan
- `constitution.md` - Project rules

---

### Fase 2: Clarificación (Clarify)
```
spec.md + plan.md → /speckit.clarify → Refine Requirements
```

**Archivos:**
- `.github/agents/speckit.clarify.agent.md` - Agente de clarificación
- `.github/prompts/speckit.clarify.prompt.md` - Prompt de clarificación
- `.roo/commands/speckit.clarify.md` - Comando Clarify

**Output:**
- Requirements refinados
- Edge cases identificados
- Success criteria definidos

---

### Fase 3: Análisis (Analyze)
```
Requirements → /speckit.analyze → Technical Analysis
```

**Archivos:**
- `.github/agents/speckit.analyze.agent.md` - Agente de análisis
- `.github/prompts/speckit.analyze.prompt.md` - Prompt de análisis
- `.roo/commands/speckit.analyze.md` - Comando Analyze

**Output:**
- Architecture decisions
- Technology stack selection
- Risk assessment

---

### Fase 4: Planificación (Plan)
```
Analysis → /speckit.plan → Detailed Implementation Plan
```

**Archivos:**
- `.github/agents/speckit.plan.agent.md` - Agente de planificación
- `.github/prompts/speckit.plan.prompt.md` - Prompt de planificación
- `.roo/commands/speckit.plan.md` - Comando Plan

**Output:**
- Technical architecture details
- File structure definition
- Implementation strategy

---

### Fase 5: Tareas (Tasks)
```
Plan → /speckit.tasks → Task Breakdown
```

**Archivos:**
- `.github/agents/speckit.tasks.agent.md` - Agente de tareas
- `.github/prompts/speckit.tasks.prompt.md` - Prompt de tareas
- `.roo/commands/speckit.tasks.md` - Comando Tasks

**Output:**
- `tasks.md` - Lista de tasks con checkboxes
- Task dependencies defined
- Execution order specified

---

### Fase 6: Implementación (Implement)
```
tasks.md → /speckit.implement → Execute Implementation
```

**Archivos:**
- `.github/agents/speckit.implement.agent.md` - Agente de implementación
- `.github/prompts/speckit.implement.prompt.md` - Prompt de implementación
- `.roo/commands/speckit.implement.md` - Comando Implement
- `.specify/scripts/bash/check-prerequisites.sh` - Verificación de prerequisitos
- `.specify/scripts/bash/update-agent-context.sh` - Actualización de contexto

**Output:**
- Código implementado
- Tests escritos
- Features desplegadas

---

### Fase 7: Checklist (Checklist)
```
Implementation → /speckit.checklist → Quality Gates
```

**Archivos:**
- `.github/agents/speckit.checklist.agent.md` - Agente de checklist
- `.github/prompts/speckit.checklist.prompt.md` - Prompt de checklist
- `.roo/commands/speckit.checklist.md` - Comando Checklist

**Output:**
- Quality gates verificados
- Security checks completed
- Performance validation

---

### Fase 8: QA (Quality Assurance)
```
All Checks → /speckit.qa → Final Validation
```

**Archivos:**
- `.github/agents/speckit.qa.agent.md` - Agente de QA
- `.github/prompts/speckit.qa.prompt.md` - Prompt de QA

**Output:**
- Final validation report
- Acceptance criteria met
- Ready for deployment

---

### Fase 9: Constitución (Constitution)
```
Project Rules → /speckit.constitution → Coding Standards
```

**Archivos:**
- `.github/agents/speckit.constitution.agent.md` - Agente de constitution
- `.github/prompts/speckit.constitution.prompt.md` - Prompt de constitution
- `.roo/commands/speckit.constitution.md` - Comando Constitution

**Output:**
- Project coding standards
- Naming conventions
- Architecture patterns

---

### Fase 10: Tasks to Issues
```
Tasks → /speckit.taskstoissues → GitHub Issues
```

**Archivos:**
- `.github/agents/speckit.taskstoissues.agent.md` - Agente de issues
- `.github/prompts/speckit.taskstoissues.prompt.md` - Prompt de issues

**Output:**
- GitHub issues created
- Tracking enabled
- Progress visible

---

## 🔗 Integraciones Cruzadas

### Scripts Principales
```
.specify/scripts/bash/
├── check-prerequisites.sh      # Validación de prerequisitos
├── common.sh                   # Funciones comunes
├── create-new-feature.sh       # Creación de nueva feature
├── setup-plan.sh              # Configuración del plan
└── update-agent-context.sh    # Actualización de contexto
```

### Hooks de Extensión
```
.specify/extensions.yml        # Hooks before/after implementation
```

### Herramientas de Verificación
```
Las herramientas de verificación se definen en plan.md (sección Available Tools for Verification)
y se asignan dinámicamente según las etiquetas [VERIFY:TEST/API/BROWSER] en cada tarea.
```

**Flujo de verificación actual:**
1. Las tareas tienen tags `[VERIFY:TEST]`, `[VERIFY:API]`, o `[VERIFY:BROWSER]`
2. El agente usa las tools MCP/skills asignadas para verificar
3. El agente emite `STATE_MATCH` cuando la verificación pasa
4. El shell verifica `STATE_MATCH` solo si la tarea tiene tags `[VERIFY:*]`

---

## ⚠️ Integración con Zero-Trust Deployment Protocol

### Puntos Críticos de Integración

#### 1. En la Fase de Especificación (Specify)
**Debe incluirse en spec.md:**
```markdown
## STATE VERIFICATION PLAN

### Existence Check
- [ ] How to prove the change exists in host system
- [ ] REST API endpoints to test
- [ ] Storage files to verify
- [ ] Log messages to search

### Effect Check
- [ ] How to prove the change is working
- [ ] Entity states to validate
- [ ] Service responses to test
- [ ] Configuration entries to verify
```

#### 2. En la Fase de Tareas (Tasks)
**Cada task debe tener:**
```markdown
- [ ] T001: Implement feature X
  **Reality Sensor Required:**
  - Existence: Check via curl/API
  - Effect: Verify state/log/service
  
- [ ] T002: Write tests
  **Verification Method:** pytest with HA custom fixtures
```

#### 3. En la Fase de Implementación (Implement)
**Obligatorio antes de marcar [x]:**
1. ✅ El agente ejecuta las tools MCP con tags `[VERIFY:TEST/API/BROWSER]`
2. ✅ El agente emite `STATE_MATCH` cuando la verificación pasa
3. ✅ El shell verifica `STATE_MATCH` solo si la tarea tiene tags `[VERIFY:*]`

**Solo entonces marcar como [x]**

#### 4. En la Fase de Checklist (Checklist)
**Checklists obligatorios:**
- [ ] Deployment verification passed
- [ ] Reality sensor returned STATE_MATCH
- [ ] All curl/API tests successful
- [ ] HA logs show initialization
- [ ] Entities registered correctly
- [ ] Config entries exist
- [ ] Services available

---

## 🔄 Flujo Coordinado Completo

```mermaid
graph TD
    A[User Request] --> B[/speckit.specify]
    B --> C[Create Feature Structure]
    C --> D[/speckit.clarify]
    D --> E[Refine Requirements]
    E --> F[/speckit.analyze]
    F --> G[Technical Analysis]
    G --> H[/speckit.plan]
    H --> I[Detailed Plan]
    I --> J[/speckit.tasks]
    J --> K[Tasks Breakdown]
    K --> L[/speckit.implement]
    
    subgraph "Zero-Trust Integration Points"
        L --> M{Before Marking [x]}
        M --> N{Has [VERIFY:*]?}
        N -->|No| T[Skip Verification]
        N -->|Yes| O[Agent Uses MCP Tools]
        O --> P[Agent Emits STATE_MATCH]
        P --> Q{STATE_MATCH?}
        Q -->|No| R[Uncheck Task & Retry]
        Q -->|Yes| T[Mark Task [x]]
    end
    
    T --> U[/speckit.checklist]
    U --> V[Quality Gates]
    V --> W[/speckit.qa]
    W --> X[Final Validation]
    X --> Y{All Pass?}
    Y -->|Yes| Z[Ready for Deployment]
    Y -->|No| Q
```

---

## 📝 Archivos Clave por Componente

### Agentes (.github/agents/)
| Archivo | Propósito | Integración Zero-Trust |
|---------|-----------|----------------------|
| `speckit.specify.agent.md` | Crear estructura feature | Agrega sección STATE VERIFICATION PLAN |
| `speckit.implement.agent.md` | Ejecutar implementación | Incluye verificación deployment REAL |
| `speckit.tasks.agent.md` | Desglosar tasks | Cada task requiere método de verificación |
| `speckit.checklist.agent.md` | Quality gates | Incluir deployment verification |

### Prompts (.github/prompts/)
| Archivo | Propósito | Integración Zero-Trust |
|---------|-----------|----------------------|
| `speckit.specify.prompt.md` | Template especificación | Sección STATE VERIFICATION PLAN |
| `speckit.implement.prompt.md` | Instrucciones implementación | Verificación deployment antes de complete |
| `speckit.tasks.prompt.md` | Generar tasks | Cada task con método de verificación |

### Comandos (.roo/commands/)
| Archivo | Propósito | Integración Zero-Trust |
|---------|-----------|----------------------|
| `speckit.specify.md` | Crear feature | Output incluye plan de verificación |
| `speckit.implement.md` | Ejecutar impl | Incluye pasos de verificación REAL |
| `speckit.tasks.md` | Desglosar tasks | Cada task con verificación requerida |

### Scripts Bash (.specify/scripts/bash/)
| Archivo | Propósito | Integración Zero-Trust |
|---------|-----------|----------------------|
| `check-prerequisites.sh` | Validar prerequisitos | Verifica tools de verificación disponibles |
| `create-new-feature.sh` | Crear feature | Incluye template de verificación |
| `update-agent-context.sh` | Actualizar contexto | Incluye información de deployment |

---

## 🎯 Reglas de Coordinación

### 1. Consistencia en Todo el Flujo
- ✅ Todos los prompts deben referenciar Zero-Trust Protocol
- ✅ Todas las tasks deben incluir método de verificación
- ✅ Todos los agents deben validar deployment REAL
- ✅ Todos los checklists deben incluir deployment verification

### 2. Flujos de Verificación Obligatorios
```
Antes de marcar [x]:
1. Si la tarea tiene [VERIFY:*]:
   - El agente usa las tools MCP asignadas
   - El agente emite STATE_MATCH cuando pasa
   - El shell verifica STATE_MATCH
2. Si la tarea NO tiene [VERIFY:*]:
   - Se salta la verificación
```

### 3. Puntos de Control Críticos
- **After Specify**: Spec debe incluir STATE VERIFICATION PLAN
- **After Tasks**: Cada task debe tener método de verificación
- **Before Mark [x]**: Deployment verification MUST pass
- **After QA**: Final validation includes REAL system checks

---

## 🔧 Actualizaciones Requeridas

### Para Completar la Integración

1. **Actualizar todos los agentes** para incluir:
   - Referencia al Zero-Trust Protocol
   - Obligación de verificación REAL
   - Prohibición de marcar [x] sin deployment verification

2. **Actualizar todos los prompts** para incluir:
   - Template de STATE VERIFICATION PLAN
   - Instrucciones de verificación deployment
   - Ejemplos de comandos curl

3. **Actualizar todos los comandos** para incluir:
   - Verificación condicional basada en [VERIFY:*]
   - Emisión de STATE_MATCH por el agente
   - Validación de STATE_MATCH por el shell

4. **Actualizar todos los scripts** para incluir:
   - Verificación de tools disponibles
   - Integración con reality_sensor.py
   - Reporte de discrepancias

---

## 📊 Estado de Integración

| Componente | Estado | Integración Zero-Trust |
|------------|--------|----------------------|
| Agents | ✅ Actualizados | ✅ Incluyen verificación REAL |
| Prompts | ⚠️ Parcial | ❌ Requieren actualización completa |
| Comandos | ⚠️ Parcial | ❌ Requieren actualización completa |
| Scripts | ✅ Actualizados | ✅ Incluyen verificación |
| RalphLoop | ✅ Actualizado | ✅ Integración completa |
| Tools | ✅ Disponibles | ✅ Listos para uso |

---

## 🚀 Próximos Pasos

1. **Actualizar prompts restantes** con templates de verificación
2. **Actualizar comandos** para ejecutar verificación automática
3. **Crear ejemplos** de cada tipo de verificación
4. **Documentar** workflow completo con ejemplos reales
5. **Testear** todo el flujo desde specify hasta deploy

---

**Última Actualización**: 2026-03-20  
**Versión**: 1.0  
**Protocolo**: Zero-Trust Deployment v1.0  
**Estado**: En Proceso de Integración Completa
