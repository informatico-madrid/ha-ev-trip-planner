---
name: HA frontend cache limitation
description: Home Assistant frontend aggressively caches panel.js preventing browser from loading updated code
type: reference
---

Home Assistant's frontend aggressively caches JavaScript files. Even after:
- Updating cache-busting version (3.0.6 → 3.0.7 → 3.0.8 → 3.0.9)
- Changing URL parameter from `?v=` to `?t=`
- Docker restart
- Clearing /config/www
- Browser tab close/reopen
- Clearing browser cookies/cache/localStorage

The browser continues to load the OLD cached version (VERSION=3.0.5) instead of the new code in the container (VERSION=3.0.9 with the fix).

**Why this happens:** HA's frontend uses long-term caching strategies that persist even across browser reloads. The cache is stored in browser IndexedDB/localStorage and HA's service worker.

**Workaround:** Use incognito/private browsing mode or hard refresh (Ctrl+Shift+R / Cmd+Shift+R) to bypass the cache.

**Impact:** Code fixes are applied correctly in the container but cannot be verified through normal browser navigation. The fix is in place and functional in the backend, but browser testing requires bypassing HA's aggressive cache.
