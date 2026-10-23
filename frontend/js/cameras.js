/**
 * ===================================================================
 * cameras.js - Camera Management Page Main Controller (Modular ES6)
 * THPT Điều Cải - Attendance System
 * ===================================================================
 */

import { CameraAPI, AttendanceAPI, showToast, API_BASE, escapeHtml } from './api.js';
import SkeletonTemplates from './components/skeleton-templates.js';
import { progressModal } from './components/progress_modal.js';
import { VmsSurveillanceController } from './modules/cameras/vms-controller.js';

// Import các sub-modules độc lập theo chuẩn ES6
import {
    openNvrModal,
    closeNvrModal,
    fillSchoolPreset,
    probeNVRChannels,
    toggleAllNvrChannels,
    saveNvrImport
} from './modules/cameras/nvr-wizard.js';

import {
    renderMatrixWall,
    closeAllCardMenus,
    updateBatchActionBar,
    deleteSelectedCameras,
    batchToggleCameraStatus,
    openLiveModal,
    closeLiveModal,
    openRoiModal,
    closeRoiModal,
    initImageControls,
    setMatrixCallbacks,
    setMatrixCameras,
    getMatrixSelectedIds,
    clearMatrixSelection
} from './modules/cameras/matrix-wall.js';

import {
    loadAvailableWebcams,
    updateBannerWebcamStatus,
    renderWebcamCards,
    selectWebcam,
    switchSourceTab,
    syncManualUrl,
    toggleAdvancedInput,
    applyPreset,
    openModalWithWebcam,
    openModal,
    closeModal,
    editCamera,
    testCurrentInputSource,
    testCameraIRNow,
    testSignalFlowAndCapture,
    runCameraValidationWizard,
    testCameraDirectly,
    saveCamera,
    deleteCamera,
    openDeleteModal,
    closeDeleteModal,
    confirmBatchDelete,
    resetDefaults,
    setCrudCallbacks,
    setCrudCameras
} from './modules/cameras/camera-crud.js';

const esc = (v) => escapeHtml(v);

if (typeof window !== 'undefined') {
    window.CameraAPI = CameraAPI;
    window.AttendanceAPI = AttendanceAPI;
}

let allCameras = [];
let isScanning = false;

// Đăng ký callbacks 2 chiều giữa controller và các sub-modules
setMatrixCallbacks({
    onEditCamera: (id) => editCamera(id),
    onDeleteCamera: (id, name) => deleteCamera(id, name),
    onRefreshCameras: async () => await loadCameras()
});

setCrudCallbacks({
    onRefreshCameras: async () => await loadCameras()
});

