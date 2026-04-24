# playwright-env.local.md — EV Trip Planner E2E Test Environment
#
# This file holds non-secret defaults and references to env var names.
# NEVER put actual passwords, tokens, or cookie values here.
# Keep this file out of version control (.gitignore entry already added).
#
# Usage:
#   1. Fill in the values for your project
#   2. Export the actual secrets in your shell:
#        export RALPH_LOGIN_USER='your@email.com'
#        export RALPH_LOGIN_PASS='your-password'
#
# Auth mode options: none | form | token | cookie | basic | oauth | storage-state | login-flow

# ── Core ────────────────────────────────────────────────────────────────────
appUrl: http://localhost:8123
appEnv: local
allowWrite: true

# ── Browser ─────────────────────────────────────────────────────────────────
browser: chromium
headless: true
viewport: desktop
# viewport: mobile          # emulates 390x844 (iPhone 14)
# viewport: tablet          # emulates 768x1024
# viewport: 1440x900        # explicit size

locale: es-ES
timezone: UTC

# ── Auth: login-flow (REST API login flow + optional trusted network bypass) ──
# auth.setup.ts performs:
#   1. POST /auth/login_flow  → create flow
#   2. POST /auth/login_flow/${flow_id}  → submit dev/dev credentials
#   3. POST /auth/token  → exchange for access token
#   4. Use token for REST API integration setup
#   5. Navigate browser to HA root → trusted_networks auto-bypasses auth
#   6. Save browser storageState to playwright/.auth/user.json
# Tests reuse storageState — no login form is ever shown.
authMode: login-flow
haUrl: http://localhost:8123
storageStatePath: playwright/.auth/user.json

# ── Auth: other modes (not used in this project) ─────────────────────────────
# These modes are documented for reference but not used:
#
# authMode: token
# authTokenVar: RALPH_AUTH_TOKEN
#
# authMode: cookie
# sessionCookieNameVar: RALPH_SESSION_COOKIE_NAME
# sessionCookieValueVar: RALPH_SESSION_COOKIE_VALUE
#
# authMode: oauth
# (agent cannot complete external IdP flows autonomously)
#
# authMode: basic
# loginUserVar: RALPH_LOGIN_USER
# loginPassVar: RALPH_LOGIN_PASS

# ── Seed / app state ────────────────────────────────────────────────────────
# seedCommand: npm run seed:e2e     # runs before verification, local/staging only

# ── Multi-tenant / feature flags ────────────────────────────────────────────
# tenant: acme-corp
# featureFlags: new-dashboard,beta-reports
