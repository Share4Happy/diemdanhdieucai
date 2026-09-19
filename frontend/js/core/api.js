/**
 * API Client for THPT Điều Cải Attendance System
 * Centralized API communication with error handling
 */

class APIClient {
  constructor(baseURL = '') {
    this.baseURL = baseURL || CONFIG?.API_BASE_URL || window.location.origin;
  }

  /**
   * Make HTTP request with error handling
   * @param {string} url - Endpoint URL
   * @param {object} options - Fetch options
   * @returns {Promise<any>} Response data
   */
  async request(url, options = {}) {
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
      },
    };

    const mergedOptions = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(`${this.baseURL}${url}`, mergedOptions);
      
      // Handle non-JSON responses (e.g., file downloads)
      const contentType = response.headers.get('content-type');
      if (contentType && !contentType.includes('application/json')) {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response;
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || data.message || `HTTP ${response.status}`);
      }

      return data;
    } catch (error) {
      console.error('API Request Error:', error);
      throw error;
    }
  }

  /**
   * GET request
   */
  async get(url, options = {}) {
    return this.request(url, { ...options, method: 'GET' });
  }

  /**
   * POST request
   */
  async post(url, data = {}, options = {}) {
    return this.request(url, {
      ...options,
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * PUT request
   */
  async put(url, data = {}, options = {}) {
    return this.request(url, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  /**
   * DELETE request
   */
  async delete(url, options = {}) {
    return this.request(url, { ...options, method: 'DELETE' });
  }

  /**
   * Upload file with FormData
   */
  async upload(url, formData, options = {}) {
    const uploadOptions = {
      ...options,
      method: 'POST',
      body: formData,
    };
    
    // Remove Content-Type header to let browser set it with boundary
    delete uploadOptions.headers;
    
    return this.request(url, uploadOptions);
  }
}

// Create singleton instance
const api = new APIClient();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { APIClient, api };
}
