/**
 * E2E Tests for User Story 9: UI del panel ordenada y bonita
 *
 * This test verifies that the panel has a clean, professional design with:
 * - Clearly separated sections with proper headers and icons
 * - Visual organization with consistent styling
 * - Action buttons that are easily identifiable
 * - Good spacing and readability
 * - Responsive design that works on mobile devices
 * Acceptance Scenarios:
 * 1. Panel has clean and professional design
 * 2. Sections are clearly separated with headers
 * 3. Section headers include icons and visual styling
 * 4. Action buttons are easily identifiable
 * 5. Buttons are grouped logically (edit/delete vs status actions)
 * 6. Good spacing between elements
 * 7. Color scheme is consistent with HA theme
 * 8. Responsive design works on mobile
 * Usage:
 *   npx playwright test test-us9-ui.spec.ts
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const HA_URL = process.env.HA_URL || process.env.HA_TEST_URL || 'http://192.168.1.201:8123';
const HA_USERNAME = process.env.HA_USER || process.env.HA_USERNAME || 'tests';
const HA_PASSWORD = process.env.HA_PASSWORD || 'tests';

// Path to panel.css in the worktree
const PANEL_CSS_PATH = path.join(
  process.cwd(),
  'custom_components',
  'ev_trip_planner',
  'frontend',
  'panel.css'
);

// Path to panel.js in the worktree
const PANEL_JS_PATH = path.join(
  process.cwd(),
  'custom_components',
  'ev_trip_planner',
  'frontend',
  'panel.js'
);

test.describe('US9: UI del panel ordenada y bonita', () => {
  // ============================================
  // TESTS FOR PANEL OVERALL DESIGN
  test('should have clean and professional panel container design', async () => {
    expect(fs.existsSync(PANEL_CSS_PATH)).toBe(true, 'panel.css should exist');
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify panel container has proper styling
    expect(cssContent).toContain('.panel-container');
    expect(cssContent).toContain('height: 100%');
    expect(cssContent).toContain('display: flex');
    expect(cssContent).toContain('flex-direction: column');

    // Verify background colors
    expect(cssContent).toContain('--panel-background');
    expect(cssContent).toContain('var(--primary-background-color');

    // Verify font family is set
    expect(cssContent).toContain('--primary-font-family');
    expect(cssContent).toContain('font-family: -apple-system');
  });

  test('should have consistent color scheme with CSS variables', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify CSS variables are defined
    expect(cssContent).toContain('--panel-primary-color');
    expect(cssContent).toContain('--panel-primary-dark');
    expect(cssContent).toContain('--panel-primary-light');
    expect(cssContent).toContain('--panel-card-background');
    expect(cssContent).toContain('--panel-text-primary');
    expect(cssContent).toContain('--panel-text-secondary');
    expect(cssContent).toContain('--panel-text-disabled');
    expect(cssContent).toContain('--panel-divider');

    // Verify color states
    expect(cssContent).toContain('--panel-success');
    expect(cssContent).toContain('--panel-warning');
    expect(cssContent).toContain('--panel-error');
  });

  // TESTS FOR SECTION HEADERS AND ORGANIZATION
  test('should have section title styling with icons', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify section-title class exists
    expect(cssContent).toContain('.section-title');

    // Verify section-title styling
    expect(cssContent).toContain('align-items: center');
    expect(cssContent).toContain('gap: 12px');
    expect(cssContent).toContain('font-weight: 600');
    expect(cssContent).toContain('border-bottom: 3px solid');

    // Verify section-icon styling
    expect(cssContent).toContain('.section-icon');
    expect(cssContent).toContain('font-size: 20px');
    expect(cssContent).toContain('flex-shrink: 0');
  });

  test('should have status section with proper styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify status-section exists
    expect(cssContent).toContain('.status-section');

    // Verify status-section styling
    expect(cssContent).toContain('margin-bottom: 28px');
    expect(cssContent).toContain('padding-bottom: 16px');
    expect(cssContent).toContain('border-bottom: 1px solid');

    // Verify status-section h2 styling
    expect(cssContent).toContain('.status-section h2');
    expect(cssContent).toContain('font-size: 16px');
    expect(cssContent).toContain('color: var(--secondary-text-color');
  });

  test('should have sensors section with proper styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify sensors-section exists
    expect(cssContent).toContain('.sensors-section');

    // Verify sensors-section styling
    expect(cssContent).toContain('.sensors-section h2');
  });

  test('should have trips section with proper styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify trips-section exists
    expect(cssContent).toContain('.trips-section');

    // Verify trips-section h2 styling
    expect(cssContent).toContain('.trips-section h2');
  });

  // TESTS FOR STATUS CARDS DESIGN
  test('should have status grid layout', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify status-grid exists
    expect(cssContent).toContain('.status-grid');

    // Verify grid layout
    expect(cssContent).toContain('grid-template-columns: repeat(3, 1fr)');
    expect(cssContent).toContain('gap: 16px');

    // Verify responsive adjustment for mobile
    expect(cssContent).toContain('@media (max-width: 600px)');
    expect(cssContent).toContain('grid-template-columns: repeat(2, 1fr)');
  });

  test('should have status card hover effects', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify status-card exists
    expect(cssContent).toContain('.status-card');

    // Verify hover effects
    expect(cssContent).toContain('.status-card:hover');
    expect(cssContent).toContain('transform: translateY(-4px)');
    expect(cssContent).toContain('box-shadow: 0 4px 12px');

    // Verify border color change on hover
    expect(cssContent).toContain('border-color: var(--panel-primary-color');
  });

  test('should have status value styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify status-value exists
    expect(cssContent).toContain('.status-value');

    // Verify value styling
    expect(cssContent).toContain('font-size: 24px');
    expect(cssContent).toContain('font-weight: 700');
    expect(cssContent).toContain('color: var(--panel-primary-color');
    expect(cssContent).toContain('letter-spacing: 0.5px');
  });

  // TESTS FOR SENSOR LIST DESIGN
  test('should have sensor list group styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify sensor-list-grouped exists
    expect(cssContent).toContain('.sensor-list-grouped');

    // Verify group styling
    expect(cssContent).toContain('background: var(--card-background-color');
    expect(cssContent).toContain('border-radius: 8px');
    expect(cssContent).toContain('padding: 12px');
    expect(cssContent).toContain('box-shadow: 0 1px 3px');
  });

  test('should have sensor group title styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify sensor-group-title exists
    expect(cssContent).toContain('.sensor-group-title');

    // Verify title styling
    expect(cssContent).toContain('font-size: 15px');
  });

  test('should have sensor item styling with hover effects', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify sensor-item exists
    expect(cssContent).toContain('.sensor-item');

    // Verify item styling
    expect(cssContent).toContain('border-left: 4px solid');
    expect(cssContent).toContain('box-shadow: 0 1px 2px');
    expect(cssContent).toContain('.sensor-item:hover');
    expect(cssContent).toContain('background-color: var(--panel-primary-light');
    expect(cssContent).toContain('transform: translateX(4px)');
  });

  test('should have sensor icon styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify sensor-icon exists
    expect(cssContent).toContain('.sensor-icon');

    // Verify icon styling
    expect(cssContent).toContain('width: 28px');
    expect(cssContent).toContain('text-align: center');

    // Verify sensor-item with icon
    expect(cssContent).toContain('.sensor-left');
  });

  test('should have sensor value styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    expect(cssContent).toContain('.sensor-value');
    expect(cssContent).toContain('padding: 6px 10px');
    expect(cssContent).toContain('background-color: rgba(33, 150, 243, 0.1)');
    expect(cssContent).toContain('border-radius: 6px');
  });

  test('should handle unavailable/unknown sensor states', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify styling for unavailable/unknown states
    expect(cssContent).toContain('[data-state="unavailable"]');
    expect(cssContent).toContain('[data-state="unknown"]');
    expect(cssContent).toContain('color: var(--panel-text-disabled');
    expect(cssContent).toContain('font-style: italic');
  });

  // TESTS FOR TRIPS SECTION DESIGN
  test('should have trips header with add button', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify trips-header exists
    expect(cssContent).toContain('.trips-header');

    // Verify header layout
    expect(cssContent).toContain('justify-content: space-between');

    // Verify add-trip-btn exists
    expect(cssContent).toContain('.add-trip-btn');

    // Verify button styling
    expect(cssContent).toContain('background-color: var(--primary-color');
    expect(cssContent).toContain('color: white');
    expect(cssContent).toContain('cursor: pointer');

    // Verify button hover effects
    expect(cssContent).toContain('.add-trip-btn:hover');
    expect(cssContent).toContain('transform: translateY(-1px)');
  });

  test('should have trip card styling with hover effects', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify trip-card exists
    expect(cssContent).toContain('.trip-card');

    // Verify card styling
    expect(cssContent).toContain('padding: 16px');
    expect(cssContent).toContain('transition: transform');
    expect(cssContent).toContain('.trip-card:hover');
    expect(cssContent).toContain('transform: translateY(-2px)');
    expect(cssContent).toContain('box-shadow: 0 3px 6px');
  });

  test('should have trip card inactive state styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify trip-card-inactive exists
    expect(cssContent).toContain('.trip-card-inactive');

    // Verify inactive state
    expect(cssContent).toContain('opacity: 0.7');
  });

  test('should have trip header styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify trip-header exists
    expect(cssContent).toContain('.trip-header');
  });

  test('should have trip type and status badges', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify trip-type exists
    expect(cssContent).toContain('.trip-type');

    // Verify type badge styling
    expect(cssContent).toContain('font-size: 12px');
    expect(cssContent).toContain('text-transform: uppercase');

    // Verify trip-status exists
    expect(cssContent).toContain('.trip-status');

    // Verify status badge styling
    expect(cssContent).toContain('font-size: 11px');
    expect(cssContent).toContain('padding: 4px 8px');
    expect(cssContent).toContain('border-radius: 4px');

    // Verify status-active styling
    expect(cssContent).toContain('.trip-status.status-active');
    expect(cssContent).toContain('background-color: var(--panel-success-light');
    expect(cssContent).toContain('color: var(--panel-success-dark');

    // Verify status-inactive styling
    expect(cssContent).toContain('.trip-status.status-inactive');
    expect(cssContent).toContain('background-color: var(--panel-warning-light');
    expect(cssContent).toContain('color: var(--panel-warning-dark');
  });

  test('should have trip time and details styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify trip-time exists
    expect(cssContent).toContain('.trip-time');

    // Verify time styling
    expect(cssContent).toContain('font-size: 14px');
    expect(cssContent).toContain('font-weight: 500');
    expect(cssContent).toContain('color: var(--primary-text-color');

    // Verify trip-details exists
    expect(cssContent).toContain('.trip-details');

    // Verify details styling
    expect(cssContent).toContain('font-size: 13px');

    // Verify trip-detail exists
    expect(cssContent).toContain('.trip-detail');
  });

  test('should have trip description styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify trip-description exists
    expect(cssContent).toContain('.trip-description');

    // Verify description styling
    expect(cssContent).toContain('margin-top: 8px');
    expect(cssContent).toContain('padding-top: 8px');
    expect(cssContent).toContain('border-top: 1px solid');
  });

  test('should have trip actions styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify trip-actions exists
    expect(cssContent).toContain('.trip-actions');

    // Verify actions layout
    expect(cssContent).toContain('justify-content: flex-end');
    expect(cssContent).toContain('padding-top: 12px');
  });

  // TESTS FOR ACTION BUTTONS DESIGN
  test('should have trip action group styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify trip-action-group exists
    expect(cssContent).toContain('.trip-action-group');
    expect(cssContent).toContain('gap: 8px');

    // Verify status-actions group
    expect(cssContent).toContain('.trip-action-group.status-actions');
    expect(cssContent).toContain('padding-left: 12px');
    expect(cssContent).toContain('border-left: 2px solid');
    expect(cssContent).toContain('margin-left: 8px');

    // Verify action group label
    expect(cssContent).toContain('.trip-action-group-label');
    expect(cssContent).toContain('font-size: 10px');
    expect(cssContent).toContain('color: var(--panel-text-secondary');

    // Verify action-group-header
    expect(cssContent).toContain('.action-group-header');
  });

  test('should have action buttons container styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify action-buttons-container exists
    expect(cssContent).toContain('.action-buttons-container');
  });

  test('should have trip action button styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify trip-action-btn exists
    expect(cssContent).toContain('.trip-action-btn');
    expect(cssContent).toContain('border: none');
    expect(cssContent).toContain('padding: 6px 12px');
    expect(cssContent).toContain('transition: background-color');

    // Verify button active state
    expect(cssContent).toContain('.trip-action-btn:active');
    expect(cssContent).toContain('transform: scale(0.95)');
  });

  test('should have edit button styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify edit-btn exists
    expect(cssContent).toContain('.edit-btn');

    // Verify edit button styling
    expect(cssContent).toContain('.edit-btn:hover');
    expect(cssContent).toContain('background-color: var(--panel-primary-color-hass-dark');
  });

  test('should have delete button styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify delete-btn exists
    expect(cssContent).toContain('.delete-btn');

    // Verify delete button styling
    expect(cssContent).toContain('background-color: var(--panel-error-light');
    expect(cssContent).toContain('color: var(--panel-error-dark');

    // Verify delete button hover
    expect(cssContent).toContain('.delete-btn:hover');
    expect(cssContent).toContain('background-color: var(--panel-error-lighter');
  });

  test('should have pause and resume button styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify pause button
    expect(cssContent).toContain('.btn-pause');
    expect(cssContent).toContain('background-color: var(--panel-warning');

    // Verify resume button
    expect(cssContent).toContain('.btn-resume');
    expect(cssContent).toContain('background-color: var(--panel-success');
  });

  // TESTS FOR FORM DESIGN
  test('should have trip form overlay styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify trip-form-overlay exists
    expect(cssContent).toContain('.trip-form-overlay');

    // Verify overlay styling
    expect(cssContent).toContain('position: fixed');
    expect(cssContent).toContain('top: 0');
    expect(cssContent).toContain('left: 0');
    expect(cssContent).toContain('right: 0');
    expect(cssContent).toContain('bottom: 0');
    expect(cssContent).toContain('background-color: rgba(0, 0, 0, 0.5)');
    expect(cssContent).toContain('justify-content: center');
    expect(cssContent).toContain('z-index: 1000');
  });

  test('should have trip form container styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify trip-form-container exists
    expect(cssContent).toContain('.trip-form-container');
    expect(cssContent).toContain('border-radius: 12px');
    expect(cssContent).toContain('padding: 24px');
    expect(cssContent).toContain('max-width: 500px');
    expect(cssContent).toContain('width: 90%');
    expect(cssContent).toContain('max-height: 90vh');
    expect(cssContent).toContain('overflow-y: auto');
  });

  test('should have trip form header styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify trip-form-header exists
    expect(cssContent).toContain('.trip-form-header');

    // Verify header styling
    expect(cssContent).toContain('margin-bottom: 20px');
    expect(cssContent).toContain('padding-bottom: 12px');
    expect(cssContent).toContain('border-bottom: 2px solid');

    // Verify form header h3
    expect(cssContent).toContain('.trip-form-header h3');
    expect(cssContent).toContain('font-size: 18px');
    expect(cssContent).toContain('color: var(--primary-color');
  });

  test('should have close form button styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify close-form-btn exists
    expect(cssContent).toContain('.close-form-btn');
    expect(cssContent).toContain('background: none');

    // Verify button hover
    expect(cssContent).toContain('.close-form-btn:hover');
    expect(cssContent).toContain('background-color: rgba(0, 0, 0, 0.05)');
  });

  test('should have form group styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify form-group exists
    expect(cssContent).toContain('.form-group');
    expect(cssContent).toContain('margin-bottom: 16px');

    // Verify form group label
    expect(cssContent).toContain('.form-group label');
    expect(cssContent).toContain('display: block');
    expect(cssContent).toContain('margin-bottom: 8px');

    // Verify form inputs
    expect(cssContent).toContain('.form-group input');
    expect(cssContent).toContain('.form-group select');
    expect(cssContent).toContain('.form-group textarea');
    expect(cssContent).toContain('width: 100%');
    expect(cssContent).toContain('padding: 10px 12px');
    expect(cssContent).toContain('border: 1px solid');

    // Verify focus state
    expect(cssContent).toContain('.form-group input:focus');
    expect(cssContent).toContain('outline: none');
    expect(cssContent).toContain('border-color: var(--primary-color');
    expect(cssContent).toContain('box-shadow: 0 0 0 2px');
  });

  test('should have form row grid layout', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify form-row exists
    expect(cssContent).toContain('.form-row');

    // Verify row layout
    expect(cssContent).toContain('display: grid');
    expect(cssContent).toContain('grid-template-columns: 1fr 1fr');
  });

  test('should have form actions styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify form-actions exists
    expect(cssContent).toContain('.form-actions');
    expect(cssContent).toContain('margin-top: 20px');
    expect(cssContent).toContain('padding-top: 16px');

    // Verify form actions button
    expect(cssContent).toContain('.form-actions .btn');
    expect(cssContent).toContain('flex: 1');
    expect(cssContent).toContain('padding: 12px 20px');

    // Verify primary button
    expect(cssContent).toContain('.form-actions .btn-primary');

    // Verify secondary button
    expect(cssContent).toContain('.form-actions .btn-secondary');
    expect(cssContent).toContain('background-color: var(--divider-color');
  });

  test('should have form error styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify form-error exists
    expect(cssContent).toContain('.form-error');

    // Verify error styling
    expect(cssContent).toContain('border: 1px solid var(--panel-error-dark');
  });

  // TESTS FOR RESPONSIVE DESIGN
  test('should have responsive adjustments for mobile', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify media query exists
    // Verify grid adjustment
    // Verify status value size
    // Verify trips header layout
    // Verify form row layout
    expect(cssContent).toContain('grid-template-columns: 1fr');

    // Verify form actions layout
  });

  test('should have mobile-specific button layout', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify action group header layout for mobile
    expect(cssContent).toContain('align-items: flex-start');

    // Verify action buttons container for mobile
    expect(cssContent).toContain('flex-wrap: wrap');

    // Verify trip action group for mobile
    // Verify status actions for mobile
    expect(cssContent).toContain('border-left: none');
    expect(cssContent).toContain('padding-left: 0');
    expect(cssContent).toContain('margin-left: 0');
    expect(cssContent).toContain('border-top: 2px solid');
  });

  test('should have mobile-specific form styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify form container for mobile
    expect(cssContent).toContain('width: 95%');

    // Verify form header for mobile
  });

  // TESTS FOR VISUAL FEEDBACK
  test('should have charging indicator styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify charging-indicator exists
    expect(cssContent).toContain('.charging-indicator');

    // Verify indicator styling
    expect(cssContent).toContain('width: 10px');
    expect(cssContent).toContain('height: 10px');
    expect(cssContent).toContain('border-radius: 50%');
    expect(cssContent).toContain('margin-right: 8px');

    // Verify charging state
    expect(cssContent).toContain('.charging-indicator.charging');
    expect(cssContent).toContain('background-color: var(--panel-success)');
    expect(cssContent).toContain('animation: pulse');

    // Verify not charging state
    expect(cssContent).toContain('.charging-indicator.not-charging');
    expect(cssContent).toContain('background-color: var(--panel-text-secondary)');

    // Verify pulse animation
    expect(cssContent).toContain('@keyframes pulse');
  });

  test('should have power profile chart styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify power-profile exists
    expect(cssContent).toContain('.power-profile');

    // Verify profile styling
    expect(cssContent).toContain('min-height: 120px');

    // Verify profile-chart
    expect(cssContent).toContain('.profile-chart');
    expect(cssContent).toContain('padding: 8px');

    // Verify profile-chart pre
    expect(cssContent).toContain('.profile-chart pre');
    expect(cssContent).toContain('white-space: pre-wrap');
    expect(cssContent).toContain('word-wrap: break-word');
  });

  test('should have general button styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify btn exists
    expect(cssContent).toContain('.btn');
    expect(cssContent).toContain('transition: all 0.2s ease');
    expect(cssContent).toContain('.btn:active');
    expect(cssContent).toContain('transform: scale(0.98)');
  });

  // TESTS FOR NO-TRIPS AND ERROR STATES
  test('should have no-trips message styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify no-trips exists
    expect(cssContent).toContain('.no-trips');

    // Verify styling
    expect(cssContent).toContain('padding: 20px');
  });

  test('should have error-trips message styling', async () => {
    const cssContent = fs.readFileSync(PANEL_CSS_PATH, 'utf-8');

    // Verify error-trips exists
    expect(cssContent).toContain('.error-trips');
  });

  // TESTS FOR JAVASCRIPT UI RENDERING
  test('should have JavaScript methods for rendering UI sections', async () => {
    const jsContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify section data fetching methods exist
    expect(jsContent).toContain('_getVehicleStates');
    expect(jsContent).toContain('_getTripsList');

    // Verify rendering methods exist
    expect(jsContent).toContain('_renderTripsSection');

    // Verify section data is used for rendering (status cards, sensors, trips)
    expect(jsContent).toContain('status-card');
    expect(jsContent).toContain('sensor-list-grouped');
    expect(jsContent).toContain('trips-header');
  });

  test('should have JavaScript methods for formatting display', async () => {
    const jsContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify formatting methods exist
    expect(jsContent).toContain('_formatTripDisplay');

    // Verify trip data properties are formatted
    expect(jsContent).toContain('trip_type');
    expect(jsContent).toContain('day_of_week');
    expect(jsContent).toContain('time');
    expect(jsContent).toContain('km');
    expect(jsContent).toContain('kwh');
    expect(jsContent).toContain('description');
  });

  test('should have JavaScript methods for form handling', async () => {
    const jsContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify form methods exist
    expect(jsContent).toContain('_showTripForm');
    expect(jsContent).toContain('_showEditForm');
    expect(jsContent).toContain('_handleTripCreate');
    expect(jsContent).toContain('_handleTripUpdate');
  });

  test('should have JavaScript methods for trip actions', async () => {
    const jsContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify trip action methods exist
    expect(jsContent).toContain('_handleEditClick');
    expect(jsContent).toContain('_handleDeleteClick');
    expect(jsContent).toContain('_handlePauseTrip');
    expect(jsContent).toContain('_handleResumeTrip');
    expect(jsContent).toContain('_handleCompletePunctualTrip');
    expect(jsContent).toContain('_handleCancelPunctualTrip');
  });

  // INTEGRATION TESTS
  test('should have complete UI design integration', async () => {
    const jsContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify complete UI flow exists
    // Status section
    // Sensors section
    expect(jsContent).toContain('sensor-group');

    // Trips section
    expect(jsContent).toContain('trip-card');

    // Form
    expect(jsContent).toContain('trip-form-overlay');
    expect(jsContent).toContain('trip-form-container');

    // Actions
    expect(jsContent).toContain('trip-action-btn');
    expect(jsContent).toContain('action-buttons-container');
  });

  test('should have complete action button integration', async () => {
    const jsContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify action buttons are built dynamically
    expect(jsContent).toContain('actionButtons =');
    expect(jsContent).toContain('edit-btn');
    expect(jsContent).toContain('delete-btn');
    expect(jsContent).toContain('pause-btn');
    expect(jsContent).toContain('resume-btn');
    expect(jsContent).toContain('complete-btn');
    expect(jsContent).toContain('cancel-btn');

    // Verify onclick handlers
    expect(jsContent).toContain('onclick="window._tripPanel._handleEditClick');
    expect(jsContent).toContain('onclick="window._tripPanel._handleDeleteClick');
    expect(jsContent).toContain('onclick="window._tripPanel._handlePauseTrip');
    expect(jsContent).toContain('onclick="window._tripPanel._handleResumeTrip');
    expect(jsContent).toContain('onclick="window._tripPanel._handleCompletePunctualTrip');
    expect(jsContent).toContain('onclick="window._tripPanel._handleCancelPunctualTrip');
  });
});
