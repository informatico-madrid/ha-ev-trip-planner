/** Native Home Assistant charging-planning panel. */
import { LitElement, html, css } from '/ev-trip-planner/lit-bundle.js';

const VERSION = '4.0.0';
const DAYS = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
const NUMBER = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 2 });
const normalize = value => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const entries = states => states instanceof Map ? [...states.entries()] : Object.entries(states || {});
const number = value => !['number', 'string'].includes(typeof value) || String(value).trim() === ''
  ? null : Number.isFinite(Number(value)) ? Number(value) : null;
const fmt = value => value === null || value === undefined ? '—' : NUMBER.format(value);
const tripId = trip => trip.id || trip.trip_id || trip.tripId;
const recurring = trip => (trip.tipo || trip.type || trip.trip_type) === 'recurrente' || trip.recurring === true;

export function isTripActive(trip) {
  return (trip.activo ?? trip.active) !== false;
}

function tripDayIndex(trip) {
  const value = trip.dia_semana ?? trip.day_of_week;
  if (value === undefined || value === null || value === '') return -1;
  if (/^[0-6]$/.test(String(value))) return Number(value);
  return DAYS.findIndex(day => normalize(day) === normalize(value));
}

export function tripDayName(trip) {
  return DAYS[tripDayIndex(trip)] || 'Día sin definir';
}

export function findPlanningSensor(states, vehicleId) {
  return entries(states).find(([id, state]) => state?.attributes?.vehicle_id === vehicleId &&
    (id.includes('emhass_perfil_diferible_') || state.attributes.number_of_deferrable_loads !== undefined))?.[1] || null;
}

function powerSegments(profile) {
  const segments = [];
  profile.forEach((watts, step) => {
    if (watts <= 0) return;
    const previous = segments[segments.length - 1];
    if (previous?.end === step && previous.watts === watts) previous.end = step + 1;
    else segments.push({ start: step, end: step + 1, watts });
  });
  return segments;
}

/**
 * Read the published input to EMHASS, not the optimizer's output.
 * The current backend uses one-hour steps and does not publish an absolute
 * time origin. Keep the chart relative; last_updated is only a publication time.
 */
export function buildChargingPlan(sensor) {
  const empty = {
    available: false, profile: [], loads: [], horizon: 0, energyKwh: null,
    chargingHours: null, peakKw: null, warnings: [], sensor,
  };
  if (!sensor || sensor.state !== 'ready') return empty;
  const attrs = sensor.attributes || {};
  const rawProfile = attrs.power_profile_watts;
  if (!Array.isArray(rawProfile)) return empty;
  const profile = rawProfile.map(number);
  if (profile.some(watts => watts === null || watts < 0)) return empty;
  if (!profile.length && number(attrs.number_of_deferrable_loads) !== 0) return empty;
  const warnings = [];
  const matrix = Array.isArray(attrs.p_deferrable_matrix) ? attrs.p_deferrable_matrix : [];
  const schedule = Array.isArray(attrs.deferrables_schedule) ? attrs.deferrables_schedule : [];
  const loads = matrix.flatMap((rawRow, index) => {
    if (!Array.isArray(rawRow)) {
      warnings.push(`La carga ${index + 1} no contiene un perfil válido.`);
      return [];
    }
    const row = rawRow.map(number);
    if (row.some(watts => watts === null || watts < 0) || row.length !== profile.length) {
      warnings.push(`El perfil de la carga ${index + 1} no coincide con el horizonte publicado.`);
      return [];
    }
    const start = number(attrs.def_start_timestep_array?.[index]);
    const end = number(attrs.def_end_timestep_array?.[index]);
    const hours = number(attrs.def_total_hours_array?.[index]);
    const nominal = number(attrs.p_deferrable_nom_array?.[index]);
    const validWindow = start !== null && end !== null && start >= 0 && end >= start && end <= profile.length;
    if (!validWindow) warnings.push(`La ventana de la carga ${index + 1} no está disponible.`);
    if (hours === null || nominal === null) warnings.push(`Faltan parámetros de la carga ${index + 1}.`);
    // Schedule records are in insertion order; matrix rows are sorted by window.
    // Only expose the EMHASS index when its published window uniquely matches.
    const matches = validWindow ? schedule.filter(item =>
      number(item.start_timestep) === start && number(item.end_timestep) === end) : [];
    return [{
      index, start: validWindow ? start : null, end: validWindow ? end : null,
      hours, nominal, emhassIndex: matches.length === 1 ? number(matches[0].index) : null,
      profile: row, segments: powerSegments(row),
      energyKwh: row.reduce((sum, watts) => sum + watts, 0) / 1000,
    }];
  });
  // The aggregate is max-merged by the backend. Summing matrix rows would
  // double-count overlapping charging slots and misrepresent the published plan.
  return {
    available: true, profile, loads, horizon: profile.length, warnings, sensor,
    energyKwh: profile.reduce((sum, watts) => sum + watts, 0) / 1000,
    chargingHours: profile.filter(watts => watts > 0).length,
    peakKw: profile.reduce((peak, watts) => Math.max(peak, watts), 0) / 1000,
  };
}

