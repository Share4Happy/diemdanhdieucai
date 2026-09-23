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
    
    // Auto-create overlay if missing
    if (!this.sidebarOverlay) {
      const overlay = document.createElement('div');
      overlay.className = 'sidebar-overlay';
      document.body.appendChild(overlay);
      this.sidebarOverlay = overlay;
    }

    // Auto-inject mobile hamburger button if missing
    let mobileBtn = document.querySelector('.mobile-menu-btn');
    if (!mobileBtn) {
      const headerLeft = document.querySelector('.header-left');
      mobileBtn = document.createElement('button');
      mobileBtn.type = 'button';
      mobileBtn.title = 'Mở Menu Điều Hướng';
      mobileBtn.setAttribute('aria-label', 'Mở Menu Điều Hướng');
      mobileBtn.innerHTML = '<i class="fa-solid fa-bars"></i>';
      if (headerLeft) {
        mobileBtn.className = 'mobile-menu-btn';
        headerLeft.prepend(mobileBtn);
      } else {
        mobileBtn.className = 'mobile-menu-btn floating-mobile-btn';
        document.body.appendChild(mobileBtn);
      }
    }
    this.mobileMenuBtn = mobileBtn;

    if (!this.sidebar) return;

    // Tự động render menu điều hướng từ 1 nguồn cấu hình duy nhất (Single Source of Truth)
    this.renderFullSidebar();

    // Apply initial state
    if (this.isCollapsed && !this.isMobile) {
      this.sidebar.classList.add('collapsed');
    }

    // Setup event listeners
    this.setupEventListeners();
    this.handleResize();
    this.setupUserNav();
  }

  renderFullSidebar() {
    if (!this.sidebar) return;

    // Nếu thẻ sidebar rỗng thì tự động tạo đầy đủ cấu trúc khung
    if (!this.sidebar.querySelector('.sidebar-header')) {
      this.sidebar.innerHTML = `
        <div class="sidebar-header">
            <div class="sidebar-logo">ĐC</div>
            <div class="sidebar-brand-text">
                <span class="brand-title">THPT ĐIỀU CẢI</span>
                <span class="brand-subtitle">AI CAMERA</span>
            </div>
        </div>
        <nav class="sidebar-nav">
            <ul class="sidebar-nav-list"></ul>
        </nav>
        <div class="sidebar-footer">
            <div class="sidebar-user-profile" id="sidebarUserProfile" title="Thông tin tài khoản">
                <div class="sidebar-user-avatar" id="sidebarUserAvatar">A</div>
                <div class="sidebar-user-info">
                    <span class="sidebar-user-name" id="sidebarUserName">Admin</span>
                    <span class="sidebar-user-role" id="sidebarUserRole">Quản Trị Viên</span>
                </div>
                <button class="sidebar-logout-btn" type="button" id="sidebarLogoutBtn" title="Đăng Xuất">
                    <i class="fa-solid fa-right-from-bracket"></i>
                </button>
            </div>
        </div>
      `;
    }

    this.renderSidebarNav();
  }

  renderSidebarNav() {
    if (!this.sidebar) return;
    const navList = this.sidebar.querySelector('.sidebar-nav-list');
    if (!navList) return;

    // CẤU HÌNH TẬP TRUNG TẤT CẢ CÁC TABS MENU CỦA HỆ THỐNG (Chỉ cần sửa tại đây sẽ tự động áp dụng mọi trang)
    const NAV_ITEMS = [
      { href: 'index.html', icon: 'fa-chart-line', text: 'Dashboard' },
      { href: 'cameras.html', icon: 'fa-video', text: 'Camera & Lớp Học' },
      { href: 'roi-config.html', icon: 'fa-draw-polygon', text: 'Vùng ROI' },
      { href: 'reports.html', icon: 'fa-file-excel', text: 'Báo Cáo & Dữ Liệu' },
      { href: 'notifications.html', icon: 'fa-paper-plane', text: 'Thông Báo' },
      { href: 'users.html', icon: 'fa-user-gear', text: 'Tài Khoản', adminOnly: true }
    ];

    const currentPath = window.location.pathname.toLowerCase();

    navList.innerHTML = NAV_ITEMS.map(item => {
      const pageName = item.href.replace('.html', '').toLowerCase();
      const isHome = (currentPath === '/' || currentPath === '' || currentPath.endsWith('/index.html') || currentPath.endsWith('/index')) && pageName === 'index';
      const isActive = isHome || (pageName !== 'index' && currentPath.includes(pageName)) || currentPath.includes(item.href.toLowerCase());
      const adminClass = item.adminOnly ? ' nav-admin-only' : '';
      const activeClass = isActive ? ' active' : '';

      return `
        <li class="sidebar-nav-item${adminClass}">
            <a href="${item.href}" class="sidebar-nav-link${activeClass}">
                <span class="sidebar-nav-icon"><i class="fa-solid ${item.icon}"></i></span>
                <span class="sidebar-nav-text">${item.text}</span>
            </a>
        </li>
      `;
    }).join('');

    // Đồng bộ quyền hiển thị cho các mục admin
    try {
      const role = localStorage.getItem('currentUserRole');
      const isAdmin = role === 'admin';
      this.sidebar.querySelectorAll('.nav-admin-only').forEach(el => {
        el.hidden = !isAdmin;
        if (isAdmin) el.classList.add('is-visible');
        else el.classList.remove('is-visible');
      });
    } catch (e) {}
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

      try {
        localStorage.removeItem('currentUserRole');
        localStorage.removeItem('currentUser');
      } catch (e) {}

      if (response.ok) {
        window.location.href = '/login.html';
      } else {
        alert('Không thể đăng xuất. Vui lòng thử lại.');
      }
    } catch (err) {
      console.error('Logout error:', err);
      try {
        localStorage.removeItem('currentUserRole');
        localStorage.removeItem('currentUser');
      } catch (e) {}
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
// Attach to window for global access
window.AppShell = AppShell;
