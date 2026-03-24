# EV Trip Planner E2E Tests

## Prerequisites

Before running these tests, ensure:

1. **Home Assistant is running** at the configured URL
2. **EV Trip Planner integration is installed** and configured
3. **Vehicle exists** (default: `chispitas`)

## Configuration

Copy `.env.example` to `.env` and update with your values:

```bash
cp .env.example .env
```

Update the `.env` file:

```env
HA_URL=http://192.168.1.100:18123
VEHICLE_ID=chispitas
TIMEOUT=30000
```

## Running Tests

### Run all tests

```bash
npx playwright test
```

### Run specific test file

```bash
npx playwright test tests/e2e/test-panel-loading.spec.ts
```

### Run with specific browser

```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

### Run with HTML report

```bash
npx playwright test --reporter=html
npx playwright show-report
```

## Test Files

| File | Description |
|------|-------------|
| `test-panel-loading.spec.ts` | Panel loading and vehicle ID extraction |
| `test-trip-list.spec.ts` | Trip list loading |
| `test-create-trip.spec.ts` | Trip creation workflow |
| `test-edit-trip.spec.ts` | Trip editing workflow |
| `test-delete-trip.spec.ts` | Trip deletion with confirmation |
| `test-base.spec.ts` | Shared test utilities |
| `test-pause-resume.spec.ts` | Pause/resume functionality |
| `test-complete-cancel.spec.ts` | Complete/cancel functionality |
| `test-integration.spec.ts` | Integration tests |
| `test-cross-browser.spec.ts` | Cross-browser compatibility |
| `test-performance.spec.ts` | Performance tests |
| `test-pr-creation.spec.ts` | PR verification |

## Environment Variables

- `HA_URL` - Home Assistant URL (default: `http://192.168.1.100:18123`)
- `VEHICLE_ID` - Vehicle ID for testing (default: `chispitas`)
- `TIMEOUT` - Test timeout in ms (default: `30000`)

## Troubleshooting

### 404 Errors on CSS

The panel CSS is served at `/ev_trip_planner/panel.css`. Ensure:
- EV Trip Planner integration is properly installed
- The integration is loaded in Home Assistant
- Static paths are correctly registered

### Panel Not Loading

Check:
- Home Assistant is running at the configured URL
- The vehicle ID exists in Home Assistant
- The EV Trip Planner panel is registered

### Console Errors

Check browser console for:
- Failed to load resource: 404 (Not Found) - CSS not found
- Panel not registered - integration not loaded

## Test Results

Run tests with report:

```bash
npx playwright test --reporter=html
npx playwright show-report
```
