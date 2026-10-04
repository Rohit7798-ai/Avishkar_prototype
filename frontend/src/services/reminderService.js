import { request } from './api';

export const reminderService = {
  /**
   * Get weekly observation reminder for a crop.
   * @param {number} cropId
   * @returns {Promise<{ id: number, crop_id: number, enabled: boolean, weekday: string, reminder_time: string, created_at: string, updated_at: string }>}
   */
  async getReminder(cropId) {
    return request(`/api/v1/crops/${cropId}/observation-reminder`);
  },

  /**
   * Create or initialize weekly observation reminder for a crop.
   * @param {number} cropId
   * @param {{ enabled?: boolean, weekday: string, reminder_time: string }} data
   * @returns {Promise<any>}
   */
  async createReminder(cropId, data) {
    return request(`/api/v1/crops/${cropId}/observation-reminder`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update weekly observation reminder for a crop.
   * @param {number} cropId
   * @param {{ enabled?: boolean, weekday?: string, reminder_time?: string }} data
   * @returns {Promise<any>}
   */
  async updateReminder(cropId, data) {
    return request(`/api/v1/crops/${cropId}/observation-reminder`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete weekly observation reminder for a crop.
   * @param {number} cropId
   * @returns {Promise<void>}
   */
  async deleteReminder(cropId) {
    return request(`/api/v1/crops/${cropId}/observation-reminder`, {
      method: 'DELETE',
    });
  },
};
