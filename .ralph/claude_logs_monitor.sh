#!/bin/bash
# Claude logs monitor - CORREGIDO CON MODO FOLLOW

set -euo pipefail

# Rutas
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$PROJECT_DIR/logs"
OUTPUT_FILE="$OUTPUT_DIR/claude_tool_logs.log"
MARKER_FILE="${OUTPUT_FILE}.marker"

MAX_LOG_SIZE="10M"
MAX_LINES_PER_SESSION=1000
DEFAULT_SINCE_DATE="$(date +%Y-%m-%d)"
CLAUDE_LOGS_DIR_DEFAULT="$HOME/.claude/projects"

SINCE_DATE=""
CLAUDE_LOGS_DIR=""
declare -gA FILE_POSITIONS

log_info() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*"; }
log_error() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >&2; }
log_warn() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $*"; }

validate_jsonl_file() {
    local file="$1"
    [[ -f "$file" && -r "$file" ]] || return 1
    [[ -s "$file" ]] || return 1
    return 0
}

get_current_line_count() {
    local file="$1"
    wc -l < "$file" 2>/dev/null || echo "0"
}

save_position() {
    local file="$1"
    local position="$2"
    echo "${file}:${position}" >> "$MARKER_FILE"
}

load_positions() {
    if [[ -f "$MARKER_FILE" ]]; then
        while IFS=':' read -r file position; do
            FILE_POSITIONS["$file"]="$position"
        done < "$MARKER_FILE"
    fi
}

process_jsonl_file() {
    local jsonl_file="$1"
    
    if [[ ! -f "$jsonl_file" ]]; then
        log_warn "Saltando archivo que ya no existe: $(basename "$jsonl_file")"
        return 0
    fi
    
    local from_line=0
    if [[ -v FILE_POSITIONS["$jsonl_file"] ]]; then
        from_line="${FILE_POSITIONS[$jsonl_file]:-0}"
    fi
    
    if [[ "$from_line" -eq 0 ]]; then
        from_line=$(get_current_line_count "$jsonl_file")
        if [[ "$from_line" -eq 0 ]]; then
            return 0
        fi
    fi
    
    local total_lines
    total_lines=$(get_current_line_count "$jsonl_file")
    
    if [[ "$total_lines" -le "$from_line" ]]; then
        return 0
    fi
    
    log_info "Procesando $jsonl_file desde línea $from_line (total: $total_lines)"
    
    local filename
    filename=$(basename "$jsonl_file")
    local session_id
    session_id=$(echo "$filename" | grep -oP '[0-9a-f]{8}-[0-9a-f]{12}' | head -1 || echo "unknown")
    
    local line_count=0
    while IFS= read -r line; do
        ((line_count++)) || true
        
        if [[ $line_count -gt $MAX_LINES_PER_SESSION ]]; then
            log_warn "Límite de líneas alcanzado para $session_id ($MAX_LINES_PER_SESSION)"
            break
        fi
        
        local timestamp tool_name tool_type tool_id tool_input tool_use_result thinking stop_reason
        
        timestamp=$(echo "$line" | jq -r '.timestamp // .message.timestamp // "unknown"' 2>/dev/null || echo "unknown")
        tool_name=$(echo "$line" | jq -r '.message.content[0].tool_use.name // "none"' 2>/dev/null || echo "none")
        tool_type=$(echo "$line" | jq -r '.message.content[0].type // "none"' 2>/dev/null || echo "none")
        
        [[ "$tool_name" == "none" || -z "$tool_name" ]] && continue
        
        tool_id=$(echo "$line" | jq -r '.message.content[0].tool_use.id // "none"' 2>/dev/null || echo "none")
        tool_input=$(echo "$line" | jq -r '.message.content[0].tool_use.input // "none"' 2>/dev/null || echo "none")
        tool_use_result=$(echo "$line" | jq -r '.message.content[0].result // "none"' 2>/dev/null || echo "none")
        thinking=$(echo "$line" | jq -r '.message.thinking // "none"' 2>/dev/null || echo "none")
        stop_reason=$(echo "$line" | jq -r '.message.stop_reason // "none"' 2>/dev/null || echo "none")
        
        [[ "$tool_type" != "tool_use" ]] && continue
        
        echo "[$timestamp] [$session_id] MSG_TYPE: $tool_type" >> "$OUTPUT_FILE"
        echo "[$timestamp] [$session_id] TOOL_NAME: $tool_name" >> "$OUTPUT_FILE"
        [[ "$tool_id" != "none" && -n "$tool_id" ]] && echo "[$timestamp] [$session_id] TOOL_ID: $tool_id" >> "$OUTPUT_FILE"
        [[ "$tool_input" != "none" && -n "$tool_input" && "$tool_input" != "{}" ]] && \
            echo "[$timestamp] [$session_id] INPUT: ${tool_input:0:150}" >> "$OUTPUT_FILE"
        [[ -n "$tool_use_result" ]] && \
            echo "[$timestamp] [$session_id] STDOUT: ${tool_use_result:0:200}" >> "$OUTPUT_FILE"
        [[ -n "$thinking" ]] && \
            echo "[$timestamp] [$session_id] THINKING: ${thinking:0:200}" >> "$OUTPUT_FILE"
        [[ "$stop_reason" != "none" && -n "$stop_reason" ]] && \
            echo "[$timestamp] [$session_id] STOP_REASON: $stop_reason" >> "$OUTPUT_FILE"
        
    done < <(tail -n +"$((from_line + 1))" "$jsonl_file" 2>/dev/null)
    
    save_position "$jsonl_file" "$total_lines"
    log_info "Procesadas $line_count líneas nuevas de $jsonl_file"
}

