/**
 * ============================================================================
 * PROGRESS MODAL COMPONENT (JavaScript)
 * Trường THPT Điều Cải - Hệ Thống Điểm Danh AI Camera
 * ============================================================================
 * Dialog hiển thị tiến trình thời gian thực cho:
 * 1. Quét Điểm Danh Toàn Trường (Chụp NVR -> AI YOLO -> Lưu CSDL)
 * 2. Chụp Lại Đồng Loạt 30 Camera NVR
 * 3. Chụp Lại Camera Đơn Lẻ Phòng Học
 * ============================================================================
 */

import { AttendanceAPI, CameraAPI } from '../api.js';

class ActionProgressModal {
    constructor() {
        this.backdrop = null;
        this.pollTimer = null;
        this.isRunning = false;
        this.currentAction = 'IDLE';
        this.onCompleteCallback = null;
        this.onErrorCallback = null;
        this._ensureDom();
    }

    _ensureDom() {
        if (typeof document === 'undefined') return;

        let el = document.getElementById('actionProgressModalBackdrop');
        if (!el) {
            if (!document.body) {
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', () => this._ensureDom(), { once: true });
                }
                return;
            }

            const html = `
        <div id="actionProgressModalBackdrop" class="progress-modal-backdrop" role="dialog" aria-modal="true">
            <div class="progress-modal-container">
                <!-- Header -->
                <div class="progress-modal-header">
                    <div class="progress-modal-header-left">
                        <div id="progIconBadge" class="progress-modal-icon-badge">
                            <i id="progIcon" class="fa-solid fa-bolt-lightning"></i>
                        </div>
                        <div>
                            <h3 id="progTitle" class="progress-modal-title">Tiến Trình Xử Lý</h3>
                            <div class="progress-modal-subtitle">
                                <span id="progStatusPill" class="progress-status-pill">
                                    <span class="dot"></span>
                                    <span id="progStatusText">Đang chạy thời gian thực</span>
                                </span>
                                <span id="progElapsedBadge" class="progress-elapsed-badge">⏱️ 0.0s</span>
                            </div>
                        </div>
                    </div>
                    <button id="progCloseBtn" class="progress-modal-close-btn" type="button" title="Đóng" disabled>
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>

                <!-- Body -->
                <div class="progress-modal-body">
                    <!-- Stepper 3 giai đoạn (cho Quét Điểm Danh) -->
                    <div id="progStepper" class="progress-stepper" style="display: none;">
                        <div id="progStep1" class="progress-step-item active">
                            <div class="progress-step-number">1</div>
                            <div class="progress-step-text">Chụp NVR 30 Camera</div>
                        </div>
                        <div id="progStep2" class="progress-step-item">
                            <div class="progress-step-number">2</div>
                            <div class="progress-step-text">AI YOLO Nhận Diện</div>
                        </div>
                        <div id="progStep3" class="progress-step-item">
                            <div class="progress-step-number">3</div>
                            <div class="progress-step-text">Lưu CSDL & Báo Cáo</div>
                        </div>
                    </div>

                    <!-- Progress Bar & Metric -->
                    <div>
                        <div class="progress-metric-row">
                            <span id="progStepTitle" class="progress-metric-label">Khởi tạo quy trình...</span>
                            <div class="progress-metric-values">
                                <span id="progPercent" class="progress-percent-huge">0%</span>
                            </div>
                        </div>
                        <div class="progress-bar-track">
                            <div id="progBarFill" class="progress-bar-fill" style="width: 0%;"></div>
                        </div>
                    </div>

                    <!-- Active Item Spotlight Box -->
                    <div id="progSpotlightBox" class="progress-spotlight-box">
                        <div class="progress-spotlight-left">
                            <div class="progress-spotlight-icon">
                                <i id="progSpotlightIcon" class="fa-solid fa-video"></i>
                            </div>
                            <div>
                                <div id="progSpotlightName" class="progress-spotlight-name">Đang chuẩn bị...</div>
                                <div id="progSpotlightDesc" class="progress-spotlight-desc">Đang thiết lập kết nối luồng camera</div>
                            </div>
                        </div>
                        <div id="progCounterBadge" class="progress-counter-badge">0 / 30</div>
                    </div>

                    <!-- Snapshot Single Preview Box (nếu chụp 1 camera lẻ) -->
                    <div id="progSinglePreviewBox" style="display: none; text-align: center; background: #0f172a; border-radius: 12px; padding: 8px; overflow: hidden;">
                        <img id="progSinglePreviewImg" src="" alt="Snapshot Preview" style="max-height: 220px; border-radius: 8px; object-fit: contain; width: 100%; display: block;" />
                    </div>

                    <!-- Mini Terminal / Logs -->
                    <div>
                        <div style="font-size: 0.78rem; font-weight: 700; color: #475569; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                            <i class="fa-solid fa-terminal" style="font-size: 0.75rem;"></i>
                            <span>Nhật ký hoạt động chi tiết:</span>
                        </div>
                        <div id="progTerminal" class="progress-log-terminal">
                            <div class="progress-log-line">
                                <span class="progress-log-time">00:00:00</span>
                                <span class="progress-log-text info">Đang kết nối hệ thống...</span>
                            </div>
                        </div>
                    </div>

                    <!-- Completion Summary Card -->
                    <div id="progSummaryCard" class="progress-summary-card">
                        <div class="progress-summary-header">
                            <i class="fa-solid fa-circle-check" style="color: #10b981; font-size: 1.25rem;"></i>
                            <span id="progSummaryTitle">Hoàn tất phiên điểm danh thành công!</span>
                        </div>
                        <div class="progress-summary-grid">
                            <div class="progress-summary-kpi">
                                <div id="progKpiTotal" class="progress-summary-kpi-val">30</div>
                                <div class="progress-summary-kpi-lbl">Tổng Lớp</div>
                            </div>
                            <div class="progress-summary-kpi">
                                <div id="progKpiPresent" class="progress-summary-kpi-val" style="color: #059669;">--</div>
                                <div class="progress-summary-kpi-lbl">Hiện Diện</div>
                            </div>
                            <div class="progress-summary-kpi">
                                <div id="progKpiAbsent" class="progress-summary-kpi-val" style="color: #dc2626;">--</div>
                                <div class="progress-summary-kpi-lbl">Vắng</div>
                            </div>
                            <div class="progress-summary-kpi">
                                <div id="progKpiDuration" class="progress-summary-kpi-val" style="color: #4f46e5;">--</div>
                                <div class="progress-summary-kpi-lbl">Thời Gian</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div class="progress-modal-footer">
                    <button id="progBtnDone" class="progress-btn-done" type="button" style="display: none;">
                        <i class="fa-solid fa-check"></i>
                        <span>Xem Kết Quả & Hoàn Tất</span>
                    </button>
                    <button id="progBtnCancel" class="progress-btn-secondary" type="button">
                        Đóng
                    </button>
                </div>
            </div>
        </div>
            `;
            document.body.insertAdjacentHTML('beforeend', html);
            el = document.getElementById('actionProgressModalBackdrop');
        }