function initApp() {
    window.vmsSurveillance = new VmsSurveillanceController();

    loadCameras();
    loadAvailableWebcams();
    loadCameraSourceStatus();
    initImageControls();
    initSourceManagerEvents();
    initClassroomSearch();
    initScheduleModalEvents();

    const btnVmsAddNvr = document.getElementById('btnVmsAddNVR');
    if (btnVmsAddNvr) btnVmsAddNvr.addEventListener('click', openNvrModal);

    const btnVmsAddCam = document.getElementById('btnVmsAddCamera');
    if (btnVmsAddCam) btnVmsAddCam.addEventListener('click', () => openModal());

    const btnVmsRefresh = document.getElementById('btnVmsRefreshTree');
    if (btnVmsRefresh) btnVmsRefresh.addEventListener('click', loadCameras);

    // Event listeners
    const btnRefresh = document.getElementById('btnRefresh');
    if (btnRefresh) btnRefresh.addEventListener('click', () => {
        loadCameras();
        loadCameraSourceStatus();
    });

    // Chụp lại ảnh đồng loạt 30 camera từ đầu ghi NVR
    const btnCaptureAll = document.getElementById('btnCaptureAllNow');
    if (btnCaptureAll) {
        btnCaptureAll.addEventListener('click', handleCaptureAll);
    }

    // Quick refresh button in banner
    const btnRefreshQuick = document.getElementById('btnRefreshQuick');
    if (btnRefreshQuick) btnRefreshQuick.addEventListener('click', loadCameras);

    // Quét điểm danh nhanh từ trang camera
    const btnTriggerScan = document.getElementById('btnTriggerScan');
    if (btnTriggerScan) btnTriggerScan.addEventListener('click', handleTriggerScan);

    const btnAdd = document.getElementById('btnAddCamera');
    if (btnAdd) btnAdd.addEventListener('click', () => openModal());

    const btnClose = document.getElementById('modalCloseBtn');
    if (btnClose) btnClose.addEventListener('click', closeModal);

    const btnCancel = document.getElementById('btnCancelModal');
    if (btnCancel) btnCancel.addEventListener('click', closeModal);

    const btnSave = document.getElementById('btnSaveCamera');
    if (btnSave) btnSave.addEventListener('click', saveCamera);

    const btnReset = document.getElementById('btnResetDefaults');
    if (btnReset) btnReset.addEventListener('click', resetDefaults);

    const btnTest = document.getElementById('btnTestStream');
    if (btnTest) btnTest.addEventListener('click', testCurrentInputSource);

    const btnTestIR = document.getElementById('btnTestCameraIR');
    if (btnTestIR) btnTestIR.addEventListener('click', testCameraIRNow);

    const btnTestSignal = document.getElementById('btnTestSignalFlow');
    if (btnTestSignal) btnTestSignal.addEventListener('click', testSignalFlowAndCapture);

    const btnWizard = document.getElementById('btnWizardValidateCamera');
    if (btnWizard) btnWizard.addEventListener('click', runCameraValidationWizard);

    const btnWebcamBanner = document.getElementById('btnWebcamBanner');
    if (btnWebcamBanner) btnWebcamBanner.addEventListener('click', openModalWithWebcam);

    const btnRefreshWebcams = document.getElementById('btnRefreshWebcams');
    if (btnRefreshWebcams) btnRefreshWebcams.addEventListener('click', () => loadAvailableWebcams(true));

    const tabWebcam = document.getElementById('tabBtnWebcam');
    if (tabWebcam) tabWebcam.addEventListener('click', () => switchSourceTab('WEBCAM'));

    const tabRtsp = document.getElementById('tabBtnRtsp');
    if (tabRtsp) tabRtsp.addEventListener('click', () => switchSourceTab('RTSP'));

    const tabFile = document.getElementById('tabBtnFile');
    if (tabFile) tabFile.addEventListener('click', () => switchSourceTab('FILE'));

    const linkAdv = document.getElementById('linkToggleAdvanced');
    if (linkAdv) linkAdv.addEventListener('click', toggleAdvancedInput);

    const btnLiveClose = document.getElementById('liveViewCloseBtn');
    if (btnLiveClose) btnLiveClose.addEventListener('click', closeLiveModal);

    const btnRefMat = document.getElementById('btnRefreshMatrix');
    if (btnRefMat) btnRefMat.addEventListener('click', loadCameras);

    const btnAddNvr = document.getElementById('btnAddNVR');
    if (btnAddNvr) btnAddNvr.addEventListener('click', openNvrModal);

    const btnCloseNvr = document.getElementById('nvrModalCloseBtn') || document.getElementById('modalNvrCloseBtn');
    if (btnCloseNvr) btnCloseNvr.addEventListener('click', closeNvrModal);

    const btnCancelNvr = document.getElementById('btnCancelNvrModal');
    if (btnCancelNvr) btnCancelNvr.addEventListener('click', closeNvrModal);

    const btnPresetHik = document.getElementById('btnFillSchoolPreset') || document.getElementById('btnPresetHikvision');
    if (btnPresetHik) btnPresetHik.addEventListener('click', fillSchoolPreset);

    const btnProbeNvr = document.getElementById('btnProbeNVR') || document.getElementById('btnProbeNvr');
    if (btnProbeNvr) btnProbeNvr.addEventListener('click', probeNVRChannels);

    const btnSelectAllNvr = document.getElementById('btnSelectAllNvr');
    if (btnSelectAllNvr) btnSelectAllNvr.addEventListener('click', () => toggleAllNvrChannels(true));

    const btnUnselectAllNvr = document.getElementById('btnUnselectAllNvr');
    if (btnUnselectAllNvr) btnUnselectAllNvr.addEventListener('click', () => toggleAllNvrChannels(false));

    const btnSaveNvr = document.getElementById('btnSaveNvrImport');
    if (btnSaveNvr) btnSaveNvr.addEventListener('click', async () => {
        await saveNvrImport();
        await loadCameras();
    });

    const btnOpenDel = document.getElementById('btnOpenDeleteModal');
    if (btnOpenDel) btnOpenDel.addEventListener('click', openDeleteModal);

    const btnCloseDel = document.getElementById('modalDeleteCloseBtn');
    if (btnCloseDel) btnCloseDel.addEventListener('click', closeDeleteModal);

    const btnCancelDel = document.getElementById('btnCancelDeleteModal');
    if (btnCancelDel) btnCancelDel.addEventListener('click', closeDeleteModal);

    const btnConfirmBatch = document.getElementById('btnConfirmDeleteBatch');
    if (btnConfirmBatch) btnConfirmBatch.addEventListener('click', confirmBatchDelete);

    const btnBatchDel = document.getElementById('btnBatchDeleteSelected');
    if (btnBatchDel) btnBatchDel.addEventListener('click', deleteSelectedCameras);

    const btnBatchDeselect = document.getElementById('btnBatchDeselectAll');
    if (btnBatchDeselect) btnBatchDeselect.addEventListener('click', () => {
        clearMatrixSelection();
        renderMatrixWall();
    });

    const btnBatchAct = document.getElementById('btnBatchActivate');
    if (btnBatchAct) btnBatchAct.addEventListener('click', () => batchToggleCameraStatus(true));

    const btnBatchDeact = document.getElementById('btnBatchDeactivate');
    if (btnBatchDeact) btnBatchDeact.addEventListener('click', () => batchToggleCameraStatus(false));

    document.querySelectorAll('button[data-preset]').forEach(btn => {
        btn.addEventListener('click', () => applyPreset(btn.dataset.preset));
    });

    const inputRtsp = document.getElementById('inputRtsp');
    if (inputRtsp) inputRtsp.addEventListener('input', (e) => syncManualUrl(e.target.value));

    const inputFile = document.getElementById('inputFile');
    if (inputFile) inputFile.addEventListener('input', (e) => syncManualUrl(e.target.value));

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.matrix-card-menu')) {
            closeAllCardMenus();
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
            closeDeleteModal();
            closeNvrModal();
            closeLiveModal();
            closeAllCardMenus();
            closeSourceManagerModal();
            closeScheduleModal();
        }
    });
}

