/**
 * Crop entity API service.
 * Handles Crop queries and mutations against FastAPI /api/v1/crops endpoints.
 */

import { request } from './api';

export const cropService = {
  /**
   * Retrieve all planted crops.
   * @returns {Promise<Array<{ id: number, farm_id: number, crop_name: string, variety: string|null, sowing_date: string, expected_harvest_date: string|null, area: number, area_unit: string, created_at: string, updated_at: string }>>}
   */
  async getCrops() {
    return request('/api/v1/crops');
  },

  /**
   * Retrieve a specific crop by ID.
   * @param {number} id
   * @returns {Promise<any>}
   */
  async getCrop(id) {
    return request(`/api/v1/crops/${id}`);
  },

  /**
   * Retrieve all crops planted on a specific farm.
   * @param {number} farmId
   * @returns {Promise<Array<any>>}
   */
  async getCropsByFarm(farmId) {
    return request(`/api/v1/farms/${farmId}/crops`);
  },

  /**
   * Register a new crop planting.
   * @param {{ farm_id: number, crop_name: string, variety?: string|null, sowing_date: string, expected_harvest_date?: string|null, area: number, area_unit: 'acre'|'hectare' }} cropData
   * @returns {Promise<any>}
   */
  async createCrop(cropData) {
    return request('/api/v1/crops', {
      method: 'POST',
      body: JSON.stringify(cropData),
    });
  },

  /**
   * Delete a crop record.
   * @param {number} id
   * @returns {Promise<null>}
   */
  async deleteCrop(id) {
    return request(`/api/v1/crops/${id}`, {
      method: 'DELETE',
    });
  },
};

export default cropService;