        this.backdrop = el;

        // Gắn sự kiện nút đóng an toàn (chỉ gắn 1 lần)
        if (this.backdrop && !this.backdrop._eventsBound) {
            this.backdrop._eventsBound = true;
            const closeBtn = document.getElementById('progCloseBtn');
            const cancelBtn = document.getElementById('progBtnCancel');
            const doneBtn = document.getElementById('progBtnDone');

            const doClose = () => this.close();
            if (closeBtn) closeBtn.onclick = doClose;
            if (cancelBtn) cancelBtn.onclick = doClose;
            if (doneBtn) doneBtn.onclick = () => {
                const cb = this.onCompleteCallback;
                this.close();
                if (cb) cb();
            };
        }
    }

    open(options = {}) {
        this._ensureDom();
        this.currentAction = options.action || 'ATTENDANCE_SCAN';
        this.onCompleteCallback = options.onComplete || null;
        this.onErrorCallback = options.onError || null;
        this.isRunning = true;

        // Reset elements
        const iconBadge = document.getElementById('progIconBadge');
        const icon = document.getElementById('progIcon');
        const title = document.getElementById('progTitle');
        const stepper = document.getElementById('progStepper');
        const spotlightBox = document.getElementById('progSpotlightBox');
        const singlePreview = document.getElementById('progSinglePreviewBox');
        const summaryCard = document.getElementById('progSummaryCard');
        const closeBtn = document.getElementById('progCloseBtn');
        const cancelBtn = document.getElementById('progBtnCancel');
        const doneBtn = document.getElementById('progBtnDone');
        const terminal = document.getElementById('progTerminal');

        if (terminal) terminal.innerHTML = '';
        if (summaryCard) summaryCard.style.display = 'none';
        if (singlePreview) singlePreview.style.display = 'none';
        if (doneBtn) doneBtn.style.display = 'none';
        if (cancelBtn) {
            cancelBtn.disabled = true;
            cancelBtn.textContent = 'Đang xử lý...';
        }
        if (closeBtn) closeBtn.disabled = true;

        this._updatePercent(5);
        this._updateElapsed('0.0s');

        if (this.currentAction === 'ATTENDANCE_SCAN') {
            if (iconBadge) iconBadge.className = 'progress-modal-icon-badge';
            if (icon) icon.className = 'fa-solid fa-bolt-lightning';
            if (title) title.textContent = 'Tiến Trình Quét Điểm Danh AI (30 Lớp)';
            if (stepper) stepper.style.display = 'grid';
            if (spotlightBox) spotlightBox.style.display = 'flex';
            this._updateStepPills(1);
        } else if (this.currentAction === 'CAPTURE_ALL') {
            if (iconBadge) iconBadge.className = 'progress-modal-icon-badge camera-mode';
            if (icon) icon.className = 'fa-solid fa-camera-rotate';
            if (title) title.textContent = 'Tiến Trình Chụp Lại 30 Camera NVR';
            if (stepper) stepper.style.display = 'none';
            if (spotlightBox) spotlightBox.style.display = 'flex';
        } else if (this.currentAction === 'CAPTURE_SINGLE') {
            if (iconBadge) iconBadge.className = 'progress-modal-icon-badge single-mode';
            if (icon) icon.className = 'fa-solid fa-camera';
            if (title) title.textContent = options.title || 'Chụp Lại Ảnh Camera Phòng Học';
            if (stepper) stepper.style.display = 'none';
            if (spotlightBox) spotlightBox.style.display = 'flex';
        } else if (this.currentAction === 'ATTENDANCE_SCAN_SINGLE') {
            if (iconBadge) iconBadge.className = 'progress-modal-icon-badge';
            if (icon) icon.className = 'fa-solid fa-qrcode';
            if (title) title.textContent = options.title || 'Quét Lại Phòng Này (AI)';
            if (stepper) stepper.style.display = 'none';
            if (spotlightBox) spotlightBox.style.display = 'flex';
        }

        this.backdrop.classList.add('active');
        this._startPolling();
    }

    close() {
        this._stopPolling();
        this.isRunning = false;
        if (this.backdrop) {
            this.backdrop.classList.remove('active');
        }
    }

    _startPolling() {
        this._stopPolling();
        const pollEndpoint = (this.currentAction === 'ATTENDANCE_SCAN' || this.currentAction === 'ATTENDANCE_SCAN_SINGLE')
            ? () => AttendanceAPI.getProgress()
            : () => CameraAPI.getProgress();

        this.pollTimer = setInterval(async () => {
            try {
                const state = await pollEndpoint();
                if (state) {
                    this._renderState(state);
                    if (!state.is_running && (state.status === 'success' || state.status === 'error')) {
                        this._stopPolling();
                        this._handleFinished(state);
                    }
                }
            } catch (err) {
                console.debug('[ProgressModal] Poll debug:', err);
            }
        }, 450);
    }

    _stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
    }

    _renderState(st) {
        if (!st) return;

        // Cập nhật phần trăm & thời gian
        this._updatePercent(st.percent || 0);
        this._updateElapsed(`${st.elapsed_seconds || 0}s`);

        // Cập nhật tiêu đề bước
        const stepTitleEl = document.getElementById('progStepTitle');
        if (stepTitleEl && st.step_title) {
            stepTitleEl.textContent = st.step_title;
        }

        // Cập nhật Stepper 3 bước (cho điểm danh)
        if (this.currentAction === 'ATTENDANCE_SCAN') {
            this._updateStepPills(st.step || 1);
        }

        // Cập nhật Spotlight card
        const spName = document.getElementById('progSpotlightName');
        const spDesc = document.getElementById('progSpotlightDesc');
        const counter = document.getElementById('progCounterBadge');

        if (spName && st.current_item) {
            spName.textContent = st.current_item;
        }
        if (spDesc && st.step_title) {
            spDesc.textContent = st.step_title;
        }
        if (counter && st.total > 0) {
            counter.textContent = `${st.current || 0} / ${st.total}`;
        }

        // Cập nhật Terminal logs
        if (Array.isArray(st.logs)) {
            const term = document.getElementById('progTerminal');
            if (term) {
                term.innerHTML = st.logs.map(l => `
                    <div class="progress-log-line">
                        <span class="progress-log-time">${l.time || ''}</span>
                        <span class="progress-log-text ${l.type || 'info'}">${l.text || ''}</span>
                    </div>
                `).join('');
                term.scrollTop = term.scrollHeight;
            }
        }
    }

    _updateStepPills(stepNum) {
        const s1 = document.getElementById('progStep1');
        const s2 = document.getElementById('progStep2');
        const s3 = document.getElementById('progStep3');

        if (s1 && s2 && s3) {
            s1.className = 'progress-step-item';
            s2.className = 'progress-step-item';
            s3.className = 'progress-step-item';

            if (stepNum === 1) {
                s1.classList.add('active');
            } else if (stepNum === 2) {
                s1.classList.add('completed');
                s2.classList.add('active');
            } else if (stepNum >= 3) {
                s1.classList.add('completed');
                s2.classList.add('completed');
                s3.classList.add('active');
            }
        }
    }

    _updatePercent(pct) {
        const percentEl = document.getElementById('progPercent');
        const barFill = document.getElementById('progBarFill');
        const val = Math.min(100, Math.max(0, parseInt(pct) || 0));

        if (percentEl) percentEl.textContent = `${val}%`;
        if (barFill) barFill.style.width = `${val}%`;
    }

    _updateElapsed(text) {
        const badge = document.getElementById('progElapsedBadge');
        if (badge) badge.textContent = `⏱️ ${text}`;
    }

    _handleFinished(st) {
        this.isRunning = false;
        const closeBtn = document.getElementById('progCloseBtn');
        const cancelBtn = document.getElementById('progBtnCancel');
        const doneBtn = document.getElementById('progBtnDone');
        const statusPill = document.getElementById('progStatusPill');
        const statusText = document.getElementById('progStatusText');
        const summaryCard = document.getElementById('progSummaryCard');

        if (closeBtn) closeBtn.disabled = false;
        if (cancelBtn) {
            cancelBtn.disabled = false;
            cancelBtn.textContent = 'Đóng';
        }

        if (st.status === 'success') {
            this._updatePercent(100);
            if (statusPill) {
                statusPill.style.background = '#ecfdf5';
                statusPill.style.color = '#059669';
            }
            if (statusText) statusText.textContent = 'Đã hoàn tất 100%';

            if (doneBtn) {
                doneBtn.style.display = 'inline-flex';
                doneBtn.innerHTML = '<i class="fa-solid fa-check-circle"></i> Xem Kết Quả & Hoàn Tất';
            }

            // Hiển thị KPI summary nếu là Quét Điểm Danh
            if (this.currentAction === 'ATTENDANCE_SCAN' && summaryCard) {
                summaryCard.style.display = 'flex';
                const res = st.result || {};
                const kTotal = document.getElementById('progKpiTotal');
                const kPresent = document.getElementById('progKpiPresent');
                const kAbsent = document.getElementById('progKpiAbsent');
                const kDur = document.getElementById('progKpiDuration');

                if (kTotal) kTotal.textContent = res.total_classes || 30;
                if (kPresent) kPresent.textContent = res.total_present != null ? res.total_present : '--';
                if (kAbsent) kAbsent.textContent = res.total_absent != null ? res.total_absent : 0;
                if (kDur) kDur.textContent = `${st.elapsed_seconds || res.scan_duration_seconds || 0}s`;
            } else if (this.currentAction === 'CAPTURE_ALL' && summaryCard) {
                summaryCard.style.display = 'flex';
                const sumTitle = document.getElementById('progSummaryTitle');
                if (sumTitle) sumTitle.textContent = 'Đã làm mới ảnh 30 camera thành công!';
                const res = st.result || {};
                const kTotal = document.getElementById('progKpiTotal');
                const kPresent = document.getElementById('progKpiPresent');
                const kAbsent = document.getElementById('progKpiAbsent');
                const kDur = document.getElementById('progKpiDuration');

                if (kTotal) kTotal.textContent = res.total || 30;
                if (kPresent) {
                    kPresent.textContent = `${res.success_count || 30}/${res.total || 30}`;
                    kPresent.style.fontSize = '1.05rem';
                }
                const lblPres = kPresent?.nextElementSibling;
                if (lblPres) lblPres.textContent = 'Thành Công';
                if (kAbsent) kAbsent.textContent = 0;
                const lblAbs = kAbsent?.nextElementSibling;
                if (lblAbs) lblAbs.textContent = 'Lỗi Bắt Hình';
                if (kDur) kDur.textContent = `${st.elapsed_seconds || 0}s`;
            } else if (this.currentAction === 'CAPTURE_SINGLE') {
                const singlePreview = document.getElementById('progSinglePreviewBox');
                const previewImg = document.getElementById('progSinglePreviewImg');
                const res = st.result || {};
                if (singlePreview && previewImg && res.snapshot_url) {
                    previewImg.src = res.snapshot_url;
                    singlePreview.style.display = 'block';
                }
            }
        } else {
            // Thất bại
            if (statusPill) {
                statusPill.style.background = '#fef2f2';
                statusPill.style.color = '#dc2626';
            }
            if (statusText) statusText.textContent = 'Gặp lỗi trong quá trình xử lý';
            if (doneBtn) doneBtn.style.display = 'none';
        }
    }

    /**
     * Kích hoạt quét điểm danh toàn trường kèm Dialog hiển thị tiến trình
     */
    async startAttendanceScan(callbacks = {}) {
        this.open({
            action: 'ATTENDANCE_SCAN',
            title: 'Tiến Trình Quét Điểm Danh AI (30 Lớp)',
            onComplete: callbacks.onComplete,
            onError: callbacks.onError
        });

        try {
            const result = await AttendanceAPI.triggerScan();
            // Đợi 1 chút để poll nhận state cuối cùng
            setTimeout(() => {
                if (this.pollTimer) {
                    AttendanceAPI.getProgress().then(st => this._renderState(st));
                }
            }, 600);
            return result;
        } catch (err) {
            console.error('[ProgressModal] Lỗi kích hoạt quét điểm danh:', err);
            this._handleFinished({
                status: 'error',
                message: err.message || 'Lỗi khi kích hoạt quét điểm danh'
            });
            if (callbacks.onError) callbacks.onError(err);
            throw err;
        }
    }

    /**
     * Kích hoạt chụp lại đồng loạt 30 camera kèm Dialog hiển thị tiến trình
     */
    async startCaptureAll(callbacks = {}) {
        this.open({
            action: 'CAPTURE_ALL',
            title: 'Tiến Trình Chụp Lại 30 Camera NVR',
            onComplete: callbacks.onComplete,
            onError: callbacks.onError
        });

        try {
            const result = await CameraAPI.refreshAllSnapshots();
            setTimeout(() => {
                if (this.pollTimer) {
                    CameraAPI.getProgress().then(st => this._renderState(st));
                }
            }, 600);
            return result;
        } catch (err) {
            console.error('[ProgressModal] Lỗi chụp lại 30 camera:', err);
            this._handleFinished({
                status: 'error',
                message: err.message || 'Lỗi khi chụp lại 30 camera'
            });
            if (callbacks.onError) callbacks.onError(err);
            throw err;
        }
    }

    /**
     * Kích hoạt chụp lại 1 camera phòng học đơn lẻ kèm Dialog
     */
    async startCaptureSingle(classroomId, className = '', callbacks = {}) {
        this.open({
            action: 'CAPTURE_SINGLE',
            title: `Chụp Lại Camera ${className || `Phòng ${classroomId}`}`,
            onComplete: callbacks.onComplete,
            onError: callbacks.onError
        });

        const spotlightName = document.getElementById('progSpotlightName');
        const spotlightDesc = document.getElementById('progSpotlightDesc');
        if (spotlightName) spotlightName.textContent = className || `Lớp ${classroomId}`;
        if (spotlightDesc) spotlightDesc.textContent = 'Đang gửi lệnh bắt hình trực tiếp từ Camera...';

        try {
            const result = await CameraAPI.refreshClassroomSnapshot(classroomId);
            setTimeout(() => {
                if (this.pollTimer) {
                    CameraAPI.getProgress().then(st => this._renderState(st));
                }
            }, 500);
            return result;
        } catch (err) {
            console.error('[ProgressModal] Lỗi chụp camera đơn:', err);
            this._handleFinished({
                status: 'error',
                message: err.message || 'Lỗi khi chụp camera phòng học'
            });
            if (callbacks.onError) callbacks.onError(err);
            throw err;
        }
    }

    /**
     * Kích hoạt quét điểm danh AI cho 1 phòng học đơn lẻ kèm Dialog
     */
    async startAttendanceScanSingle(classroomId, className = '', callbacks = {}) {
        this.open({
            action: 'ATTENDANCE_SCAN_SINGLE',
            title: `Quét Lại AI ${className || `Phòng ${classroomId}`}`,
            onComplete: callbacks.onComplete,
            onError: callbacks.onError
        });

        const spotlightName = document.getElementById('progSpotlightName');
        const spotlightDesc = document.getElementById('progSpotlightDesc');
        if (spotlightName) spotlightName.textContent = className || `Lớp ${classroomId}`;
        if (spotlightDesc) spotlightDesc.textContent = 'Đang kích hoạt chu trình nhận diện AI riêng cho phòng này...';

        try {
            const result = await AttendanceAPI.rescanSingle(classroomId);
            setTimeout(() => {
                if (this.pollTimer) {
                    AttendanceAPI.getProgress().then(st => this._renderState(st));
                }
            }, 300);
            return result;
        } catch (err) {
            console.error('[ProgressModal] Lỗi quét lại phòng đơn:', err);
            this._handleFinished({
                status: 'error',
                message: err.message || 'Lỗi khi quét lại phòng học'
            });
            if (callbacks.onError) callbacks.onError(err);
            throw err;
        }
    }
}

export const progressModal = new ActionProgressModal();
if (typeof window !== 'undefined') {
    window.ProgressModal = progressModal;
    window.triggerAttendanceScan = (cb) => progressModal.startAttendanceScan(cb);
    window.triggerCaptureAll = (cb) => progressModal.startCaptureAll(cb);
    window.triggerCaptureSingle = (id, name, cb) => progressModal.startCaptureSingle(id, name, cb);
    window.triggerAttendanceScanSingle = (id, name, cb) => progressModal.startAttendanceScanSingle(id, name, cb);
}
