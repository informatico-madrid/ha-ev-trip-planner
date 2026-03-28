# 🚨 CRITICAL: ALWAYS USE ha-e2e-testing SKILL

## NEVER FORGET THIS RULE

**When working on E2E testing for Home Assistant, you MUST use the `ha-e2e-testing` skill.**

### Why this is critical

The skill contains:
- **Pre-configured scripts** that work correctly with the project structure
- **Proven patterns** for Shadow DOM, panel URLs, authentication
- **Architecture documentation** specific to HA E2E testing
- **Lessons learned** from previous sessions

### What happens if you don't use it

1. **Scripts won't work** - `npx playwright test` directly doesn't have the correct configuration
2. **Tests fail** - Missing patterns for Shadow DOM, panel URLs, etc.
3. **Wasted time** - Debugging issues that the skill already solves

### How to use it

**NEVER use:**
```bash
npx playwright test tests/e2e/test-create-trip.spec.ts
```

**ALWAYS use:**
```bash
./scripts/run_playwright_test.sh tests/e2e/test-create-trip.spec.ts
```

### Scripts available

- `scripts/run_playwright_test.sh` - Run tests with proper configuration
- `scripts/extract_report.js` - Get structured test results

### This is NOT optional

This is not a suggestion. This is a **requirement** for E2E testing work on this project.

If you see yourself about to use `npx playwright test` directly, STOP and use the script instead.

---

## Lección aprendida

**Problema:** En sesiones anteriores, no se usaron los scripts de la skill, se usó `npx playwright test` directamente.

**Solución:** Scripts locales en el proyecto que funcionan correctamente con la skill.

**Regla:** NUNCA usar `npx playwright test` directamente. Siempre usar `./scripts/run_playwright_test.sh`.

---

**If you forget this rule, the tests will fail and you will waste time debugging.**