filter_files_by_date() {
    local follow_mode="${1:-false}"
    local files=()
    
    if [[ "$follow_mode" == "true" ]]; then
        log_info "Modo FOLLOW: Procesando todos los archivos JSONL existentes..."
        
        while IFS= read -r -d '' file; do
            if validate_jsonl_file "$file"; then
                files+=("$file")
                log_info "✓ Archivo encontrado: $(basename "$file")"
            fi
        done < <(find "$CLAUDE_LOGS_DIR" -name "*.jsonl" -type f -print0 2>/dev/null)
        
        echo "${files[@]}"
        return
    fi
    
    local since_epoch
    since_epoch=$(date -d "$SINCE_DATE" +%s 2>/dev/null || date -d "today" +%s)
    
    log_info "Filtrando archivos desde: $SINCE_DATE (epoch: $since_epoch)"
    
    while IFS= read -r -d '' file; do
        if validate_jsonl_file "$file"; then
            local file_epoch
            file_epoch=$(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file" 2>/dev/null || echo "0")
            
            if [[ "$file_epoch" -ge "$since_epoch" ]]; then
                files+=("$file")
                log_info "✓ Archivo nuevo/moderno: $(basename "$file")"
            else
                log_info "✗ Saltando archivo antiguo: $(basename "$file")"
            fi
        fi
    done < <(find "$CLAUDE_LOGS_DIR" -name "*.jsonl" -type f -print0 2>/dev/null)
    
    echo "${files[@]}"
}

main() {
    local positional_args=()
    local follow_mode=false
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)
                show_help
                ;;
            --since)
                SINCE_DATE="$2"
                shift 2
                continue
                ;;
            --follow|-f)
                follow_mode=true
                shift
                continue
                ;;
            *)
                positional_args+=("$1")
                shift
                ;;
        esac
    done
    
    if [[ ${#positional_args[@]} -ge 1 ]]; then
        SINCE_DATE="${positional_args[0]:-$DEFAULT_SINCE_DATE}"
    fi
    
    if [[ ${#positional_args[@]} -ge 2 ]]; then
        CLAUDE_LOGS_DIR="${positional_args[1]:-$CLAUDE_LOGS_DIR_DEFAULT}"
    fi
    
    SINCE_DATE="${SINCE_DATE:-$DEFAULT_SINCE_DATE}"
    CLAUDE_LOGS_DIR="${CLAUDE_LOGS_DIR:-$CLAUDE_LOGS_DIR_DEFAULT}"
    
    log_info "=== Claude Logs Monitor (CORREGIDO) ==="
    log_info "Fecha límite: $SINCE_DATE"
    log_info "Directorio de logs: $CLAUDE_LOGS_DIR"
    log_info "Archivo de salida: $OUTPUT_FILE"
    
    mkdir -p "$OUTPUT_DIR"
    
    if [[ ! -d "$CLAUDE_LOGS_DIR" ]]; then
        log_error "Directorio no encontrado: $CLAUDE_LOGS_DIR"
        exit 1
    fi
    
    declare -gA FILE_POSITIONS
    load_positions
    
    # MODO FOLLOW
    if [[ "$follow_mode" == true ]]; then
        log_info "Modo FOLLOW activado - procesando archivos actuales..."
        log_info "Reiniciando posiciones de lectura para modo follow..."
        : > "$MARKER_FILE"
        
        local filtered_files=()
        while IFS= read -r file; do
            [[ -n "$file" ]] && filtered_files+=("$file")
        done < <(filter_files_by_date true)
        
        if [[ ${#filtered_files[@]} -eq 0 ]]; then
            log_warn "No hay archivos nuevos para procesar. Esperando nuevos logs..."
        else
            log_info "Procesando ${#filtered_files[@]} archivos iniciales..."
            
            local processed=0
            local total=${#filtered_files[@]}
            local shown_warnings=0
            local max_warnings_to_show=5
            
            for jsonl_file in "${filtered_files[@]}"; do
                if [[ ! -f "$jsonl_file" ]]; then
                    ((shown_warnings++)) || true
                    if [[ $shown_warnings -le $max_warnings_to_show ]]; then
                        log_warn "Saltando archivo que ya no existe: $(basename "$jsonl_file")"
                    elif [[ $shown_warnings -eq $((max_warnings_to_show + 1)) ]]; then
                        log_warn "... y más archivos eliminados"
                    fi
                    continue
                fi
                
                log_info "[$((processed + 1))/$total] Procesando: $(basename "$jsonl_file")"
                process_jsonl_file "$jsonl_file"
                ((processed++)) || true
            done
            
            log_info "=== Procesamiento inicial completado ($processed archivos) ==="
            log_info "Ahora siguiendo nuevos logs con tail -f..."
        fi
        
        if [[ -f "$OUTPUT_FILE" ]]; then
            tail -f "$OUTPUT_FILE"
        fi
        
        exit 0
    fi
    
    # MODO NORMAL
    local filtered_files=()
    while IFS= read -r file; do
        [[ -n "$file" ]] && filtered_files+=("$file")
    done < <(filter_files_by_date)
    
    local existing_files=()
    for file in "${filtered_files[@]}"; do
        if [[ -f "$file" ]]; then
            existing_files+=("$file")
        else
            log_warn "Archivo eliminado durante procesamiento: $(basename "$file")"
        fi
    done
    filtered_files=("${existing_files[@]}")
    
    if [[ ${#filtered_files[@]} -eq 0 ]]; then
        log_warn "No se encontraron archivos JSONL nuevos desde $SINCE_DATE"
        exit 0
    fi
    
    log_info "Se encontraron ${#filtered_files[@]} archivos nuevos desde $SINCE_DATE"
    
    check_and_rotate_log() {
        if [[ -f "$OUTPUT_FILE" ]]; then
            local current_size
            current_size=$(du -b "$OUTPUT_FILE" | cut -f1)
            local max_size_bytes
            case "$MAX_LOG_SIZE" in
                *K) max_size_bytes=$((1024 * ${MAX_LOG_SIZE%K})) ;;
                *M) max_size_bytes=$((1024*1024 * ${MAX_LOG_SIZE%M})) ;;
                *) max_size_bytes=$MAX_LOG_SIZE ;;
            esac
            
            if [[ $current_size -gt $max_size_bytes ]]; then
                log_warn "Archivo de log excede tamaño máximo (${MAX_LOG_SIZE}), rotando..."
                local rotated_file="${OUTPUT_FILE}.$(date +%Y%m%d%H%M%S)"
                mv "$OUTPUT_FILE" "$rotated_file"
                touch "$OUTPUT_FILE"
                log_info "Log rotado a: $rotated_file"
            fi
        else
            touch "$OUTPUT_FILE"
        fi
    }
    
    check_and_rotate_log
    
    local max_background=5
    local background_count=0
    
    for jsonl_file in "${filtered_files[@]}"; do
        while [[ $(jobs -r | wc -l) -ge $max_background ]]; do
            sleep 1
        done
        
        (
            process_jsonl_file "$jsonl_file"
        ) &
        
        ((background_count++)) || true
        
        if [[ $((background_count % 10)) -eq 0 ]]; then
            log_info "Procesando $background_count de ${#filtered_files[@]} archivos..."
        fi
    done
    
    wait
    
    log_info "=== Proceso completado ==="
    log_info "Archivos procesados: ${#filtered_files[@]}"
    log_info "Posiciones guardadas en: $MARKER_FILE"
}

main "$@"
