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

    // Cache user settings if returned
    if (data.user && data.user.settings) {
      localStorage.setItem("cfx_settings", JSON.stringify(data.user.settings));
      localStorage.setItem("cfx_theme", data.user.settings.theme);
    }

    return data;
  },

  /**
   * Log out of current session. Clears caches and redirects.
   */
  logout() {
    localStorage.removeItem("cfx_token");
    localStorage.removeItem("cfx_user");
    localStorage.removeItem("cfx_settings");
    const isSubdir = window.location.pathname.includes("/admin");
    window.location.href = isSubdir ? "../login.html" : "login.html";
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
      const isSubdir = window.location.pathname.includes("/admin");
      window.location.href = isSubdir ? "../login.html" : "login.html";
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

    // Eager load preferences from database if logged in
    if (this.isAuthenticated()) {
      this.loadSettings();
    }
  },

  async toggleTheme() {
    const currentTheme = document.documentElement.getAttribute("data-theme");
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("cfx_theme", newTheme);
    this.updateThemeToggleIcon(newTheme);

    // Sync to database settings
    const settings = this.getCurrentSettings();
    settings.theme = newTheme;
    localStorage.setItem("cfx_settings", JSON.stringify(settings));

    if (this.isAuthenticated()) {
      try {
        await api.put("/settings/", {
          theme: newTheme,
          currency: settings.currency,
          date_format: settings.date_format
        });
      } catch (e) {
        console.error("Theme preference sync failed:", e);
      }
    }
  },

  updateThemeToggleIcon(theme) {
    const toggleBtn = document.querySelector(".theme-toggle i");
    if (!toggleBtn) return;
    
    if (theme === "dark") {
      toggleBtn.className = "ri-sun-line"; 
    } else {
      toggleBtn.className = "ri-moon-line";
    }
  },

  /* Central Workspace Preferences Formatting Helpers */
  getCurrentSettings() {
    const settingsStr = localStorage.getItem("cfx_settings");
    try {
      return settingsStr ? JSON.parse(settingsStr) : { theme: "light", currency: "INR", date_format: "DD/MM/YYYY" };
    } catch (e) {
      return { theme: "light", currency: "INR", date_format: "DD/MM/YYYY" };
    }
  },

  async loadSettings() {
    try {
      const settings = await api.get("/settings/");
      localStorage.setItem("cfx_settings", JSON.stringify(settings));
      localStorage.setItem("cfx_theme", settings.theme);
      
      // Update theme to match DB configuration
      document.documentElement.setAttribute("data-theme", settings.theme);
      this.updateThemeToggleIcon(settings.theme);
      
      return settings;
    } catch (e) {
      console.error("Failed to load settings from server:", e);
      return this.getCurrentSettings();
    }
  },

  getCurrencySymbol() {
    const settings = this.getCurrentSettings();
    const currency = settings.currency || "INR";
    if (currency === 'USD') return '$';
    if (currency === 'EUR') return '€';
    if (currency === 'GBP') return '£';
    return '₹';
  },

  formatCurrency(amount) {
    const settings = this.getCurrentSettings();
    const currency = settings.currency || "INR";
    
    let locale = 'en-IN';
    if (currency === 'USD') locale = 'en-US';
    else if (currency === 'EUR') locale = 'de-DE';
    else if (currency === 'GBP') locale = 'en-GB';
    
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currency,
      maximumFractionDigits: 0
    }).format(amount);
  },

  formatDate(dateString) {
    if (!dateString) return "N/A";
    
    let date;
    if (dateString instanceof Date) {
      date = dateString;
    } else {
      const cleanDate = dateString.split("T")[0];
      const parts = cleanDate.split("-");
      if (parts.length === 3) {
        date = new Date(parts[0], parts[1] - 1, parts[2]);
      } else {
        date = new Date(dateString);
      }
    }
    
    if (isNaN(date.getTime())) return "N/A";
    
    const settings = this.getCurrentSettings();
    const fmt = settings.date_format || "DD/MM/YYYY";
    
    const dd = String(date.getDate()).padStart(2, '0');
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const yyyy = date.getFullYear();
    
    if (fmt === "MM/DD/YYYY") {
      return `${mm}/${dd}/${yyyy}`;
    } else if (fmt === "YYYY-MM-DD") {
      return `${yyyy}-${mm}-${dd}`;
    } else {
      return `${dd}/${mm}/${yyyy}`;
    }
  }
};

// Initialize theme immediately on script import
document.addEventListener("DOMContentLoaded", () => {
  auth.initTheme();

  // Show admin link if user is admin
  const user = auth.getCurrentUser();
  if (user && user.role === "admin") {
    const adminLink = document.getElementById("sidebar-admin-link");
    if (adminLink) {
      adminLink.classList.remove("hidden");
    }
  }
});
