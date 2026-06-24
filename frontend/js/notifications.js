/**
 * CreateFlowX (CFX) Notifications Client Module
 */

const notificationsManager = {
  unreadCount: 0,
  notifications: [],

  init() {
    // Select elements
    this.bellBtn = document.getElementById("notifications-bell-btn");
    this.dropdown = document.getElementById("notifications-dropdown");
    this.dropdownList = document.getElementById("notifications-dropdown-list");
    this.badge = document.getElementById("notifications-unread-count");

    if (!this.bellBtn || !this.dropdown) {
      console.warn("Notifications bell or dropdown elements not found in DOM.");
      return;
    }

    // Toggle dropdown
    this.bellBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.toggleDropdown();
    });

    // Close dropdown on click outside
    document.addEventListener("click", (e) => {
      if (this.dropdown.classList.contains("active") && !this.dropdown.contains(e.target) && e.target !== this.bellBtn) {
        this.dropdown.classList.remove("active");
      }
    });

    // Initial load
    this.fetchAndUpdate();

    // Start background poll every 60 seconds
    setInterval(() => this.fetchAndUpdate(), 60000);
  },

  toggleDropdown() {
    const isActive = this.dropdown.classList.toggle("active");
    if (isActive) {
      // Refresh list on open
      this.fetchNotificationsList();
    }
  },

  async fetchAndUpdate() {
    try {
      // Fetch stats
      const stats = await api.get("/notifications/stats");
      this.unreadCount = stats.unread_count;
      this.updateBadge();
    } catch (err) {
      console.error("Failed to fetch notification stats:", err);
    }
  },

  updateBadge() {
    if (this.unreadCount > 0) {
      this.badge.innerText = this.unreadCount > 99 ? "99+" : this.unreadCount;
      this.badge.style.display = "flex";
    } else {
      this.badge.style.display = "none";
    }
  },

  async fetchNotificationsList() {
    try {
      this.dropdownList.innerHTML = `<li class="notification-dropdown-empty"><div class="spinner" style="border-top-color: var(--accent-color); width: 1.25rem; height: 1.25rem;"></div></li>`;
      
      // Fetch latest 5 notifications
      const data = await api.get("/notifications/?limit=5");
      this.notifications = data;
      this.renderDropdownList();
    } catch (err) {
      this.dropdownList.innerHTML = `<li class="notification-dropdown-empty">Failed to load notifications</li>`;
    }
  },

  getIconClass(type) {
    if (type.includes("client")) return "ri-user-star-line icon-client";
    if (type.includes("project")) return "ri-folders-line icon-project";
    if (type.includes("task")) return "ri-task-line icon-task";
    return "ri-error-warning-line icon-alert";
  },

  formatTime(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return "Yesterday";
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  },

  renderDropdownList() {
    if (this.notifications.length === 0) {
      this.dropdownList.innerHTML = `<li class="notification-dropdown-empty">No notifications</li>`;
      return;
    }

    this.dropdownList.innerHTML = "";
    this.notifications.forEach(notif => {
      const li = document.createElement("li");
      
      const iconClass = this.getIconClass(notif.notification_type);
      const isUnread = !notif.is_read;
      const timeAgo = this.formatTime(notif.created_at);

      li.innerHTML = `
        <a class="notification-dropdown-item ${isUnread ? 'unread' : ''}" onclick="notificationsManager.handleItemClick(event, ${notif.id})">
          <div class="notification-dropdown-item-icon ${iconClass}"></div>
          <div class="notification-dropdown-item-content">
            <div class="notification-dropdown-item-title">${notif.title}</div>
            <div class="notification-dropdown-item-desc">${notif.message}</div>
            <div class="notification-dropdown-item-time">${timeAgo}</div>
          </div>
        </a>
      `;
      this.dropdownList.appendChild(li);
    });
  },

  async handleItemClick(event, id) {
    event.preventDefault();
    try {
      // Mark as read in backend
      await api.put(`/notifications/${id}/read`);
      
      // Update local state and badge
      this.unreadCount = Math.max(0, this.unreadCount - 1);
      this.updateBadge();

      // Remove unread highlight locally
      const target = event.currentTarget;
      target.classList.remove("unread");

      // Close dropdown
      this.dropdown.classList.remove("active");
    } catch (err) {
      console.error("Failed to mark notification as read:", err);
    }
  },

  async markAllRead(event) {
    if (event) event.preventDefault();
    try {
      await api.put("/notifications/read-all");
      this.unreadCount = 0;
      this.updateBadge();
      
      // Update dropdown items style locally
      const unreadItems = this.dropdownList.querySelectorAll(".notification-dropdown-item.unread");
      unreadItems.forEach(item => item.classList.remove("unread"));
    } catch (err) {
      console.error("Failed to mark all as read:", err);
    }
  }
};

// Auto-initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  // Wait shortly to make sure api.js and auth.js are ready
  setTimeout(() => {
    notificationsManager.init();
    globalSearch.init();
  }, 100);
});

