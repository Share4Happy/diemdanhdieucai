/**
 * =====================================================
 * APP SHELL CONTROLLER - Sidebar, Navigation, Layout
 * =====================================================
 */

class AppShell {
  constructor() {
    this.sidebar = null;
    this.sidebarOverlay = null;
    this.toggleBtn = null;
    this.mobileMenuBtn = null;
    this.isCollapsed = this.getCollapsedState();
    this.isMobile = window.innerWidth <= 1024;

    this.init();
  }

  init() {
    this.sidebar = document.querySelector('.app-sidebar');
    this.sidebarOverlay = document.querySelector('.sidebar-overlay');
    this.toggleBtn = document.querySelector('.sidebar-toggle-btn');
    this.mobileMenuBtn = document.querySelector('.mobile-menu-btn');

    if (!this.sidebar) return;

    // Apply initial state
    if (this.isCollapsed && !this.isMobile) {
      this.sidebar.classList.add('collapsed');
    }

    // Setup event listeners
    this.setupEventListeners();
    this.setActiveNavItem();
    this.handleResize();
  }

  setupEventListeners() {
    // Toggle button
    if (this.toggleBtn) {
      this.toggleBtn.addEventListener('click', () => this.toggleSidebar());
    }

    // Mobile menu button
    if (this.mobileMenuBtn) {
      this.mobileMenuBtn.addEventListener('click', () => this.toggleMobileSidebar());
    }

    // Overlay click (mobile)
    if (this.sidebarOverlay) {
      this.sidebarOverlay.addEventListener('click', () => this.closeMobileSidebar());
    }

    // Window resize
    window.addEventListener('resize', () => this.handleResize());

    // Close mobile sidebar on nav link click
    const navLinks = this.sidebar?.querySelectorAll('.sidebar-nav-link');
    navLinks?.forEach(link => {
      link.addEventListener('click', () => {
        if (this.isMobile) {
          this.closeMobileSidebar();
        }
      });
    });
  }

  toggleSidebar() {
    if (this.isMobile) {
      this.toggleMobileSidebar();
    } else {
      this.isCollapsed = !this.isCollapsed;
      this.sidebar?.classList.toggle('collapsed');
      this.saveCollapsedState(this.isCollapsed);
    }
  }

  toggleMobileSidebar() {
    this.sidebar?.classList.toggle('mobile-open');
    this.sidebarOverlay?.classList.toggle('active');
    document.body.style.overflow = this.sidebar?.classList.contains('mobile-open') ? 'hidden' : '';
  }

  closeMobileSidebar() {
    this.sidebar?.classList.remove('mobile-open');
    this.sidebarOverlay?.classList.remove('active');
    document.body.style.overflow = '';
  }

  handleResize() {
    const wasMobile = this.isMobile;
    this.isMobile = window.innerWidth <= 1024;

    if (wasMobile !== this.isMobile) {
      // Reset states when switching between mobile/desktop
      if (this.isMobile) {
        this.sidebar?.classList.remove('collapsed');
        this.closeMobileSidebar();
      } else {
        this.closeMobileSidebar();
        if (this.isCollapsed) {
          this.sidebar?.classList.add('collapsed');
        }
      }
    }
  }

  setActiveNavItem() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.sidebar-nav-link');

    navLinks.forEach(link => {
      const href = link.getAttribute('href');
      if (href && currentPath.includes(href.replace('.html', ''))) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });
  }

  getCollapsedState() {
    const stored = localStorage.getItem('sidebar-collapsed');
    return stored === 'true';
  }

  saveCollapsedState(isCollapsed) {
    localStorage.setItem('sidebar-collapsed', isCollapsed.toString());
  }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.appShell = new AppShell();
  });
} else {
  window.appShell = new AppShell();
}

export default AppShell;
