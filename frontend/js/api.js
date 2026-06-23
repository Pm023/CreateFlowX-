/* CreateFlowX (CFX) Central API Fetch Wrapper */

const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://127.0.0.1:8000/api/v1"
  : "https://createflowx-production.up.railway.app/api/v1";


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
    if (response.status === 503) {
      const data = await response.json().catch(() => ({}));
      alert("System Maintenance: " + (data.detail || "The platform is currently undergoing maintenance. Please try again later."));
      localStorage.removeItem("cfx_token");
      localStorage.removeItem("cfx_user");
      localStorage.removeItem("cfx_settings");
      const isSubdir = window.location.pathname.includes("/admin");
      window.location.href = isSubdir ? "../login.html?maintenance=true" : "login.html?maintenance=true";
      throw new Error(data.detail || "System under maintenance.");
    }

    if (response.status === 401) {
      // Clear token and redirect to login if unauthorized
      localStorage.removeItem("cfx_token");
      localStorage.removeItem("cfx_user");
      
      // Prevent infinite redirect loop if already on login/register pages
      const currentPath = window.location.pathname;
      if (!currentPath.includes("login.html") && !currentPath.includes("register.html") && !currentPath.includes("index.html") && currentPath !== "/") {
        const isSubdir = currentPath.includes("/admin");
        window.location.href = isSubdir ? "../login.html?expired=true" : "login.html?expired=true";
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