/**
 * Kích hoạt quét điểm danh nhanh toàn trường kèm Progress Dialog
 */
export async function handleTriggerScan() {
    if (isScanning) return;
    const btn = document.getElementById('btnTriggerScan');

    const totalCams = allCameras.length || 30;
    const confirmed = await window.ConfirmationDialog?.confirm({
        title: 'Quét Điểm Danh Nhanh Toàn Trường',
        message: `Hệ thống sẽ đồng loạt quét và nhận diện sĩ số toàn bộ ${totalCams} lớp học qua Camera AI. Tiến trình chi tiết sẽ hiển thị trên màn hình. Bạn có chắc chắn muốn thực hiện ngay?`,
        confirmText: 'Bắt đầu quét ngay',
        confirmClass: 'btn-primary'
    }) ?? confirm(`Hệ thống sẽ đồng loạt quét toàn bộ ${totalCams} lớp học. Bạn có chắc chắn muốn thực hiện?`);

    if (!confirmed) return;

    isScanning = true;
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang quét toàn trường...';
    }

    try {
        const result = await progressModal.startAttendanceScan({
            onComplete: async (res) => {
                showToast(res.message || 'Quét điểm danh thành công!', 'success');
                await loadCameras();
            }
        });

        if (result && result.success) {
            showToast(result.message || 'Quét điểm danh thành công!', 'success');
            await loadCameras();
        }
    } catch (err) {
        console.error('Lỗi khi quét điểm danh:', err);
        showToast('Lỗi khi quét: ' + (err.message || err), 'danger');
    } finally {
        isScanning = false;
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-camera-rotate"></i> Quét Điểm Danh Toàn Trường';
        }
    }
}

/**
 * Chụp lại ảnh đồng loạt toàn bộ 30 camera
 */
export async function handleCaptureAll() {
    const btn = document.getElementById('btnCaptureAllNow');
    const totalCams = allCameras.length || 30;

    const confirmed = await window.ConfirmationDialog?.confirm({
        title: 'Chụp Lại Ảnh Toàn Bộ 30 Camera',
        message: `Hệ thống sẽ đồng loạt kết nối tới đầu ghi NVR và chụp lại khung hình thực tế mới nhất của tất cả ${totalCams} phòng học. Bạn có muốn tiếp tục?`,
        confirmText: 'Chụp Ngay Toàn Bộ',
        confirmClass: 'btn-success'
    }) ?? confirm(`Đồng loạt chụp lại ảnh thực tế mới nhất của ${totalCams} camera?`);

    if (!confirmed) return;

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang chụp 30 camera...';
    }

    try {
        const result = await progressModal.startCaptureAll({
            onComplete: async (res) => {
                showToast(res.message || 'Đã chụp lại ảnh toàn bộ camera!', 'success');
                await loadCameras();
            }
        });

        if (result && result.success) {
            showToast(result.message || 'Chụp ảnh toàn bộ thành công!', 'success');
            await loadCameras();
        }
    } catch (err) {
        console.error('Lỗi khi chụp ảnh toàn bộ:', err);
        showToast('Lỗi khi chụp: ' + (err.message || err), 'danger');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-camera"></i> Chụp Lại 30 Camera';
        }
    }
}

/**
 * Tải danh sách camera từ server
 */