export class EVTripPlannerPanel extends LitElement {
  static properties = {
    _hass: { state: true }, _vehicleId: { state: true }, _trips: { state: true },
    _isLoading: { state: true }, _showForm: { state: true }, _editingTrip: { state: true },
    _formType: { state: true }, _range: { state: true }, _filter: { state: true },
    _busy: { state: true }, _notice: { state: true }, _error: { state: true },
    _tripError: { state: true },
  };

  // Visual styles have one source of truth: the versioned local stylesheet.
  static styles = css`:host { display: block; }`;

  constructor() {
    super();
    this._vehicleId = '';
    this._trips = [];
    this._isLoading = true;
    this._showForm = false;
    this._editingTrip = null;
    this._formType = 'recurrente';
    this._range = 'week';
    this._filter = 'all';
    this._busy = false;
    this._notice = '';
    this._error = '';
    this._tripError = '';
    this._plan = buildChargingPlan(null);
    this._loadPromise = null;
    this._sourceTrips = null;
    this._sourcePlan = null;
  }

  set panel(panel) {
    this._panel = panel;
    const id = panel?.config?.vehicle_id;
    if (id && id !== this._vehicleId) {
      this._vehicleId = id;
      this._trips = [];
      this._showForm = false;
      this._editingTrip = null;
      this._isLoading = true;
      this._plan = buildChargingPlan(null);
      this._sourceTrips = null;
      this._sourcePlan = null;
      if (this._hass && this.isConnected) this._loadTrips();
    }
  }

  get panel() { return this._panel; }

  set hass(hass) {
    this._hass = hass;
    if (hass && this._vehicleId && this.isConnected) this._loadTrips();
  }

  get hass() { return this._hass; }

  connectedCallback() {
    super.connectedCallback();
    if (!this._vehicleId) {
      this._vehicleId = window.location.pathname.match(/\/ev-trip-planner-([^/]+)/)?.[1] || '';
    }
    if (this._hass && this._vehicleId) this._loadTrips();
    this._onKeyDown = event => {
      if (event.key === 'Escape' && this._showForm && !this._busy) this._closeForm();
      if (event.key === 'Tab' && this._showForm) {
        const controls = [...this.renderRoot.querySelectorAll('.trip-form-container button:not(:disabled), .trip-form-container input:not(:disabled), .trip-form-container select:not(:disabled), .trip-form-container textarea:not(:disabled)')]
          .filter(control => control.getClientRects().length);
        const first = controls[0];
        const last = controls[controls.length - 1];
        const focused = this.renderRoot.activeElement;
        if (!first) event.preventDefault();
        else if (event.shiftKey && (focused === first || !controls.includes(focused))) {
          event.preventDefault(); last.focus();
        } else if (!event.shiftKey && (focused === last || !controls.includes(focused))) {
          event.preventDefault(); first.focus();
        }
      }
    };
    this.addEventListener('keydown', this._onKeyDown);
  }

  disconnectedCallback() {
    this.removeEventListener('keydown', this._onKeyDown);
    super.disconnectedCallback();
  }

  willUpdate(changed) {
    if (changed.has('_hass') || changed.has('_vehicleId')) {
      const source = findPlanningSensor(this._hass?.states, this._vehicleId);
      if (source !== this._sourcePlan) {
        this._sourcePlan = source;
        this._plan = buildChargingPlan(source);
      }
    }
  }

  _scopedState(suffix) {
    return entries(this._hass?.states).find(([id, state]) => id.endsWith(suffix) &&
      (state.attributes?.vehicle_id !== undefined ? state.attributes.vehicle_id === this._vehicleId
        : id.endsWith(`_${this._vehicleId}${suffix}`)))?.[1] || null;
  }

