/**
 * Centralized API client service for communicating with the FastAPI backend.
 * Provides standard request lifecycle, headers, JSON serialization, and error parsing.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

/**
 * Custom API Error carrying HTTP status code and response payload details.
 */
export class ApiError extends Error {
  constructor(message, status, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Execute an HTTP request against the API backend.
 * @param {string} endpoint - Relative path (e.g. '/api/v1/farms')
 * @param {RequestInit} [options={}] - Standard Fetch options
 * @returns {Promise<any>}
 */
export async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    Accept: 'application/json',
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...options.headers,
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    // 204 No Content has no body to parse
    if (response.status === 204) {
      return null;
    }

    let data = null;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      const text = await response.text();
      data = text ? text : null;
    }

    if (!response.ok) {
      let errorMessage = `Request failed with status ${response.status}`;
      if (data && typeof data === 'object') {
        if (typeof data.detail === 'string') {
          errorMessage = data.detail;
        } else if (Array.isArray(data.detail)) {
          // Pydantic validation error array
          errorMessage = data.detail.map((err) => err.msg || JSON.stringify(err)).join(', ');
        }
      } else if (typeof data === 'string' && data.trim()) {
        errorMessage = data;
      }
      throw new ApiError(errorMessage, response.status, data);
    }

    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Network / connection errors
    throw new ApiError(
      error.message || 'Unable to connect to the backend server. Please verify it is running.',
      0
    );
  }
}

/**
 * Health check query.
 * @returns {Promise<{ status: string, service: string }>}
 */
export async function checkHealth() {
  return request('/api/health');
}
