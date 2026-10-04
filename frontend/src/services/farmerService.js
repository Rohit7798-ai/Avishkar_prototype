/**
 * Farmer entity API service.
 * Handles Farmer queries and mutations against FastAPI /api/v1/farmers endpoints.
 */

import { request } from './api';

export const farmerService = {
  /**
   * Retrieve all registered farmers.
   * @returns {Promise<Array<{ id: number, name: string, phone: string|null, created_at: string, updated_at: string }>>}
   */
  async getFarmers() {
    return request('/api/v1/farmers');
  },

  /**
   * Retrieve a specific farmer by ID.
   * @param {number} id
   * @returns {Promise<{ id: number, name: string, phone: string|null, created_at: string, updated_at: string }>}
   */
  async getFarmer(id) {
    return request(`/api/v1/farmers/${id}`);
  },

  /**
   * Register a new farmer.
   * @param {{ name: string, phone?: string|null }} farmerData
   * @returns {Promise<{ id: number, name: string, phone: string|null, created_at: string, updated_at: string }>}
   */
  async createFarmer(farmerData) {
    return request('/api/v1/farmers', {
      method: 'POST',
      body: JSON.stringify(farmerData),
    });
  },

  /**
   * Delete a farmer and cascade delete their farms and crops.
   * @param {number} id
   * @returns {Promise<null>}
   */
  async deleteFarmer(id) {
    return request(`/api/v1/farmers/${id}`, {
      method: 'DELETE',
    });
  },
};

export default farmerService;
