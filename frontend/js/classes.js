/**
 * =====================================================
 * LOGIC QUẢN LÝ LỚP HỌC & SĨ SỐ - THPT ĐIỀU CẢI
 * =====================================================
 */

import { ClassroomsAPI, showToast, escapeHtml } from './api.js';

class ClassesManager {
    constructor() {
        this.classes = [];
        this.availableCameras = [];
        this.importPreviewData = null;
        this.currentPreviewFile = null;
        this.isLoading = false;

        this.initElements();
        this.attachEvents();
        this.loadData();
    }

    initElements() {
        // Stats
        this.statTotalClasses = document.getElementById('statTotalClasses');
        this.statTotalStudents = document.getElementById('statTotalStudents');
        this.statAvgStudents = document.getElementById('statAvgStudents');
        this.statCameraRatio = document.getElementById('statCameraRatio');

        // Filter & Search
        this.searchInput = document.getElementById('searchInput');
        this.btnClearSearch = document.getElementById('btnClearSearch');
        this.gradeFilter = document.getElementById('gradeFilter');
        this.cameraFilter = document.getElementById('cameraFilter');
        this.classesTableBody = document.getElementById('classesTableBody');
        this.showingCount = document.getElementById('showingCount');

        // Header Action Buttons
        this.btnRefreshList = document.getElementById('btnRefreshList');
        this.btnOpenCreateModal = document.getElementById('btnOpenCreateModal');
        this.btnOpenImportModal = document.getElementById('btnOpenImportModal');
        this.btnExportExcel = document.getElementById('btnExportExcel');
        this.btnDownloadTemplateMenu = document.getElementById('btnDownloadTemplateMenu');
        this.templateDropdownMenu = document.getElementById('templateDropdownMenu');
        this.btnDownloadXlsxTemplate = document.getElementById('btnDownloadXlsxTemplate');
        this.btnDownloadCsvTemplate = document.getElementById('btnDownloadCsvTemplate');

        // Modal 1: Create / Edit Class
        this.classModal = document.getElementById('classModal');
        this.classModalTitle = document.getElementById('classModalTitle');
        this.classForm = document.getElementById('classForm');
        this.formClassId = document.getElementById('formClassId');
        this.formClassName = document.getElementById('formClassName');
        this.formClassCode = document.getElementById('formClassCode');
        this.formRoomNumber = document.getElementById('formRoomNumber');
        this.formStandardCount = document.getElementById('formStandardCount');
        this.formChannelNumber = document.getElementById('formChannelNumber');
        this.formRtspUrl = document.getElementById('formRtspUrl');
        this.formIsActive = document.getElementById('formIsActive');
        this.radioModeNvr = document.getElementById('radioModeNvr');
        this.radioModeCustom = document.getElementById('radioModeCustom');
        this.panelNvrChannelSelect = document.getElementById('panelNvrChannelSelect');
        this.panelCustomRtspInput = document.getElementById('panelCustomRtspInput');

        // Modal 2: Import Excel / CSV
        this.importModal = document.getElementById('importModal');
        this.importDropzone = document.getElementById('importDropzone');
        this.importFileInput = document.getElementById('importFileInput');
        this.importStep1 = document.getElementById('importStep1');
        this.importStep2 = document.getElementById('importStep2');
        this.importFilenameDisplay = document.getElementById('importFilenameDisplay');
        this.importRowCountDisplay = document.getElementById('importRowCountDisplay');
        this.btnImportChangeFile = document.getElementById('btnImportChangeFile');
        this.mapColName = document.getElementById('mapColName');
        this.mapColCount = document.getElementById('mapColCount');
        this.mapColRoom = document.getElementById('mapColRoom');
        this.mapColChannel = document.getElementById('mapColChannel');
        this.importPreviewTableBody = document.getElementById('importPreviewTableBody');
        this.checkUpdateExisting = document.getElementById('checkUpdateExisting');
        this.btnConfirmBatchImport = document.getElementById('btnConfirmBatchImport');
        this.btnDownloadSampleXlsx = document.getElementById('btnDownloadSampleXlsx');
        this.btnDownloadSampleCsv = document.getElementById('btnDownloadSampleCsv');

        // Modal 3: Quick Count
        this.quickCountModal = document.getElementById('quickCountModal');
        this.quickCountForm = document.getElementById('quickCountForm');
        this.quickCountClassId = document.getElementById('quickCountClassId');
        this.quickCountInput = document.getElementById('quickCountInput');
        this.quickCountSubtitle = document.getElementById('quickCountSubtitle');

        // Modal 4: Classroom Image Lightbox
        this.cameraPreviewModal = document.getElementById('cameraPreviewModal');
        this.cameraPreviewTitle = document.getElementById('cameraPreviewTitle');
        this.cameraPreviewSubtitle = document.getElementById('cameraPreviewSubtitle');
        this.cameraPreviewImg = document.getElementById('cameraPreviewImg');
        this.cameraPreviewLoading = document.getElementById('cameraPreviewLoading');
        this.cameraPreviewInfo = document.getElementById('cameraPreviewInfo');
        this.btnOpenPhotoTab = document.getElementById('btnOpenPhotoTab');
    }

