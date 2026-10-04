/**
 * AI Explanation Layer API client service.
 * Fetches farmer-friendly structured explanations grounded in Observed, Calculated,
 * Predicted, and Assessment data categories.
 */

import { request } from './api';

export const explanationService = {
  /**
   * Retrieves structured, farmer-friendly explanation for a crop planting.
   * @param {number|string} cropId
   * @returns {Promise<Object>} CropExplanationResponse
   */
  async getCropExplanation(cropId) {
    return request(`/api/v1/crops/${cropId}/explanation`);
  },
};
