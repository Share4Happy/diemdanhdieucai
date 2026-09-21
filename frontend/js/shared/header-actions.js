/**
 * Header Action Buttons Controller
 * Handles notification bell, settings gear, and mobile menu
 */

class HeaderActions {
    constructor() {
        this.init();
    }

    init() {
        this.bindNotificationButton();
        this.bindSettingsButton();
        this.bindMobileMenuButton();
    }

    /**
     * Notification Bell - Show live notifications gathered from system APIs
     */
    bindNotificationButton() {
        const bellBtn = document.querySelector('.header-action-btn[title="Thông báo"]');
        if (!bellBtn) return;

        bellBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.openNotificationDropdown(bellBtn);
        });

        // Badge with real unread count
        this.refreshBadge();
    }

    fetchJSON(endpoint) {
        const base = (window.location.protocol === 'file:' || (!window.location.origin.includes(':8000') && !window.location.origin.includes(':80')))
            ? 'http://localhost:8000'
            : '';
        return fetch(`${base}${endpoint}`, {
            headers: { 'Accept': 'application/json' }
        }).then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
        });
    }

    /**
     * Thu thập các thông báo thật từ dữ liệu hệ thống đang chạy
     */
    async buildNotifications() {
        const items = [];
        const settle = (p) => p.then(v => v).catch(() => null);

        const [att, cams, reports, zaloStatus, distStatus] = await Promise.all([
            settle(this.fetchJSON('/api/attendance/latest')),
            settle(this.fetchJSON('/api/cameras')),
            settle(this.fetchJSON('/api/reports/list')),
            settle(this.fetchJSON('/api/reports/zalo-status')),
            settle(this.fetchJSON('/api/reports/distribution-status'))
        ]);

        // 1. Phiên điểm danh gần nhất
        const session = att && att.session;
        if (session) {
            const at = session.scan_date ? `${session.scan_date} ${session.scan_time || ''}` : 'gần nhất';
            if (session.total_absent > 0) {
                items.push({
                    type: 'warning',
                    icon: 'fa-triangle-exclamation',
                    title: 'Có học sinh vắng mặt',
                    desc: `Phiên ${at}: vắng ${session.total_absent}/${session.total_standard} học sinh`,
                    time: session.scan_time || ''
                });
            } else {
                items.push({
                    type: 'success',
                    icon: 'fa-check-circle',
                    title: 'Điểm danh hoàn tất',
                    desc: `Phiên ${at}: ${session.total_present}/${session.total_standard} học sinh có mặt`,
                    time: session.scan_time || ''
                });
            }
        }

        // 2. Camera chưa kích hoạt
        if (cams && cams.cameras) {
            const inactive = (cams.cameras || []).filter(c => !c.is_active);
            if (inactive.length > 0) {
                const names = inactive.slice(0, 3).map(c => c.name).join(', ');
                items.push({
                    type: 'warning',
                    icon: 'fa-video-slash',
                    title: `${inactive.length} camera chưa kích hoạt`,
                    desc: names + (inactive.length > 3 ? ` và ${inactive.length - 3} camera khác` : ''),
                    time: 'Cấu hình'
                });
            }
        }

        // 3. Báo cáo Excel mới nhất
        if (reports && reports.reports && reports.reports.length > 0) {
            const latest = reports.reports[0];
            items.push({
                type: 'primary',
                icon: 'fa-file-export',
                title: 'Báo cáo mới nhất',
                desc: `${latest.filename} (${latest.size_kb || ''} KB)`,
                time: latest.created_at || ''
            });
        }

        // 4. Kênh thông báo Zalo chưa cấu hình
        if (zaloStatus && zaloStatus.enabled) {
            const configured = zaloStatus.webhook_configured || zaloStatus.oa_configured || zaloStatus.bot_configured;
            if (!configured) {
                items.push({
                    type: 'warning',
                    icon: 'fa-comments',
                    title: 'Kênh thông báo Zalo chưa cấu hình',
                    desc: 'Vào Báo Cáo & Dữ Liệu để nhập API Key + Bot ID',
                    time: 'Cấu hình'
                });
            }
        }

        // 5. Email báo cáo thiếu SMTP
        if (distStatus && distStatus.email_enabled && !distStatus.smtp_configured) {
            items.push({
                type: 'warning',
                icon: 'fa-envelope',
                title: 'Email báo cáo thiếu SMTP',
                desc: 'Mật khẩu ứng dụng SMTP chưa được cấu hình',
                time: 'Cấu hình'
            });
        }

        if (items.length === 0) {
            items.push({
                type: 'success',
                icon: 'fa-circle-check',
                title: 'Không có thông báo mới',
                desc: 'Hệ thống đang hoạt động bình thường',
                time: 'Ngay bây giờ'
            });
        }

        return items;
    }

    renderNotificationList(listEl, items) {
        listEl.innerHTML = items.map(item => `
            <div class="notification-item unread">
                <div class="notification-icon ${item.type}">
                    <i class="fa-solid ${item.icon}"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-title">${item.title}</div>
                    <div class="notification-desc">${item.desc || ''}</div>
                    <div class="notification-time">${item.time || ''}</div>
                </div>
            </div>
        `).join('');
    }

    async openNotificationDropdown(button) {
        // Remove existing dropdown
        const existing = document.querySelector('.notification-dropdown');
        if (existing) {
            existing.remove();
            return;
        }

        // Create dropdown
        const dropdown = document.createElement('div');
        dropdown.className = 'notification-dropdown';
        dropdown.innerHTML = `
            <div class="notification-dropdown-header">
                <h4>Thông Báo</h4>
                <button class="notification-mark-read">Đánh dấu đã đọc</button>
            </div>
            <div class="notification-list">
                <div class="notification-item">
                    <div class="notification-icon primary">
                        <i class="fa-solid fa-spinner fa-spin"></i>
                    </div>
                    <div class="notification-content">
                        <div class="notification-title">Đang tải thông báo...</div>
                    </div>
                </div>
            </div>
            <div class="notification-dropdown-footer">
                <a href="reports.html" class="notification-view-all">Xem tất cả thông báo</a>
            </div>
        `;

        document.body.appendChild(dropdown);

        // Position below button
        const rect = button.getBoundingClientRect();
        dropdown.style.top = `${rect.bottom + 8}px`;
        dropdown.style.right = `${window.innerWidth - rect.right}px`;

        // Close on outside click
        setTimeout(() => {
            document.addEventListener('click', () => {
                dropdown.remove();
            }, { once: true });
        }, 0);

        // Mark as read button
        dropdown.querySelector('.notification-mark-read').addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.querySelectorAll('.notification-item').forEach(item => {
                item.classList.remove('unread');
            });
            this.updateNotificationBadge(0);
        });

        // Load live notifications
        const listEl = dropdown.querySelector('.notification-list');
        const items = await this.buildNotifications();
        if (!document.body.contains(dropdown)) return; // dropdown đã bị đóng
        this.renderNotificationList(listEl, items);
        this.updateNotificationBadge(items.length);
    }

    async refreshBadge() {
        try {
            const items = await this.buildNotifications();
            this.updateNotificationBadge(items.length);
        } catch (e) {
            // Bỏ qua lỗi, không hiện badge khi không kết nối được
        }
    }

    updateNotificationBadge(count) {
        const bellBtn = document.querySelector('.header-action-btn[title="Thông báo"]');
        if (!bellBtn) return;

        let badge = bellBtn.querySelector('.notification-badge');
        if (count > 0) {
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'notification-badge';
                bellBtn.style.position = 'relative';
                bellBtn.appendChild(badge);
            }
            badge.textContent = count > 9 ? '9+' : count;
        } else if (badge) {
            badge.remove();
        }
    }

    /**
     * Settings Gear - Open settings modal
     */
    bindSettingsButton() {
        const gearBtn = document.querySelector('.header-action-btn[title="Cài đặt"]');
        if (!gearBtn) return;

        gearBtn.addEventListener('click', () => {
            this.openSettingsModal();
        });
    }

    openSettingsModal() {
        // Create modal backdrop
        const backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop active';
        backdrop.innerHTML = `
            <div class="modal-content" style="max-width: 600px;">
                <div class="modal-header">
                    <h3><i class="fa-solid fa-gear"></i> Cài Đặt Hệ Thống</h3>
                    <button class="modal-close" id="settingsModalClose">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="settings-section">
                        <h4 class="settings-section-title">Thông Tin Hệ Thống</h4>
                        <div class="settings-item">
                            <label>Tên Trường</label>
                            <input type="text" class="form-control" value="THPT Điều Cải" readonly>
                        </div>
                        <div class="settings-item">
                            <label>Phiên Bản</label>
                            <input type="text" class="form-control" value="v2.0 - Professional Dashboard" readonly>
                        </div>
                    </div>

                    <div class="settings-section">
                        <h4 class="settings-section-title">Cấu Hình Điểm Danh</h4>
                        <div class="settings-item">
                            <label>
                                <input type="checkbox" checked> Tự động điểm danh lúc 06:45 sáng
                            </label>
                        </div>
                        <div class="settings-item">
                            <label>
                                <input type="checkbox" checked> Gửi email thông báo tự động
                            </label>
                        </div>
                        <div class="settings-item">
                            <label>
                                <input type="checkbox"> Gửi thông báo Zalo
                            </label>
                        </div>
                    </div>

                    <div class="settings-section">
                        <h4 class="settings-section-title">Hiển Thị</h4>
                        <div class="settings-item">
                            <label>Chế độ giao diện</label>
                            <select class="form-control">
                                <option selected>Sáng (Light)</option>
                                <option>Tối (Dark)</option>
                                <option>Tự động (Auto)</option>
                            </select>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" id="settingsCancelBtn">Đóng</button>
                    <button class="btn btn-primary" id="settingsSaveBtn">Lưu Thay Đổi</button>
                </div>
            </div>
        `;

        document.body.appendChild(backdrop);

        // Bind close buttons
        backdrop.querySelector('#settingsModalClose').addEventListener('click', () => backdrop.remove());
        backdrop.querySelector('#settingsCancelBtn').addEventListener('click', () => backdrop.remove());
        backdrop.querySelector('#settingsSaveBtn').addEventListener('click', () => {
            // TODO: Save settings to backend
            alert('Đã lưu cài đặt!');
            backdrop.remove();
        });

        // Close on backdrop click
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) {
                backdrop.remove();
            }
        });
    }

    /**
     * Mobile Menu Button - Toggle sidebar on mobile
     */
    bindMobileMenuButton() {
        const menuBtn = document.querySelector('.mobile-menu-btn');
        if (!menuBtn) return;

        menuBtn.addEventListener('click', () => {
            document.body.classList.toggle('sidebar-mobile-open');
        });
    }
}

// Auto-initialize
document.addEventListener('DOMContentLoaded', () => {
    new HeaderActions();
});
