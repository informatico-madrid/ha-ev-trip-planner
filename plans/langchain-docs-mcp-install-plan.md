# Plan de Instalación: LangChain Docs MCP para Roo Code

## Contexto

El usuario desea instalar el **LangChain Docs MCP Server** oficial para acceder a la documentación de LangChain desde Roo Code. El usuario usa **VS Code a través de SSH** conectándose a un servidor Linux.

## Análisis del Entorno

### Configuración MCP de Roo Code/VS Code (Remote SSH)

| Ubicación | Archivo de Configuración | Formato |
|-----------|-------------------------|---------|
| Servidor (Linux) - RECOMENDADO | `.vscode/mcp.json` (en proyecto) | JSON (`servers`) |
| Servidor (Linux) - Global | `~/.config/Code/User/mcp.json` | JSON (`servers`) |
| Host (Windows) | `%APPDATA%\Code\User\mcp.json` | JSON (`servers`) |

### Decisión: Instalar en SERVIDOR (Linux)

El usuario confirmó que quiere que el MCP se ejecute en el servidor Linux para que funcione con los archivos del proyecto.

### Estado Actual
- ❌ No existe `.vscode/mcp.json` en el proyecto
- ❌ No existe `~/.config/Code/User/mcp.json` en el servidor
- ✅ Existe `%APPDATA%\Code\User\mcp.json` en el host Windows (pero no se usará)

---

## Pasos de Instalación (Servidor Linux)

### Paso 1: Crear el directorio `.vscode` en el proyecto

**Ubicación:** `/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/.vscode/`

```bash
mkdir -p .vscode
```

### Paso 2: Crear el archivo `mcp.json` con la configuración del LangChain Docs MCP

**Contenido del archivo:**

```json
{
  "servers": {
    "langchain-docs": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@langchain/mcp"],
      "env": {}
    }
  }
}
```

**Ubicación:** `.vscode/mcp.json` (en la raíz del proyecto)

### Paso 3: Instalar el paquete npm (si no está instalado)

```bash
npm install -g @langchain/mcp
```

O verificar con:
```bash
npx -y @langchain/mcp --version
```

### Paso 4: Reiniciar VS Code/Roo Code

1. Cerrar completamente VS Code en el servidor SSH
2. Volver a abrir VS Code y reconectar al servidor
3. Verificar que el MCP aparece en: **Roo Code Settings > MCP Servers**

---

## Diagrama de Flujo de Instalación

```mermaid
flow TD
    A[Inicio] --> B[Crear .vscode/]
    B --> C[Crear mcp.json]
    C --> D{Hay npm instalado?}
    D -->|No| E[Instalar @langchain/mcp]
    D -->|Sí| F[Continuar]
    E --> F
    F --> G[Reiniciar VS Code]
    G --> H{MCP conectado?}
    H -->|Éxito| I[✓ LangChain Docs MCP listo]
    H -->|Fallo| J[Ver logs de error]
    J --> K[Corregir configuración]
    K --> G
```

---

## Diagrama de Flujo

```mermaid
flow TD
    A[Inicio] --> B{Verificar mcp.json existente}
    B -->|No existe| C[Crear archivo mcp.json]
    B -->|Existe| D[Leer contenido actual]
    C --> E[Agregar config langchain-docs]
    D --> E
    E --> F[Guardar archivo]
    F --> G[Reiniciar VS Code/Roo Code]
    G --> H{Verificar instalación}
    H -->|Éxito| I[MCP listo para usar]
    H -->|Fallo| J[Verificar logs/error]
    J --> K[Corregir configuración]
    K --> G
```

---

## Verificación Post-Instalación

Para verificar que el MCP está funcionando correctamente:

1. Abrir VS Code / Roo Code
2. Ir a: **Roo Code Settings** > **MCP Servers**
3. Deberías ver **langchain-docs** en la lista
4. Prueba pedirle a Roo Code que busque algo en la documentación de LangChain

## Troubleshooting

Si el MCP no conecta:
1. Verificar que `npx -y @langchain/mcp` funciona en terminal
2. Revisar los logs de Roo Code en: **View > Output > Rous (Workspace)**
3. Asegurarse de que el archivo `.vscode/mcp.json` tiene formato JSON válido

## Checklist de Implementación

- [x] 1. Identificar que el usuario usa SSH (servidor Linux)
- [x] 2. Confirmar que el MCP debe instalarse en el servidor
- [x] 3. Crear el archivo `.vscode/mcp.json` con configuración
- [ ] 4. Crear directorio `.vscode` si no existe
- [ ] 5. Verificar instalación del paquete npm
- [ ] 6. Reiniciar VS Code y verificar conexión
