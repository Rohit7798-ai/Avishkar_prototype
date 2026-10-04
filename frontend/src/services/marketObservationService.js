/**
 * Market Observation API service.
 * Handles mandi market price quote records and commodity arrival rates.
 */

import { request } from './api';

export const marketObservationService = {
  /**
   * Retrieve all recorded market price observations.
   * @param {{ crop_name?: string, market_name?: string }} [params={}]
   * @returns {Promise<Array<{ id: number, crop_name: string, market_name: string, observed_date: string, price: number, unit: string, created_at: string, updated_at: string }>>}
   */
  async getMarketObservations(params = {}) {
    const query = new URLSearchParams();
    if (params.crop_name) query.set('crop_name', params.crop_name);
    if (params.market_name) query.set('market_name', params.market_name);
    const queryString = query.toString() ? `?${query.toString()}` : '';
    return request(`/api/v1/market-observations${queryString}`);
  },

  /**
   * Record a new mandi price observation.
   * @param {{ crop_name: string, market_name: string, observed_date: string, price: number, unit: string }} data
   * @returns {Promise<any>}
   */
  async createMarketObservation(data) {
    return request('/api/v1/market-observations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete an existing market observation record.
   * @param {number} observationId
   * @returns {Promise<null>}
   */
  async deleteMarketObservation(observationId) {
    return request(`/api/v1/market-observations/${observationId}`, {
      method: 'DELETE',
    });
  },
};

export default marketObservationService;
