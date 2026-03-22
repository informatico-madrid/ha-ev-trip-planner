# Data Model: Panel de Control Nativo

## Entities

### PanelConfig

Configuración del panel que se registra en Home Assistant.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| frontend_url_path | string | Yes | URL única del panel (ej: "ev-trip-planner-tesla_model_3") |
| sidebar_title | string | Yes | Título visible en el sidebar |
| sidebar_icon | string | Yes | Icono MDI (ej: "mdi:car-electric") |
| webcomponent_name | string | Yes | Nombre del web component |
| module_url | string | Yes | Ruta al archivo JS |
| config | dict | No | Configuración adicional pasadata al panel |
| require_admin | bool | No | Si requiere permisos de admin (default: False) |

### Vehicle

Vehículo configurado en EV Trip Planner.

| Field | Type | Description |
|-------|------|-------------|
| vehicle_id | string | ID único del vehículo |
| name | string | Nombre para mostrar |
| created_at | datetime | Fecha de creación |
| panel_url_path | string | URL del panel asociado |

### Panel State

Estado del panel en Home Assistant.

| Field | Type | Description |
|-------|------|-------------|
| registered | bool | Si el panel está registrado |
| url_path | string | URL del panel |
| error | string | Mensaje de error si falló |

## Relationships

```
Vehicle (1) -----> (1) PanelConfig
                              |
                              v
                      hass.data[DATA_PANELS]
```

## Validation Rules

- `frontend_url_path`: debe ser único, solo caracteres alfanuméricos y guiones bajos
- `sidebar_title`: máximo 50 caracteres
- `sidebar_icon`: debe ser un icono MDI válido
- `module_url`: debe empezar con "/local/"

## State Transitions

```
No existe -> Registrado (async_register_panel)
Registrado -> Error (fallback)
Registrado -> Eliminado (async_remove_panel)
```

## Storage

Los paneles se almacenan en:
- Memoria: `hass.data["frontend_panels"]`
- Persistencia: No requerida (se recrea en startup)
