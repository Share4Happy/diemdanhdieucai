/**
 * Modal Notification System
 * Thay thế alert() bằng các modal đẹp, tái sử dụng
 * 
 * Usage:
 *   showSuccess('Lưu thành công!');
 *   showError('Có lỗi xảy ra!');
 *   showWarning('Cảnh báo!');
 *   showInfo('Thông tin');
 *   confirmAction('Bạn có chắc?', () => { // do something });
 */

// ============================================================================
// SUCCESS MODAL
// ============================================================================
function showSuccess(message, title = 'Thành Công', duration = 3000) {
    const existingModal = document.getElementById('successNotificationModal');
    if (existingModal) {
        existingModal.remove();
    }

    const modalHTML = `
        <div class="modal-backdrop active" id="successNotificationModal">
            <div class="modal-container modal-sm modal-success">
                <div class="modal-header">
                    <div class="modal-header-content">
                        <h3 class="modal-title">
                            <i class="fa-solid fa-circle-check modal-title-icon"></i>
                            ${title}
                        </h3>
                    </div>
                    <button class="modal-close-btn" onclick="closeSuccessModal()">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
                <div class="modal-body" style="text-align: center; padding: 32px 24px;">
                    <div style="font-size: 3rem; color: #10b981; margin-bottom: 16px;">
                        <i class="fa-solid fa-circle-check"></i>
                    </div>
                    <p style="font-size: 1rem; line-height: 1.6; color: var(--text-main);">
                        ${message}
                    </p>
                </div>
                <div class="modal-footer">
                    <button class="modal-btn modal-btn-primary" onclick="closeSuccessModal()">
                        <i class="fa-solid fa-check"></i>
                        OK
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Auto close after duration
    if (duration > 0) {
        setTimeout(() => {
            closeSuccessModal();
        }, duration);
    }
}

function closeSuccessModal() {
    const modal = document.getElementById('successNotificationModal');
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => modal.remove(), 300);
    }
}

// ============================================================================
// ERROR MODAL
// ============================================================================
function showError(message, title = 'Lỗi') {
    const existingModal = document.getElementById('errorNotificationModal');
    if (existingModal) {
        existingModal.remove();
    }

    const modalHTML = `
        <div class="modal-backdrop active" id="errorNotificationModal">
            <div class="modal-container modal-sm modal-danger">
                <div class="modal-header">
                    <div class="modal-header-content">
                        <h3 class="modal-title">
                            <i class="fa-solid fa-circle-xmark modal-title-icon"></i>
                            ${title}
                        </h3>
                    </div>
                    <button class="modal-close-btn" onclick="closeErrorModal()">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
                <div class="modal-body" style="text-align: center; padding: 32px 24px;">
                    <div style="font-size: 3rem; color: #ef4444; margin-bottom: 16px;">
                        <i class="fa-solid fa-circle-xmark"></i>
                    </div>
                    <p style="font-size: 1rem; line-height: 1.6; color: var(--text-main);">
                        ${message}
                    </p>
                </div>
                <div class="modal-footer">
                    <button class="modal-btn modal-btn-danger" onclick="closeErrorModal()">
                        <i class="fa-solid fa-xmark"></i>
                        Đóng
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function closeErrorModal() {
    const modal = document.getElementById('errorNotificationModal');
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => modal.remove(), 300);
    }
}

// ============================================================================
// WARNING MODAL
// ============================================================================
function showWarning(message, title = 'Cảnh Báo') {
    const existingModal = document.getElementById('warningNotificationModal');
    if (existingModal) {
        existingModal.remove();
    }

    const modalHTML = `
        <div class="modal-backdrop active" id="warningNotificationModal">
            <div class="modal-container modal-sm modal-warning">
                <div class="modal-header">
                    <div class="modal-header-content">
                        <h3 class="modal-title">
                            <i class="fa-solid fa-triangle-exclamation modal-title-icon"></i>
                            ${title}
                        </h3>
                    </div>
                    <button class="modal-close-btn" onclick="closeWarningModal()">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
                <div class="modal-body" style="text-align: center; padding: 32px 24px;">
                    <div style="font-size: 3rem; color: #f59e0b; margin-bottom: 16px;">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                    </div>
                    <p style="font-size: 1rem; line-height: 1.6; color: var(--text-main);">
                        ${message}
                    </p>
                </div>
                <div class="modal-footer">
                    <button class="modal-btn modal-btn-secondary" onclick="closeWarningModal()">
                        <i class="fa-solid fa-check"></i>
                        Đã Hiểu
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function closeWarningModal() {
    const modal = document.getElementById('warningNotificationModal');
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => modal.remove(), 300);
    }
}

// ============================================================================
// INFO MODAL
// ============================================================================
function showInfo(message, title = 'Thông Tin') {
    const existingModal = document.getElementById('infoNotificationModal');
    if (existingModal) {
        existingModal.remove();
    }

    const modalHTML = `
        <div class="modal-backdrop active" id="infoNotificationModal">
            <div class="modal-container modal-sm modal-info">
                <div class="modal-header">
                    <div class="modal-header-content">
                        <h3 class="modal-title">
                            <i class="fa-solid fa-circle-info modal-title-icon"></i>
                            ${title}
                        </h3>
                    </div>
                    <button class="modal-close-btn" onclick="closeInfoModal()">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
                <div class="modal-body" style="text-align: center; padding: 32px 24px;">
                    <div style="font-size: 3rem; color: #3b82f6; margin-bottom: 16px;">
                        <i class="fa-solid fa-circle-info"></i>
                    </div>
                    <p style="font-size: 1rem; line-height: 1.6; color: var(--text-main);">
                        ${message}
                    </p>
                </div>
                <div class="modal-footer">
                    <button class="modal-btn modal-btn-primary" onclick="closeInfoModal()">
                        <i class="fa-solid fa-check"></i>
                        OK
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function closeInfoModal() {
    const modal = document.getElementById('infoNotificationModal');
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => modal.remove(), 300);
    }
}

