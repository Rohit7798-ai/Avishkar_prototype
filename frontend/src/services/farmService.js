/**
 * Farm entity API service.
 * Handles Farm queries and mutations against FastAPI /api/v1/farms endpoints.
 */

import { request } from './api';

export const farmService = {
  /**
   * Retrieve all registered farms.
   * @returns {Promise<Array<{ id: number, farmer_id: number, name: string, location: string, area: number, area_unit: string, created_at: string, updated_at: string }>>}
   */
  async getFarms() {
    return request('/api/v1/farms');
  },

  /**
   * Retrieve a specific farm by ID.
   * @param {number} id
   * @returns {Promise<{ id: number, farmer_id: number, name: string, location: string, area: number, area_unit: string, created_at: string, updated_at: string }>}
   */
  async getFarm(id) {
    return request(`/api/v1/farms/${id}`);
  },

  /**
   * Retrieve all farms belonging to a specific farmer.
   * @param {number} farmerId
   * @returns {Promise<Array<any>>}
   */
  async getFarmsByFarmer(farmerId) {
    return request(`/api/v1/farmers/${farmerId}/farms`);
  },

  /**
   * Register a new farm parcel.
   * @param {{ farmer_id: number, name: string, location: string, area: number, area_unit: 'acre'|'hectare' }} farmData
   * @returns {Promise<any>}
   */
  async createFarm(farmData) {
    return request('/api/v1/farms', {
      method: 'POST',
      body: JSON.stringify(farmData),
    });
  },

  /**
   * Delete a farm parcel and its planted crops.
   * @param {number} id
   * @returns {Promise<null>}
   */
  async deleteFarm(id) {
    return request(`/api/v1/farms/${id}`, {
      method: 'DELETE',
    });
  },
};

export default farmService;