  async _loadTrips(fresh = false) {
    if (!this._hass || !this._vehicleId) return;
    const source = this._scopedState('_ev_trip_planner_trips_list');
    // HA pushes the canonical trip lists with state updates. Do not query a
    // service every five seconds because unrelated household sensors changed.
    if (!fresh && Array.isArray(source?.attributes?.recurring_trips)) {
      if (source !== this._sourceTrips) {
        this._trips = [
          ...source.attributes.recurring_trips.map(trip => ({ ...trip, trip_type: 'recurrente' })),
          ...(source.attributes.punctual_trips || []).map(trip => ({ ...trip, trip_type: 'puntual' })),
        ];
        this._sourceTrips = source;
      }
      this._isLoading = false;
      this._tripError = '';
      return;
    }
    if (this._loadPromise) return this._loadPromise;
    const vehicleId = this._vehicleId;
    this._loadPromise = this._getTripsList().then(trips => {
      if (vehicleId !== this._vehicleId) return;
      this._trips = trips;
      this._tripError = '';
    }).catch(() => {
      if (vehicleId !== this._vehicleId) return;
      this._tripError = 'No se han podido actualizar los viajes. Inténtalo de nuevo.';
    }).finally(() => {
      if (vehicleId === this._vehicleId) this._isLoading = false;
      this._loadPromise = null;
      if (vehicleId !== this._vehicleId && this.isConnected) this._loadTrips();
    });
    return this._loadPromise;
  }

  async _getTripsList() {
    const response = await this._hass.callService('ev_trip_planner', 'trip_list',
      { vehicle_id: this._vehicleId }, undefined, undefined, true);
    const data = response?.response || response?.result || response;
    if (data?.vehicle_id && data.vehicle_id !== this._vehicleId) throw new Error('Vehicle mismatch');
    if (!Array.isArray(data?.recurring_trips)) throw new Error('Invalid trip list');
    return [
      ...data.recurring_trips.map(trip => ({ ...trip, trip_type: 'recurrente' })),
      ...(data.punctual_trips || []).map(trip => ({ ...trip, trip_type: 'puntual' })),
    ];
  }

  _zone() { return this._hass?.config?.time_zone || 'Europe/Madrid'; }

  _dateLabel(value) {
    if (!value) return 'Fecha sin definir';
    const text = String(value);
    const absolute = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(text);
    const date = new Date(absolute ? text : `${text.replace(' ', 'T')}Z`);
    if (Number.isNaN(date.getTime())) return 'Fecha sin definir';
    return new Intl.DateTimeFormat('es-ES', {
      weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
      timeZone: absolute ? this._zone() : 'UTC',
    }).format(date);
  }

  _tripLabel(trip) {
    return recurring(trip) ? `${tripDayName(trip)} · ${trip.hora || trip.time || 'Sin hora'}`
      : this._dateLabel(trip.fecha_hora || trip.datetime || trip.date);
  }

