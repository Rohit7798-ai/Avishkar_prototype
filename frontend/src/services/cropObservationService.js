/**
 * Crop Observation API service.
 * Handles crop field measurements and phenology observation records.
 */

import { request } from './api';

export const cropObservationService = {
  /**
   * Retrieve all recorded field observations for a specific crop planting.
   * @param {number} cropId
   * @returns {Promise<Array<{ id: number, crop_id: number, observation_date: string, growth_stage: string, health_status: string, notes: string|null, created_at: string, updated_at: string }>>}
   */
  async getCropObservations(cropId) {
    return request(`/api/v1/crops/${cropId}/observations`);
  },

  /**
   * Record a new crop observation.
   * @param {number} cropId
   * @param {{ observation_date: string, growth_stage: string, health_status: string, notes?: string|null }} data
   * @returns {Promise<any>}
   */
  async createCropObservation(cropId, data) {
    return request(`/api/v1/crops/${cropId}/observations`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete an existing crop observation record.
   * @param {number} observationId
   * @returns {Promise<null>}
   */
  async deleteCropObservation(observationId) {
    return request(`/api/v1/crop-observations/${observationId}`, {
      method: 'DELETE',
    });
  },
};

export default cropObservationService;
