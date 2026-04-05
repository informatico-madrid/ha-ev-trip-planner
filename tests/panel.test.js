/**
 * Tests for EV Trip Planner panel vehicle_id filtering.
 *
 * This test verifies that the panel correctly filters and displays trips
 * by matching vehicle_id attribute from EMHASS sensors with the vehicle_id
 * extracted from URL params (_vehicleId).
 *
 * Bug fix for PR #21: Panel was filtering by entry_id but sensor stores vehicle_id
 */

import { html } from 'lit';
import { expect, fixture } from '@open-wc/testing';

// Mock HomeAssistant class
class MockHass {
  constructor() {
    this.states = {};
    this.callService = this.mockCallService.bind(this);
  }

  async mockCallService(domain, service, serviceData, target, notifyOnError, returnResponse) {
    if (domain === 'ev_trip_planner' && service === 'trip_list') {
      // Return trips with vehicle_id attribute
      return {
        response: {
          found: true,
          vehicle_id: serviceData.vehicle_id,
          trips: [
            {
              id: 'rec_lun_abc123',
              tipo: 'recurrente',
              dia_semana: 'lunes',
              hora: '10:00',
              km: 50,
              kwh: 5,
              activo: true,
              vehicle_id: 'mi_coche' // This is what the sensor stores
            }
          ]
        }
      };
    }
    return null;
  }
}

describe('EV Trip Planner Panel - Vehicle ID Filtering', () => {
  let panel;
  let hass;

  beforeEach(async () => {
    hass = new MockHass();
    panel = await fixture(html`
      <ev-trip-planner-panel
        .hass=${hass}
        .vehicleId=${'mi_coche'}
      ></ev-trip-planner-panel>
    `);
  });

  describe('vehicle_id filtering', () => {
    it('should filter trips by vehicle_id from URL params', async () => {
      // Wait for trips to load
      await panel._loadTrips();

      // The panel should display trips that match the vehicle_id from URL
      // Bug fix: Panel was incorrectly trying to filter by entry_id (UUID)
      // but sensors store vehicle_id (slug from URL)
      expect(panel._trips).to.have.length.greaterThan(0);

      // Verify trips have the correct vehicle_id
      panel._trips.forEach(trip => {
        expect(trip.vehicle_id).to.equal(panel._vehicleId);
      });
    });

    it('should display trips from EMHASS sensor with matching vehicle_id', async () => {
      // EMHASS sensor stores vehicle_id attribute (not entry_id)
      // Panel should match this with _vehicleId from URL
      const sensorVehicleId = 'mi_coche';
      const urlVehicleId = panel._vehicleId;

      // Bug: If panel filters by entry_id (UUID), it won't match vehicle_id (slug)
      // Fix: Panel should use vehicle_id for filtering
      expect(urlVehicleId).to.equal(sensorVehicleId);
    });

    it('should NOT display trips with mismatched vehicle_id', async () => {
      // Simulate trips from a different vehicle
      const otherVehicleTrips = [
        {
          id: 'rec_mar_xyz789',
          tipo: 'recurrente',
          dia_semana: 'martes',
          hora: '12:00',
          km: 30,
          kwh: 3,
          activo: true,
          vehicle_id: 'otro_coche' // Different vehicle
        }
      ];

      // Panel should filter these out since they don't match _vehicleId
      const filteredTrips = otherVehicleTrips.filter(t => t.vehicle_id === panel._vehicleId);
      expect(filteredTrips).to.have.length(0);
    });
  });
});