// ============================================================================
// CONFIRM MODAL (Yes/No)
// ============================================================================
function confirmAction(message, onConfirm, onCancel = null, title = 'Xác Nhận') {
    const existingModal = document.getElementById('confirmNotificationModal');
    if (existingModal) {
        existingModal.remove();
    }

    const modalHTML = `
        <div class="modal-backdrop active" id="confirmNotificationModal">
            <div class="modal-container modal-sm modal-warning">
                <div class="modal-header">
                    <div class="modal-header-content">
                        <h3 class="modal-title">
                            <i class="fa-solid fa-circle-question modal-title-icon"></i>
                            ${title}
                        </h3>
                    </div>
                    <button class="modal-close-btn" onclick="closeConfirmModal()">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
                <div class="modal-body" style="text-align: center; padding: 32px 24px;">
                    <div style="font-size: 3rem; color: #f59e0b; margin-bottom: 16px;">
                        <i class="fa-solid fa-circle-question"></i>
                    </div>
                    <p style="font-size: 1rem; line-height: 1.6; color: var(--text-main);">
                        ${message}
                    </p>
                </div>
                <div class="modal-footer" style="display: flex; gap: 12px; justify-content: center;">
                    <button class="modal-btn modal-btn-secondary" onclick="closeConfirmModal()" id="confirmCancelBtn">
                        <i class="fa-solid fa-xmark"></i>
                        Hủy
                    </button>
                    <button class="modal-btn modal-btn-primary" id="confirmOkBtn">
                        <i class="fa-solid fa-check"></i>
                        Xác Nhận
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Event listeners
    document.getElementById('confirmOkBtn').addEventListener('click', () => {
        closeConfirmModal();
        if (onConfirm) onConfirm();
    });

    document.getElementById('confirmCancelBtn').addEventListener('click', () => {
        closeConfirmModal();
        if (onCancel) onCancel();
    });
}

function closeConfirmModal() {
    const modal = document.getElementById('confirmNotificationModal');
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => modal.remove(), 300);
    }
}

// ============================================================================
// LOADING MODAL (Global)
// ============================================================================
function showGlobalLoading(message = 'Đang xử lý...') {
    const existingModal = document.getElementById('globalLoadingModal');
    if (existingModal) {
        return; // Already showing
    }

    const modalHTML = `
        <div class="modal-backdrop active" id="globalLoadingModal" style="pointer-events: all;">
            <div class="modal-container modal-sm" style="background: transparent; box-shadow: none; border: none;">
                <div class="modal-body" style="text-align: center; padding: 32px 24px; background: white; border-radius: 12px;">
                    <div class="modal-loading-spinner" style="position: static; transform: none; margin: 0 auto 20px;"></div>
                    <p style="font-size: 1rem; font-weight: 600; color: var(--text-main); margin: 0;">
                        ${message}
                    </p>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function hideGlobalLoading() {
    const modal = document.getElementById('globalLoadingModal');
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => modal.remove(), 300);
    }
}

// ============================================================================
// BACKWARDS COMPATIBILITY: Replace alert()
// ============================================================================
// Uncomment this to automatically replace all alert() calls
// window.alert = function(message) {
//     if (message.toLowerCase().includes('lỗi') || message.toLowerCase().includes('error')) {
//         showError(message);
//     } else if (message.toLowerCase().includes('thành công') || message.toLowerCase().includes('success')) {
//         showSuccess(message);
//     } else if (message.toLowerCase().includes('cảnh báo') || message.toLowerCase().includes('warning')) {
//         showWarning(message);
//     } else {
//         showInfo(message);
//     }
// };
