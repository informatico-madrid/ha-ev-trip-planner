# Research: Context Window Configuration en Claude Code con Proveedores Terceros

**Fecha:** 2026-05-16
**Pregunta:** ¿Cómo cambiar la ventana de contexto en Claude Code cuando usas modelos de otro proveedor (Bedrock, Vertex, Azure Foundry)?
**Categoría:** Arquitectura / Configuración de Agentes IA

---

## Resumen Ejecutivo

Claude Code permite configurar modelos de proveedores terceros (AWS Bedrock, Google Vertex, Azure Foundry) modificando el archivo `~/.claude/settings.json` y variables de entorno. La ventana de contexto no se cambia directamente, sino que se determina por el modelo seleccionado y las capacidades del proveedor subyacente.

---

## Mecanismos de Configuración

### 1. `modelOverrides` en `settings.json`

```json
{
  "modelOverrides": {
    "sonnet": "anthropic.claude-sonnet-4-5-20251101-v1:0",
    "opus": "arn:aws:bedrock:us-east-1:123456789:inference-profile/us.anthropic.claude-opus-4-5"
  }
}
```

**Función:** Mapea los alias `sonnet`, `opus`, `haiku` a IDs de modelos específicos del proveedor.

**Caso de uso:** Usar un modelo Bedrock con un alias conocido sin cambiar código.

---

### 2. Variables de Entorno para Control de Alias

| Variable | Función |
|----------|---------|
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | Modelo al que resuelve el alias `opus` |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | Modelo al que resuelve el alias `sonnet` |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | Modelo al que resuelve el alias `haiku` |
| `ANTHROPIC_CUSTOM_MODEL_OPTION` | Añade entrada personalizada al selector `/model` |
| `ANTHROPIC_CUSTOM_MODEL_OPTION_NAME` | Nombre visible en el picker |
| `ANTHROPIC_CUSTOM_MODEL_OPTION_DESCRIPTION` | Descripción del modelo |

**Ejemplo:**
```bash
export ANTHROPIC_DEFAULT_OPUS_MODEL="anthropic.claude-opus-4-5-20251101-v1:0"
```

---

### 3. Override de Capacidades del Modelo

Para proveedores terceros, Claude Code puede no detectar correctamente las capacidades del modelo (thinking, tool use, etc.):

```bash
export ANTHROPIC_DEFAULT_OPUS_MODEL_SUPPORTS="thinking,tool-use,search"
export ANTHROPIC_DEFAULT_SONNET_MODEL_SUPPORTS="tool-use,search"
```

---

### 4. Cadenas de Modelo por Plataforma

Diferentes proveedores usan formatos distintos para identificar el mismo modelo:

| Proveedor | Formato del Model ID |
|-----------|---------------------|
| **Anthropic API** | `claude-opus-4-5-20251101` |
| **AWS Bedrock** | `anthropic.claude-opus-4-5-20251101-v1:0` |
| **Google Vertex** | `claude-opus-4-5@20251101` |
| **Azure Foundry** | `claude-opus-4-5-20251101` |

---

## Limitaciones de la Ventana de Contexto

**Nota importante:** La ventana de contexto no se configura directamente. Depende de:

1. **El modelo seleccionado** — Cada modelo tiene un límite de tokens predefinido
   - Claude Opus 4.5: 200K tokens
   - Claude Sonnet 4.5: 200K tokens
   - Claude Haiku: 200K tokens

2. **El proveedor** — Algunos proveedores implementan límites diferentes:
   - **Anthropic directo:** 200K tokens
   - **Bedrock:** Puede variar según la región y perfil de inferencia
   - **Vertex:** Puede variar según la configuración del proyecto
   - **Azure Foundry:** Puede tener límites propios del deployment

3. **Perfiles de inferencia (Bedrock):** Bedrock usa "inference profiles" que pueden agregar límites adicionales.

---

## Variables de Entorno Adicionales Relevantes

| Variable | Función |
|----------|---------|
| `ANTHROPIC_BASE_URL` | Endpoint API personalizado (para proxies) |
| `ANTHROPIC_AUTH_TOKEN` | Token de autenticación |
| `ENABLE_PROMPT_CACHING_1H` | Optar por cache de prompts de 1h |
| `FORCE_PROMPT_CACHING_5M` | Forzar cache de 5 min |
| `ANTHROPIC_BETAS` | Headers beta personalizados |
| `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` | Deshabilitar betas experimentales |

---

## Ejemplo: Configuración para Bedrock

```json
// ~/.claude/settings.json
{
  "modelOverrides": {
    "opus": "arn:aws:bedrock:us-east-1:123456789:inference-profile/us.anthropic.claude-opus-4-5"
  }
}
```

```bash
# ~/.bashrc o ~/.zshrc
export ANTHROPIC_AUTH_TOKEN="tu-token-bedrock"
export ANTHROPIC_BASE_URL="https://bedrock-runtime.us-east-1.amazonaws.com"
export ANTHROPIC_DEFAULT_OPUS_MODEL_SUPPORTS="thinking,tool-use,search"
```

---

## Verificación de Límites

Para verificar la ventana de contexto disponible:

1. `/model` — Muestra modelos disponibles con sus límites
2. `claude mcp list` — Lista servers MCP activos
3. Revisar documentación del proveedor para límites específicos