// Global Search Module
const globalSearch = {
  init() {
    this.searchInput = document.getElementById("sidebar-search");
    if (!this.searchInput) return;

    // Create search results container
    this.resultsContainer = document.createElement("div");
    this.resultsContainer.id = "global-search-results";
    this.resultsContainer.className = "global-search-results hidden";
    this.searchInput.parentNode.appendChild(this.resultsContainer);

    // Setup input listener with debounce
    let debounceTimer = null;
    this.searchInput.addEventListener("input", () => {
      clearTimeout(debounceTimer);
      const query = this.searchInput.value.trim();
      if (query.length < 2) {
        this.resultsContainer.innerHTML = "";
        this.resultsContainer.classList.add("hidden");
        return;
      }

      debounceTimer = setTimeout(() => {
        this.performSearch(query);
      }, 300);
    });

    // Close dropdown on click outside
    document.addEventListener("click", (e) => {
      if (!this.searchInput.contains(e.target) && !this.resultsContainer.contains(e.target)) {
        this.resultsContainer.classList.add("hidden");
      }
    });

    // Show dropdown on focus if input has value
    this.searchInput.addEventListener("focus", () => {
      if (this.searchInput.value.trim().length >= 2) {
        this.resultsContainer.classList.remove("hidden");
      }
    });

    // Setup global hotkey (Ctrl + /)
    document.addEventListener("keydown", (e) => {
      if (e.ctrlKey && e.key === "/") {
        e.preventDefault();
        this.searchInput.focus();
      }
    });
  },

  async performSearch(query) {
    try {
      this.resultsContainer.innerHTML = `
        <div style="padding: 12px; text-align: center; color: var(--text-muted); font-size: 0.8rem;">
          <div class="spinner" style="border-top-color: var(--accent-color); width: 1rem; height: 1rem; margin-right: 6px; display: inline-block;"></div> Searching...
        </div>
      `;
      this.resultsContainer.classList.remove("hidden");

      // Fire searches in parallel
      const [projects, tasks, clients, invoices] = await Promise.all([
        api.get("/projects/?search=" + encodeURIComponent(query)).catch(() => []),
        api.get("/tasks/?search=" + encodeURIComponent(query)).catch(() => []),
        api.get("/clients/?search=" + encodeURIComponent(query)).catch(() => []),
        api.get("/invoices/?search=" + encodeURIComponent(query)).catch(() => [])
      ]);

      let html = "";
      let totalResults = 0;

      // Render Clients
      if (clients && clients.length > 0) {
        html += `<div class="global-search-category">Clients</div>`;
        clients.forEach(c => {
          totalResults++;
          html += `
            <a href="clients.html" class="global-search-item">
              <i class="ri-user-star-line" style="color: var(--accent-color);"></i>
              <div style="flex:1;">
                <div style="font-weight: 600;">${this.escape(c.client_name)}</div>
                <div style="font-size: 0.72rem; color: var(--text-muted);">${this.escape(c.email || c.company_name || '')}</div>
              </div>
            </a>
          `;
        });
      }

      // Render Projects
      if (projects && projects.length > 0) {
        html += `<div class="global-search-category">Projects</div>`;
        projects.forEach(p => {
          totalResults++;
          html += `
            <a href="projects.html" class="global-search-item">
              <i class="ri-folders-line" style="color: #3b82f6;"></i>
              <div style="flex:1;">
                <div style="font-weight: 600;">${this.escape(p.project_name)}</div>
                <div style="font-size: 0.72rem; color: var(--text-muted);">${this.escape(p.client_name || '')} &bull; ${p.status}</div>
              </div>
            </a>
          `;
        });
      }

      // Render Tasks
      if (tasks && tasks.length > 0) {
        html += `<div class="global-search-category">Tasks</div>`;
        tasks.forEach(t => {
          totalResults++;
          html += `
            <a href="tasks.html" class="global-search-item">
              <i class="ri-task-line" style="color: #7c3aed;"></i>
              <div style="flex:1;">
                <div style="font-weight: 600;">${this.escape(t.task_name)}</div>
                <div style="font-size: 0.72rem; color: var(--text-muted);">${this.escape(t.project_name || '')} &bull; ${t.status}</div>
              </div>
            </a>
          `;
        });
      }

      // Render Invoices
      if (invoices && invoices.length > 0) {
        html += `<div class="global-search-category">Invoices</div>`;
        invoices.forEach(inv => {
          totalResults++;
          html += `
            <a href="invoices.html" class="global-search-item">
              <i class="ri-bill-line" style="color: #10b981;"></i>
              <div style="flex:1;">
                <div style="font-weight: 600;">Invoice #${this.escape(inv.invoice_number)}</div>
                <div style="font-size: 0.72rem; color: var(--text-muted);">${this.escape(inv.client_name || '')} &bull; ₹${inv.amount.toLocaleString('en-IN')} &bull; ${inv.status}</div>
              </div>
            </a>
          `;
        });
      }

      if (totalResults === 0) {
        this.resultsContainer.innerHTML = `
          <div style="padding: 12px; text-align: center; color: var(--text-muted); font-size: 0.8rem;">
            No results found for "${this.escape(query)}"
          </div>
        `;
      } else {
        this.resultsContainer.innerHTML = html;
      }

    } catch (err) {
      console.error("Global search failed:", err);
      this.resultsContainer.innerHTML = `
        <div style="padding: 12px; text-align: center; color: #ef4444; font-size: 0.8rem;">
          Error executing search
        </div>
      `;
    }
  },

  escape(str) {
    if (!str) return "";
    return str.toString().replace(/[&<>'"]/g, 
      tag => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        "'": '&#39;',
        '"': '&quot;'
      }[tag] || tag)
    );
  }
};
