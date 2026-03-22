# Quickstart: Testing E2E con Playwright

## Prerequisites

- Node.js 18+ instalado
- Home Assistant accesible en la red (ej: `http://homeassistant.local:8123`)
- Credenciales de acceso a Home Assistant

## Setup

### 1. Instalar dependencias

```bash
npm install
```

### 2. Instalar browsers de Playwright

```bash
npx playwright install
```

### 3. Configurar entorno

Crear archivo `.env` con las siguientes variables:

```env
HA_URL=http://homeassistant.local:8123
HA_TOKEN=your_long_lived_access_token
HA_USERNAME=malka
```

### 4. Configurar Playwright

El archivo `playwright.config.js` está pre-configurado con:
- Timeout global: 120 segundos
- Viewport: 1280x720
- Modo headless: enabled
- Ignorar errores HTTPS: enabled

## Ejecutar Tests

### Ejecutar todos los tests

```bash
npm test
```

### Ejecutar test específico

```bash
npx playwright test tests/e2e/native-panel.spec.js
```

### Ejecutar test con modo UI (interactive)

```bash
npx playwright test --ui
```

### Ejecutar test con verbose logging

```bash
npx playwright test --debug
```

## Debugging

### Ver logs del test

```bash
npx playwright test --trace on
```

### Ver videos de los tests

Los videos se guardan automáticamente en `test-results/`

### Ver screenshots de fallos

Los screenshots se guardan automáticamente en `test-results/`

### Ejecutar test en modo UI para debug

```bash
npx playwright test --ui
```

## Estructura del Test

```
tests/e2e/
└── native-panel.spec.js    # Test principal para panel nativo
```

## Verificación del Test

El test verifica:

1. **Login**: Se loguea correctamente en Home Assistant
2. **Navegación**: Navega a Configuración > Integraciones
3. **Integración**: Agrega EV Trip Planner correctamente
4. **Configuración**: Crea un vehículo sin errores
5. **Panel**: Verifica que aparece el panel en el sidebar
6. **API**: Consulta entidades y servicios de HA
7. **Logs**: Captura console logs y page errors
8. **Screenshots**: Genera screenshot al completar

## Troubleshooting

### Error: browser not found

```bash
npx playwright install chromium
```

### Error: HA not accessible

Verificar que:
- HA está corriendo
- La URL en `.env` es correcta
- No hay firewall bloqueando el acceso

### Error: login failed

Verificar que:
- El username es correcto
- El password/token es correcto
- El token tiene permisos de administrador

### Error: test timeout

Aumentar timeout en `playwright.config.js`:

```javascript
module.exports = {
  timeout: 180000, // 3 minutos
};
```

## Next Steps

- Ver `tests/e2e/native-panel.spec.js` para ver el código del test
- Ver `specs/018-e2e-playwright-testing/spec.md` para la especificación completa
- Ver `specs/018-e2e-playwright-testing/plan.md` para el plan de implementación
