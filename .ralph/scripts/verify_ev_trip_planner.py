#!/usr/bin/env python3
"""
Reality Sensor Verification for EV Trip Planner Integration
Generated: 2026-03-20

This script verifies the EV Trip Planner integration exists and is working correctly.
"""

import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Configuration
HA_URL = "http://192.168.1.100:8123"
PROJECT_ROOT = Path(__file__).parent.parent.parent

def check_integration_loaded():
    """Verify the integration is loaded in Home Assistant."""
    print(f"Checking integration: ev_trip_planner")
    
    # Method 1: Check via REST API config
    url = f"{HA_URL}/api/config"
    result = subprocess.run(
        ["curl", "-s", url],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode == 0:
        config = json.loads(result.stdout)
        integrations = config.get("components", [])
        
        if "ev_trip_planner" in integrations:
            print(f"✓ Integration loaded in HA components")
            return True
        else:
            print(f"✗ Integration not found in components list")
            print(f"  Available: {integrations[:5]}...")
            return False
    else:
        print(f"✗ Failed to fetch HA config: {result.stderr}")
        return False

def check_config_entries():
    """Verify the integration has config entries."""
    print(f"\nChecking config entries for: ev_trip_planner")
    
    url = f"{HA_URL}/api/config/config_entries/entry"
    result = subprocess.run(
        ["curl", "-s", url],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode == 0:
        entries = json.loads(result.stdout)
        matching_entries = [e for e in entries if e.get("domain") == "ev_trip_planner"]
        
        if len(matching_entries) > 0:
            print(f"✓ Found {len(matching_entries)} config entry(ies)")
            for entry in matching_entries:
                print(f"  - ID: {entry.get('entry_id')}")
                print(f"    Domain: {entry.get('domain')}")
                print(f"    Title: {entry.get('title')}")
                print(f"    State: {entry.get('state')}")
            return True
        else:
            print(f"✗ No config entries found for ev_trip_planner")
            return False
    else:
        print(f"✗ Failed to fetch config entries: {result.stderr}")
        return False

def check_entities_registered():
    """Verify entities are registered from the integration."""
    print(f"\nChecking entity registry for: ev_trip_planner")
    
    url = f"{HA_URL}/api/states"
    result = subprocess.run(
        ["curl", "-s", url],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode == 0:
        all_states = json.loads(result.stdout)
        ev_entities = [s for s in all_states if "ev_trip" in s.get("entity_id", "")]
        
        if len(ev_entities) > 0:
            print(f"✓ Found {len(ev_entities)} EV Trip Planner entities")
            for entity in ev_entities[:5]:  # Show first 5
                print(f"  - {entity.get('entity_id')}: {entity.get('state')}")
            return True
        else:
            print(f"⚠ No EV Trip Planner entities found (may be expected if no trips configured)")
            return True  # Not necessarily an error
    else:
        print(f"✗ Failed to fetch states: {result.stderr}")
        return False

def check_log_messages():
    """Check for initialization messages in HA logs."""
    print(f"\nChecking log messages for: ev-trip-planner")
    
    log_file = PROJECT_ROOT / ".." / "homeassistant" / "home-assistant.log"
    
    if not log_file.exists():
        print(f"⚠ Log file not found at: {log_file}")
        return True  # Not critical
    
    try:
        # Search for relevant log messages
        cmd = f"grep -i 'ev-trip-planner' {log_file} | tail -10"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            print(f"✓ Found {len(lines)} log message(s) related to ev-trip-planner")
            for line in lines[-3:]:  # Show last 3
                print(f"  {line[:200]}...")
            return True
        else:
            print(f"⚠ No specific log messages found (may be expected)")
            return True  # Not critical
            
    except Exception as e:
        print(f"⚠ Could not read logs: {e}")
        return True

def main():
    print("=" * 70)
    print("REALITY SENSOR VERIFICATION - EV TRIP PLANNER INTEGRATION")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)
    print()
    
    all_passed = True
    
    # Existence checks
    print("🔍 EXISTENCE CHECKS")
    print("-" * 70)
    
    if not check_integration_loaded():
        all_passed = False
    
    if not check_config_entries():
        all_passed = False
    
    # Effect checks
    print("\n⚡ EFFECT CHECKS")
    print("-" * 70)
    
    if not check_entities_registered():
        all_passed = False
    
    if not check_log_messages():
        all_passed = False
    
    # Summary
    print(f"\n{'='*70}")
    passed_count = sum(1 for c in [] if c)  # Count passed checks
    total_checks = 4  # Total number of checks performed
    
    status = "STATE_MATCH" if all_passed else "STATE_MISMATCH"
    print(f"FINAL STATUS: {status}")
    print(f"{'='*70}\n")
    
    # Save results
    results_file = PROJECT_ROOT / ".ralph" / f"reality-sensor-ev-trip-planner.json"
    results = {
        "feature": "ev-trip-planner",
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "checks_performed": [
            "integration_loaded",
            "config_entries", 
            "entities_registered",
            "log_messages"
        ],
        "all_passed": all_passed
    }
    
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to: {results_file}")
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
