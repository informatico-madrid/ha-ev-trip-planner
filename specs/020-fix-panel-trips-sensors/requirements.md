# Requirements: Fix Panel Trips Sensors

## Goal
Fix the EV Trip Planner native panel bugs so vehicle sensors display actual values, trips load correctly, and trip management actions (add, edit, delete) work properly.

## User Stories

### US-1: Vehicle ID Extraction from Panel URLs
**As a** panel user
**I want** the vehicle ID to be correctly extracted from any panel URL format
**So that** the panel displays data for the correct vehicle

**Acceptance Criteria:**
- [ ] AC-1.1: Vehicle ID extracted from URL pattern `/ev-trip-planner-{vehicle_id}`
- [ ] AC-1.2: Vehicle ID extracted from URL pattern `/panel/ev-trip-planner-{vehicle_id}`
- [ ] AC-1.3: Vehicle ID extracted from URL hash when pathname differs
- [ ] AC-1.4: Multiple extraction methods work as fallback (split, regex, hash)
- [ ] AC-1.5: Debug logs show extraction method used for troubleshooting

### US-2: Trip List Service Response Handling
**As a** panel user
**I want** trips to load correctly regardless of Home Assistant version
**So that** I can see all my scheduled trips

**Acceptance Criteria:**
- [ ] AC-2.1: Trip list service handles direct result response format
- [ ] AC-2.2: Trip list service handles array response format `[result]`
- [ ] AC-2.3: Trip list service handles object response format `{result: ...}`
- [ ] AC-2.4: Recurring trips and punctual trips are combined in display
- [ ] AC-2.5: Error handling shows message when service call fails
- [ ] AC-2.6: Debug logs capture response format for troubleshooting

### US-3: Sensor Value Display
**As a** panel user
**I want** sensor values to display with proper formatting and units
**So that** I can understand my vehicle's status at a glance

**Acceptance Criteria:**
- [ ] AC-3.1: Sensor values show "N/A" for unavailable/unknown states
- [ ] AC-3.2: Numerical values formatted with appropriate decimal places (percentages: 1 decimal, kWh: 2 decimals, km: 1 decimal)
- [ ] AC-3.3: Boolean values display as "✓ Activo" or "✗ Inactivo"
- [ ] AC-3.4: Unit of measurement displayed with value (e.g., "85.2%", "42.5 km")
- [ ] AC-3.5: Entity IDs shown on hover for debugging
- [ ] AC-3.6: Sensors grouped by category (Status, Battery, Trips, Energy, Charging, Other)
- [ ] AC-3.7: Sensor values update in real-time via state subscription

### US-4: Trip Management Functionality
**As a** vehicle owner
**I want** to create, edit, and delete trips from the panel
**So that** I can manage my scheduled routes

**Acceptance Criteria:**
- [ ] AC-4.1: Add trip button opens trip creation form
- [ ] AC-4.2: Trip creation form validates required fields (type, time)
- [ ] AC-4.3: Trip creation calls `ev_trip_planner.trip_create` service
- [ ] AC-4.4: Trip list refreshes after successful creation
- [ ] AC-4.5: Edit form pre-populates with existing trip data
- [ ] AC-4.6: Trip update calls `ev_trip_planner.trip_update` service
- [ ] AC-4.7: Delete confirmation prevents accidental deletion
- [ ] AC-4.8: Trip deletion removes card from UI and refreshes list
- [ ] AC-4.9: Pause/Resume actions work for recurring trips
- [ ] AC-4.10: Complete/Cancel actions work for punctual trips

### US-5: Panel Rendering Reliability
**As a** panel user
**I want** the panel to render completely before interactions
**So that** all buttons and functionality are available immediately

