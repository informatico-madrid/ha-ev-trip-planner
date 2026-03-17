# Clarification Questions for Milestone 3.2

**Purpose**: Identify ambiguities and gaps in the specification based on Home Assistant best practices

## Question 1: Entity Naming Conventions

**Context**: The specification mentions entities like `sensor.emhass_deferrable_load_config_{index}` but doesn't specify the naming pattern for vehicle-specific entities.

**Question**: What should be the naming convention for vehicle-specific sensors and switches?

**Options**:
| Option | Description | Recommendation |
|--------|-------------|----------------|
| A | `{vehicle_name}_{sensor_type}` (e.g., `my_car_presence_status`) | **Recommended** - Human-readable, follows HA conventions |
| B | `{vehicle_id}_{sensor_type}` (e.g., `vehicle_1_presence_status`) | Less user-friendly |
| C | `{unique_id}_{sensor_type}` (e.g., `abc123_presence_status`) | Not discoverable by users |
| D | Custom pattern per vehicle | Inconsistent, hard to maintain |

**Suggested**: Option A - Use vehicle name for human-readable entity IDs. This follows Home Assistant best practices and makes entities discoverable in the UI.

---

## Question 2: Presence Detection Implementation

**Context**: The specification mentions "presence detection" but doesn't specify the implementation approach.

**Question**: How should presence detection be implemented for home/plugged status?

**Options**:
| Option | Description | Recommendation |
|--------|-------------|----------------|
| A | Use binary_sensor entities (home sensor, plugged sensor) | **Recommended** - Native HA construct, follows best practices |
| B | Use device_tracker entities | More complex, requires location tracking |
| C | Use coordinate-based calculation | Overkill for simple home/away detection |
| D | Use template sensor combining multiple sources | Unnecessary complexity |

**Suggested**: Option A - Use binary_sensor entities for home and plugged status. This follows the Home Assistant best practice of using native constructs instead of templates.

---

## Question 3: Notification Service Configuration

**Context**: The specification mentions `persistent_notification.create` as the default notification service.

**Question**: Should the notification service be configurable per vehicle or global?

**Options**:
| Option | Description | Recommendation |
|--------|-------------|----------------|
| A | Configurable per vehicle in config flow | **Recommended** - Allows different notification strategies per vehicle |
| B | Global setting in integration config | Less flexible |
| C | Hardcoded to `persistent_notification.create` | Too restrictive |
| D | Allow user to select any service | Too complex for initial version |

**Suggested**: Option A - Make it configurable per vehicle. This allows users to have different notification strategies (e.g., email for one vehicle, push notifications for another).

---

## Question 4: EMHASS Configuration Snippet

**Context**: The specification mentions showing a configuration snippet for users to copy into EMHASS config.

**Question**: What level of detail should the configuration snippet include?

**Options**:
| Option | Description | Recommendation |
|--------|-------------|----------------|
| A | Complete YAML snippet with all required fields | **Recommended** - Users can copy-paste directly |
| B | Just the structure, users fill in values | Requires more user effort |
| C | Dynamic snippet generation based on user config | Complex, error-prone |
| D | Link to EMHASS documentation | Not actionable |

**Suggested**: Option A - Provide a complete, copy-paste ready YAML snippet. This reduces user error and follows the principle of making things easy for users.

---

## Question 5: Vehicle Control Strategy Factory

**Context**: The specification mentions supporting different control strategies (switch, service, script).

**Question**: Should the control strategy be selected during initial vehicle setup or can it be changed later?

**Options**:
| Option | Description | Recommendation |
|--------|-------------|----------------|
| A | Selected once during setup, immutable | **Recommended** - Simpler, less error-prone |
| B | Configurable in options flow, changeable anytime | More flexible but complex |
| C | Auto-detected from available entities | Too magical, may fail |
| D | Multiple strategies per vehicle | Overkill for most use cases |

**Suggested**: Option A - Select strategy once during setup. This keeps the configuration simple and prevents accidental changes that could break charging control.

---

## Question 6: Max Deferrable Loads Validation

**Context**: The specification mentions `CONF_MAX_DEFERRABLE_LOADS` with a default of 50.

**Question**: Should the max deferrable loads be validated against actual EMHASS capacity or user input?

**Options**:
| Option | Description | Recommendation |
|--------|-------------|----------------|
| A | Validate against EMHASS configuration (read from config) | **Recommended** - Ensures consistency |
| B | Accept any user input (1-100) | Simple but may exceed EMHASS capacity |
| C | Auto-detect from EMHASS integration | Too complex, may fail |
| D | Hardcoded to 50 | Too restrictive |

**Suggested**: Option A - Validate against EMHASS configuration. This ensures the configured max doesn't exceed what EMHASS can actually handle.

---

## Question 7: Trip Expansion Horizon

**Context**: The specification mentions `CONF_PLANNING_HORIZON` with a default of 7 days.

**Question**: Should the planning horizon be validated against the EMHASS planning horizon?

**Options**:
| Option | Description | Recommendation |
|--------|-------------|----------------|
| A | User sets horizon, system validates against EMHASS sensor | **Recommended** - Ensures consistency |
| B | User sets horizon, no validation | Simple but may cause issues |
| C | Auto-detect from EMHASS | Too magical |
| D | Fixed to 7 days | Too restrictive |

**Suggested**: Option A - Allow user to set horizon but validate against EMHASS planning sensor if available. This gives flexibility while ensuring consistency.

---

## Summary

**Total Questions**: 7  
**Critical Questions**: 4 (Questions 1, 2, 4, 6)  
**Recommended Answers**: All 7 questions have clear recommendations based on Home Assistant best practices

**Next Steps**:
1. Answer these questions to finalize the specification
2. Update spec.md with clarified requirements
3. Proceed to `/speckit.plan` for implementation planning
