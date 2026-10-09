import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { createContext, SourceTextModule, SyntheticModule } from 'node:vm';

// Exercise the actual panel module without a browser or a Home Assistant server.
const context = createContext({
  console, Intl, Date, Map, setTimeout, clearTimeout,
  customElements: { get: () => undefined, define: () => {} },
});
const lit = new SyntheticModule(['LitElement', 'html', 'css'], function () {
  this.setExport('LitElement', class {});
  this.setExport('html', (strings, ...values) => ({ strings, values }));
  this.setExport('css', (strings) => strings.join(''));
}, { context });
const source = await readFile(new URL('../custom_components/ev_trip_planner/frontend/panel.js', import.meta.url), 'utf8');
const module = new SourceTextModule(source, { context });
await module.link(() => lit);
await module.evaluate();
const { buildChargingPlan, findPlanningSensor, tripDayName, isTripActive, EVTripPlannerPanel } = module.namespace;
const plain = value => JSON.parse(JSON.stringify(value));

test('the registered resource version matches the frontend version shipped with it', async () => {
  const backend = await readFile(new URL('../custom_components/ev_trip_planner/panel.py', import.meta.url), 'utf8');
  const frontendVersion = source.match(/const VERSION = '([^']+)'/)?.[1];
  const registeredVersion = backend.match(/PANEL_FRONTEND_VERSION = "([^"]+)"/)?.[1];
  assert.ok(frontendVersion);
  assert.equal(registeredVersion, frontendVersion,
    'A frontend release must update its registered resource URL so existing clients fetch the new module');
});

function sensor(attributes, state = 'ready') {
  return { entity_id: 'sensor.test_emhass_perfil_diferible_car', state, attributes };
}

test('plots the published profile, without summing overlapping loads', () => {
  const plan = buildChargingPlan(sensor({
    power_profile_watts: [0, 3400, 3400, 0],
    p_deferrable_matrix: [[0, 3400, 0, 0], [0, 3400, 3400, 0]],
    def_total_hours_array: [1, 2], p_deferrable_nom_array: [3400, 3400],
    def_start_timestep_array: [0, 0], def_end_timestep_array: [2, 3],
    number_of_deferrable_loads: 2,
  }));
  assert.equal(plan.energyKwh, 6.8);
  assert.equal(plan.chargingHours, 2);
  assert.equal(plan.peakKw, 3.4);
  assert.deepEqual(plain(plan.profile), [0, 3400, 3400, 0]);
});

test('availability and actual non-zero matrix slots remain distinct', () => {
  const plan = buildChargingPlan(sensor({
    power_profile_watts: [0, 0, 3400, 3400],
    p_deferrable_matrix: [[0, 0, 3400, 3400]],
    def_total_hours_array: [2], p_deferrable_nom_array: [3400],
    def_start_timestep_array: [0], def_end_timestep_array: [4],
  }));
  assert.equal(plan.loads[0].start, 0);
  assert.equal(plan.loads[0].end, 4);
  assert.deepEqual(plain(plan.loads[0].segments), [{ start: 2, end: 4, watts: 3400 }]);
});

test('the precise departure remains 12:35 while the last whole slot ends at 12:00', () => {
  const plan = buildChargingPlan(sensor({
    power_profile_watts: [0, 3400, 3400, 0], p_deferrable_matrix: [[0, 3400, 3400, 0]],
    def_total_hours_array: [2], p_deferrable_nom_array: [3400],
    def_start_timestep_array: [0], def_end_timestep_array: [3],
    planning_reference: '2026-10-09T07:00:00+00:00',
    deadline_array: ['2026-10-09T10:35:00+00:00'],
    window_start_array: ['2026-10-09T06:31:00+00:00'],
  }));
  const panel = new EVTripPlannerPanel();
  panel._hass = { config: { time_zone: 'Europe/Madrid' } };
  panel._plan = plan;
  assert.equal(plan.loads[0].end, 3);
  assert.ok(plan.loads[0].departureSlot > 3 && plan.loads[0].departureSlot < 4);
  assert.equal(panel._slotTime(3), '12:00');
  assert.equal(panel._slotTime(plan.loads[0].departureSlot), '12:35');
  assert.deepEqual(plain(plan.loads[0].segments), [{ start: 1, end: 3, watts: 3400 }]);
});

