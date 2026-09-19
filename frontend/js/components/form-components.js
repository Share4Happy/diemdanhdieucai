/**
 * FORM COMPONENTS LIBRARY
 * Thư viện JavaScript cho hệ thống form components
 * Version: 1.0
 */

class FormComponentsManager {
    constructor() {
        this.modals = new Map();
        this.forms = new Map();
        this.validators = new Map();
        this.init();
    }

    init() {
        // Auto-init khi DOM load xong
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.autoInit());
        } else {
            this.autoInit();
        }
    }

    autoInit() {
        // Tự động khởi tạo các component
        this.initTabs();
        this.initCardSelectors();
        this.initFileUploads();
        this.initFormValidation();
    }

    // ==================== MODAL MANAGEMENT ====================
    
    /**
     * Tạo một modal mới
     * @param {Object} config - Cấu hình modal
     * @returns {HTMLElement} Modal element
     */
    createModal(config) {
        const {
            id,
            title,
            subtitle = '',
            content = '',
            maxWidth = '650px',
            onClose = null,
            closeOnBackdrop = true
        } = config;

        // Kiểm tra modal đã tồn tại
        if (document.getElementById(id)) {
            console.warn(`Modal với ID "${id}" đã tồn tại`);
            return document.getElementById(id);
        }

        const modalHTML = `
            <div class="modal-backdrop" id="${id}">
                <div class="modal-content" style="max-width: ${maxWidth};">
                    <div class="modal-header">
                        <div>
                            <h3 class="modal-title">${title}</h3>
                            ${subtitle ? `<p class="modal-subtitle">${subtitle}</p>` : ''}
                        </div>
                        <button class="modal-close" data-modal-close>&times;</button>
                    </div>
                    <div class="modal-body">
                        ${content}
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        const modal = document.getElementById(id);

        // Event listeners
        const closeBtn = modal.querySelector('[data-modal-close]');
        const backdrop = modal;

        closeBtn.addEventListener('click', () => {
            this.closeModal(id);
            if (onClose) onClose();
        });

        if (closeOnBackdrop) {
            backdrop.addEventListener('click', (e) => {
                if (e.target === backdrop) {
                    this.closeModal(id);
                    if (onClose) onClose();
                }
            });
        }

        this.modals.set(id, modal);
        return modal;
    }

    /**
     * Mở modal
     */
    openModal(id) {
        const modal = document.getElementById(id);
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }

    /**
     * Đóng modal
     */
    closeModal(id) {
        const modal = document.getElementById(id);
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    // ==================== TAB MANAGEMENT ====================
    
    initTabs() {
        document.querySelectorAll('.form-tabs').forEach(tabContainer => {
            const tabs = tabContainer.querySelectorAll('.form-tab');
            const panels = document.querySelectorAll('.form-tab-panel');

            tabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    const targetId = tab.dataset.tab;

                    // Deactivate all
                    tabs.forEach(t => t.classList.remove('active'));
                    panels.forEach(p => p.classList.remove('active'));

                    // Activate selected
                    tab.classList.add('active');
                    const targetPanel = document.getElementById(targetId);
                    if (targetPanel) {
                        targetPanel.classList.add('active');
                    }

                    // Trigger custom event
                    const event = new CustomEvent('tabChange', { 
                        detail: { tabId: targetId } 
                    });
                    tabContainer.dispatchEvent(event);
                });
            });
        });
    }

    /**
     * Chuyển đổi tab programmatically
     */
    switchTab(tabId) {
        const tab = document.querySelector(`[data-tab="${tabId}"]`);
        if (tab) {
            tab.click();
        }
    }

    // ==================== CARD SELECTOR ====================
    
    initCardSelectors() {
        document.querySelectorAll('.form-card-selector').forEach(card => {
            card.addEventListener('click', () => {
                const groupName = card.dataset.group;
                const value = card.dataset.value;

                if (groupName) {
                    // Deselect all in group
                    document.querySelectorAll(`.form-card-selector[data-group="${groupName}"]`)
                        .forEach(c => c.classList.remove('selected'));
                }

                // Select this card
                card.classList.add('selected');

                // Update hidden input if exists
                const hiddenInput = document.querySelector(`input[name="${groupName}"]`);
                if (hiddenInput) {
                    hiddenInput.value = value;
                }

                // Trigger custom event
                const event = new CustomEvent('cardSelected', {
                    detail: { group: groupName, value: value }
                });
                card.dispatchEvent(event);
            });
        });
    }

    /**
     * Chọn card programmatically
     */
    selectCard(groupName, value) {
        const card = document.querySelector(
            `.form-card-selector[data-group="${groupName}"][data-value="${value}"]`
        );
        if (card) {
            card.click();
        }
    }

    // ==================== FILE UPLOAD ====================
    
    initFileUploads() {
        document.querySelectorAll('.form-file-input').forEach(input => {
            input.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (!file) return;

                const previewContainer = input.closest('.form-file-upload')
                    .querySelector('.form-file-preview');
                
                if (previewContainer) {
                    this.showFilePreview(file, previewContainer);
                }

                // Trigger custom event
                const event = new CustomEvent('fileSelected', {
                    detail: { file: file }
                });
                input.dispatchEvent(event);
            });
        });
    }

    /**
     * Hiển thị preview file
     */
    showFilePreview(file, container) {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            if (file.type.startsWith('image/')) {
                container.innerHTML = `
                    <img src="${e.target.result}" class="form-file-preview-img" alt="Preview">
                    <div>
                        <div style="font-weight: 600; font-size: 0.875rem;">${file.name}</div>
                        <div style="font-size: 0.75rem; color: #64748b;">
                            ${this.formatFileSize(file.size)}
                        </div>
                    </div>
                `;
            } else {
                container.innerHTML = `
                    <i class="fa-solid fa-file" style="font-size: 2rem; color: #64748b;"></i>
                    <div>
                        <div style="font-weight: 600; font-size: 0.875rem;">${file.name}</div>
                        <div style="font-size: 0.75rem; color: #64748b;">
                            ${this.formatFileSize(file.size)}
                        </div>
                    </div>
                `;
            }
            container.style.display = 'flex';
        };

        reader.readAsDataURL(file);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    // ==================== FORM VALIDATION ====================
    
    initFormValidation() {
        document.querySelectorAll('[data-validate]').forEach(form => {
            const formId = form.id || `form_${Date.now()}`;
            form.id = formId;

            form.addEventListener('submit', (e) => {
                e.preventDefault();
                if (this.validateForm(formId)) {
                    // Form valid - trigger custom event
                    const event = new CustomEvent('formValid', {
                        detail: { formData: this.getFormData(formId) }
                    });
                    form.dispatchEvent(event);
                }
            });

            // Real-time validation
            form.querySelectorAll('input, select, textarea').forEach(input => {
                input.addEventListener('blur', () => {
                    this.validateField(input);
                });

                input.addEventListener('input', () => {
                    if (input.classList.contains('error')) {
                        this.validateField(input);
                    }
                });
            });
        });
    }

    /**
     * Validate toàn bộ form
     */
    validateForm(formId) {
        const form = document.getElementById(formId);
        if (!form) return false;

        let isValid = true;
        const inputs = form.querySelectorAll('input, select, textarea');

        inputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });

        return isValid;
    }

    /**
     * Validate một field
     */
    validateField(input) {
        const rules = input.dataset.rules ? input.dataset.rules.split('|') : [];
        let isValid = true;
        let errorMessage = '';

        // Required
        if (rules.includes('required') || input.required) {
            if (!input.value.trim()) {
                isValid = false;
                errorMessage = 'Trường này là bắt buộc';
            }
        }

        // Email
        if (rules.includes('email') && input.value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(input.value)) {
                isValid = false;
                errorMessage = 'Email không hợp lệ';
            }
        }

        // Min length
        const minLength = rules.find(r => r.startsWith('min:'));
        if (minLength && input.value) {
            const min = parseInt(minLength.split(':')[1]);
            if (input.value.length < min) {
                isValid = false;
                errorMessage = `Tối thiểu ${min} ký tự`;
            }
        }

        // Max length
        const maxLength = rules.find(r => r.startsWith('max:'));
        if (maxLength && input.value) {
            const max = parseInt(maxLength.split(':')[1]);
            if (input.value.length > max) {
                isValid = false;
                errorMessage = `Tối đa ${max} ký tự`;
            }
        }

        // Number
        if (rules.includes('number') && input.value) {
            if (isNaN(input.value)) {
                isValid = false;
                errorMessage = 'Phải là số';
            }
        }

        // URL
        if (rules.includes('url') && input.value) {
            try {
                new URL(input.value);
            } catch {
                isValid = false;
                errorMessage = 'URL không hợp lệ';
            }
        }

        // Update UI
        this.updateFieldValidation(input, isValid, errorMessage);
        return isValid;
    }

    /**
     * Update UI validation cho field
     */
    updateFieldValidation(input, isValid, message) {
        const formGroup = input.closest('.form-group');
        const existingError = formGroup?.querySelector('.form-helper-text.error');

        if (isValid) {
            input.classList.remove('error');
            input.classList.add('success');
            if (existingError) {
                existingError.remove();
            }
        } else {
            input.classList.remove('success');
            input.classList.add('error');
            
            if (existingError) {
                existingError.textContent = message;
            } else if (formGroup) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'form-helper-text error';
                errorDiv.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i> ${message}`;
                formGroup.appendChild(errorDiv);
            }
        }
    }

    /**
     * Lấy dữ liệu form dưới dạng object
     */
    getFormData(formId) {
        const form = document.getElementById(formId);
        if (!form) return {};

        const formData = new FormData(form);
        const data = {};

        for (let [key, value] of formData.entries()) {
            if (data[key]) {
                // Handle multiple values (checkboxes, etc)
                if (Array.isArray(data[key])) {
                    data[key].push(value);
                } else {
                    data[key] = [data[key], value];
                }
            } else {
                data[key] = value;
            }
        }

        return data;
    }

    /**
     * Set dữ liệu vào form
     */
    setFormData(formId, data) {
        const form = document.getElementById(formId);
        if (!form) return;

        Object.keys(data).forEach(key => {
            const input = form.querySelector(`[name="${key}"]`);
            if (input) {
                if (input.type === 'checkbox') {
                    input.checked = data[key];
                } else if (input.type === 'radio') {
                    const radio = form.querySelector(`[name="${key}"][value="${data[key]}"]`);
                    if (radio) radio.checked = true;
                } else {
                    input.value = data[key];
                }
            }
        });
    }

    /**
     * Reset form
     */
    resetForm(formId) {
        const form = document.getElementById(formId);
        if (!form) return;

        form.reset();
        
        // Clear validation states
        form.querySelectorAll('.error, .success').forEach(el => {
            el.classList.remove('error', 'success');
        });

        form.querySelectorAll('.form-helper-text.error').forEach(el => {
            el.remove();
        });
    }

    // ==================== UTILITIES ====================
    
    /**
     * Show loading state cho form
     */
    showFormLoading(formId) {
        const form = document.getElementById(formId);
        if (form) {
            form.classList.add('form-loading');
        }
    }

    /**
     * Hide loading state
     */
    hideFormLoading(formId) {
        const form = document.getElementById(formId);
        if (form) {
            form.classList.remove('form-loading');
        }
    }

    /**
     * Show notification toast
     */
    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `form-toast form-toast-${type}`;
        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px;">
                <i class="fa-solid fa-${this.getToastIcon(type)}"></i>
                <span>${message}</span>
            </div>
        `;

        // Add styles if not exists
        if (!document.getElementById('toast-styles')) {
            const style = document.createElement('style');
            style.id = 'toast-styles';
            style.textContent = `
                .form-toast {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    padding: 12px 20px;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    z-index: 10000;
                    animation: slideInRight 0.3s ease;
                    font-size: 0.875rem;
                    font-weight: 600;
                    min-width: 250px;
                }
                .form-toast-info { background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; }
                .form-toast-success { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
                .form-toast-warning { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }
                .form-toast-error { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideInRight 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    getToastIcon(type) {
        const icons = {
            info: 'circle-info',
            success: 'circle-check',
            warning: 'triangle-exclamation',
            error: 'circle-xmark'
        };
        return icons[type] || 'circle-info';
    }
}

// Initialize global instance
const FormComponents = new FormComponentsManager();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FormComponents;
}
