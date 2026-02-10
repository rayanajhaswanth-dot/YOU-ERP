/**
 * safeFetch - A robust fetch wrapper that prevents "body stream already used" errors
 * 
 * Problem: In JavaScript, Response.json() and Response.text() consume the body stream.
 * If you try to read the body twice (e.g., check if it's JSON, then parse), you get:
 * "TypeError: body stream already read"
 * 
 * Solution: This wrapper clones the response before attempting to parse,
 * and handles both JSON and text responses gracefully.
 */

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

/**
 * Safe fetch wrapper with automatic JSON/text handling
 * @param {string} endpoint - API endpoint (will be prefixed with BACKEND_URL)
 * @param {Object} options - Fetch options (method, headers, body, etc.)
 * @returns {Promise<{ok: boolean, status: number, data: any, error?: string}>}
 */
export const safeFetch = async (endpoint, options = {}) => {
  const url = endpoint.startsWith('http') ? endpoint : `${BACKEND_URL}${endpoint}`;
  
  // Default headers
  const headers = {
    ...options.headers,
  };
  
  // Add auth token if available
  const token = localStorage.getItem('token');
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  // Add Content-Type for JSON if body is an object (not FormData)
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }
  
  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });
    
    // Clone the response BEFORE reading the body
    // This allows us to try JSON first, then fall back to text
    const clonedResponse = response.clone();
    
    let data;
    const contentType = response.headers.get('content-type') || '';
    
    if (contentType.includes('application/json')) {
      // It's JSON, parse directly
      try {
        data = await response.json();
      } catch (jsonError) {
        // JSON parse failed, try text from cloned response
        data = await clonedResponse.text();
      }
    } else {
      // Not JSON, read as text
      data = await response.text();
      
      // Try to parse as JSON anyway (some servers don't set content-type correctly)
      try {
        data = JSON.parse(data);
      } catch {
        // Keep as text
      }
    }
    
    return {
      ok: response.ok,
      status: response.status,
      data,
      error: response.ok ? undefined : (data?.detail || data?.message || `HTTP ${response.status}`),
    };
    
  } catch (networkError) {
    // Network error (no internet, CORS, etc.)
    console.error('safeFetch network error:', networkError);
    return {
      ok: false,
      status: 0,
      data: null,
      error: networkError.message || 'Network error',
    };
  }
};

/**
 * Convenience methods for common HTTP verbs
 */
export const api = {
  get: (endpoint, options = {}) => 
    safeFetch(endpoint, { ...options, method: 'GET' }),
  
  post: (endpoint, body, options = {}) => 
    safeFetch(endpoint, { ...options, method: 'POST', body }),
  
  put: (endpoint, body, options = {}) => 
    safeFetch(endpoint, { ...options, method: 'PUT', body }),
  
  patch: (endpoint, body, options = {}) => 
    safeFetch(endpoint, { ...options, method: 'PATCH', body }),
  
  delete: (endpoint, options = {}) => 
    safeFetch(endpoint, { ...options, method: 'DELETE' }),
  
  /**
   * Upload file with FormData
   * @param {string} endpoint 
   * @param {FormData} formData 
   * @param {Object} options 
   */
  upload: async (endpoint, formData, options = {}) => {
    // Don't set Content-Type for FormData - browser will set it with boundary
    const headers = { ...options.headers };
    delete headers['Content-Type'];
    
    return safeFetch(endpoint, {
      ...options,
      method: 'POST',
      headers,
      body: formData,
    });
  },
};

export default safeFetch;