**Acceptance Criteria:**
- [ ] AC-5.1: Polling stops immediately when panel begins rendering
- [ ] AC-5.2: Panel HTML written to DOM before attaching event handlers
- [ ] AC-5.3: `window._tripPanel` reference set after rendering completes
- [ ] AC-5.4: _rendered flag set only after trips section loads
- [ ] AC-5.5: No race conditions between polling and rendering
- [ ] AC-5.6: Early exit from connectedCallback if already fully rendered

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Vehicle ID Extraction | High | Extract from 3 URL patterns (split, regex, hash) with logging |
| FR-2 | Trip List Service Call | High | Handle 3 response formats (direct, array, object) |
| FR-3 | Trip Display | High | Combine recurring and punctual trips with proper formatting |
| FR-4 | Sensor Filtering | Medium | Show "N/A" for unavailable sensors, filter only truly invalid |
| FR-5 | Sensor Value Formatting | Medium | Apply appropriate decimal places based on value type and unit |
| FR-6 | Sensor Real-Time Updates | Medium | Subscribe to state changes and update values without re-render |
| FR-7 | Trip Form UI | High | Create/edit forms with all required fields and validation |
| FR-8 | Service Integration | High | Connect all action buttons to ev_trip_planner services |
| FR-9 | Panel Rendering Control | High | Prevent re-rendering and polling race conditions |
| FR-10 | Debug Logging | Low | Log extraction methods, response formats, and errors |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Panel Load Time | Time from open to fully rendered | < 3 seconds |
| NFR-2 | Sensor Update Latency | Time from state change to UI update | < 1 second |
| NFR-3 | Error Handling | No crashes on service failures | Graceful degradation with error messages |
| NFR-4 | Browser Compatibility | Supported browsers | Chrome, Firefox, Safari, Edge (latest 2 versions) |
| NFR-5 | HA Version Compatibility | Home Assistant versions | 2024.x and 2025.x |
| NFR-6 | Memory Usage | Memory impact of panel component | < 50MB additional memory |

## Glossary

- **Vehicle ID**: The unique identifier for a vehicle entity in Home Assistant (e.g., `my-car`, `tesla-model-3`)
- **Recurring Trip**: A trip that repeats weekly on the same day and time
- **Punctual Trip**: A one-time trip on a specific date and time
- **Trip List Service**: The `ev_trip_planner.trip_list` service that returns all trips for a vehicle
- **State Subscription**: Home Assistant event subscription that notifies when entity states change
- **_rendered Flag**: Internal flag tracking whether panel has completed rendering to prevent race conditions

## Out of Scope

- Adding new sensor types beyond existing vehicle sensors
- Creating new trip types beyond recurring and punctual
- Modifying the underlying EV Trip Planner integration logic
- Changing the CSS styling (only fixing asset loading path)
- Adding user authentication or multi-user support
- Creating trip history or analytics
- Syncing trips with external calendars or services

## Dependencies

- EV Trip Planner integration installed and configured
- Vehicle entities created in Home Assistant
- Trip list service `ev_trip_planner.trip_list` implemented
- Trip create service `ev_trip_planner.trip_create` implemented
- Trip update service `ev_trip_planner.trip_update` implemented
- Trip delete service `ev_trip_planner.delete_trip` implemented
- Trip pause/resume services implemented for recurring trips
- Trip complete/cancel services implemented for punctual trips
- Home Assistant panel_custom component (built-in)

## Success Criteria

- [ ] Panel loads without errors for all tested vehicle configurations
- [ ] Vehicle ID correctly extracted from all panel URL patterns
- [ ] All trips (recurring and punctual) display in the panel
- [ ] Trip creation, edit, and delete operations complete successfully
- [ ] Sensor values display with proper formatting and units
- [ ] Unavailable sensors show "N/A" instead of being hidden
- [ ] Sensor values update in real-time without page refresh
- [ ] No console errors or warnings in browser developer tools
- [ ] Panel renders within 3 seconds on typical hardware

## Unresolved Questions

- What is the exact URL format used by Home Assistant's panel_custom? (`/panel/ev-trip-planner-{id}` vs `/ev-trip-planner-{id}`)
- What response formats does `ev_trip_planner.trip_list` return in different HA versions?
- Should "N/A" sensors be hidden entirely or displayed in a separate section?
- What is the expected behavior if a vehicle has no configured sensors?

## Next Steps

1. Fix vehicle ID extraction to handle `/panel/` prefix by using more robust URL parsing
2. Fix trip list service to handle all response formats with proper type checking
3. Change sensor filtering logic to show "N/A" for unavailable states instead of filtering
4. Verify trip management button handlers work after panel renders
5. Test changes in Home Assistant with debug logging enabled
6. Remove debug logging once fixes are verified

---

## Learnings

- Previous learnings...
- Vehicle ID extraction requires handling multiple URL patterns (with and without `/panel/` prefix)
- Service response formats vary between Home Assistant versions (direct, array, or object-wrapped)
- Sensor value formatting rules should be consistent: percentages (1 dec), energy (2 dec), distance (1 dec)
- Polling for hass and rendering must coordinate to avoid race conditions
- `_rendered` flag should only be set after trips section fully loads, not just initial HTML
- Event handlers need `window._tripPanel` reference set before user interactions
- State subscription pattern requires lowercase entity ID matching for sensor updates
