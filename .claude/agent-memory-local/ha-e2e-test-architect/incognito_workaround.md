---
name: Incognito workaround for HA frontend cache
description: Workaround for HA aggressive JavaScript caching - use incognito mode to bypass IndexedDB cache
type: reference
---

**CRITICAL:** Home Assistant's frontend aggressively caches JavaScript files in browser IndexedDB. Even after:
- `docker cp` to update panel.js
- `docker restart homeassistant`
- Version changes (3.0.5 → 3.0.12)
- Touching files to invalidate cache
- Service workers disabled in Playwright

**The browser continues to serve the OLD cached version.**

**WORKAROUND:** Open browser in **incognito/private mode** to bypass IndexedDB cache:

```bash
# In browser DevTools Console, verify incognito bypasses cache:
# 1. Open incognito window
# 2. Navigate to HA panel
# 3. Open DevTools (F12)
# 4. Check console for VERSION log
# Expected: Shows latest VERSION (e.g., 3.0.12)
# Normal mode: Shows old cached VERSION (e.g., 3.0.5)
```

**Impact:** Code fixes are applied correctly in the container but browser verification requires incognito mode.

**Why this works:** Incognito mode uses a fresh, isolated browser context with no IndexedDB persistence.

**Pattern for testing:**
1. Apply fix in code
2. `docker cp` to container
3. `docker restart homeassistant`
4. Open HA panel in **incognito mode**
5. Check console for VERSION log
6. If VERSION matches → fix is loaded
7. Test functionality

**Known limitation:** Normal browser navigation will always load cached JS from HA's IndexedDB cache.
