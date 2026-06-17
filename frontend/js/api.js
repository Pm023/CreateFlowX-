/* CreateFlowX (CFX) Central API Fetch Wrapper */

const API_BASE_URL = "http://localhost:8000/api/v1";

const api = {
  /**
   * Helper to compile request headers (injects JWT token if available)
   */
  getHeaders(customHeaders = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...customHeaders,
    };
    
    const token = localStorage.getItem("cfx_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    
    return headers;
  },

  /**
   * Evaluates request response. If status is 401, clears invalid tokens and redirects.
   */
  async handleResponse(response) {
    if (response.status === 401) {
      // Clear token and redirect to login if unauthorized
      localStorage.removeItem("cfx_token");
      localStorage.removeItem("cfx_user");
      
      // Prevent infinite redirect loop if already on login/register pages
      const currentPath = window.location.pathname;
      if (!currentPath.includes("login.html") && !currentPath.includes("register.html") && !currentPath.includes("index.html") && currentPath !== "/") {
        window.location.href = "login.html?expired=true";
      }
    }
    
    const data = await response.json().catch(() => ({}));
    
    if (!response.ok) {
      const errorMsg = data.detail || "An unexpected error occurred.";
      throw new Error(errorMsg);
    }
    
    return data;
  },

  /**
   * GET Request
   */
  async get(endpoint, customHeaders = {}) {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "GET",
        headers: this.getHeaders(customHeaders),
      });
      return await this.handleResponse(response);
    } catch (error) {
      console.error(`API GET [${endpoint}] failed:`, error);
      throw error;
    }
  },

  /**
   * POST Request
   */
  async post(endpoint, body = {}, customHeaders = {}) {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: this.getHeaders(customHeaders),
        body: JSON.stringify(body),
      });
      return await this.handleResponse(response);
    } catch (error) {
      console.error(`API POST [${endpoint}] failed:`, error);
      throw error;
    }
  },

  /**
   * PUT Request
   */
  async put(endpoint, body = {}, customHeaders = {}) {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "PUT",
        headers: this.getHeaders(customHeaders),
        body: JSON.stringify(body),
      });
      return await this.handleResponse(response);
    } catch (error) {
      console.error(`API PUT [${endpoint}] failed:`, error);
      throw error;
    }
  },

  /**
   * DELETE Request
   */
  async delete(endpoint, customHeaders = {}) {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "DELETE",
        headers: this.getHeaders(customHeaders),
      });
      return await this.handleResponse(response);
    } catch (error) {
      console.error(`API DELETE [${endpoint}] failed:`, error);
      throw error;
    }
  }
};