  _localNow(date = new Date()) {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: this._zone(), year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    }).formatToParts(date);
    const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
    return `${values.year}-${values.month}-${values.day}T${values.hour}:${values.minute}`;
  }

  _dateInputValue(value) {
    const text = String(value || '');
    if (/(?:Z|[+-]\d{2}:?\d{2})$/i.test(text)) {
      const date = new Date(text);
      return Number.isNaN(date.getTime()) ? '' : this._localNow(date);
    }
    return text.replace(' ', 'T').slice(0, 16);
  }

  _tripOrder(trip) {
    // Sort by upcoming local calendar occurrence, without using this to infer
    // the absolute origin of EMHASS's relative hourly slots.
    const now = new Date(`${this._localNow()}Z`);
    if (!recurring(trip)) {
      const value = trip.fecha_hora || trip.datetime || trip.date;
      const date = new Date(value ? `${this._dateInputValue(value)}Z` : NaN);
      return Number.isNaN(date.getTime()) ? Infinity : date.getTime();
    }
    const day = tripDayIndex(trip);
    const match = String(trip.hora || trip.time || '').match(/^(\d{2}):(\d{2})$/);
    if (day < 0 || !match) return Infinity;
    const date = new Date(now);
    date.setUTCDate(date.getUTCDate() + (day - now.getUTCDay() + 7) % 7);
    date.setUTCHours(Number(match[1]), Number(match[2]), 0, 0);
    if (date < now) date.setUTCDate(date.getUTCDate() + 7);
    return date.getTime();
  }

  _sortedTrips() {
    return [...this._trips].sort((a, b) => Number(isTripActive(b)) - Number(isTripActive(a)) ||
      this._tripOrder(a) - this._tripOrder(b));
  }

  _nextTrip() {
    const nextId = this._scopedState('_ev_trip_planner_next_trip')?.state;
    return this._trips.find(trip => tripId(trip) === nextId && isTripActive(trip)) ||
      this._sortedTrips().find(isTripActive);
  }

  _publicationTime() {
    const value = this._plan.sensor?.last_updated;
    if (!value) return 'Sin actualización';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Sin actualización';
    return `Actualizado a las ${new Intl.DateTimeFormat('es-ES', {
      hour: '2-digit', minute: '2-digit', timeZone: this._zone(),
    }).format(date)}`;
  }

  render() {
    if (!this._hass || !this._vehicleId) {
      return html`<link rel="stylesheet" href="/ev-trip-planner/panel.css?v=${VERSION}">
        <div class="loading-panel" role="status">Conectando con el planificador…</div>`;
    }
    const activeCount = this._trips.filter(isTripActive).length;
    const pausedCount = this._trips.length - activeCount;
    const next = this._nextTrip();
    const plan = this._plan;
    const vehicleName = this._panel?.title || this._vehicleId.replace(/_/g, ' ');
    return html`
      <link rel="stylesheet" href="/ev-trip-planner/panel.css?v=${VERSION}">
      <div class="panel-container" data-version=${VERSION} data-dark=${Boolean(this._hass?.themes?.darkMode)}>
        <header class="panel-header">
          <div class="header-main">
            <ha-menu-button class="mobile-menu" .hass=${this._hass} .narrow=${true}></ha-menu-button>
            <div class="brand-icon"><ha-icon icon="mdi:ev-station"></ha-icon></div>
            <div><div class="eyebrow">EV Trip Planner · ${vehicleName}</div>
              <h1>Planificación de carga</h1>
              <p>Tus viajes, la energía que necesitan y el plan para EMHASS.</p></div>
          </div>
          <button class="add-trip-btn" @click=${this._showTripForm} ?disabled=${this._busy}>
            <ha-icon icon="mdi:plus"></ha-icon> Nuevo viaje
          </button>
        </header>
        <main class="panel-content">
          ${this._notice ? html`<div class="notice" role="status">${this._notice}</div>` : ''}
          ${this._error ? html`<div class="notice error" role="alert">${this._error}</div>` : ''}
          <section class="summary-grid" aria-label="Resumen de la planificación">
            ${this._summaryCard('Energía propuesta', `${fmt(plan.energyKwh)} kWh`, 'Del perfil publicado', 'mdi:lightning-bolt', 'energy')}
            ${this._summaryCard('Tiempo de carga', `${fmt(plan.chargingHours)} h`, 'Pasos con potencia de carga', 'mdi:timer-outline')}
            ${this._summaryCard('Potencia del perfil', `${fmt(plan.peakKw)} kW`, 'Máximo publicado', 'mdi:flash-outline')}
            ${this._summaryCard('Próximo viaje', next ? this._tripLabel(next) : 'Sin viajes activos',
              next ? `${fmt(number(next.km))} km · ${fmt(number(next.kwh))} kWh de consumo` : 'Añade un viaje para planificar', 'mdi:calendar-arrow-right', 'next-trip')}
          </section>
          ${this._renderPlan()}
          <section class="trips-section" aria-labelledby="trips-title">
            <div class="section-header">
              <div><div class="eyebrow">Gestiona tus necesidades</div><h2 id="trips-title">Viajes programados</h2>
                <p>${activeCount} ${activeCount === 1 ? 'activo' : 'activos'}${pausedCount ? ` · ${pausedCount} ${pausedCount === 1 ? 'pausado' : 'pausados'}` : ''}</p></div>
              <div class="segmented-control" role="group" aria-label="Filtrar viajes">
                ${[['all', 'Todos'], ['active', 'Activos'], ['paused', 'Pausados']].map(([value, label]) => html`
                  <button aria-pressed=${this._filter === value} @click=${() => { this._filter = value; }}>${label}</button>`)}
              </div>
            </div>
            ${this._tripError ? html`<div class="notice error" role="alert">${this._tripError}
              <button class="text-button" @click=${() => this._loadTrips(true)}>Reintentar</button></div>` : ''}
            ${this._isLoading ? html`<div class="empty-state" role="status">Cargando viajes…</div>` : this._renderTrips()}
          </section>
        </main>
        ${this._showForm ? this._renderForm() : ''}
      </div>`;
  }

  _summaryCard(label, value, hint, icon, extra = '') {
    return html`<article class="summary-card ${extra}"><div class="summary-label"><ha-icon icon=${icon}></ha-icon>${label}</div>
      <div class="summary-value">${value}</div><div class="summary-hint">${hint}</div></article>`;
  }

  _renderPlan() {
    const plan = this._plan;
    const visible = this._range === '48h' ? Math.min(48, plan.horizon) : plan.horizon;
    const tickSize = visible <= 48 ? 6 : 24;
    const ticks = Array.from({ length: Math.floor(visible / tickSize) + 1 }, (_, index) => index * tickSize);
    if (visible && ticks[ticks.length - 1] !== visible) ticks.push(visible);
    const columns = plan.profile.slice(0, visible);
    return html`<section class="planning-card" aria-labelledby="plan-title">
      <div class="section-header">
        <div><div class="eyebrow">Entrada al optimizador</div><h2 id="plan-title">Perfil de carga para EMHASS</h2>
          <p>Potencia propuesta y ventanas disponibles para cada carga.</p></div>
        <div class="plan-state ${plan.available ? 'ready' : 'unavailable'}"><span class="state-dot"></span>
          ${plan.available ? 'Plan disponible' : 'Plan no disponible'}</div>
      </div>
      ${!plan.available ? html`<div class="empty-state"><ha-icon icon="mdi:chart-timeline-variant"></ha-icon>
        <h3>Esperando la planificación</h3><p>El sensor de EMHASS todavía no publica un perfil válido para este vehículo.</p></div>`
        : !plan.horizon ? html`<div class="empty-state"><ha-icon icon="mdi:battery-check-outline"></ha-icon>
          <h3>No hay cargas previstas</h3><p>El sensor no publica cargas diferibles en este momento.</p></div>` : html`
          <div class="plan-toolbar"><div class="plan-meta">${visible < plan.horizon ? `${visible} de ${plan.horizon} h visibles` : `${fmt(plan.horizon)} h de horizonte`} · Pasos de 1 h
            <span>${this._publicationTime()}</span></div>
            <div class="segmented-control" role="group" aria-label="Tramo de la planificación">
              <button aria-pressed=${this._range === '48h'} @click=${() => { this._range = '48h'; }}>Próximas 48 h</button>
              <button aria-pressed=${this._range === 'week'} @click=${() => { this._range = 'week'; }}>Todo el horizonte</button>
            </div></div>
          <p class="chart-mobile-hint">Desliza la gráfica para recorrer el horizonte.</p>
          <div class="chart-scroll" @scroll=${this._syncChartScroll} tabindex="0" role="region" aria-label="Gráfica del perfil de potencia; desplázate horizontalmente en pantallas pequeñas">
            <div class="profile-chart">
              <div class="power-axis"><span>${fmt(plan.peakKw)} kW</span><span>0 kW</span></div>
              <div class="profile-main"><div class="power-columns" style="--steps: ${visible}" role="img"
                aria-label="Perfil publicado: ${fmt(plan.energyKwh)} kilovatios hora, ${fmt(plan.chargingHours)} horas de carga y un máximo de ${fmt(plan.peakKw)} kilovatios">
                ${columns.map((watts, step) => html`<div class="power-cell" title="Paso ${step}–${step + 1}: ${fmt(watts / 1000)} kW">
                  <span class="power-bar" data-step=${step} data-watts=${watts}
                    style="height: ${plan.peakKw > 0 ? watts / 1000 / plan.peakKw * 100 : 0}%"></span></div>`)}
              </div><div class="time-axis">${ticks.map(step => html`<span style="left: ${step / visible * 100}%">${step ? `+${step}` : '0'} h</span>`)}</div></div>
            </div>
          </div>
          ${plan.loads.length ? html`<div class="loads-heading"><h3>Ventanas por carga</h3><span>${plan.loads.length} cargas publicadas</span></div>
            <div class="chart-scroll" @scroll=${this._syncChartScroll} tabindex="0" role="region" aria-label="Ventanas disponibles y carga propuesta por fila de la matriz EMHASS">
              <div class="loads-chart">
                ${plan.loads.map(load => this._renderLoad(load, visible, tickSize))}
              </div>
            </div>` : ''}
          <div class="chart-legend"><span><i class="legend-charge"></i>Carga propuesta</span>
            <span><i class="legend-window"></i>Ventana disponible</span><span><i class="legend-deadline"></i>Límite de la ventana</span></div>
          <p class="plan-explanation">Las horas del eje son relativas al cálculo del plan, no horas del reloj.
            Este es el perfil publicado por EV Trip Planner; EMHASS decide el horario optimizado final.</p>
          ${plan.warnings.length ? html`<div class="notice warning" role="status">${plan.warnings.join(' ')}</div>` : ''}
          ${this._renderPlanDetails()}
        `}
    </section>`;
  }

  _syncChartScroll(event) {
    const current = event.currentTarget;
    for (const chart of this.renderRoot.querySelectorAll('.chart-scroll')) {
      if (chart !== current && Math.abs(chart.scrollLeft - current.scrollLeft) > 1) {
        chart.scrollLeft = current.scrollLeft;
      }
    }
  }

  _renderLoad(load, visible, tickSize) {
    const start = load.start === null ? null : Math.min(load.start, visible);
    const end = load.end === null ? null : Math.min(load.end, visible);
    const segments = load.segments.filter(segment => segment.start < visible);
    return html`<div class="load-row" style="--load-color: var(--load-${load.index % 3})">
      <div class="load-label"><strong><span class="load-dot"></span>Carga ${load.index + 1}</strong>
        <span>${fmt(load.energyKwh)} kWh · ${fmt(load.hours)} h</span></div>
      <div class="load-track" style="--tick-width: ${tickSize / visible * 100}%" role="img"
        aria-label="Carga ${load.index + 1}. Ventana: ${load.start === null ? 'no disponible' : `pasos ${load.start} a ${load.end}`}. Perfil: ${load.segments.map(segment => `pasos ${segment.start} a ${segment.end}`).join(', ') || 'sin carga'}.">
        ${start !== null && end > start ? html`<span class="availability-band" style="left: ${start / visible * 100}%; width: ${(end - start) / visible * 100}%"
          title="Ventana disponible: +${load.start} h a +${load.end} h"></span>` : ''}
        ${segments.map(segment => html`<span class="charging-band"
          style="left: ${segment.start / visible * 100}%; width: ${(Math.min(segment.end, visible) - segment.start) / visible * 100}%"
          title="Carga propuesta: +${segment.start} h a +${segment.end} h · ${fmt(segment.watts / 1000)} kW"></span>`)}
        ${load.end !== null && load.end <= visible ? html`<span class="deadline-marker" style="left: ${load.end / visible * 100}%"
          title="Límite de la ventana: +${load.end} h"></span>` : ''}
        ${!segments.length && load.segments.length ? html`<span class="outside-range">Carga a +${load.segments[0].start} h · fuera de este tramo</span>` : ''}
      </div></div>`;
  }

  _renderPlanDetails() {
    return html`<details class="plan-details"><summary>Ver parámetros publicados para EMHASS</summary>
      <p class="sensor-reference">Sensor de origen: <code>${this._plan.sensor?.entity_id || 'Sin identificar'}</code></p>
      <div class="table-scroll"><table><caption>Parámetros de las cargas, en el orden de la matriz publicada</caption>
        <thead><tr><th scope="col">Carga</th><th scope="col">Índice EMHASS</th><th scope="col">Inicio</th><th scope="col">Límite</th><th scope="col">Duración</th><th scope="col">Potencia nominal</th></tr></thead>
        <tbody>${this._plan.loads.map(load => html`<tr><th scope="row">${load.index + 1}</th><td>${fmt(load.emhassIndex)}</td>
          <td>${fmt(load.start)} h</td><td>${fmt(load.end)} h</td><td>${fmt(load.hours)} h</td><td>${fmt(load.nominal === null ? null : load.nominal / 1000)} kW</td></tr>`)}</tbody>
      </table></div></details>`;
  }

  _renderTrips() {
    const trips = this._sortedTrips().filter(trip => this._filter === 'all' ||
      (this._filter === 'active' ? isTripActive(trip) : !isTripActive(trip)));
    if (!trips.length) return html`<div class="empty-state"><ha-icon icon="mdi:calendar-blank-outline"></ha-icon>
      <h3>${this._trips.length ? 'No hay viajes en este filtro' : 'Tu próxima carga empieza con un viaje'}</h3>
      <p>${this._trips.length ? 'Selecciona otro filtro para ver el resto.' : 'Añade una salida y el planificador calculará la carga necesaria.'}</p></div>`;
    return html`<div class="trips-list">${trips.map(trip => this._formatTripDisplay(trip))}</div>`;
  }

  _formatTripDisplay(trip) {
    const active = isTripActive(trip);
    const weekly = recurring(trip);
    const id = tripId(trip);
    return html`<article class="trip-card ${active ? '' : 'trip-card-inactive'}" data-trip-id=${id}>
      <div class="trip-header"><span class="trip-type"><ha-icon icon=${weekly ? 'mdi:calendar-refresh' : 'mdi:calendar'}></ha-icon>
        ${weekly ? 'Semanal' : 'Puntual'}</span><span class="trip-status ${active ? 'status-active' : 'status-inactive'}">${active ? 'Activo' : 'Pausado'}</span></div>
      <h3 class="trip-time">${this._tripLabel(trip)}</h3>
      <p class="trip-description">${trip.descripcion || trip.description || (weekly ? 'Se repite cada semana' : 'Viaje de una sola vez')}</p>
      <div class="trip-details"><span><ha-icon icon="mdi:map-marker-distance"></ha-icon><strong>${fmt(number(trip.km))}</strong> km</span>
        <span><ha-icon icon="mdi:lightning-bolt-outline"></ha-icon><strong>${fmt(number(trip.kwh))}</strong> kWh <small>de consumo</small></span></div>
      ${!active ? html`<p class="paused-note">No participa en la planificación de carga.</p>` : ''}
      <div class="trip-actions">
        <button class="trip-action-btn edit-btn" @click=${() => this._handleEditClick(id)} ?disabled=${this._busy}>Editar</button>
        ${weekly ? html`<button class="trip-action-btn ${active ? 'pause-btn' : 'resume-btn'}"
          @click=${() => this._handleTripAction(trip, active ? 'pause' : 'resume')} ?disabled=${this._busy}>${active ? 'Pausar' : 'Reanudar'}</button>` : html`
          <button class="trip-action-btn" @click=${() => this._handleTripAction(trip, 'complete')} ?disabled=${this._busy}>Completar</button>
          <button class="trip-action-btn" @click=${() => this._handleTripAction(trip, 'cancel')} ?disabled=${this._busy}>Cancelar</button>`}
        <button class="trip-action-btn delete-btn" @click=${() => this._handleTripAction(trip, 'delete')} ?disabled=${this._busy}
          aria-label="Eliminar viaje ${this._tripLabel(trip)}"><ha-icon icon="mdi:trash-can-outline"></ha-icon><span>Eliminar</span></button>
      </div>
    </article>`;
  }

  _showTripForm() {
    this._returnFocus = this.renderRoot.activeElement;
    this._formDate = this._localNow();
    this._formType = 'recurrente';
    this._editingTrip = null;
    this._error = '';
    this._showForm = true;
    this.updateComplete.then(() => this.renderRoot.querySelector('#trip-type')?.focus());
  }

  _closeForm() {
    if (this._busy) return;
    this._showForm = false;
    this._editingTrip = null;
    this._error = '';
    this.updateComplete.then(() => {
      const target = this._returnFocus?.isConnected ? this._returnFocus : this.renderRoot.querySelector('.add-trip-btn');
      target?.focus();
    });
  }

  async _handleEditClick(id) {
    const trip = this._trips.find(item => tripId(item) === id);
    if (!trip) return;
    this._returnFocus = this.renderRoot.activeElement;
    this._formDate = this._localNow();
    this._editingTrip = trip;
    this._formType = recurring(trip) ? 'recurrente' : 'puntual';
    this._error = '';
    this._showForm = true;
    await this.updateComplete;
    this.renderRoot.querySelector('#trip-type')?.focus();
  }

  _renderForm() {
    const trip = this._editingTrip;
    const punctual = this._formType === 'puntual';
    const now = this._formDate || this._localNow();
    const day = trip ? tripDayIndex(trip) : 1;
    const rawDate = trip?.fecha_hora || trip?.datetime || trip?.date || now;
    return html`<div class="trip-form-overlay" @click=${event => { if (event.target === event.currentTarget) this._closeForm(); }}>
      <section class="trip-form-container" role="dialog" aria-modal="true" aria-labelledby="form-title">
        <div class="trip-form-header"><div><div class="eyebrow">Planificación de carga</div><h2 id="form-title">${trip ? 'Editar viaje' : 'Nuevo viaje'}</h2></div>
          <button class="close-form-btn" aria-label="Cerrar formulario" @click=${this._closeForm} ?disabled=${this._busy}><ha-icon icon="mdi:close"></ha-icon></button></div>
        ${this._error ? html`<div class="notice error" role="alert">${this._error}</div>` : ''}
        <form @submit=${this._handleTripSave}>
          <div class="form-group"><label for="trip-type">Tipo de viaje</label><select id="trip-type" name="type" .value=${this._formType}
            @change=${event => { this._formType = event.target.value; }} ?disabled=${this._busy}>
            <option value="recurrente" ?selected=${!punctual}>Semanal · se repite cada semana</option><option value="puntual" ?selected=${punctual}>Puntual · una sola vez</option></select></div>
          <div class="form-row" ?hidden=${punctual}>
            <div class="form-group"><label for="trip-day">Día de la semana</label><select id="trip-day" name="day" .value=${String(day < 0 ? 1 : day)}
              ?disabled=${this._busy || punctual}>${DAYS.map((label, index) => html`<option value=${index} ?selected=${index === (day < 0 ? 1 : day)}>${label}</option>`)}</select></div>
            <div class="form-group"><label for="trip-time">Hora de salida</label><input id="trip-time" name="time" type="time"
              .value=${trip?.hora || trip?.time || now.slice(11)} ?required=${!punctual} ?disabled=${this._busy || punctual}></div>
          </div>
          <div class="form-group" ?hidden=${!punctual}><label for="trip-datetime">Fecha y hora de salida</label>
            <input id="trip-datetime" name="datetime" type="datetime-local" .value=${this._dateInputValue(rawDate)}
              ?required=${punctual} ?disabled=${this._busy || !punctual}></div>
          <div class="form-row">
            <div class="form-group"><label for="trip-km">Distancia · km</label><input id="trip-km" name="km" type="number" min="0" step="0.1"
              .value=${String(trip?.km ?? '')} placeholder="Ej. 30" ?disabled=${this._busy}></div>
            <div class="form-group"><label for="trip-kwh">Consumo previsto · kWh</label><input id="trip-kwh" name="kwh" type="number" min="0" step="0.1"
              .value=${String(trip?.kwh ?? '')} placeholder="Ej. 5" ?disabled=${this._busy}></div>
          </div>
          <p class="form-hint">La energía del viaje es el consumo previsto, no la carga que publicará el planificador.</p>
          <div class="form-group"><label for="trip-description">Descripción · opcional</label><textarea id="trip-description" name="description"
            .value=${trip?.descripcion || trip?.description || ''} placeholder="Ej. Trabajo, escapada…" ?disabled=${this._busy}></textarea></div>
          <div class="form-actions"><button class="btn btn-secondary" type="button" @click=${this._closeForm} ?disabled=${this._busy}>Cancelar</button>
            <button class="btn btn-primary" type="submit" ?disabled=${this._busy}>${this._busy ? 'Guardando…' : trip ? 'Guardar cambios' : 'Crear viaje'}</button></div>
        </form>
      </section></div>`;
  }

  async _handleTripSave(event) {
    event.preventDefault();
    if (this._busy) return;
    const values = new FormData(event.target);
    const editing = this._editingTrip;
    const data = { vehicle_id: this._vehicleId, type: values.get('type') };
    if (editing) data.trip_id = tripId(editing);
    if (data.type === 'puntual') data.datetime = values.get('datetime');
    else { data.dia_semana = values.get('day'); data.hora = values.get('time'); }
    for (const field of ['km', 'kwh']) {
      if (values.get(field) !== '') data[field] = Number(values.get(field));
    }
    // Retain the existing service contract, including its description key.
    data.description = values.get('description') || '';
    this._busy = true;
    this._error = '';
    try {
      await this._hass.callService('ev_trip_planner', editing ? 'trip_update' : 'trip_create', data);
      await this._loadTrips(true);
      this._notice = editing ? 'Viaje actualizado. El planificador actualizará el perfil de carga.' : 'Viaje creado. El planificador actualizará el perfil de carga.';
      this._busy = false;
      this._closeForm();
    } catch (error) {
      this._error = `No se ha podido guardar el viaje: ${error.message || 'revisa la conexión'}`;
    } finally { this._busy = false; }
  }

  async _handleTripAction(trip, action) {
    if (this._busy) return;
    const actions = {
      pause: ['pause_recurring_trip', '¿Pausar este viaje y excluirlo de la planificación?', 'Viaje pausado.'],
      resume: ['resume_recurring_trip', null, 'Viaje reanudado.'],
      delete: ['delete_trip', '¿Eliminar este viaje?', 'Viaje eliminado.'],
      complete: ['complete_punctual_trip', '¿Marcar este viaje como completado?', 'Viaje completado.'],
      cancel: ['cancel_punctual_trip', '¿Cancelar este viaje?', 'Viaje cancelado.'],
    };
    const [service, question, message] = actions[action];
    if (question && !window.confirm(question)) return;
    this._busy = true;
    this._error = '';
    try {
      await this._hass.callService('ev_trip_planner', service, { vehicle_id: this._vehicleId, trip_id: tripId(trip) });
      await this._loadTrips(true);
      this._notice = message;
    } catch (error) {
      this._error = `No se ha podido realizar la acción: ${error.message || 'revisa la conexión'}`;
    } finally { this._busy = false; }
  }
}

if (!customElements.get('ev-trip-planner-panel')) customElements.define('ev-trip-planner-panel', EVTripPlannerPanel);
