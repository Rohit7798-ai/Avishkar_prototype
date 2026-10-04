/**
 * API Service for Agricultural Decision-Ready Indicators.
 * Communicates with backend indicator endpoints to fetch deterministic analytics.
 */

import { request } from './api';

export const indicatorService = {
  /**
   * Retrieves deterministic crop growth & observation indicators.
   * @param {number|string} cropId
   * @returns {Promise<Object>}
   */
  async getCropIndicators(cropId) {
    return request(`/api/v1/crops/${cropId}/indicators`);
  },

  /**
   * Retrieves statistical farm weather indicators from recorded measurements.
   * @param {number|string} farmId
   * @returns {Promise<Object>}
   */
  async getFarmWeatherIndicators(farmId) {
    return request(`/api/v1/farms/${farmId}/weather-indicators`);
  },

  /**
   * Retrieves summary market metrics and price change indicators for crop/market.
   * @param {Object} [params] - Optional { crop_name, market_name }
   * @returns {Promise<Object>}
   */
  async getMarketIndicators(params = {}) {
    const searchParams = new URLSearchParams();
    if (params.crop_name && params.crop_name.trim()) {
      searchParams.append('crop_name', params.crop_name.trim());
    }
    if (params.market_name && params.market_name.trim()) {
      searchParams.append('market_name', params.market_name.trim());
    }
    const queryString = searchParams.toString();
    const endpoint = queryString ? `/api/v1/market-indicators?${queryString}` : '/api/v1/market-indicators';
    return request(endpoint);
  },
};
