/**
 * API service for triggering manual synchronization with external weather and mandi providers.
 */

import { request } from './api';

export const syncService = {
  /**
   * Manually synchronizes weather observations for a farm from Open-Meteo.
   * @param {number} farmId - ID of the target farm
   * @param {Object} [payload] - Optional explicit coordinates and range
   * @param {number} [payload.latitude]
   * @param {number} [payload.longitude]
   * @param {number} [payload.days]
   * @returns {Promise<{ provider: string, records_received: number, records_accepted: number, records_rejected: number, message: string }>}
   */
  syncFarmWeather: async (farmId, payload = {}) => {
    return request(`/api/v1/farms/${farmId}/weather/sync`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Manually synchronizes mandi commodity quotes from Government of India OGD.
   * @param {Object} [payload] - Query parameters
   * @param {string} [payload.crop_name] - Target commodity (default "Onion")
   * @param {string} [payload.market_name] - Optional APMC market yard
   * @param {number} [payload.limit] - Max records
   * @returns {Promise<{ provider: string, records_received: number, records_accepted: number, records_rejected: number, message: string }>}
   */
  syncMarketData: async (payload = {}) => {
    return request('/api/v1/market/sync', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
