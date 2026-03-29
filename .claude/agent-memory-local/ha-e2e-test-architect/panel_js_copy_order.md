# Regla CRÍTICA: Orden de copiado de panel.js en E2E Testing

## El Problema del Error 404 en /local/panel.js

**El error:** Cuando HA arranca, registra el endpoint `/local/` apuntando a la carpeta `config/www/`. Si la carpeta `www/` no existe en el momento del arranque, el endpoint `/local/` NO se registra y las solicitudes a `/local/panel.js` fallan con 404.

**La causa:** En el código anterior, copiábamos el panel.js **DESPUÉS** de crear la instancia HA:

```typescript
// ❌ INCORRECTO: Copiar DESPUÉS de crear HA
const hassInstance = await HomeAssistant.create({...});  // HA arranca sin www/
const wwwDir = (hassInstance as any).configDir;
fs.mkdirSync(wwwDir, { recursive: true });
const wwwPath = path.join(wwwDir, 'www');
fs.mkdirSync(wwwPath);
fs.copyFileSync(panelJsPath, path.join(wwwPath, 'panel.js'));  // Demasiado tarde
```

**El resultado:** HA arranca sin la carpeta `www/`, el endpoint `/local/` nunca se registra, y el panel no se carga con error 404.

## La Solución: Orquestación con webServer

**ARQUITECTURA CORRECTA:** Usar `webServer` en `playwright.config.ts` para orquestar el arranque externo del servidor HA, con un script que copia el panel.js ANTES de iniciar HA.

```
┌─────────────────────────────────────────────────────────────────┐
│  playwright.config.ts                                           │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ webServer: {                                               │ │
│  │   command: './scripts/start_ephemeral_ha.sh',              │ │
│  │   url: 'http://127.0.0.1:8123',                            │ │
│  │   timeout: 120000                                          │ │
│  │ }                                                          │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  scripts/start_ephemeral_ha.sh                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 1. Crear directorio config/                                │ │
│  │ 2. Crear subcarpeta config/www/  ← CRÍTICO                │ │
│  │ 3. Copiar panel.js a config/www/panel.js  ← CRÍTICO       │ │
│  │ 4. Crear configuration.yaml                                │ │
│  │ 5. Arrancar HA con python -m homeassistant -c config/     │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  tests/global.setup.ts                                          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 1. Esperar HA ready (webServer lo maneja)                  │ │
│  │ 2. Navegar a http://127.0.0.1:8123                         │ │
│  │ 3. Login con credenciales dev/dev                          │ │
│  │ 4. Guardar storageState en playwright/.auth/user.json     │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Patrón de Implementación

### 1. playwright.config.ts - Orquestación webServer

```typescript
export default defineConfig({
  // ... configuración ...

  // CRÍTICO: El script copia panel.js ANTES de que HA arranque
  webServer: {
    command: './scripts/start_ephemeral_ha.sh',
    url: 'http://127.0.0.1:8123',
    timeout: 120000,
    reuseExistingServer: false,
    stdout: 'pipe',
    stderr: 'pipe'
  },

  globalSetup: './tests/global.setup.ts',
  // ...
});
```

### 2. scripts/start_ephemeral_ha.sh - Preparar panel.js ANTES de HA

```bash
#!/bin/bash
set -e

# 1. Crear directorio config
CONFIG_DIR="/tmp/ha-test-config-$$"
rm -rf "$CONFIG_DIR"
mkdir -p "$CONFIG_DIR/www"

# 2. Copiar panel.js a www/ ANTES de que HA arranque
cp "$PANEL_JS" "$CONFIG_DIR/www/panel.js"

# 3. Arrancar HA con la configuración preparada
python3 -m homeassistant -c "$CONFIG_DIR" -v
```

### 3. tests/global.setup.ts - Solo autenticación

```typescript
async function globalSetup(config: FullConfig) {
  // Esperar que webServer haya arrancado HA
  await new Promise(resolve => setTimeout(resolve, 10000));

  // Solo autenticarse - panel.js YA está disponible
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:8123');
  await page.fill('input[type="email"]', 'dev');
  await page.fill('input[type="password"]', 'dev');
  await page.click('button[type="submit"]');

  // Guardar estado de autenticación
  await context.storageState({ path: 'playwright/.auth/user.json' });
}
```

## Por Qué Funciona

1. **HA registra el mapeo `/local/` → `config/www/` DURANTE el arranque**
2. Si `www/` ya existe con `panel.js`, el endpoint `/local/panel.js` está disponible inmediatamente
3. El navegador puede cargar el panel correctamente sin error 404

## Verificación

Para verificar que el panel se carga correctamente:

1. **En la consola del navegador (F12):** No debe haber errores 404 en `/local/panel.js`
2. **En el DOM:** El panel debe mostrar el contenido esperado (ej: "EV Trip Planner")
3. **En los logs del script:** Debe aparecer "panel.js copied successfully"

## Referencias

- **Script modificado:** `scripts/start_ephemeral_ha.sh`
- **Config modificada:** `playwright.config.ts` (líneas 111-119)
- **Setup modificado:** `tests/global.setup.ts` (solo autenticación)
- **Error documentado:** 404 Not Found en `/local/panel.js` cuando HA arranca sin www/