test('insufficient full-slot capacity is visible instead of implying completed charging', () => {
  const plan = buildChargingPlan(sensor({
    power_profile_watts: [0], p_deferrable_matrix: [[0]],
    def_total_hours_array: [0], p_deferrable_nom_array: [0],
    def_start_timestep_array: [0], def_end_timestep_array: [0],
    unserved_energy_kwh_array: [3.4],
  }));
  assert.equal(plan.energyKwh, 0);
  assert.ok(plan.warnings.some(warning => warning.includes('3,4 kWh')));
});

test('matches schedule indices by window, never by insertion order', () => {
  const plan = buildChargingPlan(sensor({
    power_profile_watts: [3400, 0, 3400, 0],
    p_deferrable_matrix: [[3400, 0, 0, 0], [0, 0, 3400, 0]],
    def_total_hours_array: [1, 1], p_deferrable_nom_array: [3400, 3400],
    def_start_timestep_array: [0, 2], def_end_timestep_array: [1, 3],
    deferrables_schedule: [
      { index: 9, start_timestep: 2, end_timestep: 3 },
      { index: 4, start_timestep: 0, end_timestep: 1 },
    ],
  }));
  assert.deepEqual(plain(plan.loads.map(load => load.emhassIndex)), [4, 9]);
});

test('does not guess an EMHASS index when windows are ambiguous', () => {
  const plan = buildChargingPlan(sensor({
    power_profile_watts: [3400], p_deferrable_matrix: [[3400]],
    def_start_timestep_array: [0], def_end_timestep_array: [1],
    deferrables_schedule: [
      { index: 3, start_timestep: 0, end_timestep: 1 },
      { index: 4, start_timestep: 0, end_timestep: 1 },
    ],
  }));
  assert.equal(plan.loads[0].emhassIndex, null);
});

test('missing/unavailable sensors do not invent zero-energy plans', () => {
  for (const input of [null, sensor({}, 'unavailable'), sensor({}, 'error')]) {
    const plan = buildChargingPlan(input);
    assert.equal(plan.available, false);
    assert.equal(plan.energyKwh, null);
  }
});

test('a genuine empty plan has zero load, rather than an invented seven-day horizon', () => {
  const plan = buildChargingPlan(sensor({
    number_of_deferrable_loads: 0, power_profile_watts: [], deferrables_schedule: [],
  }));
  assert.equal(plan.available, true);
  assert.equal(plan.energyKwh, 0);
  assert.equal(plan.horizon, 0);
  assert.equal(plan.loads.length, 0);
});

test('an empty profile with pending loads is not presented as a zero-energy plan', () => {
  const plan = buildChargingPlan(sensor({ number_of_deferrable_loads: 3, power_profile_watts: [] }));
  assert.equal(plan.available, false);
  assert.equal(plan.energyKwh, null);
});

test('malformed arrays are flagged and cannot render NaN or fabricated windows', () => {
  const plan = buildChargingPlan(sensor({
    power_profile_watts: [0, 3400], p_deferrable_matrix: [[0, 3400]],
    def_start_timestep_array: [], def_end_timestep_array: [null],
  }));
  assert.equal(plan.loads[0].start, null);
  assert.equal(plan.loads[0].end, null);
  assert.ok(plan.warnings.length > 0);
  assert.equal(plan.energyKwh, 3.4);
});

test('invalid power data is not silently converted into a valid charging plan', () => {
  const plan = buildChargingPlan(sensor({ power_profile_watts: [0, 'not a number', -10] }));
  assert.equal(plan.available, false);
  assert.equal(plan.energyKwh, null);
});

