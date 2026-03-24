  /**
   * Update the panel (re-render specific parts)
   */
  _update() {
    if (!this._rendered || !this._hass) {
      return;
    }

    // Update only specific sections, not full re-render
    const states = this._getVehicleStates();
    const stateKeys = Object.keys(states);
    const groupedSensors = this._groupSensors(states);

    // Update status section
    const statusCards = groupedSensors.status.map(s => `
      <div class="status-card">
        <span class="status-icon">${s.icon}</span>
        <span class="status-label">${s.name}</span>
        <span class="status-value">${this._formatSensorValue(s.entityId)}</span>
      </div>
    `).join('');

    const statusSection = document.querySelector('.status-section');
    if (statusSection && statusCards) {
      statusSection.innerHTML = `
        <h2>Vehicle Status</h2>
        <div class="status-grid">
          ${statusCards}
        </div>
      `;
    }

    // Update sensors section
    const sensorListHtml = Object.entries(groupedSensors)
      .filter(([_, sensors]) => sensors.length > 0)
      .map(([groupName, sensors]) => {
        const groupNameMapping = {
          status: 'Estado del Vehículo',
          battery: 'Batería',
          trips: 'Viajes',
          energy: 'Energía y Consumo',
          charging: 'Carga',
          other: 'Otros Sensores'
        };
        return `
        <div class="sensor-group">
          <h3 class="sensor-group-title">${groupNameMapping[groupName] || this._getGroupName(groupName)}</h3>
          <div class="sensor-items-list">
            ${sensors.map(s => {
              const formattedValue = this._formatSensorValue(s.entityId);
              const entityIdDisplay = s.entityId.split('.').slice(1).join('.');
              const isUnavailable = formattedValue === 'No disponible';
              const stateAttr = isUnavailable ? 'data-state="unavailable"' : '';
              return `
            <div class="sensor-item" ${stateAttr} data-entity-id="${s.entityId}">
              <div class="sensor-left">
                <span class="sensor-icon">${s.icon}</span>
                <span class="sensor-name" title="${entityIdDisplay}">${s.name}</span>
              </div>
              <div class="sensor-right">
                <span class="sensor-value">${formattedValue}</span>
              </div>
            </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
      }).join('');

    const sensorsSection = document.querySelector('.sensors-section');
    if (sensorsSection) {
      sensorsSection.innerHTML = `
        <h2>Available Sensors (${stateKeys.length})</h2>
        ${stateKeys.length > 0 ? `
          <div class="sensor-list-grouped">
            ${sensorListHtml || '<p class="no-sensors">No sensors found</p>'}
          </div>
        ` : '<p class="no-sensors">No sensors found</p>'}
      `;
    }

    // Update trips section
    this._renderTripsSection().catch(error => {
      console.error('Error rendering trips section:', error);
    });
  }
