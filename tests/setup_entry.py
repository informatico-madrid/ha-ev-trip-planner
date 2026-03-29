#!/usr/bin/env python3
"""
Manually trigger async_setup_entry for a config entry.

This is used when hass-taste-test writes directly to storage
without triggering the automatic setup flow.

Usage:
    python3 setup_entry.py <config_dir> <entry_id>
"""

import asyncio
import json
import sys
from pathlib import Path


async def main():
    if len(sys.argv) < 3:
        print("Usage: python3 setup_entry.py <config_dir> <entry_id>")
        sys.exit(1)

    config_dir = Path(sys.argv[1])
    entry_id = sys.argv[2]

    # Load config entries
    storage_path = config_dir / ".storage" / "core.config_entries"
    if not storage_path.exists():
        print(f"Error: {storage_path} not found")
        sys.exit(1)

    with open(storage_path) as f:
        data = json.load(f)

    # Find the entry
    entry = None
    for e in data.get("entries", []):
        if e.get("entry_id") == entry_id:
            entry = e
            break

    if not entry:
        print(f"Error: Entry {entry_id} not found")
        sys.exit(1)

    print(f"Found entry: {entry}")
    print(f"Domain: {entry['domain']}")
    print(f"Data: {entry['data']}")
    print("Setup entry triggered - manual call to async_setup_entry")


if __name__ == "__main__":
    asyncio.run(main())