test('uses the actual profile length instead of assuming 168 slots', () => {
  const plan = buildChargingPlan(sensor({ power_profile_watts: [0, 1000, 1000] }));
  assert.equal(plan.horizon, 3);
  assert.equal(plan.energyKwh, 2);
});

test('finds only the current vehicle sensor, even when entity IDs have been renamed', () => {
  const wrong = sensor({ vehicle_id: 'another_car', power_profile_watts: [9000] });
  const right = sensor({ vehicle_id: 'car', power_profile_watts: [3400] });
  const states = { 'sensor.other_emhass_perfil_diferible_a': wrong, 'sensor.renamed_emhass_perfil_diferible_b': right };
  assert.equal(findPlanningSensor(states, 'car'), right);
  assert.equal(findPlanningSensor(new Map(Object.entries(states)), 'car'), right);
  assert.equal(findPlanningSensor(states, 'missing'), null);
});

test('Spanish day labels accept numeric strings, integers, and names, including Sunday zero', () => {
  assert.equal(tripDayName({ dia_semana: '5' }), 'Viernes');
  assert.equal(tripDayName({ dia_semana: 0 }), 'Domingo');
  assert.equal(tripDayName({ day_of_week: 3 }), 'Miércoles');
  assert.equal(tripDayName({ dia_semana: 'MIERCOLES' }), 'Miércoles');
  assert.equal(tripDayName({ dia_semana: 'bogus' }), 'Día sin definir');
});

test('a paused trip remains paused when the other legacy flag is absent', () => {
  assert.equal(isTripActive({ activo: false }), false);
  assert.equal(isTripActive({ active: false }), false);
  assert.equal(isTripActive({ activo: true }), true);
  assert.equal(isTripActive({}), true);
});

test('renders absolute appointment times in Home Assistant timezone, not browser timezone', () => {
  const panel = new EVTripPlannerPanel();
  panel._hass = { config: { time_zone: 'Europe/Madrid' } };
  assert.equal(panel._dateInputValue('2026-10-09T10:30:00Z'), '2026-10-09T12:30');
  assert.equal(panel._dateInputValue('2026-10-09T12:30'), '2026-10-09T12:30');
  assert.equal(panel._dateInputValue('2026-12-09T10:30:00Z'), '2026-12-09T11:30');
});

test('uses pushed trip state without repeatedly querying services on unrelated updates', async () => {
  const panel = new EVTripPlannerPanel();
  panel._vehicleId = 'car';
  const tripState = { attributes: {
    recurring_trips: [{ id: 'paused', activo: false, dia_semana: '0', hora: '10:00' }],
    punctual_trips: [],
  } };
  panel._hass = {
    states: { 'sensor.trip_planner_car_ev_trip_planner_trips_list': tripState },
    callService: () => { throw new Error('An unrelated update must not invoke a service'); },
  };
  await panel._loadTrips();
  const snapshot = panel._trips;
  await panel._loadTrips();
  assert.equal(panel._trips, snapshot);
  assert.equal(panel._trips.length, 1);
  assert.equal(isTripActive(panel._trips[0]), false);
  assert.equal(panel._isLoading, false);
});

test('rejects another vehicle trip source even with a similar name', async () => {
  const panel = new EVTripPlannerPanel();
  panel._vehicleId = 'car';
  panel._hass = { states: {
    'sensor.trip_planner_car2_ev_trip_planner_trips_list': { attributes: { recurring_trips: [{ id: 'other' }] } },
    'sensor.trip_planner_car_backup_ev_trip_planner_trips_list': { attributes: { recurring_trips: [{ id: 'also_other' }] } },
  } };
  assert.equal(panel._scopedState('_ev_trip_planner_trips_list'), null);
});

test('explicit vehicle metadata takes precedence over an old entity name', () => {
  const panel = new EVTripPlannerPanel();
  panel._vehicleId = 'car';
  panel._hass = { states: {
    'sensor.trip_planner_car_ev_trip_planner_trips_list': { attributes: { vehicle_id: 'another_car', recurring_trips: [] } },
  } };
  assert.equal(panel._scopedState('_ev_trip_planner_trips_list'), null);
});

