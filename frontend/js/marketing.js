/**
 * CreateFlowX Public Landing Page Refinement & UX Animations
 * Handles: Mockup tab switches, simulated live dashboard actions, mouse-based parallax, scroll triggers
 */

// Tab Swapping Logic
window.switchMockupTab = function(tabId, buttonElement) {
  // Find all mockup buttons in the mockup sidebar and deactivate them
  const sidebar = buttonElement.closest('div');
  if (sidebar) {
    sidebar.querySelectorAll('.mockup-sidebar-btn').forEach(btn => btn.classList.remove('active'));
  }
  buttonElement.classList.add('active');

  // Deactivate all panels
  const panelParent = document.getElementById(tabId).parentNode;
  if (panelParent) {
    panelParent.querySelectorAll('.mockup-panel').forEach(panel => {
      panel.classList.remove('active');
    });
  }

  // Activate target panel
  const targetPanel = document.getElementById(tabId);
  if (targetPanel) {
    targetPanel.classList.add('active');

    // Run animations specific to the active panel
    if (tabId === 'mockup-projects') {
      animateMockupProjects();
    } else if (tabId === 'mockup-dashboard') {
      animateMockupDashboard();
    } else if (tabId === 'mockup-analytics') {
      animateMockupAnalytics();
    }
  }
};

// Counter Number Animation
function animateValue(id, start, end, duration, prefix = '', suffix = '') {
  const obj = document.getElementById(id);
  if (!obj) return;
  
  let startTimestamp = null;
  const step = (timestamp) => {
    if (!startTimestamp) startTimestamp = timestamp;
    const progress = Math.min((timestamp - startTimestamp) / duration, 1);
    const value = Math.floor(progress * (end - start) + start);
    
    // Format currency if needed
    if (prefix === '₹') {
      obj.innerHTML = prefix + value.toLocaleString('en-IN');
    } else {
      obj.innerHTML = prefix + value + suffix;
    }
    
    if (progress < 1) {
      window.requestAnimationFrame(step);
    }
  };
  window.requestAnimationFrame(step);
}

// Animate dashboard elements
let revenueValue = 125000;
let projectsCount = 10;
let tasksCount = 14;

function animateMockupDashboard() {
  animateValue("mockup-count-projects", 0, projectsCount, 850);
  animateValue("mockup-count-tasks", 0, tasksCount, 850);
  animateValue("mockup-count-revenue", 0, revenueValue, 1050, '₹');
  animateValue("mockup-count-clients", 0, 8, 850);

  // SVG Chart path drawing animation
  const chartPath = document.querySelector('.chart-path');
  if (chartPath) {
    const length = chartPath.getTotalLength();
    chartPath.style.transition = 'none';
    chartPath.style.strokeDasharray = length + ' ' + length;
    chartPath.style.strokeDashoffset = length;
    chartPath.getBoundingClientRect(); // trigger reflow
    chartPath.style.transition = 'stroke-dashoffset 1.5s ease-in-out';
    chartPath.style.strokeDashoffset = '0';
  }
}

// Animate projects page progress bars
function animateMockupProjects() {
  const bars = [
    { fillId: 'mockup-proj-fill-1', textId: 'mockup-proj-text-1', target: 75 },
    { fillId: 'mockup-proj-fill-2', textId: 'mockup-proj-text-2', target: 90 },
    { fillId: 'mockup-proj-fill-3', textId: 'mockup-proj-text-3', target: 40 }
  ];

  bars.forEach(bar => {
    const fillEl = document.getElementById(bar.fillId);
    const textEl = document.getElementById(bar.textId);
    if (fillEl && textEl) {
      fillEl.style.width = '0%';
      textEl.innerHTML = '0%';
      setTimeout(() => {
        fillEl.style.width = bar.target + '%';
        animateValue(bar.textId, 0, bar.target, 1200, '', '%');
      }, 50);
    }
  });
}

// Animate analytics SVG paths
function animateMockupAnalytics() {
  const chartPath = document.querySelector('.chart-path-2');
  if (chartPath) {
    const length = chartPath.getTotalLength();
    chartPath.style.transition = 'none';
    chartPath.style.strokeDasharray = length + ' ' + length;
    chartPath.style.strokeDashoffset = length;
    chartPath.getBoundingClientRect(); // trigger reflow
    chartPath.style.transition = 'stroke-dashoffset 1.5s ease-in-out';
    chartPath.style.strokeDashoffset = '0';
  }
}

