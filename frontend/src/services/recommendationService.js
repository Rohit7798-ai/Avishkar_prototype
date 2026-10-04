/**
 * Recommendation Engine API client service.
 * Fetches decoupled, transparent Harvest and Sell recommendations
 * grounded strictly in recorded observations, indicators, decision engine rules, and ML baseline forecasts.
 */

import { request } from './api';

export const recommendationService = {
  /**
   * Retrieves decoupled Harvest and Sell recommendations for a crop planting.
   * @param {number|string} cropId
   * @returns {Promise<Object>} CropRecommendationResponse
   */
  async getCropRecommendation(cropId) {
    return request(`/api/v1/crops/${cropId}/recommendation`);
  },
};
