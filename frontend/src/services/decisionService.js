/**
 * Decision Assessment API client service.
 * Fetches deterministic rule-based assessments for crop harvest readiness and mandi price momentum.
 */

import { request } from './api';

export const decisionService = {
  /**
   * Retrieves deterministic harvest assessment for a crop planting.
   * @param {number|string} cropId
   * @returns {Promise<{ crop_id: number, status: string, data_sufficiency: string, factors: Array<{ name: string, value: any, observation: string }> }>}
   */
  async getCropDecisionAssessment(cropId) {
    return request(`/api/v1/crops/${cropId}/decision-assessment`);
  },

  /**
   * Retrieves deterministic market trend assessment for a crop/market combination.
   * @param {Object} [params] - { crop_name, market_name }
   * @returns {Promise<{ crop_name: string|null, market_name: string|null, status: string, data_sufficiency: string, factors: Array<{ name: string, value: any, observation: string }> }>}
   */
  async getMarketDecisionAssessment(params = {}) {
    const searchParams = new URLSearchParams();
    if (params.crop_name && params.crop_name.trim()) {
      searchParams.append('crop_name', params.crop_name.trim());
    }
    if (params.market_name && params.market_name.trim()) {
      searchParams.append('market_name', params.market_name.trim());
    }
    const queryString = searchParams.toString();
    const endpoint = queryString
      ? `/api/v1/market-decision-assessment?${queryString}`
      : '/api/v1/market-decision-assessment';
    return request(endpoint);
  },
};