---

## Modelos Locales Compatibles con OpenAI (Ollama, LM Studio, vLLM)

Claude Code puede configurarse para usar modelos locales que implementan la API compatible con OpenAI. La clave principal es la variable `ANTHROPIC_BASE_URL` que apunta a tu servidor local.

### Configuración para Ollama / LM Studio / vLLM

```bash
# En tu ~/.bashrc o ~/.zshrc
export ANTHROPIC_BASE_URL="http://localhost:11434/v1"
export ANTHROPIC_AUTH_TOKEN="not-required"  # O cualquier dummy token
export ANTHROPIC_DEFAULT_SONNET_MODEL="tu-modelo-local"  # ej: "llama3" o "mistral"
```

```json
// ~/.claude/settings.json
{
  "modelOverrides": {
    "sonnet": "llama3",
    "opus": "mixtral",
    "haiku": "phi3"
  }
}
```

### Variables de Entorno Relevantes

| Variable | Función |
|----------|---------|
| `ANTHROPIC_BASE_URL` | Endpoint del servidor local (requiere path `/v1`) |
| `ANTHROPIC_AUTH_TOKEN` | Token (Ollama no requiere auth, usar dummy) |
| `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL` | Alias → modelo local |
| `ANTHROPIC_CUSTOM_MODEL_OPTION` | Añadir modelo al picker `/model` |
| `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL_SUPPORTS` | Capacidades del modelo |

### Límites de Ventana de Contexto

**Depende del modelo local**, no de Claude Code:

| Modelo Local | Ventana Típica |
|--------------|----------------|
| **Llama 3.1 8B** | 8K-128K tokens (según quantized) |
| **Llama 3.1 70B** | 8K-128K tokens |
| **Mistral 7B** | 8K-32K tokens |
| **Mixtral 8x7B** | 32K tokens |
| **Phi-3** | 4K-128K tokens |
| **Qwen 2.5** | 32K-128K tokens |

**Ollama define límites propios.** Verificar con:
```bash
curl http://localhost:11434/api/show -d '{"name":"llama3"}' | jq '.context_length'
```

### Configuración de Ollama Específica

1. **Arrancar Ollama** con API abierta:
   ```bash
   OLLAMA_HOST=0.0.0.0:11434 ollama serve
   ```

2. **Ver modelos disponibles** y sus contextos:
   ```bash
   ollama list
   ```

3. **Probar conexión**:
   ```bash
   curl http://localhost:11434/v1/models
   ```

### Limitaciones Conocidas

- Claude Code fue diseñado para Anthropic API. Compatibilidad con OpenAI-local puede ser parcial.
- Funciones como `thinking`/`extended thinking` dependen del modelo y proveedor.
- `/model` puede no mostrar correctamente los modelos locales.

### ¿Cómo Determina Claude Code el Límite de Contexto?

Claude Code **NO detecta automáticamente** los límites de contexto de modelos locales. El comportamiento depende del proveedor:

#### 1. **Anthropic API (oficial)**
- Claude Code conoce los límites exactos (200K tokens para Opus/Sonnet/Haiku)
- Detecta capacidades via el endpoint `/v1/models` que devuelve metadata del modelo

#### 2. **Proveedores Terceros (Bedrock, Vertex, Azure Foundry)**
- Claude Code envía запрос al endpoint del proveedor
- El proveedor devuelve el `context_length` en la respuesta
- Si el proveedor no lo devuelve, Claude Code usa valores por defecto

#### 3. **Modelos OpenAI-Compatible Locales (Ollama, vLLM, LM Studio)**
- **Claude Code NO recibe automáticamente el límite** del modelo local
- El endpoint `/v1/models` de Ollama devuelve `context_length` (ej: 4096, 8192, 32768)
- Pero Claude Code fue diseñado para Anthropic API y puede no leer correctamente este valor de proveedores OpenAI-compatible

#### Cuando Excedes el Límite

Si el contexto excede el límite del modelo, recibirás un error tipo:

```
"maximum context length is 32768 tokens, 
but requested at least 50000 tokens"
```

En ese caso, Claude Code intentará hacer contexto summarizing o truncará.

#### Recomendación

Para modelos locales, **verificar manualmente** el límite:

```bash
# Ver límites de todos los modelos Ollama
curl http://localhost:11434/v1/models | jq '.data[].context_length'

# Ver límite de un modelo específico
curl http://localhost:11434/api/show -d '{"name":"llama3"}' | jq '.context_length'
```

---

## Recomendaciones

1. **Para proyectos con contexto largo:** Usar modelo local con ventana >32K tokens (Qwen, Llama 3.1 70B)
2. **Para controlar costos:** Modelos pequeños como Phi-3 o Llama 3.2 3B
3. **Verificar límites:** Siempre probar `/model` y hacer запрос con contexto grande para confirmar

---

## Referencias

- [Anthropic Claude Code CHANGELOG](https://github.com/anthropics/claude-code/blob/main/claude-code/CHANGELOG.md)
- [Frontmatter Reference - Model Field](https://github.com/anthropics/claude-code/blob/main/plugins/plugin-dev/skills/command-development/references/frontmatter-reference.md)
- [Context7: Claude Code Documentation](https://context7.com/anthropics/claude-code)