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
    this.setupUserNav();
  }

  setupUserNav() {
    // Setup logout button (sidebar and header fallback)
    const logoutBtns = document.querySelectorAll('#sidebarLogoutBtn, #headerLogoutBtn');
    logoutBtns.forEach(btn => {
      btn.addEventListener('click', () => this.handleLogout());
    });

    // Display current user info
    this.displayUserInfo();
  }

  async displayUserInfo() {
    try {
      // Get current user from global window object (set by auth-guard)
      const user = window.currentUser;
      if (!user) return;

      const nameEls = document.querySelectorAll('#sidebarUserName, #headerUserName');
      const roleEls = document.querySelectorAll('#sidebarUserRole, #headerUserRole');
      const avatarEls = document.querySelectorAll('#sidebarUserAvatar, #headerUserAvatar');

      const displayName = user.full_name || user.email || 'Admin';
      const displayRole = user.role === 'admin' ? 'Quản Trị Viên' : 'Nhân Viên';
      const initial = displayName.charAt(0).toUpperCase();

      nameEls.forEach(el => {
        el.textContent = displayName;
        el.title = `${displayName} (${user.email || ''})`;
      });

      roleEls.forEach(el => {
        el.textContent = displayRole;
      });

      avatarEls.forEach(el => {
        el.textContent = initial;
        el.title = `${displayName} (${displayRole})`;
      });
    } catch (err) {
      console.error('Failed to display user info:', err);
    }
  }

  async handleLogout() {
    if (!confirm('Bạn có chắc chắn muốn đăng xuất?')) return;

    try {
      const response = await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });

      if (response.ok) {
        window.location.href = '/login.html';
      } else {
        alert('Không thể đăng xuất. Vui lòng thử lại.');
      }
    } catch (err) {
      console.error('Logout error:', err);
      alert('Lỗi kết nối. Vui lòng thử lại.');
    }
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
      if (!href) return;
      const pageName = href.replace('.html', '');
      const isHome = (currentPath === '/' || currentPath === '' || currentPath.endsWith('/index.html')) && pageName === 'index';
      if (isHome || (pageName !== 'index' && currentPath.includes(pageName)) || currentPath.includes(href)) {
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
