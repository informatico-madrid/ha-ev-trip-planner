#!/bin/bash
# Start ephemeral HA server for E2E testing
# CRITICAL: panel.js MUST be copied BEFORE HA starts so /local/ endpoint is registered

set -e

echo "[Ephemeral HA] Creating temp config directory..."
CONFIG_DIR="/tmp/ha-test-config-$$"
rm -rf "$CONFIG_DIR"
mkdir -p "$CONFIG_DIR/www"

echo "[Ephemeral HA] Config directory: $CONFIG_DIR"

# Copy panel.js to www/ BEFORE HA starts - this is CRITICAL for /local/ to work
PANEL_JS="/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/frontend/panel.js"
if [ ! -f "$PANEL_JS" ]; then
    echo "[Ephemeral HA] ERROR: panel.js not found at $PANEL_JS"
    exit 1
fi

echo "[Ephemeral HA] Copying panel.js to $CONFIG_DIR/www/..."
cp "$PANEL_JS" "$CONFIG_DIR/www/panel.js"
echo "[Ephemeral HA] panel.js copied successfully"

# Create configuration.yaml
echo "[Ephemeral HA] Creating configuration.yaml..."
cat > "$CONFIG_DIR/configuration.yaml" <<EOF
# Home Assistant Configuration for E2E Testing
default_config:

http:
  server_host: 127.0.0.1
  server_port: 8123

binary_sensor:
  - platform: demo
    devices:
      - name: "Coche1 Cargando"
        device_class: plug
      - name: "Coche1 En Casa"
        device_class: home
      - name: "Coche1 Enchufado"
        device_class: plug

lovelace:
  mode: storage
  resources:
    - url: /local/panel.js
      type: module
EOF

# Start Home Assistant with the prepared config
echo "[Ephemeral HA] Starting Home Assistant..."
cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner
python3 -m homeassistant -c "$CONFIG_DIR" -v
