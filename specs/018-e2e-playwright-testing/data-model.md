# Data Model: E2E Testing con Playwright

## Entities

### TestRun

Representa una ejecución individual del test E2E.

**Fields**:
- `id` (string, UUID): Identificador único de la ejecución
- `timestamp` (DateTime): Cuándo se ejecutó el test
- `status` (enum): 'pending', 'running', 'passed', 'failed'
- `duration` (number): Tiempo de ejecución en milisegundos
- `errorCount` (number): Número de errores capturados
- `logCount` (number): Número de logs capturados
- `hasScreenshot` (boolean): Si se generó screenshot
- `panelCreated` (boolean): Si el panel se creó correctamente

**State Transitions**:
- `pending` → `running` (al iniciar)
- `running` → `passed` (si todo pasa)
- `running` → `failed` (si hay error)

### BrowserContext

Representa el contexto del navegador durante el test.

**Fields**:
- `id` (string, UUID): Identificador único del contexto
- `pageCount` (number): Número de páginas abiertas
- `userAgent` (string): User agent del navegador
- `viewport` (object): Dimensiones del viewport {width, height}
- `networkEnabled` (boolean): Si se permite network
- `storageState` (object): Estado de storage (cookies, localStorage)

### ConsoleLog

Representa un log capturado del navegador.

**Fields**:
- `type` (enum): 'log', 'info', 'warn', 'error'
- `timestamp` (DateTime): Cuándo ocurrió el log
- `text` (string): Texto del mensaje
- `url` (string): URL donde ocurrió el log
- `line` (number): Número de línea (si aplicable)

### PageError

Representa un error capturado en la página.

**Fields**:
- `message` (string): Mensaje del error
- `stack` (string): Stack trace completo (si disponible)
- `url` (string): URL donde ocurrió el error
- `timestamp` (DateTime): Cuándo ocurrió el error

### VerificationResult

Representa el resultado de la verificación del panel.

**Fields**:
- `panelExists` (boolean): Si el panel existe en el sidebar
- `panelUrl` (string): URL del panel si existe
- `panelTitle` (string): Título del panel
- `entitiesFound` (number): Número de entidades EV Trip Planner encontradas
- `servicesFound` (number): Número de servicios EV Trip Planner disponibles
- `haVersion` (string): Versión de Home Assistant detectada
- `errorMessages` (array): Lista de mensajes de error si hay fallos

### TestConfiguration

Representa la configuración del test.

**Fields**:
- `haUrl` (string): URL de Home Assistant
- `haToken` (string): Token de acceso (encriptado)
- `username` (string): Usuario para login
- `timeout` (number): Timeout en milisegundos
- `viewportWidth` (number): Ancho del viewport
- `viewportHeight` (number): Alto del viewport
- `headless` (boolean): Si se ejecuta en modo headless
- `ignoreHTTPSErrors` (boolean): Si se ignoran errores HTTPS

## Relationships

```
TestRun
├── BrowserContext (1:1)
├── ConsoleLog[] (1:Many)
├── PageError[] (1:Many)
└── VerificationResult (1:1)

TestConfiguration (used by TestRun)
```

## Validation Rules

- `haUrl`: Debe ser una URL válida (http:// o https://)
- `haToken`: Mínimo 64 caracteres (token de largo acceso)
- `timeout`: Mínimo 30000 (30 segundos), máximo 300000 (5 minutos)
- `viewportWidth`: Mínimo 800, máximo 3840
- `viewportHeight`: Mínimo 600, máximo 2160

## State Transitions

### VerificationResult

| Current State | Action | New State |
|---------------|--------|-----------|
| any | panel found | panelExists = true |
| any | panel not found | panelExists = false |
| any | entities verified | entitiesFound = count |
| any | services verified | servicesFound = count |
| any | error occurred | errorMessages.push(error) |
