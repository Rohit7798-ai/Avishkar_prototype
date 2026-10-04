/**
 * Weather Observation API service.
 * Handles farm weather measurements and ambient field climate records.
 */

import { request } from './api';

export const weatherObservationService = {
  /**
   * Retrieve all recorded weather observations for a specific farm parcel.
   * @param {number} farmId
   * @returns {Promise<Array<{ id: number, farm_id: number, observed_at: string, temperature: number, humidity: number, rainfall: number, wind_speed: number, created_at: string, updated_at: string }>>}
   */
  async getWeatherObservations(farmId) {
    return request(`/api/v1/farms/${farmId}/weather-observations`);
  },

  /**
   * Record a new weather observation for a farm.
   * @param {number} farmId
   * @param {{ observed_at: string, temperature: number, humidity: number, rainfall: number, wind_speed: number }} data
   * @returns {Promise<any>}
   */
  async createWeatherObservation(farmId, data) {
    return request(`/api/v1/farms/${farmId}/weather-observations`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete an existing weather observation record.
   * @param {number} observationId
   * @returns {Promise<null>}
   */
  async deleteWeatherObservation(observationId) {
    return request(`/api/v1/weather-observations/${observationId}`, {
      method: 'DELETE',
    });
  },
};

export default weatherObservationService;
