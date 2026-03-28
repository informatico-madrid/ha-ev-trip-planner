---
name: feedback_no_skip_tests
description: NEVER skip tests with test.describe.skip() or @pytest.mark.skip() - always fix the test instead
type: feedback
---

**Rule:** Under NO circumstances skip tests using `test.describe.skip()`, `@pytest.mark.skip()`, or similar. Tests must be fixed, not skipped.

**Why:** Skipping tests defeats the purpose of a test suite. Every test should either pass or be removed entirely if it's not useful. Skipping hides problems and gives false confidence.

**How to apply:**
- When a test fails, diagnose the root cause
- Fix the test's mocks, fixtures, or assertions
- If a test is testing obsolete functionality, DELETE the test file
- If a test requires infrastructure not available, implement the missing mock/fixture
- Never use `.skip()` or `.mark.skip()` as a workaround

**Examples:**
- ❌ `test.describe.skip('Old tests', () => { ... })` → Fix the tests or delete file
- ❌ `@pytest.mark.skip(reason='...')` → Fix the test or delete it
- ✅ Fix mock to match HA API (e.g., add `supports_response` parameter)
- ✅ Implement missing infrastructure (e.g., virtualenv for dependencies)

**Files modified:**
- `/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/.claude/output-styles/ha-e2e-test-architect.md` - Added rule to strict blacklist
