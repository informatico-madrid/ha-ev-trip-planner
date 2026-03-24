#!/bin/bash
# Claude logs monitor - VERSIÓN SIMPLIFICADA Y FUNCIONAL

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$PROJECT_DIR/logs"
OUTPUT_FILE="$OUTPUT_DIR/claude_tool_logs.log"

mkdir -p "$OUTPUT_DIR"

log_info() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*"; }
log_error() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >&2; }

# Buscar directorio de logs
CLAUDE_LOGS_DIR="$HOME/.claude/projects/-home-malka-ha-ev-trip-planner/"

if [[ ! -d "$CLAUDE_LOGS_DIR" ]]; then
    log_error "Directorio no encontrado: $CLAUDE_LOGS_DIR"
    exit 1
fi

log_info "Monitorizando: $CLAUDE_LOGS_DIR"

# Modo follow
if [[ "${1:-}" == "--follow" || "${1:-}" == "-f" ]]; then
    log_info "Modo FOLLOW activado..."
    
    # Seguir todos los archivos JSONL nuevos
    tail -f "$CLAUDE_LOGS_DIR"/*.jsonl 2>/dev/null | while read -r line; do
        # Buscar patrones de herramientas en cada línea
        tools=$(echo "$line" | grep -oP '(browser_click|browser_hover|browser_take_screenshot|read_file|write_file|shell_command)' | sort | uniq)
        
        if [[ -n "$tools" ]]; then
            timestamp=$(date "+%Y-%m-%d %H:%M:%S")
            
            # Extraer session ID del path o contenido
            session_id=$(echo "$line" | grep -oP '[0-9a-f]{8}-[0-9a-f]{12}' | head -1)
            [[ -z "$session_id" ]] && session_id="unknown"
            
            # Escribir al log
            for tool in $tools; do
                echo "[$timestamp] SESSION: $session_id | TOOL: $tool" >> "$OUTPUT_FILE"
                echo "→ [$tool]"
            done
        fi
    done
else
    # Modo normal: procesar archivos existentes
    log_info "Procesando archivos JSONL existentes..."
    
    processed=0
    for jsonl_file in "$CLAUDE_LOGS_DIR"*.jsonl; do
        [[ -f "$jsonl_file" ]] || continue
        
        filename=$(basename "$jsonl_file")
        log_info "Procesando: $filename"
        
        # Extraer todas las herramientas de este archivo
        tools_found=$(grep -oP '(browser_click|browser_hover|browser_take_screenshot|read_file|write_file|shell_command)' "$jsonl_file" 2>/dev/null | sort | uniq)
        
        if [[ -n "$tools_found" ]]; then
            session_id="${filename%.jsonl}"
            
            for tool in $tools_found; do
                count=$(grep -c "$tool" "$jsonl_file" 2>/dev/null || echo "0")
                echo "  → $tool: $count veces"
                echo "[$(date "+%Y-%m-%d %H:%M:%S")] SESSION: $session_id | TOOL: $tool" >> "$OUTPUT_FILE"
            done
            
            ((processed++)) || true
        fi
    done
    
    log_info "=== Procesados $processed archivos ==="
    log_info "Verifica: $OUTPUT_FILE"
fi
