/**
 * Confirmation Dialog System
 * Beautiful, customizable confirmation dialogs for the entire app
 */

class ConfirmationDialog {
    constructor() {
        this.createModal();
        this.resolveCallback = null;
    }

    createModal() {
        // Remove existing modal if any
        const existing = document.getElementById('confirmationModal');
        if (existing) existing.remove();

        const modal = document.createElement('div');
        modal.id = 'confirmationModal';
        modal.className = 'confirmation-modal';
        modal.innerHTML = `
            <div class="confirmation-backdrop"></div>
            <div class="confirmation-container">
                <div class="confirmation-icon-wrapper">
                    <div class="confirmation-icon" id="confirmIcon">
                        <i class="fa-solid fa-circle-exclamation"></i>
                    </div>
                </div>
                <div class="confirmation-content">
                    <h3 class="confirmation-title" id="confirmTitle">Xác nhận</h3>
                    <p class="confirmation-message" id="confirmMessage">Bạn có chắc chắn muốn thực hiện hành động này?</p>
                </div>
                <div class="confirmation-actions">
                    <button type="button" class="btn btn-secondary" id="confirmCancelBtn">
                        Hủy bỏ
                    </button>
                    <button type="button" class="btn btn-danger" id="confirmOkBtn">
                        Xác nhận
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Event listeners
        modal.querySelector('#confirmCancelBtn').addEventListener('click', () => this.close(false));
        modal.querySelector('#confirmOkBtn').addEventListener('click', () => this.close(true));
        modal.querySelector('.confirmation-backdrop').addEventListener('click', () => this.close(false));

        // ESC key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.classList.contains('active')) {
                this.close(false);
            }
        });
    }

    show(options = {}) {
        const {
            title = 'Xác nhận',
            message = 'Bạn có chắc chắn muốn thực hiện hành động này?',
            confirmText = 'Xác nhận',
            cancelText = 'Hủy bỏ',
            type = 'warning', // warning, danger, info, success
            confirmClass = 'btn-danger'
        } = options;

        const modal = document.getElementById('confirmationModal');
        const iconEl = modal.querySelector('#confirmIcon');
        const titleEl = modal.querySelector('#confirmTitle');
        const messageEl = modal.querySelector('#confirmMessage');
        const confirmBtn = modal.querySelector('#confirmOkBtn');
        const cancelBtn = modal.querySelector('#confirmCancelBtn');

        // Set content
        titleEl.textContent = title;
        messageEl.innerHTML = message;
        confirmBtn.textContent = confirmText;
        cancelBtn.textContent = cancelText;

        // Set icon and colors based on type
        iconEl.className = 'confirmation-icon';
        iconEl.classList.add(`type-${type}`);

        const icons = {
            warning: 'fa-circle-exclamation',
            danger: 'fa-triangle-exclamation',
            info: 'fa-circle-info',
            success: 'fa-circle-check'
        };
        iconEl.querySelector('i').className = `fa-solid ${icons[type] || icons.warning}`;

        // Set button class
        confirmBtn.className = `btn ${confirmClass}`;

        // Show modal
        modal.classList.add('active');
        confirmBtn.focus();

        // Return promise
        return new Promise((resolve) => {
            this.resolveCallback = resolve;
        });
    }

    close(confirmed) {
        const modal = document.getElementById('confirmationModal');
        modal.classList.remove('active');

        if (this.resolveCallback) {
            this.resolveCallback(confirmed);
            this.resolveCallback = null;
        }
    }

    // Shorthand methods
    static async confirm(options) {
        if (!window.confirmationDialog) {
            window.confirmationDialog = new ConfirmationDialog();
        }
        return await window.confirmationDialog.show(options);
    }

    static async delete(itemName, itemType = 'mục này') {
        return await ConfirmationDialog.confirm({
            title: 'Xác nhận xóa',
            message: `Bạn có chắc chắn muốn xóa <strong>${itemName}</strong>?<br><small class="text-muted">Hành động này không thể hoàn tác.</small>`,
            confirmText: 'Xóa',
            cancelText: 'Hủy',
            type: 'danger',
            confirmClass: 'btn-danger'
        });
    }

    static async warning(title, message) {
        return await ConfirmationDialog.confirm({
            title,
            message,
            confirmText: 'Tiếp tục',
            cancelText: 'Hủy',
            type: 'warning',
            confirmClass: 'btn-warning'
        });
    }

    static async info(title, message) {
        return await ConfirmationDialog.confirm({
            title,
            message,
            confirmText: 'OK',
            cancelText: 'Đóng',
            type: 'info',
            confirmClass: 'btn-primary'
        });
    }
}

// Initialize on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.confirmationDialog = new ConfirmationDialog();
    });
} else {
    window.confirmationDialog = new ConfirmationDialog();
}

// Export
window.ConfirmationDialog = ConfirmationDialog;