export async function loadCameras() {
    const container = document.getElementById('matrixGrid');
    if (container && allCameras.length === 0) {
        const cachedCount = parseInt(localStorage.getItem('dieucai_classrooms_count'), 10) || 30;
        container.innerHTML = (SkeletonTemplates.cameraGrid || SkeletonTemplates.cameraMatrixGrid)(cachedCount);
    }
    try {
        const data = await CameraAPI.getAll();
        allCameras = data.cameras || [];
        if (allCameras.length > 0) {
            try {
                localStorage.setItem('dieucai_classrooms_count', allCameras.length);
            } catch (_) {}
        }
        setMatrixCameras(allCameras);
        setCrudCameras(allCameras);
        if (window.vmsSurveillance) {
            window.vmsSurveillance.setCameras(allCameras);
        }
        renderMatrixWall(allCameras);
    } catch (err) {
        console.error('Lỗi tải danh sách camera:', err);
        showToast('Không thể tải danh sách camera: ' + (err.message || err), 'error');
        if (container) {
            container.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: #ef4444;">
                    <i class="fa-solid fa-triangle-exclamation" style="font-size: 2rem; margin-bottom: 0.75rem; display: block;"></i>
                    <p style="margin-bottom: 1rem; font-weight: 600;">Không thể tải danh sách camera từ máy chủ</p>
                    <button type="button" class="btn btn-secondary btn-sm" id="btnRetryLoad">
                        <i class="fa-solid fa-rotate-right"></i> Thử lại
                    </button>
                </div>
            `;
            container.querySelector('#btnRetryLoad')?.addEventListener('click', loadCameras);
        }
    }
}

// ==================== QUẢN LÝ NGUỒN PHÁT (MOCK / REAL NVR) ====================
export async function loadCameraSourceStatus(checkFolder = null) {
    try {
        const res = await CameraAPI.getSourceStatus(checkFolder);
        if (!res || !res.success) return;

        const info = res.source_info;
        const banner = document.getElementById('cameraSourceBanner');
        const badge = document.getElementById('sourceModeBadge');
        const desc = document.getElementById('sourceModeDesc');
        const stats = document.getElementById('sourceStatsInfo');
        const mockNotice = document.getElementById('mockFolderNotice');

        if (badge) {
            if (info.mode === 'MOCK_IMAGES') {
                badge.className = 'source-badge badge-mock';
                badge.innerHTML = '<i class="fa-solid fa-images"></i> Đang Dùng Ảnh Test';
            } else if (info.mode === 'REAL_NVR') {
                badge.className = 'source-badge badge-nvr';
                badge.innerHTML = '<i class="fa-solid fa-server"></i> Đầu Ghi NVR Thật';
            } else {
                badge.className = 'source-badge badge-mixed';
                badge.innerHTML = '<i class="fa-solid fa-sliders"></i> Chế Độ Hỗn Hợp';
            }
        }

        if (desc) {
            if (info.mode === 'MOCK_IMAGES') {
                desc.innerHTML = `Nguồn phát: Thư mục <code>${esc(info.mock_folder)}</code> (${info.mock_image_count} ảnh test • Giả lập 30 lớp học).`;
            } else if (info.mode === 'REAL_NVR') {
                desc.innerHTML = `Đang kết nối luồng RTSP trực tiếp từ Đầu Ghi NVR (${esc(info.nvr_brand)} • ${esc(info.nvr_ip)}).`;
            } else {
                desc.innerHTML = `Hệ thống gồm ${info.mock_cams} camera dùng ảnh test và ${info.rtsp_cams} camera dùng luồng RTSP.`;
            }
        }

        if (stats) {
            stats.innerHTML = `
                <span class="stat-pill"><i class="fa-solid fa-camera"></i> ${info.total_cameras} camera</span>
                <span class="stat-pill"><i class="fa-solid fa-folder-open"></i> ${info.mock_image_count} ảnh test</span>
            `;
        }

        if (mockNotice) {
            if (info.mode === 'MOCK_IMAGES') {
                mockNotice.style.display = 'block';
                const fName = document.getElementById('noticeMockFolderName');
                if (fName) fName.innerText = info.mock_folder;
            } else {
                mockNotice.style.display = 'none';
            }
        }

        if (res.target_folder_details) {
            renderMockFolderDetails(res.target_folder_details);
        }
    } catch (err) {
        console.warn('Không thể nạp trạng thái nguồn phát camera:', err);
    }
}

function renderMockFolderDetails(details) {
    const previewBox = document.getElementById('mockFolderPreviewBox');
    if (!previewBox) return;

    if (!details || !details.exists) {
        previewBox.innerHTML = `
            <div class="mock-preview-empty error">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <strong>Thư mục không tồn tại:</strong> <code>${esc(details?.path || '')}</code>
                <p>Vui lòng chọn thư mục hợp lệ hoặc chọn từ danh sách gợi ý bên dưới.</p>
            </div>
        `;
        const btnApply = document.getElementById('btnApplyMockDeploy');
        if (btnApply) btnApply.disabled = true;
        return;
    }

    const btnApply = document.getElementById('btnApplyMockDeploy');
    if (btnApply) btnApply.disabled = (details.total_images === 0);

    let html = `
        <div class="mock-summary-card">
            <div class="summary-header">
                <div>
                    <strong>Thư mục:</strong> <code>${esc(details.path)}</code>
                    <span class="badge ${details.is_empty ? 'badge-danger' : 'badge-success'}" style="margin-left: 8px;">
                        ${details.total_images} ảnh
                    </span>
                </div>
                <div class="summary-size">${details.formatted_size || ''}</div>
            </div>
    `;

    if (details.sample_images && details.sample_images.length > 0) {
        html += '<div class="mock-sample-grid">';
        details.sample_images.forEach(img => {
            html += `
                <div class="mock-sample-thumb" title="${esc(img.filename)} (${img.formatted_size || ''})">
                    <img src="${img.url}" alt="${esc(img.filename)}" onerror="this.src='/dataset/samples/classroom_sample.jpg'">
                    <span class="thumb-name">${esc(img.filename)}</span>
                </div>
            `;
        });
        html += '</div>';
    } else {
        html += '<p style="color: #94a3b8; font-size: 0.85rem; margin-top: 8px;">Thư mục này hiện không chứa file ảnh nào (.jpg, .jpeg, .png).</p>';
    }

    html += '</div>';
    previewBox.innerHTML = html;
}

export async function inspectMockFolder(folderPath = null) {
    const input = document.getElementById('mockFolderInput');
    const target = folderPath || (input ? input.value.trim() : 'camera');
    const previewBox = document.getElementById('mockFolderPreviewBox');
    if (previewBox) {
        previewBox.innerHTML = '<div style="padding: 1.5rem; text-align: center; color: #64748b;"><i class="fa-solid fa-spinner fa-spin"></i> Đang kiểm tra thư mục...</div>';
    }
    await loadCameraSourceStatus(target);
}

export function openSourceManagerModal() {
    const modal = document.getElementById('modalSourceManager') || document.getElementById('sourceManagerModal');
    if (!modal) return;
    modal.classList.add('active');
    inspectMockFolder();
}

export function closeSourceManagerModal() {
    const modal = document.getElementById('modalSourceManager') || document.getElementById('sourceManagerModal');
    if (modal) modal.classList.remove('active');
}

export function switchSourceManagerTab(tab) {
    const tabNvr = document.getElementById('tabSourceNvr');
    const tabMock = document.getElementById('tabSourceMock');
    const panelNvr = document.getElementById('panelSourceNvr');
    const panelMock = document.getElementById('panelSourceMock');

    if (tabNvr) tabNvr.classList.toggle('active', tab === 'nvr');
    if (tabMock) tabMock.classList.toggle('active', tab === 'mock');
    if (panelNvr) panelNvr.style.display = (tab === 'nvr') ? 'block' : 'none';
    if (panelMock) panelMock.style.display = (tab === 'mock') ? 'block' : 'none';

    if (tab === 'mock') {
        inspectMockFolder();
    }
}

export function browseMockFolder() {
    const picker = document.getElementById('folderPickerInput');
    if (picker) {
        picker.click();
    }
}

export function selectMockPreset(folder) {
    const input = document.getElementById('mockFolderInput');
    if (input) {
        input.value = folder;
        inspectMockFolder(folder);
    }
}

export async function applyMockFolder() {
    const input = document.getElementById('mockFolderInput');
    const folder = input ? input.value.trim() : 'camera';
    const btn = document.getElementById('btnApplyMockDeploy');

    if (!folder) {
        alert('Vui lòng nhập tên thư mục ảnh test!');
        return;
    }

    const confirmed = await window.ConfirmationDialog?.confirm({
        title: 'Kích Hoạt Chế Độ Ảnh Test',
        message: `Hệ thống sẽ cập nhật lại toàn bộ 30 camera trỏ tới thư mục ảnh "${folder}". Toàn bộ quy trình điểm danh sẽ dùng các ảnh trong thư mục này.`,
        confirmText: 'Kích Hoạt Ngay',
        confirmClass: 'btn-primary'
    }) ?? confirm(`Kích hoạt toàn bộ 30 camera dùng ảnh từ thư mục "${folder}"?`);

    if (!confirmed) return;

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang cấu hình...';
    }

    try {
        const res = await CameraAPI.switchSourceMode({
            mode: 'MOCK_IMAGES',
            mock_folder: folder
        });

        if (res && res.success) {
            showToast(res.message || 'Đã chuyển nguồn phát thành công!', 'success');
            closeSourceManagerModal();
            await loadCameras();
            await loadCameraSourceStatus();
        } else {
            alert('Lỗi: ' + (res?.message || res?.detail || 'Không thể chuyển đổi'));
        }
    } catch (err) {
        console.error('Lỗi chuyển nguồn mock:', err);
        showToast('Lỗi: ' + (err.message || err), 'danger');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-play"></i> KÍCH HOẠT DÙNG THƯ MỤC NÀY CHO 30 CAMERA';
        }
    }
}

export async function deleteMockFolder() {
    const input = document.getElementById('mockFolderInput');
    const folder = input ? input.value.trim() : '';

    if (!folder) {
        alert('Vui lòng chọn thư mục muốn xóa!');
        return;
    }

    const confirmed = await window.ConfirmationDialog?.confirm({
        title: `Xóa Thư Mục Ảnh Test: ${folder}`,
        message: `CẢNH BÁO: Toàn bộ ảnh trong thư mục "${folder}" sẽ bị xóa vĩnh viễn khỏi máy chủ! Thao tác này không thể hoàn tác. Bạn có chắc chắn muốn xóa?`,
        confirmText: 'Xóa Vĩnh Viễn Thư Mục',
        confirmClass: 'btn-danger'
    }) ?? confirm(`CẢNH BÁO: Xóa vĩnh viễn thư mục "${folder}"?`);

    if (!confirmed) return;

    const btnDeleteMock = document.getElementById('btnDeleteMockFolder');
    if (btnDeleteMock) {
        btnDeleteMock.disabled = true;
        btnDeleteMock.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang xóa...';
    }

    try {
        const res = await CameraAPI.deleteMockFolder(folder);
        if (res && res.success) {
            showToast(res.message || 'Đã xóa thư mục ảnh!', 'success');
            if (input) input.value = 'camera';
            await inspectMockFolder('camera');
            await loadCameras();
            await loadCameraSourceStatus();
        } else {
            alert('Lỗi: ' + (res?.message || res?.detail || 'Không thể xóa thư mục'));
        }
    } catch (err) {
        console.error('Lỗi xóa thư mục ảnh test:', err);
        showToast('Lỗi: ' + (err.message || err), 'danger');
    } finally {
        if (btnDeleteMock) {
            btnDeleteMock.disabled = false;
            btnDeleteMock.innerHTML = '<i class="fa-solid fa-trash-can"></i> Xóa Thư Mục Này';
        }
    }
}

export async function applyNvrDeploy() {
    const btnApplyNvr = document.getElementById('btnApplyNvrDeploy');
    const ip = document.getElementById('deployNvrIp')?.value.trim() || '192.168.10.200';
    const port = parseInt(document.getElementById('deployNvrPort')?.value || '554', 10);
    const user = document.getElementById('deployNvrUser')?.value.trim() || 'admin';
    const pass = document.getElementById('deployNvrPass')?.value || '';
    const brand = document.getElementById('deployNvrBrand')?.value || 'DAHUA';
    const channelStart = parseInt(document.getElementById('deployNvrChannelStart')?.value || '1', 10);
    const cleanupMock = Boolean(document.getElementById('deployCleanupMock')?.checked);
    const mockFolder = document.getElementById('mockFolderInput')?.value.trim() || 'camera';

    if (!ip) {
        alert('Vui lòng nhập địa chỉ IP Đầu Ghi NVR!');
        return;
    }

    const confirmMsg = `Bạn có chắc chắn muốn chuyển đổi toàn bộ 30 camera sang luồng RTSP của Đầu Ghi NVR (${brand} - ${ip}:${port})?` +
        (cleanupMock ? `\n\nChú ý: Thư mục ảnh test (${mockFolder}) sẽ được XÓA BỎ sau khi chuyển đổi.` : '');

    const confirmed = await window.ConfirmationDialog?.confirm({
        title: 'Bàn Giao Đầu Ghi NVR Thật',
        message: confirmMsg,
        confirmText: 'Bàn Giao & Áp Dụng',
        confirmClass: 'btn-success'
    }) ?? confirm(confirmMsg);

    if (!confirmed) return;

    if (btnApplyNvr) {
        btnApplyNvr.disabled = true;
        btnApplyNvr.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Đang cấu hình và chuyển đổi...';
    }

    try {
        const res = await CameraAPI.switchSourceMode({
            mode: 'REAL_NVR',
            nvr_ip: ip,
            nvr_port: port,
            nvr_user: user,
            nvr_pass: pass,
            nvr_brand: brand,
            channel_start: channelStart,
            cleanup_mock_images: cleanupMock,
            mock_folder: mockFolder
        });

        if (res && res.success) {
            showToast(res.message || 'Đã chuyển sang Đầu Ghi NVR thành công!', 'success');
            closeSourceManagerModal();
            await loadCameras();
            await loadCameraSourceStatus();
        } else {
            alert('Lỗi: ' + (res?.message || res?.detail || 'Không thể chuyển đổi'));
        }
    } catch (err) {
        console.error('Lỗi chuyển đổi NVR:', err);
        showToast('Lỗi: ' + (err.message || err), 'danger');
    } finally {
        if (btnApplyNvr) {
            btnApplyNvr.disabled = false;
            btnApplyNvr.innerHTML = '<i class="fa-solid fa-rocket"></i> ÁP DỤNG ĐẦU GHI NVR & BÀN GIAO TOÀN BỘ 30 CAMERA';
        }
    }
}

function initSourceManagerEvents() {
    const btnOpen = document.getElementById('btnOpenSourceManager');
    if (btnOpen) btnOpen.addEventListener('click', openSourceManagerModal);

    const btnClose = document.getElementById('modalSourceCloseBtn');
    if (btnClose) btnClose.addEventListener('click', closeSourceManagerModal);

    const btnCancel = document.getElementById('btnCancelSourceModal');
    if (btnCancel) btnCancel.addEventListener('click', closeSourceManagerModal);

    const tabNvr = document.getElementById('tabSourceNvr');
    const tabMock = document.getElementById('tabSourceMock');
    if (tabNvr) tabNvr.addEventListener('click', () => switchSourceManagerTab('nvr'));
    if (tabMock) tabMock.addEventListener('click', () => switchSourceManagerTab('mock'));

    const btnCheck = document.getElementById('btnCheckMockFolder');
    if (btnCheck) {
        btnCheck.addEventListener('click', () => inspectMockFolder());
    }

    const inputMockFolder = document.getElementById('mockFolderInput');
    if (inputMockFolder) {
        let debounceTimer;
        inputMockFolder.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => inspectMockFolder(), 400);
        });
    }

    document.querySelectorAll('.preset-folder-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const folder = btn.dataset.folder;
            if (folder) selectMockPreset(folder);
        });
    });

    const btnBrowse = document.getElementById('btnBrowseMockFolder');
    const folderPicker = document.getElementById('folderPickerInput');
    if (btnBrowse && folderPicker) {
        btnBrowse.addEventListener('click', browseMockFolder);
        folderPicker.addEventListener('change', (e) => {
            const files = e.target.files;
            if (files && files.length > 0) {
                const relPath = files[0].webkitRelativePath || '';
                const dirName = relPath.split('/')[0] || '';
                if (dirName && inputMockFolder) {
                    inputMockFolder.value = dirName;
                    inspectMockFolder(dirName);
                    showToast(`Đã chọn thư mục: ${dirName} (${files.length} tệp)`, 'info');
                }
            }
        });
    }

    const btnApplyNvr = document.getElementById('btnApplyNvrDeploy');
    if (btnApplyNvr) {
        btnApplyNvr.addEventListener('click', applyNvrDeploy);
    }

    const btnApplyMock = document.getElementById('btnApplyMockDeploy');
    if (btnApplyMock) {
        btnApplyMock.addEventListener('click', applyMockFolder);
    }

    const btnDeleteMock = document.getElementById('btnDeleteMockFolder');
    if (btnDeleteMock) {
        btnDeleteMock.addEventListener('click', deleteMockFolder);
    }
}

export function initClassroomSearch() {
    const searchInput = document.getElementById('searchClassroomInput');
    const clearBtn = document.getElementById('btnClearClassroomSearch');
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim().toLowerCase();
        if (clearBtn) {
            clearBtn.style.display = query.length > 0 ? 'inline-block' : 'none';
        }

        const cards = document.querySelectorAll('#matrixGrid .matrix-card');
        let visibleCount = 0;
        cards.forEach(card => {
            const titleEl = card.querySelector('.matrix-class-title');
            const roomEl = card.querySelector('.matrix-class-room');
            const chEl = card.querySelector('.matrix-ch-badge');
            
            const title = (titleEl?.innerText || '').toLowerCase();
            const room = (roomEl?.innerText || '').toLowerCase();
            const ch = (chEl?.innerText || '').toLowerCase();

            const isMatch = !query || title.includes(query) || room.includes(query) || ch.includes(query);
            card.style.display = isMatch ? '' : 'none';
            if (isMatch) visibleCount++;
        });

        let emptyEl = document.getElementById('searchEmptyIndicator');
        if (visibleCount === 0 && query.length > 0 && cards.length > 0) {
            if (!emptyEl) {
                emptyEl = document.createElement('div');
                emptyEl.id = 'searchEmptyIndicator';
                emptyEl.style.cssText = 'grid-column: 1 / -1; text-align: center; padding: 2.5rem 1rem; color: #64748b; font-size: 0.95rem; font-weight: 600;';
                document.getElementById('matrixGrid')?.appendChild(emptyEl);
            }
            emptyEl.innerHTML = `<i class="fa-solid fa-magnifying-glass" style="margin-right: 6px; color: #94a3b8;"></i> Không tìm thấy phòng học nào khớp với từ khóa "<strong>${query}</strong>"`;
            emptyEl.style.display = 'block';
        } else if (emptyEl) {
            emptyEl.style.display = 'none';
        }
    });

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            searchInput.value = '';
            clearBtn.style.display = 'none';
            searchInput.dispatchEvent(new Event('input'));
            searchInput.focus();
        });
    }
}

// Gắn các hàm ra window để tương thích hoàn toàn các thuộc tính onclick trong HTML
window.selectWebcam = selectWebcam;
window.applyPreset = applyPreset;
window.switchSourceTab = switchSourceTab;
window.openModal = openModal;
window.closeModal = closeModal;
window.openModalWithWebcam = openModalWithWebcam;
window.openDeleteModal = openDeleteModal;
window.closeDeleteModal = closeDeleteModal;
window.openNvrModal = openNvrModal;
window.closeNvrModal = closeNvrModal;
window.fillSchoolPreset = fillSchoolPreset;
window.probeNVRChannels = probeNVRChannels;
window.toggleAllNvrChannels = toggleAllNvrChannels;
window.saveNvrImport = saveNvrImport;
window.renderMatrixWall = renderMatrixWall;
window.deleteSelectedCameras = deleteSelectedCameras;
window.updateBatchActionBar = updateBatchActionBar;
window.openSourceManagerModal = openSourceManagerModal;
window.closeSourceManagerModal = closeSourceManagerModal;
window.loadCameraSourceStatus = loadCameraSourceStatus;
window.inspectMockFolder = inspectMockFolder;
window.switchSourceManagerTab = switchSourceManagerTab;
window.browseMockFolder = browseMockFolder;
window.selectMockPreset = selectMockPreset;
window.applyMockFolder = applyMockFolder;
window.deleteMockFolder = deleteMockFolder;
window.applyNvrDeploy = applyNvrDeploy;
window.handleCaptureAll = handleCaptureAll;
window.handleTriggerScan = handleTriggerScan;
window.triggerCaptureAll = handleCaptureAll;
window.triggerAttendanceScan = handleTriggerScan;
window.openLiveModal = openLiveModal;
window.closeLiveModal = closeLiveModal;
window.openRoiModal = openRoiModal;
window.closeRoiModal = closeRoiModal;
window.initClassroomSearch = initClassroomSearch;
window.openScheduleModal = openScheduleModal;
window.closeScheduleModal = closeScheduleModal;
window.saveScheduleSettings = saveScheduleSettings;
window.loadScheduleSettings = loadScheduleSettings;

// ==================== QUẢN LÝ LỊCH QUÉT TỰ ĐỘNG (AUTO-SCAN SCHEDULE) ====================
export async function openScheduleModal() {
    const modal = document.getElementById('scheduleModal');
    if (!modal) return;
    modal.style.display = 'flex';
    modal.classList.add('active');
    await loadScheduleSettings();
}

export function closeScheduleModal() {
    const modal = document.getElementById('scheduleModal');
    if (!modal) return;
    modal.style.display = 'none';
    modal.classList.remove('active');
}

export async function loadScheduleSettings() {
    try {
        const res = await CameraAPI.getAutoSchedule();
        if (res && res.success) {
            const chk = document.getElementById('chkAutoScanEnabled');
            const chkAfternoon = document.getElementById('chkAfternoonScanEnabled');
            const inM = document.getElementById('inputMorningScanTime');
            const inA = document.getElementById('inputAfternoonScanTime');
            const selDays = document.getElementById('selectScheduleDays');
            const statusTxt = document.getElementById('scheduleStatusText');
            const aftHint = document.getElementById('afternoonScanHint');

            if (chk) chk.checked = Boolean(res.auto_scan_enabled);
            const aftEnabled = res.afternoon_enabled !== false;
            if (chkAfternoon) chkAfternoon.checked = aftEnabled;
            if (inM) inM.value = res.scan_time_morning || '06:45';
            if (inA) {
                inA.value = res.scan_time_afternoon || '12:45';
                inA.disabled = !aftEnabled;
                inA.style.opacity = aftEnabled ? '1' : '0.45';
            }
            if (aftHint) {
                aftHint.innerText = aftEnabled ? 'Khung chuẩn: 12:45 - 13:15' : 'Đã tắt ca chiều (không quét)';
            }
            if (selDays) selDays.value = res.schedule_days || 'mon-sat';

            updateScheduleDayChips(res.schedule_days || 'mon-sat');
            if (statusTxt) {
                statusTxt.innerText = res.auto_scan_enabled
                    ? 'Đang bật: Tự động quét theo lịch trình vào các ca học'
                    : 'Đang tắt: Hệ thống tạm ngưng quét tự động';
                statusTxt.style.color = res.auto_scan_enabled ? '#059669' : '#dc2626';
            }
        }
    } catch (err) {
        console.warn('Lỗi tải cài đặt lịch trình quét:', err);
    }
}

export function updateScheduleDayChips(daysMode) {
    const chips = document.querySelectorAll('#scheduleModal .day-chip');
    chips.forEach(chip => {
        const day = chip.getAttribute('data-day');
        if (daysMode === 'all') {
            chip.classList.add('active');
        } else if (daysMode === 'mon-fri') {
            if (['mon', 'tue', 'wed', 'thu', 'fri'].includes(day)) {
                chip.classList.add('active');
            } else {
                chip.classList.remove('active');
            }
        } else { // mon-sat default
            if (day !== 'sun') {
                chip.classList.add('active');
            } else {
                chip.classList.remove('active');
            }
        }
    });
}

export async function saveScheduleSettings() {
    const btn = document.getElementById('btnSaveScheduleSettings');
    const chk = document.getElementById('chkAutoScanEnabled');
    const chkAfternoon = document.getElementById('chkAfternoonScanEnabled');
    const inM = document.getElementById('inputMorningScanTime');
    const inA = document.getElementById('inputAfternoonScanTime');
    const selDays = document.getElementById('selectScheduleDays');

    const payload = {
        auto_scan_enabled: chk ? chk.checked : true,
        afternoon_enabled: chkAfternoon ? chkAfternoon.checked : true,
        scan_time_morning: inM ? inM.value.trim() : '06:45',
        scan_time_afternoon: inA ? inA.value.trim() : '12:45',
        schedule_days: selDays ? selDays.value : 'mon-sat'
    };

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';
    }

    try {
        const res = await CameraAPI.saveAutoSchedule(payload);
        if (res && res.success) {
            showToast('Đã lưu cấu hình lịch quét tự động thành công!', 'success');
            closeScheduleModal();
        } else {
            showToast(res.message || 'Không thể lưu lịch trình', 'danger');
        }
    } catch (err) {
        console.error('Lỗi khi lưu lịch trình:', err);
        showToast('Lỗi lưu lịch trình: ' + (err.message || err), 'danger');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Lưu Cài Đặt Lịch';
        }
    }
}

export function initScheduleModalEvents() {
    const btnOpen = document.getElementById('btnOpenScheduleModal');
    if (btnOpen) btnOpen.addEventListener('click', openScheduleModal);

    const btnClose = document.getElementById('scheduleModalCloseBtn');
    if (btnClose) btnClose.addEventListener('click', closeScheduleModal);

    const btnCancel = document.getElementById('btnCancelScheduleModal');
    if (btnCancel) btnCancel.addEventListener('click', closeScheduleModal);

    const btnSave = document.getElementById('btnSaveScheduleSettings');
    if (btnSave) btnSave.addEventListener('click', saveScheduleSettings);

    const selDays = document.getElementById('selectScheduleDays');
    if (selDays) {
        selDays.addEventListener('change', (e) => {
            updateScheduleDayChips(e.target.value);
        });
    }

    const chk = document.getElementById('chkAutoScanEnabled');
    if (chk) {
        chk.addEventListener('change', (e) => {
            const statusTxt = document.getElementById('scheduleStatusText');
            if (statusTxt) {
                statusTxt.innerText = e.target.checked
                    ? 'Đang bật: Tự động quét theo lịch trình vào các ca học'
                    : 'Đang tắt: Hệ thống tạm ngưng quét tự động';
                statusTxt.style.color = e.target.checked ? '#059669' : '#dc2626';
            }
        });
    }

    const chkAfternoon = document.getElementById('chkAfternoonScanEnabled');
    if (chkAfternoon) {
        chkAfternoon.addEventListener('change', (e) => {
            const inA = document.getElementById('inputAfternoonScanTime');
            const aftHint = document.getElementById('afternoonScanHint');
            if (inA) {
                inA.disabled = !e.target.checked;
                inA.style.opacity = e.target.checked ? '1' : '0.45';
            }
            if (aftHint) {
                aftHint.innerText = e.target.checked ? 'Khung chuẩn: 12:45 - 13:15' : 'Đã tắt ca chiều (không quét)';
            }
        });
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
