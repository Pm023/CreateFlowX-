/* CreateFlowX (CFX) Client Auth Management & Theme Controller */

const auth = {
  /**
   * Registers a new user account, then automatically logs them in.
   */
  async register(fullName, email, password) {
    // 1. Call register endpoint
    await api.post("/auth/register", {
      email: email,
      password: password,
      full_name: fullName
    });

    // 2. Perform auto login
    return await this.login(email, password);
  },

  /**
   * Log into account. Caches token & profile, then redirects to dashboard.
   */
  async login(email, password) {
    const data = await api.post("/auth/login", {
      email: email,
      password: password
    });

    // Cache user credentials
    localStorage.setItem("cfx_token", data.access_token);
    localStorage.setItem("cfx_user", JSON.stringify(data.user));

    return data;
  },

  /**
   * Log out of current session. Clears caches and redirects.
   */
  logout() {
    localStorage.removeItem("cfx_token");
    localStorage.removeItem("cfx_user");
    window.location.href = "login.html";
  },

  /**
   * Checks if user is authenticated
   */
  isAuthenticated() {
    return localStorage.getItem("cfx_token") !== null;
  },

  /**
   * Retrieves cached user profile object
   */
  getCurrentUser() {
    const userStr = localStorage.getItem("cfx_user");
    try {
      return userStr ? JSON.parse(userStr) : null;
    } catch (e) {
      return null;
    }
  },

  /**
   * Guard function: Redirects to login if user isn't authenticated
   */
  guardRoute() {
    if (!this.isAuthenticated()) {
      window.location.href = "login.html";
    }
  },

  /**
   * Guard function for authentication pages: redirects to dashboard if already logged in
   */
  guardAuthPages() {
    if (this.isAuthenticated()) {
      window.location.href = "dashboard.html";
    }
  },

  /**
   * Global Theme Manager (Light/Dark Mode toggle)
   */
  initTheme() {
    // Get stored theme or default to light theme
    const currentTheme = localStorage.getItem("cfx_theme") || "light";
    document.documentElement.setAttribute("data-theme", currentTheme);
    this.updateThemeToggleIcon(currentTheme);
  },

  toggleTheme() {
    const currentTheme = document.documentElement.getAttribute("data-theme");
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("cfx_theme", newTheme);
    this.updateThemeToggleIcon(newTheme);
  },

  updateThemeToggleIcon(theme) {
    const toggleBtn = document.querySelector(".theme-toggle i");
    if (!toggleBtn) return;
    
    if (theme === "dark") {
      toggleBtn.className = "ri-sun-line"; // Assuming Remix Icon, or standard replacement
    } else {
      toggleBtn.className = "ri-moon-line";
    }
  }
};

// Initialize theme immediately on script import
document.addEventListener("DOMContentLoaded", () => {
  auth.initTheme();
});