    attachEvents() {
        // Refresh
        this.btnRefreshList?.addEventListener('click', () => this.loadData(true));

        // Search & Filter
        let searchDebounce;
        this.searchInput?.addEventListener('input', () => {
            clearTimeout(searchDebounce);
            this.btnClearSearch.style.display = this.searchInput.value ? 'block' : 'none';
            searchDebounce = setTimeout(() => this.filterAndRender(), 200);
        });

        this.btnClearSearch?.addEventListener('click', () => {
            this.searchInput.value = '';
            this.btnClearSearch.style.display = 'none';
            this.filterAndRender();
        });

        this.gradeFilter?.addEventListener('change', () => this.filterAndRender());
        this.cameraFilter?.addEventListener('change', () => this.filterAndRender());

        // Dropdown Tải Tệp Mẫu
        this.btnDownloadTemplateMenu?.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = this.templateDropdownMenu.style.display === 'block';
            this.templateDropdownMenu.style.display = isOpen ? 'none' : 'block';
        });

        document.addEventListener('click', () => {
            if (this.templateDropdownMenu) this.templateDropdownMenu.style.display = 'none';
        });

        this.btnDownloadXlsxTemplate?.addEventListener('click', (e) => {
            e.preventDefault();
            this.downloadFile(ClassroomsAPI.getTemplateUrl('xlsx'), 'mau_nhap_danh_sach_lop_hoc_thpt_dieu_cai.xlsx');
        });

        this.btnDownloadCsvTemplate?.addEventListener('click', (e) => {
            e.preventDefault();
            this.downloadFile(ClassroomsAPI.getTemplateUrl('csv'), 'mau_nhap_danh_sach_lop_hoc.csv');
        });

        this.btnDownloadSampleXlsx?.addEventListener('click', () => {
            this.downloadFile(ClassroomsAPI.getTemplateUrl('xlsx'), 'mau_nhap_danh_sach_lop_hoc_thpt_dieu_cai.xlsx');
        });

        this.btnDownloadSampleCsv?.addEventListener('click', () => {
            this.downloadFile(ClassroomsAPI.getTemplateUrl('csv'), 'mau_nhap_danh_sach_lop_hoc.csv');
        });

        // Xuất Excel
        this.btnExportExcel?.addEventListener('click', () => {
            const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
            this.downloadFile(ClassroomsAPI.getExportUrl(), `danh_sach_lop_hoc_dieu_cai_${today}.xlsx`);
        });

        // Modal Thêm Mới Lớp Học
        this.btnOpenCreateModal?.addEventListener('click', () => this.openCreateModal());
        this.classForm?.addEventListener('submit', (e) => this.handleSaveClass(e));

        // Chuyển chế độ NVR vs Custom RTSP trong modal
        this.radioModeNvr?.addEventListener('change', () => this.toggleCameraSourceMode());
        this.radioModeCustom?.addEventListener('change', () => this.toggleCameraSourceMode());

        // Modal Import Excel / CSV
        this.btnOpenImportModal?.addEventListener('click', () => this.openImportModal());
        this.setupDropzone();
        this.btnImportChangeFile?.addEventListener('click', () => this.resetImportStep1());
        this.btnConfirmBatchImport?.addEventListener('click', () => this.handleConfirmBatchImport());

        // Mapping column change listeners
        [this.mapColName, this.mapColCount, this.mapColRoom, this.mapColChannel].forEach(el => {
            el?.addEventListener('change', () => this.updatePreviewFromMapping());
        });

        // Quick Count Submit
        this.quickCountForm?.addEventListener('submit', (e) => this.handleQuickCountSubmit(e));

        // Generic modal close handler
        document.querySelectorAll('[data-close-modal]').forEach(btn => {
            btn.addEventListener('click', () => this.closeAllModals());
        });

        // Close on backdrop click
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
            backdrop.addEventListener('click', (e) => {
                if (e.target === backdrop) this.closeAllModals();
            });
        });
    }

    async loadData(isManualRefresh = false) {
        if (this.isLoading) return;
        this.isLoading = true;
        this.renderSkeleton();

        try {
            const [classesRes, camerasRes] = await Promise.all([
                ClassroomsAPI.getAll(),
                ClassroomsAPI.getAvailableCameras().catch(() => ({ nvr_channels: [] }))
            ]);

            if (classesRes && classesRes.success) {
                this.classes = classesRes.data || [];
                this.updateStats(classesRes.stats);
            }

            if (camerasRes && camerasRes.success) {
                this.availableCameras = camerasRes.nvr_channels || [];
            }

            this.populateNvrChannelsDropdown();
            this.filterAndRender();

            if (isManualRefresh) {
                showToast('Đã làm mới dữ liệu danh sách lớp học', 'success');
            }
        } catch (err) {
            console.error('Lỗi tải dữ liệu lớp học:', err);
            showToast('Không thể tải danh sách lớp học: ' + (err.message || err), 'error');
            this.classesTableBody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 40px; color: #ef4444;">
                        <i class="fa-solid fa-triangle-exclamation" style="font-size: 2rem; margin-bottom: 8px;"></i>
                        <div>Lỗi kết nối máy chủ khi tải danh sách lớp học</div>
                        <button class="btn btn-secondary" onclick="window.classesManager.loadData()" style="margin-top: 12px;">Thử lại</button>
                    </td>
                </tr>
            `;
        } finally {
            this.isLoading = false;
        }
    }

    updateStats(stats) {
        if (!stats) return;
        if (this.statTotalClasses) this.statTotalClasses.textContent = stats.total_classes ?? this.classes.length;
        if (this.statTotalStudents) this.statTotalStudents.textContent = stats.total_students ? stats.total_students.toLocaleString() : '0';
        if (this.statAvgStudents) this.statAvgStudents.textContent = stats.avg_students ?? '0';
        if (this.statCameraRatio) {
            const ratioPercent = stats.total_classes > 0
                ? Math.round((stats.with_camera / stats.total_classes) * 100)
                : 0;
            this.statCameraRatio.textContent = `${stats.with_camera}/${stats.total_classes} (${ratioPercent}%)`;
        }
    }

    renderSkeleton() {
        if (!this.classesTableBody) return;
        let html = '';
        for (let i = 0; i < 8; i++) {
            html += `
                <tr>
                    <td style="text-align: center;"><div class="skeleton" style="width: 24px; height: 16px; margin: auto;"></div></td>
                    <td><div class="skeleton" style="width: 80px; height: 16px;"></div></td>
                    <td><div class="skeleton" style="width: 100px; height: 20px;"></div></td>
                    <td><div class="skeleton" style="width: 70px; height: 16px;"></div></td>
                    <td style="text-align: center;"><div class="skeleton" style="width: 50px; height: 24px; margin: auto; border-radius: 6px;"></div></td>
                    <td><div class="skeleton" style="width: 140px; height: 20px; border-radius: 6px;"></div></td>
                    <td style="text-align: center;"><div class="skeleton" style="width: 70px; height: 20px; margin: auto; border-radius: 6px;"></div></td>
                    <td style="text-align: center;"><div class="skeleton" style="width: 80px; height: 28px; margin: auto; border-radius: 6px;"></div></td>
                </tr>
            `;
        }
        this.classesTableBody.innerHTML = html;
    }

    filterAndRender() {
        const query = (this.searchInput?.value || '').toLowerCase().trim();
        const selectedGrade = this.gradeFilter?.value || 'all';
        const selectedCamera = this.cameraFilter?.value || 'all';

        let filtered = this.classes.filter(c => {
            // Lọc khối
            if (selectedGrade !== 'all' && c.grade !== selectedGrade) {
                return false;
            }

            // Lọc camera
            if (selectedCamera === 'with_camera' && !c.has_camera) return false;
            if (selectedCamera === 'no_camera' && c.has_camera) return false;

            // Tìm kiếm
            if (query) {
                const matchName = c.name.toLowerCase().includes(query);
                const matchCode = (c.code || '').toLowerCase().includes(query);
                const matchRoom = (c.room_number || '').toLowerCase().includes(query);
                const matchCam = (c.camera_label || '').toLowerCase().includes(query);
                if (!matchName && !matchCode && !matchRoom && !matchCam) {
                    return false;
                }
            }

            return true;
        });

        if (this.showingCount) {
            this.showingCount.textContent = filtered.length;
        }

        if (filtered.length === 0) {
            this.classesTableBody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 48px 20px; color: #94a3b8;">
                        <i class="fa-solid fa-magnifying-glass" style="font-size: 2.2rem; margin-bottom: 12px; color: #cbd5e1;"></i>
                        <div style="font-size: 1rem; font-weight: 600; color: #64748b; margin-bottom: 4px;">Không tìm thấy lớp học nào</div>
                        <div style="font-size: 0.82rem;">Thử thay đổi từ khóa tìm kiếm hoặc bỏ chọn các bộ lọc khối</div>
                    </td>
                </tr>
            `;
            return;
        }

        let html = '';
        filtered.forEach((c, idx) => {
            const gradeBadgeClass = `badge-grade-${c.grade}`;
            const cameraAction = c.has_camera
                ? `<button type="button" class="btn-view-class-photo" onclick="window.classesManager.openClassImageModal(${c.id}, '${escapeHtml(c.name)}')"
                     title="Xem hình ảnh chụp góc lớp ${escapeHtml(c.name)}">
                     <i class="fa-regular fa-image"></i> Xem hình lớp
                   </button>`
                : `<span class="badge-camera-none">
                     <i class="fa-solid fa-video-slash"></i> Chưa gán camera
                   </span>`;

            const statusBadge = c.is_active
                ? `<span class="badge badge-success" style="font-size: 0.78rem; font-weight: 600;">Hoạt động</span>`
                : `<span class="badge badge-secondary" style="font-size: 0.78rem;">Tạm ngưng</span>`;

            html += `
                <tr style="border-bottom: 1px solid #f1f5f9; transition: background 0.15s ease;" onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background=''">
                    <td class="col-stt" style="color: #64748b; font-weight: 600; font-size: 0.85rem;">${idx + 1}</td>
                    <td class="col-code" style="font-weight: 600; font-family: monospace; color: #475569; font-size: 0.82rem;">${escapeHtml(c.code || '--')}</td>
                    <td class="col-name">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <strong style="color: #0f172a; font-size: 0.95rem;">${escapeHtml(c.name)}</strong>
                            <span class="badge-grade ${gradeBadgeClass}">K${escapeHtml(c.grade)}</span>
                        </div>
                    </td>
                    <td class="col-room" style="color: #334155; font-weight: 500;">
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <i class="fa-solid fa-door-open" style="color: #94a3b8; font-size: 0.82rem;"></i>
                            <span>${escapeHtml(c.room_number || 'Chưa xếp phòng')}</span>
                        </div>
                    </td>
                    <td class="col-count">
                        <div class="student-count-display" onclick="window.classesManager.openQuickCountModal(${c.id}, '${escapeHtml(c.name)}', ${c.standard_count})"
                            title="Bấm để cập nhật nhanh sĩ số">
                            <span>${c.standard_count}</span>
                            <i class="fa-solid fa-pencil"></i>
                        </div>
                    </td>
                    <td class="col-photo">
                        <div style="display: inline-flex; justify-content: center; align-items: center;">
                            ${cameraAction}
                        </div>
                    </td>
                    <td class="col-status">${statusBadge}</td>
                    <td class="col-actions">
                        <div style="display: inline-flex; gap: 6px; justify-content: center;">
                            <button type="button" class="btn btn-secondary" onclick="window.classesManager.openEditModal(${c.id})"
                                style="width: 32px; height: 32px; padding: 0; display: inline-flex; align-items: center; justify-content: center; border-radius: 6px;"
                                title="Chỉnh sửa thông tin lớp & camera">
                                <i class="fa-solid fa-pen-to-square" style="color: #2563eb;"></i>
                            </button>
                            <button type="button" class="btn btn-secondary" onclick="window.classesManager.confirmDeleteClass(${c.id}, '${escapeHtml(c.name)}')"
                                style="width: 32px; height: 32px; padding: 0; display: inline-flex; align-items: center; justify-content: center; border-radius: 6px;"
                                title="Xóa lớp học khỏi hệ thống">
                                <i class="fa-solid fa-trash-can" style="color: #ef4444;"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });

        this.classesTableBody.innerHTML = html;
    }

    populateNvrChannelsDropdown(selectedChannel = null) {
        if (!this.formChannelNumber) return;
        let html = '<option value="">-- Chưa gán camera (Để trống) --</option>';

        for (let ch = 1; ch <= 30; ch++) {
            const camInfo = this.availableCameras.find(c => c.channel === ch);
            let label = `Kênh ${ch < 10 ? '0' + ch : ch} (Phòng ${ch})`;
            if (camInfo && camInfo.is_assigned && camInfo.assigned_class_name) {
                label += ` - Đang gán lớp ${camInfo.assigned_class_name}`;
            } else {
                label += ' - [Còn trống]';
            }
            const isSelected = selectedChannel !== null && Number(selectedChannel) === ch ? 'selected' : '';
            html += `<option value="${ch}" ${isSelected}>${label}</option>`;
        }

        this.formChannelNumber.innerHTML = html;
    }

    toggleCameraSourceMode() {
        const isCustom = this.radioModeCustom.checked;
        this.panelNvrChannelSelect.style.display = isCustom ? 'none' : 'block';
        this.panelCustomRtspInput.style.display = isCustom ? 'block' : 'none';
    }

    openCreateModal() {
        this.classModalTitle.innerHTML = `<i class="fa-solid fa-plus modal-title-icon" style="color: #2563eb;"></i> Thêm Lớp Học Mới`;
        this.formClassId.value = '';
        this.formClassName.value = '';
        this.formClassCode.value = '';
        this.formRoomNumber.value = '';
        this.formStandardCount.value = '44';
        this.formRtspUrl.value = '';
        this.formIsActive.checked = true;
        this.radioModeNvr.checked = true;
        this.toggleCameraSourceMode();
        this.populateNvrChannelsDropdown();
        this.classModal.classList.add('active');
        this.formClassName.focus();
    }

    async openEditModal(classId) {
        const cls = this.classes.find(c => c.id === classId);
        if (!cls) return;

        this.classModalTitle.innerHTML = `<i class="fa-solid fa-pen-to-square modal-title-icon" style="color: #2563eb;"></i> Chỉnh Sửa Lớp ${escapeHtml(cls.name)}`;
        this.formClassId.value = cls.id;
        this.formClassName.value = cls.name;
        this.formClassCode.value = cls.code || '';
        this.formRoomNumber.value = cls.room_number || '';
        this.formStandardCount.value = cls.standard_count || 40;
        this.formRtspUrl.value = cls.rtsp_url || '';
        this.formIsActive.checked = cls.is_active !== false;

        if (cls.channel_number && cls.channel_number > 0) {
            this.radioModeNvr.checked = true;
            this.populateNvrChannelsDropdown(cls.channel_number);
        } else if (cls.rtsp_url) {
            this.radioModeCustom.checked = true;
        } else {
            this.radioModeNvr.checked = true;
            this.populateNvrChannelsDropdown(null);
        }
        this.toggleCameraSourceMode();
        this.classModal.classList.add('active');
    }

    async handleSaveClass(e) {
        e.preventDefault();
        const id = this.formClassId.value;
        const name = this.formClassName.value.trim();
        const code = this.formClassCode.value.trim();
        const roomNumber = this.formRoomNumber.value.trim();
        const standardCount = parseInt(this.formStandardCount.value, 10);
        const isActive = this.formIsActive.checked;

        if (!name) {
            showToast('Vui lòng nhập tên lớp học', 'warning');
            return;
        }

        let channelNumber = null;
        let rtspUrl = '';

        if (this.radioModeNvr.checked) {
            const chVal = this.formChannelNumber.value;
            if (chVal) {
                channelNumber = parseInt(chVal, 10);
                rtspUrl = `rtsp://localhost:8554/stream${channelNumber}`;
            }
        } else {
            rtspUrl = this.formRtspUrl.value.trim();
        }

        const payload = {
            name,
            code: code || undefined,
            room_number: roomNumber,
            standard_count: standardCount,
            channel_number: channelNumber,
            rtsp_url: rtspUrl,
            is_active: isActive
        };

        const btnSave = document.getElementById('btnSaveClass');
        const origBtnText = btnSave.innerHTML;
        btnSave.disabled = true;
        btnSave.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...`;

        try {
            if (id) {
                await ClassroomsAPI.update(id, payload);
                showToast(`Đã cập nhật lớp ${name} thành công`, 'success');
            } else {
                await ClassroomsAPI.create(payload);
                showToast(`Đã thêm mới lớp ${name} thành công`, 'success');
            }
            this.closeAllModals();
            this.loadData();
        } catch (err) {
            showToast('Lỗi lưu lớp học: ' + (err.message || err), 'error');
        } finally {
            btnSave.disabled = false;
            btnSave.innerHTML = origBtnText;
        }
    }

    openQuickCountModal(classId, className, currentCount) {
        this.quickCountClassId.value = classId;
        this.quickCountSubtitle.textContent = `Lớp ${className}`;
        this.quickCountInput.value = currentCount;
        this.quickCountModal.classList.add('active');
        setTimeout(() => {
            this.quickCountInput.focus();
            this.quickCountInput.select();
        }, 50);
    }

    async handleQuickCountSubmit(e) {
        e.preventDefault();
        const id = this.quickCountClassId.value;
        const count = parseInt(this.quickCountInput.value, 10);
        if (!count || count < 1 || count > 100) {
            showToast('Sĩ số phải từ 1 đến 100 học sinh', 'warning');
            return;
        }

        try {
            await ClassroomsAPI.quickUpdateCount(id, count);
            showToast(`Cập nhật sĩ số thành công: ${count} học sinh`, 'success');
            this.closeAllModals();

            // Update in-memory state
            const cls = this.classes.find(c => c.id == id);
            if (cls) cls.standard_count = count;
            this.filterAndRender();

            // Re-calculate stats
            const totalStudents = this.classes.reduce((sum, c) => sum + c.standard_count, 0);
            const avg = Math.round((totalStudents / this.classes.length) * 10) / 10;
            if (this.statTotalStudents) this.statTotalStudents.textContent = totalStudents.toLocaleString();
            if (this.statAvgStudents) this.statAvgStudents.textContent = avg;
        } catch (err) {
            showToast('Lỗi cập nhật sĩ số: ' + (err.message || err), 'error');
        }
    }

    async confirmDeleteClass(classId, className) {
        const confirmed = confirm(`Bạn có chắc chắn muốn xóa lớp "${className}"?\nToàn bộ dữ liệu gắn camera và vùng ROI của lớp này cũng sẽ bị xóa.`);
        if (!confirmed) return;

        try {
            await ClassroomsAPI.delete(classId);
            showToast(`Đã xóa lớp "${className}" khỏi hệ thống`, 'success');
            this.loadData();
        } catch (err) {
            showToast('Lỗi xóa lớp: ' + (err.message || err), 'error');
        }
    }

    openClassImageModal(classId, className) {
        if (!this.cameraPreviewModal) return;

        this.cameraPreviewTitle.innerHTML = `<i class="fa-regular fa-image modal-title-icon" style="color: #2563eb;"></i> Hình Ảnh Lớp: ${escapeHtml(className)}`;
        this.cameraPreviewSubtitle.textContent = `Ảnh chụp góc quan sát phòng học ${className}`;
        this.cameraPreviewInfo.innerHTML = `<i class="fa-solid fa-camera" style="color: #0ea5e9;"></i> Lớp <strong>${escapeHtml(className)}</strong> • Tệp: <code>Lop_${classId}.jpg</code>`;

        if (this.cameraPreviewImg) {
            this.cameraPreviewImg.style.display = 'none';
        }
        if (this.cameraPreviewLoading) {
            this.cameraPreviewLoading.style.display = 'flex';
            this.cameraPreviewLoading.innerHTML = `
                <i class="fa-solid fa-circle-notch fa-spin" style="color: #38bdf8; font-size: 2rem;"></i>
                <span>Đang tải hình ảnh phòng học...</span>
            `;
        }

        const photoUrl = `/storage/captures/latest/Lop_${classId}.jpg?t=${Date.now()}`;
        if (this.btnOpenPhotoTab) {
            this.btnOpenPhotoTab.href = photoUrl;
            this.btnOpenPhotoTab.style.display = 'inline-flex';
        }

        this.cameraPreviewModal.classList.add('active');

        if (this.cameraPreviewImg) {
            this.cameraPreviewImg.onload = () => {
                if (this.cameraPreviewLoading) this.cameraPreviewLoading.style.display = 'none';
                this.cameraPreviewImg.style.display = 'block';
            };

            this.cameraPreviewImg.onerror = () => {
                if (this.cameraPreviewLoading) {
                    this.cameraPreviewLoading.style.display = 'flex';
                    this.cameraPreviewLoading.innerHTML = `
                        <i class="fa-solid fa-image-slash" style="font-size: 2.2rem; color: #64748b; margin-bottom: 8px;"></i>
                        <span style="font-size: 0.95rem; font-weight: 600; color: #cbd5e1;">Chưa có ảnh chụp của lớp này</span>
                        <span style="font-size: 0.8rem; color: #94a3b8;">Hệ thống sẽ tự động cập nhật khi camera lớp được kích hoạt hoặc quét điểm danh.</span>
                    `;
                }
                this.cameraPreviewImg.style.display = 'none';
                if (this.btnOpenPhotoTab) {
                    this.btnOpenPhotoTab.style.display = 'none';
                }
            };

            this.cameraPreviewImg.src = photoUrl;
        }
    }

    // Alias để tương thích ngược
    openCameraPreviewModal(classId, className) {
        this.openClassImageModal(classId, className);
    }

    async downloadFile(url, defaultFilename) {
        try {
            showToast('Đang tạo và tải tệp tin...', 'info');
            const res = await fetch(url, { credentials: 'include' });
            if (!res.ok) {
                let errText = `Lỗi máy chủ (${res.status})`;
                try {
                    const errJson = await res.json();
                    if (errJson.detail) errText = errJson.detail;
                } catch(e) {}
                throw new Error(errText);
            }

            // 1. Trích xuất tên tệp từ header Content-Disposition (nếu có)
            let filename = defaultFilename || 'file';
            const disposition = res.headers.get('content-disposition');
            if (disposition) {
                // Ưu tiên RFC 5987: filename*=UTF-8''...
                const utf8Match = disposition.match(/filename\*=UTF-8''([^;\r\n]+)/i);
                if (utf8Match && utf8Match[1]) {
                    try {
                        filename = decodeURIComponent(utf8Match[1].trim());
                    } catch (e) {
                        filename = utf8Match[1].trim();
                    }
                } else {
                    // Chuẩn thông thường: filename="..." hoặc filename=...
                    const match = disposition.match(/filename="?([^";\r\n]+)"?/i);
                    if (match && match[1]) {
                        filename = match[1].trim();
                    }
                }
            }

            // 2. Kiểm tra và bổ sung phần mở rộng nếu tên tệp bị thiếu
            const lowerUrl = url.toLowerCase();
            const lowerDef = (defaultFilename || '').toLowerCase();
            const lowerName = filename.toLowerCase();

            const isXlsx = lowerUrl.includes('xlsx') || lowerDef.endsWith('.xlsx') || lowerUrl.includes('export');
            const isCsv = lowerUrl.includes('csv') || lowerDef.endsWith('.csv');

            if (isXlsx && !lowerName.endsWith('.xlsx')) {
                filename += '.xlsx';
            } else if (isCsv && !lowerName.endsWith('.csv')) {
                filename += '.csv';
            }

            // 3. Xác định MIME type tương ứng chuẩn quốc tế
            let mimeType = 'application/octet-stream';
            if (filename.toLowerCase().endsWith('.xlsx')) {
                mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
            } else if (filename.toLowerCase().endsWith('.csv')) {
                mimeType = 'text/csv;charset=utf-8;';
            }

            // 4. Đọc nhị phân và tạo Blob chuẩn hóa MIME
            const arrayBuffer = await res.arrayBuffer();
            const blob = new Blob([arrayBuffer], { type: mimeType });
            const blobUrl = window.URL.createObjectURL(blob);

            // 5. Kích hoạt tải tệp tự động
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = blobUrl;
            a.download = filename;
            a.setAttribute('download', filename);
            document.body.appendChild(a);
            a.click();

            setTimeout(() => {
                a.remove();
                window.URL.revokeObjectURL(blobUrl);
            }, 2000);

            showToast(`Tải xuống "${filename}" thành công!`, 'success');
        } catch (err) {
            console.error('Lỗi tải tệp:', err);
            showToast('Không thể tải tệp tin: ' + (err.message || err), 'error');
        }
    }

    // ==========================================
    // EXCEL / CSV IMPORT WORKFLOW
    // ==========================================
    openImportModal() {
        this.resetImportStep1();
        this.importModal.classList.add('active');
    }

    resetImportStep1() {
        this.importStep1.style.display = 'block';
        this.importStep2.style.display = 'none';
        this.btnConfirmBatchImport.style.display = 'none';
        this.importFileInput.value = '';
        this.importPreviewData = null;
        this.currentPreviewFile = null;
    }

    setupDropzone() {
        if (!this.importDropzone) return;

        this.importDropzone.addEventListener('click', () => {
            this.importFileInput.click();
        });

        this.importFileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) this.handleProcessImportFile(file);
        });

        this.importDropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.importDropzone.classList.add('dragover');
        });

        this.importDropzone.addEventListener('dragleave', () => {
            this.importDropzone.classList.remove('dragover');
        });

        this.importDropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.importDropzone.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file) this.handleProcessImportFile(file);
        });
    }

    async handleProcessImportFile(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['xlsx', 'xls', 'csv'].includes(ext)) {
            showToast('Chỉ hỗ trợ file định dạng Excel (.xlsx, .xls) hoặc CSV (.csv)', 'warning');
            return;
        }

        this.currentPreviewFile = file;
        showToast('Đang phân tích cấu trúc tệp dữ liệu...', 'info');

        try {
            const res = await ClassroomsAPI.importPreview(file);
            if (res && res.success) {
                this.importPreviewData = res;
                this.renderImportStep2(res);
            }
        } catch (err) {
            showToast('Lỗi đọc tệp: ' + (err.message || err), 'error');
        }
    }

    renderImportStep2(data) {
        this.importStep1.style.display = 'none';
        this.importStep2.style.display = 'block';
        this.btnConfirmBatchImport.style.display = 'inline-flex';

        this.importFilenameDisplay.textContent = data.filename;
        this.importRowCountDisplay.textContent = `${data.total_rows} dòng dữ liệu`;

        // Populate column mapping dropdowns
        const headers = data.headers || [];
        const detected = data.detected_mapping || {};

        const populateSelect = (selectEl, defaultCol) => {
            let html = '<option value="">-- Bỏ qua cột này --</option>';
            headers.forEach(h => {
                const isSelected = h === defaultCol ? 'selected' : '';
                html += `<option value="${escapeHtml(h)}" ${isSelected}>${escapeHtml(h)}</option>`;
            });
            selectEl.innerHTML = html;
        };

        populateSelect(this.mapColName, detected.name_col);
        populateSelect(this.mapColCount, detected.count_col);
        populateSelect(this.mapColRoom, detected.room_col);
        populateSelect(this.mapColChannel, detected.channel_col);

        this.renderPreviewTable(data.preview_rows);
    }

    renderPreviewTable(rows) {
        if (!this.importPreviewTableBody) return;
        if (!rows || rows.length === 0) {
            this.importPreviewTableBody.innerHTML = `
                <tr><td colspan="6" style="text-align: center; padding: 20px; color: #94a3b8;">Không có dữ liệu xem trước</td></tr>
            `;
            return;
        }

        let html = '';
        rows.forEach(r => {
            const badgeAction = r.is_existing
                ? `<span class="preview-badge-update">Cập nhật</span>`
                : `<span class="preview-badge-new">Thêm mới</span>`;

            const chLabel = r.channel_number ? `Kênh NVR ${r.channel_number}` : (r.rtsp_url ? 'RTSP Custom' : 'Chưa gán');

            html += `
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="padding: 6px 8px; text-align: center; color: #64748b;">${r.index}</td>
                    <td style="padding: 6px 8px; font-weight: 700; color: #0f172a;">${escapeHtml(r.name)}</td>
                    <td style="padding: 6px 8px; text-align: center; font-weight: 600; color: #2563eb;">${r.standard_count}</td>
                    <td style="padding: 6px 8px; color: #475569;">${escapeHtml(r.room_number || '--')}</td>
                    <td style="padding: 6px 8px; font-size: 0.78rem; color: #059669;">${escapeHtml(chLabel)}</td>
                    <td style="padding: 6px 8px; text-align: center;">${badgeAction}</td>
                </tr>
            `;
        });

        this.importPreviewTableBody.innerHTML = html;
    }

    updatePreviewFromMapping() {
        if (!this.importPreviewData) return;
        // Client-side quick feedback on mapping change
        const nameCol = this.mapColName.value;
        const countCol = this.mapColCount.value;
        const roomCol = this.mapColRoom.value;
        const channelCol = this.mapColChannel.value;

        // Update preview rows based on selected columns
        const updatedRows = (this.importPreviewData.preview_rows || []).map(r => ({
            ...r,
            // Re-render
        }));
        this.renderPreviewTable(updatedRows);
    }

    async handleConfirmBatchImport() {
        if (!this.importPreviewData || !this.importPreviewData.preview_rows) {
            showToast('Không có dữ liệu hợp lệ để import', 'warning');
            return;
        }

        const items = this.importPreviewData.preview_rows.map(r => ({
            name: r.name,
            standard_count: r.standard_count || 40,
            room_number: r.room_number || '',
            channel_number: r.channel_number || null,
            rtsp_url: r.rtsp_url || '',
            is_active: true
        }));

        const updateExisting = this.checkUpdateExisting ? this.checkUpdateExisting.checked : true;

        this.btnConfirmBatchImport.disabled = true;
        this.btnConfirmBatchImport.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu dữ liệu...`;

        try {
            const res = await ClassroomsAPI.batchImport({
                items,
                update_existing: updateExisting
            });

            if (res && res.success) {
                showToast(res.message || 'Import danh sách lớp học thành công!', 'success');
                this.closeAllModals();
                this.loadData();
            }
        } catch (err) {
            showToast('Lỗi khi lưu danh sách lớp học: ' + (err.message || err), 'error');
        } finally {
            this.btnConfirmBatchImport.disabled = false;
            this.btnConfirmBatchImport.innerHTML = `<i class="fa-solid fa-check"></i> Xác Nhận Lưu Dữ Liệu`;
        }
    }

    closeAllModals() {
        [this.classModal, this.importModal, this.quickCountModal, this.cameraPreviewModal].forEach(m => {
            if (m) {
                m.classList.remove('active');
                m.style.display = '';
            }
        });
        if (this.cameraPreviewImg) {
            this.cameraPreviewImg.src = '';
        }
    }
}

// Khởi chạy an toàn khi DOM sẵn sàng
function initClassesManager() {
    if (!window.classesManager) {
        window.classesManager = new ClassesManager();
    }
    return window.classesManager;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initClassesManager);
} else {
    initClassesManager();
}

window.openImportModal = () => {
    const mgr = initClassesManager();
    mgr.openImportModal();
};

window.openCreateModal = () => {
    const mgr = initClassesManager();
    mgr.openCreateModal();
};