test('switching vehicle clears the previous vehicle summary and trip cards', () => {
  const panel = new EVTripPlannerPanel();
  panel._vehicleId = 'car';
  panel._trips = [{ id: 'old' }];
  panel._showForm = true;
  panel._editingTrip = { id: 'old' };
  panel._plan = buildChargingPlan(sensor({ power_profile_watts: [3400] }));
  panel.panel = { config: { vehicle_id: 'other_car' } };
  assert.equal(panel._vehicleId, 'other_car');
  assert.equal(panel._trips.length, 0);
  assert.equal(panel._showForm, false);
  assert.equal(panel._editingTrip, null);
  assert.equal(panel._plan.available, false);
  assert.equal(panel._isLoading, true);
});

test('an old in-flight trip response cannot overwrite the newly selected vehicle', async () => {
  const panel = new EVTripPlannerPanel();
  panel._vehicleId = 'car';
  let finish;
  panel._hass = {};
  panel._getTripsList = () => new Promise(resolve => { finish = resolve; });
  const loading = panel._loadTrips();
  panel.panel = { config: { vehicle_id: 'other_car' } };
  finish([{ id: 'old_vehicle_trip' }]);
  await loading;
  assert.equal(panel._trips.length, 0);
  assert.equal(panel._isLoading, true);
});

context.FormData = class {
  constructor(form) { this.values = form.values; }
  get(name) { return this.values[name] ?? null; }
};

test('the weekly form retains the service contract and accepts Sunday zero', async () => {
  const panel = new EVTripPlannerPanel();
  panel._vehicleId = 'car';
  const calls = [];
  panel._hass = { callService: async (...args) => {
    calls.push(args);
    return { response: { recurring_trips: [], punctual_trips: [] } };
  } };
  panel._closeForm = () => {};
  await panel._handleTripSave({ preventDefault() {}, target: { values: {
    type: 'recurrente', day: '0', time: '07:30', km: '15', kwh: '', description: 'Trabajo',
  } } });
  assert.deepEqual(plain(calls[0]), ['ev_trip_planner', 'trip_create', {
    vehicle_id: 'car', type: 'recurrente', dia_semana: '0', hora: '07:30', km: 15, description: 'Trabajo',
  }]);
  assert.equal(panel._busy, false);
  assert.equal(panel._error, '');
});

test('a punctual edit does not send hidden weekday/time fields', async () => {
  const panel = new EVTripPlannerPanel();
  panel._vehicleId = 'car';
  panel._editingTrip = { id: 'appointment' };
  const calls = [];
  panel._hass = { callService: async (...args) => {
    calls.push(args);
    return { response: { recurring_trips: [], punctual_trips: [] } };
  } };
  panel._closeForm = () => {};
  await panel._handleTripSave({ preventDefault() {}, target: { values: {
    type: 'puntual', datetime: '2026-11-01T10:00', day: '1', time: '08:00', km: '100', kwh: '12', description: '',
  } } });
  assert.deepEqual(plain(calls[0]), ['ev_trip_planner', 'trip_update', {
    vehicle_id: 'car', type: 'puntual', trip_id: 'appointment', datetime: '2026-11-01T10:00', km: 100, kwh: 12, description: '',
  }]);
});

test('failed saves keep the form open and release its busy state', async () => {
  const panel = new EVTripPlannerPanel();
  panel._vehicleId = 'car';
  panel._showForm = true;
  panel._hass = { callService: async () => { throw new Error('offline'); } };
  await panel._handleTripSave({ preventDefault() {}, target: { values: {
    type: 'recurrente', day: '1', time: '08:00', km: '30', kwh: '5', description: '',
  } } });
  assert.equal(panel._showForm, true);
  assert.equal(panel._busy, false);
  assert.match(panel._error, /offline/);
});
