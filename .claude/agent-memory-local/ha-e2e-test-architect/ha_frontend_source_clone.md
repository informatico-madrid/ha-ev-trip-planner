---
name: ha_frontend_source_clone
description: Repositorio clonado de home-assistant/frontend para investigar código fuente original
type: reference
---

## Clon del Repositorio Frontend de Home Assistant

**Ubicación:** `/mnt/bunker_data/ha-ev-trip-planner/ha-frontend-source/`

**Repositorio:** https://github.com/home-assistant/frontend.git

## Uso

Este clon permite investigar el código fuente original sin minificar de Home Assistant frontend para:

1. **Ver la firma exacta de métodos** como `callService`
2. **Investigar implementaciones** reales en lugar de adivinar
3. **Buscar patrones** correctos de uso de la API

## Firma de callService (fuente de verdad)

**Archivo:** `src/types.ts`

```typescript
callService<T = any>(
  domain: ServiceCallRequest["domain"],
  service: ServiceCallRequest["service"],
  serviceData?: ServiceCallRequest["serviceData"],
  target?: ServiceCallRequest["target"],
  notifyOnError?: boolean,
  returnResponse?: boolean  // ← SEXTO PARÁMETRO, boolean (NO objeto!)
): Promise<ServiceCallResponse<T>>;
```

**Parámetros:**
1. `domain` - String (ej: "ev_trip_planner")
2. `service` - String (ej: "trip_list")
3. `serviceData` - Object (opcional)
4. `target` - Object (opcional)
5. `notifyOnError` - Boolean (opcional)
6. `returnResponse` - Boolean (opcional) ← **CORRECTO: boolean, no objeto**

## Lección Aprendida

**Nunca adivinar la API:** Cuando hay duda sobre cómo usar una función, investigar directamente el código fuente original en lugar de intentar deducir la firma.

**Fuente de verdad:** El código fuente clonado en `/mnt/bunker_data/ha-ev-trip-planner/ha-frontend-source/` es la fuente de verdad para la API del frontend de Home Assistant.

## Búsqueda de Otros Problemas

Usar grep para buscar patrones incorrectos:
```bash
cd /mnt/bunker_data/ha-ev-trip-planner/ha-frontend-source
grep -rn "callService.*{" src --include="*.ts" | grep "return_response"
```

Buscar en el proyecto actual:
```bash
cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner
grep -rn "callService" custom_components/ev_trip_planner/frontend/ --include="*.js"
```