// Live simulation actions
function runDashboardSimulation() {
  setInterval(() => {
    const activePanel = document.querySelector('.mockup-panel.active');
    if (!activePanel) return;

    if (activePanel.id === 'mockup-dashboard') {
      const rand = Math.random();
      if (rand < 0.45) {
        // Increment Revenue
        const increment = Math.floor(Math.random() * 4500) + 1500;
        const oldRevenue = revenueValue;
        revenueValue += increment;
        animateValue("mockup-count-revenue", oldRevenue, revenueValue, 1500, '₹');
        
        // Show pulse on notifications
        const pulse = document.getElementById('mockup-notif-pulse');
        if (pulse) {
          pulse.style.display = 'block';
        }
      } else if (rand < 0.8) {
        // Toggle Priority Task Completion
        const task1 = document.getElementById('mockup-task-icon-1');
        const taskText1 = document.getElementById('mockup-task-text-1');
        if (task1 && taskText1) {
          const isCompleted = task1.classList.contains('ri-checkbox-circle-fill');
          if (!isCompleted) {
            task1.className = 'ri-checkbox-circle-fill';
            task1.style.color = '#10b981';
            taskText1.style.textDecoration = 'line-through';
            taskText1.style.color = 'var(--text-muted)';
            tasksCount = Math.max(0, tasksCount - 1);
            document.getElementById('mockup-count-tasks').innerHTML = tasksCount;
          } else {
            task1.className = 'ri-checkbox-blank-circle-line';
            task1.style.color = '#7c3aed';
            taskText1.style.textDecoration = 'none';
            taskText1.style.color = 'var(--text-primary)';
            tasksCount += 1;
            document.getElementById('mockup-count-tasks').innerHTML = tasksCount;
          }
        }
      }
    } else if (activePanel.id === 'mockup-projects') {
      // Periodically increase progress bar 1
      const fillEl = document.getElementById('mockup-proj-fill-1');
      const textEl = document.getElementById('mockup-proj-text-1');
      if (fillEl && textEl) {
        let current = parseInt(textEl.innerHTML);
        if (current < 95) {
          let next = current + 3;
          fillEl.style.width = next + '%';
          textEl.innerHTML = next + '%';
        }
      }
    }
  }, 8000);
}

// 3D Parallax Mouse Hover Effect on Hero Mockup
function initMockupParallax() {
  const mockupWrapper = document.querySelector('.hero-mockup-wrapper');
  const heroSection = document.querySelector('.market-hero');
  if (!mockupWrapper || !heroSection) return;

  heroSection.addEventListener('mousemove', (e) => {
    const rect = mockupWrapper.getBoundingClientRect();
    const x = e.clientX - (rect.left + rect.width / 2);
    const y = e.clientY - (rect.top + rect.height / 2);
    
    // Normalize coordinates
    const tiltX = (y / (rect.height / 2)) * -4; // Max tilt 4 degrees
    const tiltY = (x / (rect.width / 2)) * 4;
    
    mockupWrapper.style.transform = `perspective(1000px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) translateY(-5px)`;
    mockupWrapper.style.transition = 'transform 0.1s ease-out';
  });

  heroSection.addEventListener('mouseleave', () => {
    mockupWrapper.style.transform = 'perspective(1000px) rotateX(2deg) rotateY(0deg) translateY(0)';
    mockupWrapper.style.transition = 'transform 0.5s ease-out';
  });
}

// Scroll Reveal Observer
function initScrollReveal() {
  const revealElements = document.querySelectorAll('.reveal-fade-up, .reveal-scale-in, .reveal-stagger');
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('active');
        
        // If it has stagger class, also make children active
        if (entry.target.classList.contains('reveal-stagger')) {
          entry.target.querySelectorAll('*').forEach(child => {
            child.classList.add('active');
          });
        }
        
        observer.unobserve(entry.target); // Trigger only once
      }
    });
  }, {
    threshold: 0.15,
    rootMargin: '0px 0px -50px 0px'
  });

  revealElements.forEach(el => observer.observe(el));
}

// Initialize everything on load
document.addEventListener("DOMContentLoaded", () => {
  animateMockupDashboard();
  runDashboardSimulation();
  initMockupParallax();
  initScrollReveal();
});
