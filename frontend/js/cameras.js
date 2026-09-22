/**
 * cameras.js - Camera Management Page Controller
 * THPT Điều Cải - Attendance System
 */
import { CameraAPI, AttendanceAPI, showToast, API_BASE } from './api.js';
import SkeletonTemplates from './components/skeleton-templates.js';

if (typeof window !== 'undefined') {
    window.CameraAPI = CameraAPI;
    window.AttendanceAPI = AttendanceAPI;
}

let allCameras = [];
let availableWebcams = [];
let selectedWebcamId = '0';
let currentSourceType = 'WEBCAM';
let probedChannels = [];
let isScanning = false;

function initApp() {
    loadCameras();
    loadAvailableWebcams();
    initImageControls(); // Initialize image viewer controls

    // Event listeners
    const btnRefresh = document.getElementById('btnRefresh');
    if (btnRefresh) btnRefresh.addEventListener('click', loadCameras);

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

    // Sự kiện Modal Xóa Camera Chọn Lọc
    const btnOpenDelete = document.getElementById('btnOpenBatchDeleteModal');
    if (btnOpenDelete) btnOpenDelete.addEventListener('click', openDeleteModal);

    const btnCloseDel = document.getElementById('deleteModalCloseBtn');
    if (btnCloseDel) btnCloseDel.addEventListener('click', closeDeleteModal);

    const btnCancelDel = document.getElementById('btnCancelDeleteModal');
    if (btnCancelDel) btnCancelDel.addEventListener('click', closeDeleteModal);

    const btnCheckAll = document.getElementById('btnDeleteCheckAll');
    if (btnCheckAll) btnCheckAll.addEventListener('click', () => {
        const checklist = document.getElementById('deleteModalChecklist');
        if (checklist) checklist.querySelectorAll('.cam-del-cb').forEach(cb => cb.checked = true);
    });

    const btnUncheckAll = document.getElementById('btnDeleteUncheckAll');
    if (btnUncheckAll) btnUncheckAll.addEventListener('click', () => {
        const checklist = document.getElementById('deleteModalChecklist');
        if (checklist) checklist.querySelectorAll('.cam-del-cb').forEach(cb => cb.checked = false);
        const selQuick = document.getElementById('deleteModalSelectQuick');
        if (selQuick) selQuick.value = '';
    });

    const btnConfirmDel = document.getElementById('btnConfirmDeleteBatch');
    if (btnConfirmDel) btnConfirmDel.addEventListener('click', confirmBatchDelete);

    // ==================== MATRIX REFRESH ====================
    const btnRefMat = document.getElementById('btnRefreshMatrix');
    if (btnRefMat) btnRefMat.addEventListener('click', loadCameras);

    // ==================== NVR MODAL EVENTS ====================
    const btnOpenNvr = document.getElementById('btnAddNVR');
    if (btnOpenNvr) btnOpenNvr.addEventListener('click', openNvrModal);

    const btnCloseNvr = document.getElementById('nvrModalCloseBtn');
    if (btnCloseNvr) btnCloseNvr.addEventListener('click', closeNvrModal);

    const btnCancelNvr = document.getElementById('btnCancelNvrModal');
    if (btnCancelNvr) btnCancelNvr.addEventListener('click', closeNvrModal);

    const btnFillPreset = document.getElementById('btnFillSchoolPreset');
    if (btnFillPreset) btnFillPreset.addEventListener('click', fillSchoolPreset);

    const selectBrand = document.getElementById('nvrBrand');
    if (selectBrand) {
        selectBrand.addEventListener('change', () => {
            const patternBox = document.getElementById('nvrCustomPatternBox');
            if (patternBox) {
                patternBox.style.display = (selectBrand.value === 'CUSTOM') ? 'block' : 'none';
            }
        });
    }

    const btnProbe = document.getElementById('btnProbeNVR');
    if (btnProbe) btnProbe.addEventListener('click', probeNVRChannels);

    const btnSelectAll = document.getElementById('btnSelectAllNvr');
    if (btnSelectAll) btnSelectAll.addEventListener('click', () => toggleAllNvrChannels(true));

    const btnUnselectAll = document.getElementById('btnUnselectAllNvr');
    if (btnUnselectAll) btnUnselectAll.addEventListener('click', () => toggleAllNvrChannels(false));

    const btnSaveNvr = document.getElementById('btnSaveNvrImport');
    if (btnSaveNvr) btnSaveNvr.addEventListener('click', saveNvrImport);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}

/**
 * Quét điểm danh đồng loạt tất cả các lớp học trực tiếp từ trang Camera
 */
export async function handleTriggerScan() {
    if (isScanning) {
        showToast('Hệ thống đang trong quá trình quét điểm danh!', 'warning');
        return;
    }

    const btn = document.getElementById('btnTriggerScan');
    if (!confirm('Bạn có chắc chắn muốn kích hoạt quét điểm danh đồng loạt 30 lớp ngay bây giờ?')) {
        return;
    }

    try {
        isScanning = true;
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang quét...';
        }

        showToast('Đang kích hoạt quét và chụp ảnh đồng loạt các camera lớp học...', 'info');

        const result = await AttendanceAPI.triggerScan();

        if (result && result.success) {
            showToast('Đã hoàn tất phiên điểm danh 30 lớp!', 'success');
            await loadCameras();
        } else {
            showToast(result?.message || 'Quét điểm danh hoàn tất', 'info');
            await loadCameras();
        }

    } catch (err) {
        console.error('Lỗi khi quét điểm danh:', err);
        showToast('Lỗi khi kích hoạt quét điểm danh: ' + (err.message || err), 'danger');
    } finally {
        isScanning = false;
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-bolt" style="color: #fde047;"></i> Quét Điểm Danh';
        }
    }
}
if (typeof window !== 'undefined') {
    window.handleTriggerScan = handleTriggerScan;
}

// Load available webcams
export async function loadAvailableWebcams(forceRefresh = false) {
    const icon = document.getElementById('webcamRefreshIcon');
    const btn = document.getElementById('btnRefreshWebcams');
    if (icon) icon.classList.add('fa-spin');
    if (btn) btn.disabled = true;

    const container = document.getElementById('webcamListContainer');
    if (container && forceRefresh) {
        container.innerHTML = `
            <div class="webcam-card" style="pointer-events: none;">
                <div class="webcam-thumb-box skeleton" style="height: 110px; border-radius: 6px;"></div>
                <div class="webcam-card-info" style="margin-top: 6px;">
                    <div class="skeleton" style="width: 80%; height: 14px; margin-bottom: 4px;"></div>
                    <div class="skeleton" style="width: 50%; height: 12px;"></div>
                </div>
            </div>
            <div class="webcam-card" style="pointer-events: none;">
                <div class="webcam-thumb-box skeleton" style="height: 110px; border-radius: 6px;"></div>
                <div class="webcam-card-info" style="margin-top: 6px;">
                    <div class="skeleton" style="width: 70%; height: 14px; margin-bottom: 4px;"></div>
                    <div class="skeleton" style="width: 45%; height: 12px;"></div>
                </div>
            </div>
        `;
    }

    try {
        const data = await CameraAPI.getWebcams(forceRefresh);

        if (data && data.webcams) {
            availableWebcams = data.webcams;
            renderWebcamCards();
            updateBannerWebcamStatus();

            // Tự động chọn webcam đầu tiên khả dụng nếu chưa có hoặc ID hiện tại không tồn tại
            if (availableWebcams.length > 0) {
                const currentExists = availableWebcams.some(w => String(w.id) === String(selectedWebcamId));
                if (!currentExists) {
                    selectedWebcamId = String(availableWebcams[0].id);
                }
            }
        }
    } catch (err) {
        console.error('Lỗi khi tải danh sách webcam máy tính:', err);
        if (container) {
            container.innerHTML = `
                <div class="webcam-empty-box" style="color: #ef4444; padding: 1.25rem;">
                    <i class="fa-solid fa-circle-exclamation" style="font-size: 1.6rem; margin-bottom: 8px; display: block;"></i>
                    <strong>Không thể dò quét webcam máy tính:</strong><br>
                    <span style="font-size: 0.85rem; color: #64748b;">${err.message || err}</span>
                    <div style="margin-top: 10px;">
                        <button type="button" class="btn btn-secondary btn-sm" onclick="window.loadAvailableWebcams ? window.loadAvailableWebcams(true) : location.reload()">
                            <i class="fa-solid fa-rotate-right"></i> Thử Dò Tìm Lại
                        </button>
                    </div>
                </div>`;
        }
    } finally {
        if (icon) icon.classList.remove('fa-spin');
        if (btn) btn.disabled = false;
    }
}

if (typeof window !== 'undefined') {
    window.loadAvailableWebcams = loadAvailableWebcams;
}


function updateBannerWebcamStatus() {
    const badge = document.getElementById('webcamBannerText');
    if (!badge) return;
    if (availableWebcams.length > 0) {
        badge.innerHTML = `Webcam máy: <strong>${availableWebcams.length} camera</strong> sẵn sàng`;
    } else {
        badge.innerText = 'Chưa phát hiện Webcam máy';
    }
}

function renderWebcamCards() {
    const container = document.getElementById('webcamListContainer');
    if (!container) return;

    if (availableWebcams.length === 0) {
        container.innerHTML = `
            <div class="webcam-empty-box">
                <i class="fa-solid fa-video-slash" style="font-size: 1.5rem; color: #94a3b8; margin-bottom: 6px; display: block;"></i>
                Không tìm thấy camera/webcam nào đang kết nối trên máy tính.<br>
                <small style="color: var(--text-muted);">Hãy cắm webcam USB hoặc kiểm tra quyền truy cập Camera của Windows, sau đó bấm <strong>"Dò Tìm Lại"</strong>.</small>
            </div>
        `;
        return;
    }

    container.innerHTML = '';
    availableWebcams.forEach(cam => {
        const isSelected = String(cam.id) === String(selectedWebcamId);
        const card = document.createElement('div');
        card.className = `webcam-card ${isSelected ? 'selected' : ''}`;
        card.id = `webcam_card_${cam.id}`;
        card.onclick = () => selectWebcam(cam.id);

        const thumbHtml = cam.thumbnail
            ? `<img src="${cam.thumbnail}" class="webcam-thumb-img" alt="${cam.name}">`
            : `<div style="text-align: center; color: #64748b;"><i class="fa-solid fa-camera" style="font-size: 1.8rem;"></i></div>`;

        card.innerHTML = `
            <div class="webcam-thumb-box">
                ${thumbHtml}
                <span class="webcam-badge-id">Cổng ${cam.id}</span>
                <span class="webcam-badge-res">${cam.resolution}</span>
                <div class="webcam-selected-check"><i class="fa-solid fa-check"></i></div>
            </div>
            <div class="webcam-card-info">
                <div class="webcam-card-title" title="${cam.name}">${cam.short_name || cam.name}</div>
                <div class="webcam-card-sub"><i class="fa-solid fa-circle-check"></i> ${cam.quality_label || 'Hoạt động'}</div>
            </div>
        `;
        container.appendChild(card);
    });
}

export function selectWebcam(id) {
    selectedWebcamId = String(id);
    const rtspInput = document.getElementById('formRtspUrl');
    if (rtspInput) rtspInput.value = selectedWebcamId;

    document.querySelectorAll('.webcam-card').forEach(c => c.classList.remove('selected'));
    const targetCard = document.getElementById(`webcam_card_${id}`);
    if (targetCard) targetCard.classList.add('selected');

    const cam = availableWebcams.find(w => String(w.id) === String(id));
    if (cam) {
        const testMsg = document.getElementById('testStatusMsg');
        const testImg = document.getElementById('testPreviewImg');
        if (cam.thumbnail && testImg) {
            testImg.src = cam.thumbnail;
            testImg.style.display = 'inline-block';
        }
        if (testMsg) {
            testMsg.innerHTML = `<span style="color: #10b981; font-weight: 700;"><i class="fa-solid fa-circle-check"></i> Đã chọn ${cam.name} (${cam.resolution})</span>`;
        }

        const nameInput = document.getElementById('formName');
        const codeInput = document.getElementById('formCode');
        const isEdit = !!document.getElementById('formCamId').value;
        if (!isEdit) {
            if (!nameInput.value || nameInput.value.startsWith('Webcam')) {
                nameInput.value = `Webcam Test (${cam.short_name || 'Cổng ' + id})`;
            }
            if (!codeInput.value || codeInput.value.startsWith('CAM_WEBCAM')) {
                codeInput.value = `CAM_WEBCAM_${id}`;
            }
        }
    }
}

export function switchSourceTab(type) {
    currentSourceType = type;
    const tabWebcam = document.getElementById('tabBtnWebcam');
    const tabRtsp = document.getElementById('tabBtnRtsp');
    const tabFile = document.getElementById('tabBtnFile');

    if (tabWebcam) tabWebcam.classList.toggle('active', type === 'WEBCAM');
    if (tabRtsp) tabRtsp.classList.toggle('active', type === 'RTSP');
    if (tabFile) tabFile.classList.toggle('active', type === 'FILE');

    const pWebcam = document.getElementById('panelWebcam');
    const pRtsp = document.getElementById('panelRtsp');
    const pFile = document.getElementById('panelFile');

    if (pWebcam) pWebcam.style.display = (type === 'WEBCAM') ? 'block' : 'none';
    if (pRtsp) pRtsp.style.display = (type === 'RTSP') ? 'block' : 'none';
    if (pFile) pFile.style.display = (type === 'FILE') ? 'block' : 'none';

    const rtspInput = document.getElementById('formRtspUrl');
    if (type === 'WEBCAM') {
        if (rtspInput) rtspInput.value = selectedWebcamId || '0';
        renderWebcamCards();
    } else if (type === 'RTSP') {
        const val = (document.getElementById('inputRtsp')?.value || '').trim();
        if (rtspInput) rtspInput.value = val || 'rtsp://';
    } else if (type === 'FILE') {
        const val = (document.getElementById('inputFile')?.value || '').trim();
        if (rtspInput) rtspInput.value = val || 'dataset/samples/classroom_sample_15s.mp4';
    }
}

export function syncManualUrl(val) {
    const target = document.getElementById('formRtspUrl');
    if (target) target.value = (val || '').trim();
}

export function toggleAdvancedInput() {
    const box = document.getElementById('advancedUrlBox');
    if (box) box.style.display = (box.style.display === 'none') ? 'block' : 'none';
}

export async function loadCameras() {
    const container = document.getElementById('matrixGrid');
    if (container && allCameras.length === 0) {
        container.innerHTML = (SkeletonTemplates.cameraGrid || SkeletonTemplates.cameraMatrixGrid)(8);
    }
    try {
        const data = await CameraAPI.getAll();
        allCameras = data.cameras || [];
        renderMatrixWall();
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

// Removed renderKPIs() - Stats handled by Dashboard page only

export function applyPreset(type) {
    if (type === 'WEBCAM') {
        switchSourceTab('WEBCAM');
        if (availableWebcams.length > 0) {
            selectWebcam(availableWebcams[0].id);
        } else {
            selectWebcam('0');
        }
    } else if (type === 'FILE_VIDEO') {
        switchSourceTab('FILE');
        const input = document.getElementById('inputFile');
        if (input) {
            input.value = 'dataset/samples/classroom_sample_15s.mp4';
            syncManualUrl(input.value);
        }
    } else if (type === 'FILE_IMG') {
        switchSourceTab('FILE');
        const input = document.getElementById('inputFile');
        if (input) {
            input.value = 'dataset/samples/classroom_sample_1.jpg';
            syncManualUrl(input.value);
        }
    } else if (type === 'DAHUA') {
        switchSourceTab('RTSP');
        const input = document.getElementById('inputRtsp');
        if (input) {
            input.value = 'rtsp://admin:Lhu%402025@192.168.10.200:554/cam/realmonitor?channel=1&subtype=0';
            syncManualUrl(input.value);
        }
    } else if (type === 'HIK') {
        switchSourceTab('RTSP');
        const input = document.getElementById('inputRtsp');
        if (input) {
            input.value = 'rtsp://admin:matkhau@192.168.10.201:554/Streaming/Channels/101';
            syncManualUrl(input.value);
        }
    }
}

export function openModalWithWebcam() {
    openModal();
    switchSourceTab('WEBCAM');
}

export function openModal(camera = null) {
    document.getElementById('formCamId').value = camera ? camera.id : '';
    document.getElementById('modalTitle').innerText = camera ? `Chỉnh Sửa Camera: ${camera.name}` : 'Thêm Camera / Lớp Học Mới';

    const codeInput = document.getElementById('formCode');
    codeInput.value = camera ? camera.code : '';
    codeInput.disabled = !!camera;

    document.getElementById('formName').value = camera ? camera.name : '';
    document.getElementById('formRoom').value = camera ? camera.room_number : '';
    document.getElementById('formStandard').value = camera ? camera.standard_count : 40;
    document.getElementById('formRelayIp').value = camera ? camera.relay_ip : '192.168.10.200';
    document.getElementById('formActive').checked = camera ? camera.is_active : true;

    const previewImg = document.getElementById('testPreviewImg');
    if (previewImg) {
        previewImg.style.display = 'none';
        previewImg.src = '';
    }
    const statusMsg = document.getElementById('testStatusMsg');
    if (statusMsg) statusMsg.innerHTML = 'Bấm nút để thử kết nối và chụp 1 ảnh xem trước từ nguồn camera trên.';

    const url = camera ? (camera.rtsp_url || '').trim() : '';

    if (url) {
        if (url.match(/^\d+$/)) {
            switchSourceTab('WEBCAM');
            selectWebcam(url);
        } else if (url.startsWith('rtsp://')) {
            switchSourceTab('RTSP');
            const rInput = document.getElementById('inputRtsp');
            if (rInput) rInput.value = url;
            syncManualUrl(url);
        } else {
            switchSourceTab('FILE');
            const fInput = document.getElementById('inputFile');
            if (fInput) fInput.value = url;
            syncManualUrl(url);
        }
    } else {
        switchSourceTab('WEBCAM');
        if (availableWebcams.length > 0) {
            selectWebcam(availableWebcams[0].id);
        } else {
            selectWebcam('0');
        }
    }

    document.getElementById('cameraModal')?.classList.add('active');
}

export function closeModal() {
    document.getElementById('cameraModal')?.classList.remove('active');
}

export function editCamera(id) {
    const cam = allCameras.find(c => c.id === id);
    if (cam) openModal(cam);
}

export async function testCurrentInputSource() {
    const url = document.getElementById('formRtspUrl')?.value.trim();
    if (!url) {
        alert('Vui lòng nhập Đường dẫn nguồn Camera trước khi test!');
        return;
    }

    const btn = document.getElementById('btnTestStream');
    const msg = document.getElementById('testStatusMsg');
    const img = document.getElementById('testPreviewImg');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang kết nối...';
    }
    if (msg) msg.innerHTML = '<span style="color: var(--primary);">Đang kiểm tra tín hiệu từ camera...</span>';
    if (img) img.style.display = 'none';

    try {
        const data = await CameraAPI.testConnection(url);
        if (data.success) {
            if (msg) msg.innerHTML = `<span style="color: #10b981; font-weight: 700;"><i class="fa-solid fa-circle-check"></i> ${data.message}</span>`;
            if (data.preview_url && img) {
                img.src = data.preview_url;
                img.style.display = 'inline-block';
            }
            showToast('Kết nối thành công', 'success');
        } else {
            if (msg) msg.innerHTML = `<span style="color: #ef4444; font-weight: 600;"><i class="fa-solid fa-circle-xmark"></i> ${data.message}</span>`;
            showToast(data.message || 'Kết nối thất bại', 'error');
        }
    } catch (err) {
        if (msg) msg.innerHTML = `<span style="color: #ef4444;">Lỗi khi gửi yêu cầu kiểm tra: ${err.message || err}</span>`;
        showToast('Lỗi kết nối kiểm tra camera', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-play"></i> Bắt Ảnh Xem Trước';
        }
    }
}

export async function testCameraIRNow() {
    const url = document.getElementById('formRtspUrl')?.value.trim();
    const relayIp = document.getElementById('formRelayIp')?.value.trim();
    const camId = document.getElementById('formCamId')?.value;
    const btn = document.getElementById('btnTestCameraIR');
    const msg = document.getElementById('irStatusMsg');

    if (!url && !camId) {
        alert('Vui lòng chọn hoặc nhập nguồn Camera trước khi thử đèn!');
        return;
    }

    const originalText = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang bật đèn...';
    }
    if (msg) msg.innerHTML = '<span style="color: #ef4444; font-weight: 700;"><i class="fa-solid fa-lightbulb"></i> Đang kích hoạt đèn hồng ngoại camera (sáng đỏ 4 giây)...</span>';

    try {
        let res;
        if (camId) {
            res = await CameraAPI.testClassroomIR(camId, 4, 'IR_ON');
        } else {
            res = await CameraAPI.testIRByUrl(url, relayIp);
        }
        
        if (res && res.success) {
            if (msg) {
                msg.innerHTML = `<span style="color: #10b981; font-weight: 700;"><i class="fa-solid fa-circle-check"></i> ${res.message || 'Đèn hồng ngoại đã kích hoạt thành công (tự động tắt sau 4s)!'}</span>`;
            }
            showToast(res.message || 'Đã kích hoạt đèn hồng ngoại camera!', 'success');
        } else {
            const errMsg = (res && res.message) ? res.message : 'Không thể gửi lệnh điều khiển tới camera!';
            if (msg) {
                msg.innerHTML = `<span style="color: #ef4444; font-weight: 700;"><i class="fa-solid fa-triangle-exclamation"></i> ${errMsg}</span>`;
            }
            showToast(errMsg, 'warning');
        }
    } catch (err) {
        if (msg) msg.innerHTML = `<span style="color: #ef4444;"><i class="fa-solid fa-triangle-exclamation"></i> Lỗi: ${err.message || err}</span>`;
        showToast('Không thể kích hoạt đèn camera: ' + (err.message || err), 'warning');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
}

export async function testSignalFlowAndCapture() {
    const url = document.getElementById('formRtspUrl')?.value.trim();
    const relayIp = document.getElementById('formRelayIp')?.value.trim();
    if (!url) {
        alert('Vui lòng nhập Đường dẫn nguồn Camera trước khi test!');
        return;
    }

    const btn = document.getElementById('btnTestSignalFlow');
    const msg = document.getElementById('testStatusMsg');
    const img = document.getElementById('testPreviewImg');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang thử chu trình...';
    }
    if (msg) msg.innerHTML = '<span style="color: #0284c7; font-weight: 700;"><i class="fa-solid fa-lightbulb" style="color: #ef4444;"></i> Bước 1: Bật đèn hồng ngoại báo hiệu (2.5s) -> Bước 2: Chuyển sang ẢNH MÀU...</span>';
    if (img) img.style.display = 'none';

    try {
        const data = await CameraAPI.testConnection(url, true, relayIp);
        if (data.success) {
            if (msg) msg.innerHTML = `<span style="color: #10b981; font-weight: 700;"><i class="fa-solid fa-circle-check"></i> Hoàn tất chu trình: Đèn hồng ngoại đã báo hiệu thành công và thu nhận ẢNH MÀU chuẩn 100%!</span>`;
            if (data.preview_url && img) {
                img.src = data.preview_url;
                img.style.display = 'inline-block';
            }
            showToast('Chu trình hoàn tất: Thu nhận ảnh màu chuẩn', 'success');
        } else {
            if (msg) msg.innerHTML = `<span style="color: #ef4444; font-weight: 600;"><i class="fa-solid fa-circle-xmark"></i> ${data.message}</span>`;
            showToast(data.message || 'Thử chu trình thất bại', 'error');
        }
    } catch (err) {
        if (msg) msg.innerHTML = `<span style="color: #ef4444;">Lỗi: ${err.message || err}</span>`;
        showToast('Lỗi thử chu trình: ' + (err.message || err), 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Thử Chu Trình: Bật Đèn Báo -> Bắt Ảnh Màu';
        }
    }
}

export async function testCameraDirectly(url, name) {
    const titleEl = document.getElementById('liveViewTitle');
    const subEl = document.getElementById('liveViewSubtitle');
    const imgEl = document.getElementById('liveViewImg');

    if (titleEl) titleEl.innerText = `Xem Thử Trực Tiếp: ${name}`;
    if (subEl) subEl.innerText = `Nguồn: ${url}`;
    if (imgEl) imgEl.src = '';
    document.getElementById('liveViewModal')?.classList.add('active');

    try {
        const data = await CameraAPI.testConnection(url);
        if (data.success && data.preview_url) {
            if (imgEl) imgEl.src = data.preview_url;
            if (subEl) subEl.innerText = `${data.message}`;
            showToast(`Đã lấy khung hình ${name}`, 'success');
        } else {
            alert(`Không thể kết nối camera: ${data.message}`);
            if (typeof closeLiveModal === 'function') closeLiveModal();
        }
    } catch (err) {
        alert('Lỗi kết nối kiểm tra camera: ' + (err.message || err));
        if (typeof closeLiveModal === 'function') closeLiveModal();
    }
}

export async function saveCamera() {
    const id = document.getElementById('formCamId')?.value;
    const code = document.getElementById('formCode')?.value.trim();
    const name = document.getElementById('formName')?.value.trim();
    const room_number = document.getElementById('formRoom')?.value.trim();
    const standard_count = parseInt(document.getElementById('formStandard')?.value) || 40;
    const rtsp_url = document.getElementById('formRtspUrl')?.value.trim();
    const relay_ip = document.getElementById('formRelayIp')?.value.trim();
    const is_active = document.getElementById('formActive')?.checked ?? true;

    if (!name || !rtsp_url) {
        alert('Vui lòng nhập đầy đủ Tên lớp và Đường dẫn camera!');
        return;
    }

    try {
        let result;
        if (id) {
            result = await CameraAPI.update(id, {
                name, room_number, standard_count, rtsp_url, relay_ip, is_active
            });
        } else {
            if (!code) {
                alert('Vui lòng nhập Mã lớp!');
                return;
            }
            result = await CameraAPI.create({
                code, name, room_number, standard_count, rtsp_url, relay_ip, is_active
            });
        }

        if (result.success) {
            closeModal();
            await loadCameras();
            showToast(result.message || 'Lưu thành công', 'success');
        } else {
            alert('Lỗi: ' + (result.detail || result.message || 'Không thể lưu camera.'));
        }
    } catch (err) {
        alert('Lỗi kết nối máy chủ: ' + (err.message || err));
    }
}

export async function deleteCamera(id, name) {
    const confirmed = await ConfirmationDialog.delete(name);
    if (!confirmed) return;

    try {
        const result = await CameraAPI.delete(id);
        await loadCameras();
        showToast(result.message || 'Đã xóa camera thành công', 'success');
    } catch (err) {
        showToast('Lỗi khi xóa camera: ' + (err.message || err), 'danger');
    }
}

export function openDeleteModal() {
    const modal = document.getElementById('deleteCameraModal');
    const selectQuick = document.getElementById('deleteModalSelectQuick');
    const checklist = document.getElementById('deleteModalChecklist');

    if (!modal) return;

    // Cập nhật danh sách chọn nhanh 1 camera
    if (selectQuick) {
        selectQuick.innerHTML = '<option value="">-- Bấm vào đây để chọn camera --</option>' +
            allCameras.map(c => `
                <option value="${c.id}">${c.name} (${c.room_number || 'Phòng ' + c.id}) - Mã: ${c.code}</option>
            `).join('');
    }

    // Cập nhật danh sách checklist chọn nhiều camera
    if (checklist) {
        if (!allCameras || allCameras.length === 0) {
            checklist.innerHTML = '<div style="text-align: center; color: #94a3b8; padding: 16px; font-size: 0.85rem;"><i class="fa-solid fa-circle-info"></i> Hiện không có camera nào trong danh sách</div>';
        } else {
            checklist.innerHTML = allCameras.map(c => `
                <label class="delete-cam-item">
                    <input type="checkbox" value="${c.id}" class="cam-del-cb" data-name="${encodeURIComponent(c.name)}">
                    <span style="flex: 1; font-weight: 500;">
                        <strong style="color: #0f172a;">${c.code}</strong> - ${c.name} 
                        <span style="color: #64748b; font-size: 0.8rem;">(${c.room_number || '--'})</span>
                    </span>
                    <span class="badge ${c.source_type === 'WEBCAM' ? 'badge-warning' : (c.source_type === 'FILE' ? 'badge-primary' : 'badge-success')}" style="font-size: 0.72rem;">
                        ${c.source_type || 'RTSP'}
                    </span>
                </label>
            `).join('');

            // Khi tích chọn từng checkbox, đồng bộ với dropdown chọn nhanh
            checklist.querySelectorAll('.cam-del-cb').forEach(cb => {
                cb.addEventListener('change', () => {
                    const checked = checklist.querySelectorAll('.cam-del-cb:checked');
                    if (checked.length === 1 && selectQuick) {
                        selectQuick.value = checked[0].value;
                    } else if (selectQuick) {
                        selectQuick.value = '';
                    }
                });
            });
        }
    }

    // Khi chọn từ dropdown, tự động tích checkbox tương ứng
    if (selectQuick) {
        selectQuick.onchange = () => {
            const val = selectQuick.value;
            if (checklist) {
                checklist.querySelectorAll('.cam-del-cb').forEach(cb => {
                    cb.checked = (String(cb.value) === String(val));
                });
            }
        };
    }

    modal.classList.add('active');
}

export function closeDeleteModal() {
    const modal = document.getElementById('deleteCameraModal');
    if (modal) modal.classList.remove('active');
}

export async function confirmBatchDelete() {
    const checklist = document.getElementById('deleteModalChecklist');
    const checkedBoxes = checklist ? Array.from(checklist.querySelectorAll('.cam-del-cb:checked')) : [];

    if (checkedBoxes.length === 0) {
        alert('Vui lòng chọn ít nhất 1 camera bạn muốn xóa.');
        return;
    }

    const count = checkedBoxes.length;
    const names = checkedBoxes.slice(0, 3).map(cb => decodeURIComponent(cb.dataset.name)).join(', ') + (count > 3 ? ` và ${count - 3} camera khác` : '');

    if (!confirm(`Bạn có chắc chắn muốn xóa ${count} camera (${names}) khỏi hệ thống? Dữ liệu vùng của các lớp này cũng sẽ bị xóa.`)) {
        return;
    }

    const btnConfirm = document.getElementById('btnConfirmDeleteBatch');
    if (btnConfirm) {
        btnConfirm.disabled = true;
        btnConfirm.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang xóa...';
    }

    let successCount = 0;
    let failCount = 0;

    for (const cb of checkedBoxes) {
        const id = parseInt(cb.value);
        try {
            const res = await CameraAPI.delete(id);
            if (res.success) successCount++;
            else failCount++;
        } catch (err) {
            console.error('Lỗi xóa camera ID', id, err);
            failCount++;
        }
    }

    if (btnConfirm) {
        btnConfirm.disabled = false;
        btnConfirm.innerHTML = '<i class="fa-solid fa-trash-can"></i> Xác Nhận Xóa';
    }

    closeDeleteModal();
    await loadCameras();

    if (failCount === 0) {
        showToast(`Đã xóa thành công ${successCount} camera đã chọn!`, 'info');
    } else {
        showToast(`Đã xóa ${successCount} camera, thất bại ${failCount} camera.`, 'warning');
    }
}

export async function resetDefaults() {
    if (!confirm('Khôi phục danh sách 30 lớp học chuẩn của trường THPT Điều Cải? Các camera test bạn vừa thêm có thể sẽ bị đặt lại.')) {
        return;
    }

    try {
        const result = await CameraAPI.resetDefaults();
        await loadCameras();
        showToast(result.message || 'Đã khôi phục mặc định', 'success');
    } catch (err) {
        alert('Lỗi kết nối máy chủ: ' + (err.message || err));
    }
}

// Attach preset buttons
document.querySelectorAll('button[data-preset]').forEach(btn => {
    btn.addEventListener('click', () => applyPreset(btn.dataset.preset));
});

const inputRtsp = document.getElementById('inputRtsp');
if (inputRtsp) inputRtsp.addEventListener('input', (e) => syncManualUrl(e.target.value));

const inputFile = document.getElementById('inputFile');
if (inputFile) inputFile.addEventListener('input', (e) => syncManualUrl(e.target.value));

// ==================== MATRIX TV WALL RENDERER ====================
export function renderMatrixWall() {
    const container = document.getElementById('matrixGrid');
    if (!container) return;
    container.innerHTML = '';

    if (!allCameras || allCameras.length === 0) {
        container.innerHTML = `
            <div class="camera-empty-state" style="grid-column: 1 / -1; text-align: center; padding: 3.5rem 1.5rem; color: var(--text-muted, #64748b);">
                <div style="width: 60px; height: 60px; border-radius: 50%; background: rgba(14, 165, 233, 0.08); color: var(--primary, #0284c7); display: inline-flex; align-items: center; justify-content: center; margin-bottom: 1rem;">
                    <i class="fa-solid fa-video-slash" style="font-size: 1.6rem;"></i>
                </div>
                <h3 style="font-size: 1.1rem; font-weight: 700; color: var(--text-primary, #0f172a); margin: 0 0 0.5rem 0;">Chưa có camera nào trong hệ thống</h3>
                <p style="font-size: 0.875rem; color: var(--text-muted, #64748b); max-width: 480px; margin: 0 auto 1.5rem auto; line-height: 1.5;">
                    Hệ thống chưa ghi nhận camera nào. Bạn có thể thêm camera từ máy tính/Webcam, camera IP RTSP của từng lớp học hoặc quét tự động từ đầu ghi NVR.
                </p>
                <div style="display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap;">
                    <button type="button" class="btn btn-primary btn-sm" id="btnEmptyAddCam">
                        <i class="fa-solid fa-plus"></i> Thêm Camera / Lớp
                    </button>
                    <button type="button" class="btn btn-success btn-sm" id="btnEmptyAddNvr">
                        <i class="fa-solid fa-server"></i> Thêm Đầu Ghi (NVR)
                    </button>
                </div>
            </div>`;
        const btnAdd = container.querySelector('#btnEmptyAddCam');
        if (btnAdd) btnAdd.onclick = () => document.getElementById('btnAddCamera')?.click();
        const btnNvr = container.querySelector('#btnEmptyAddNvr');
        if (btnNvr) btnNvr.onclick = () => document.getElementById('btnAddNVR')?.click();
        return;
    }

    const badge = document.getElementById('matrixOnlineBadge') || document.getElementById('matrixStatus');
    if (badge) {
        const activeCams = allCameras.filter(c => c.is_active).length;
        badge.innerText = `${activeCams}/${allCameras.length} Camera Sẵn Sàng`;
    }

    allCameras.forEach((cam, idx) => {
        const chNum = cam.channel_number || (idx + 1);
        const card = document.createElement('div');
        card.className = 'matrix-card';
        card.id = `matrix_card_${cam.id}`;

        const snapUrl = `/storage/captures/latest/Lop_${cam.id}.jpg?t=${Date.now()}`;
        const isOnline = cam.is_active;

        card.innerHTML = `
            <div class="matrix-card-screen">
                <img src="${snapUrl}" class="matrix-thumb-img" alt="${cam.name}" 
                     onerror="this.onerror=null; this.src='dataset/samples/classroom_sample.jpg';">
                <div class="matrix-osd-top">
                    <span class="matrix-ch-badge">CH${String(chNum).padStart(2, '0')}</span>
                    <span class="matrix-status-dot ${isOnline ? '' : 'offline'}" title="${isOnline ? 'Đang kích hoạt' : 'Tạm dừng'}"></span>
                </div>
                <div class="matrix-hover-actions">
                    <button type="button" class="matrix-action-btn view" title="Xem ảnh phóng to" data-id="${cam.id}" data-name="${encodeURIComponent(cam.name)}">
                        <i class="fa-solid fa-expand"></i>
                    </button>
                    <button type="button" class="matrix-action-btn edit" title="Sửa thông tin camera này" data-id="${cam.id}">
                        <i class="fa-solid fa-pen"></i>
                    </button>
                    <button type="button" class="matrix-action-btn roi" title="Vẽ vùng nhận diện" data-id="${cam.id}">
                        <i class="fa-solid fa-draw-polygon"></i>
                    </button>
                    <button type="button" class="matrix-action-btn delete" title="Xóa riêng camera này" data-id="${cam.id}" data-name="${encodeURIComponent(cam.name)}">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </div>
            <div class="matrix-card-footer">
                <div class="matrix-footer-meta">
                    <div class="matrix-class-title" title="${cam.name}">${cam.name}</div>
                    <div class="matrix-class-room">${cam.room_number || `Phòng ${100 + chNum}`}</div>
                </div>
                <span class="matrix-std-pill">${cam.standard_count} HS</span>
            </div>
        `;
        container.appendChild(card);
    });

    // Attach quick actions inside Matrix cards
    container.querySelectorAll('.matrix-action-btn.view').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const id = btn.getAttribute('data-id');
            const name = decodeURIComponent(btn.getAttribute('data-name'));
            openLiveModal(id, name);
        });
    });

    container.querySelectorAll('.matrix-action-btn.edit').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const id = parseInt(btn.getAttribute('data-id'));
            editCamera(id);
        });
    });

    container.querySelectorAll('.matrix-action-btn.roi').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const id = btn.getAttribute('data-id');
            window.location.href = `roi-config.html?class_id=${id}&refresh=true`;
        });
    });

    container.querySelectorAll('.matrix-action-btn.delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const id = parseInt(btn.getAttribute('data-id'));
            const name = decodeURIComponent(btn.getAttribute('data-name'));
            deleteCamera(id, name);
        });
    });

    // Click on any card to open modal (except action buttons)
    container.querySelectorAll('.matrix-card').forEach(card => {
        card.addEventListener('click', (e) => {
            // Don't open if clicking on action buttons
            if (!e.target.closest('.matrix-action-btn')) {
                const viewBtn = card.querySelector('.matrix-action-btn.view');
                if (viewBtn) {
                    const id = viewBtn.getAttribute('data-id');
                    const name = decodeURIComponent(viewBtn.getAttribute('data-name'));
                    openLiveModal(id, name);
                }
            }
        });
    });
}

export function openLiveModal(id, name) {
    const cam = allCameras.find(c => c.id === parseInt(id));
    const titleEl = document.getElementById('liveViewTitle');
    const subEl = document.getElementById('liveViewSubtitle');
    const imgEl = document.getElementById('liveViewImg');

    if (titleEl) titleEl.innerText = `Camera: ${name}`;
    if (subEl) {
        const info = cam ? `${cam.room_number || 'Phòng N/A'} • Sĩ số: ${cam.standard_count} • ${cam.is_active ? 'Online' : 'Offline'}` : `ID: ${id}`;
        subEl.innerText = info;
    }

    if (imgEl) {
        imgEl.src = `/storage/captures/latest/Lop_${id}.jpg?t=${Date.now()}`;
        imgEl.onerror = () => {
            imgEl.onerror = null;
            imgEl.src = 'dataset/samples/classroom_sample.jpg';
        };
        imgEl.style.transform = 'scale(1)';
        imgEl.classList.remove('zoomed');

        // Store current camera ID for refresh
        imgEl.dataset.cameraId = id;
        imgEl.dataset.cameraName = name;
    }

    document.getElementById('liveViewModal')?.classList.add('active');

    // Update resolution info when image loads
    if (imgEl) {
        imgEl.onload = function () {
            const resEl = document.getElementById('imageResolution');
            if (resEl) {
                resEl.innerText = `${this.naturalWidth} × ${this.naturalHeight}`;
            }
        };
    }
}

export function closeLiveModal() {
    const modal = document.getElementById('liveViewModal');
    if (modal) modal.classList.remove('active');

    // Reset zoom
    const imgEl = document.getElementById('liveViewImg');
    if (imgEl) {
        imgEl.style.transform = 'scale(1)';
        imgEl.classList.remove('zoomed');
    }
}

// Image zoom controls
let currentZoom = 1;

function initImageControls() {
    const btnClose = document.getElementById('liveViewCloseBtn');
    if (btnClose) btnClose.addEventListener('click', closeLiveModal);

    const btnZoomIn = document.getElementById('btnZoomIn');
    if (btnZoomIn) {
        btnZoomIn.addEventListener('click', () => {
            currentZoom = Math.min(currentZoom + 0.25, 3);
            applyZoom();
        });
    }

    const btnZoomOut = document.getElementById('btnZoomOut');
    if (btnZoomOut) {
        btnZoomOut.addEventListener('click', () => {
            currentZoom = Math.max(currentZoom - 0.25, 0.5);
            applyZoom();
        });
    }

    const btnZoomReset = document.getElementById('btnZoomReset');
    if (btnZoomReset) {
        btnZoomReset.addEventListener('click', () => {
            currentZoom = 1;
            applyZoom();
        });
    }

    const btnRefresh = document.getElementById('btnRefreshImage');
    if (btnRefresh) {
        btnRefresh.addEventListener('click', () => {
            const imgEl = document.getElementById('liveViewImg');
            if (imgEl && imgEl.dataset.cameraId) {
                const id = imgEl.dataset.cameraId;
                imgEl.src = `/storage/captures/latest/Lop_${id}.jpg?t=${Date.now()}`;
                showToast('Đã làm mới ảnh', 'success');
            }
        });
    }

    // Click on image to toggle zoom
    const imgEl = document.getElementById('liveViewImg');
    if (imgEl) {
        imgEl.addEventListener('click', () => {
            if (currentZoom === 1) {
                currentZoom = 2;
            } else {
                currentZoom = 1;
            }
            applyZoom();
        });
    }

    // ESC key to close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const modal = document.getElementById('liveViewModal');
            if (modal && modal.classList.contains('active')) {
                closeLiveModal();
            }
        }
    });

    // Click backdrop to close
    const modal = document.getElementById('liveViewModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target.id === 'liveViewModal') {
                closeLiveModal();
            }
        });
    }
}

function applyZoom() {
    const imgEl = document.getElementById('liveViewImg');
    if (imgEl) {
        imgEl.style.transform = `scale(${currentZoom})`;
        if (currentZoom > 1) {
            imgEl.classList.add('zoomed');
        } else {
            imgEl.classList.remove('zoomed');
        }
    }
}

// Export for window scope
if (typeof window !== 'undefined') {
    window.openLiveModal = openLiveModal;
    window.closeLiveModal = closeLiveModal;
}

// ==================== SMART NVR IMPORT WIZARD ====================
export function openNvrModal() {
    const modal = document.getElementById('nvrModal');
    if (!modal) {
        console.error('Không tìm thấy element #nvrModal');
        return;
    }
    const probeResults = document.getElementById('nvrProbeResults');
    if (probeResults) probeResults.style.display = 'none';
    const probeLoading = document.getElementById('nvrProbeLoading');
    if (probeLoading) probeLoading.style.display = 'none';
    const btnSave = document.getElementById('btnSaveNvrImport');
    if (btnSave) btnSave.disabled = true;
    modal.classList.add('active');
}

export function closeNvrModal() {
    const modal = document.getElementById('nvrModal');
    if (modal) modal.classList.remove('active');
}

export function fillSchoolPreset() {
    document.getElementById('nvrIp').value = '192.168.10.200';
    document.getElementById('nvrPort').value = '554';
    document.getElementById('nvrUsername').value = 'admin';
    document.getElementById('nvrPassword').value = 'Lhu@2025';
    document.getElementById('nvrBrand').value = 'DAHUA';
    document.getElementById('nvrChannelsCount').value = '30';
    document.getElementById('nvrNamingMode').value = 'DEFAULT_30_CLASSES';
    const patternBox = document.getElementById('nvrCustomPatternBox');
    if (patternBox) patternBox.style.display = 'none';
    showToast('Đã điền cấu hình mẫu THPT Điều Cải!', 'info');
}

export async function probeNVRChannels() {
    const ip_address = document.getElementById('nvrIp')?.value.trim();
    const rtsp_port = parseInt(document.getElementById('nvrPort')?.value) || 554;
    const username = document.getElementById('nvrUsername')?.value.trim() || 'admin';
    const password = document.getElementById('nvrPassword')?.value.trim() || '';
    const brand = document.getElementById('nvrBrand')?.value || 'DAHUA';
    const channels_count = parseInt(document.getElementById('nvrChannelsCount')?.value) || 30;
    const naming_mode = document.getElementById('nvrNamingMode')?.value || 'DEFAULT_30_CLASSES';
    const custom_pattern = document.getElementById('nvrCustomPattern')?.value.trim() || '';

    if (!ip_address) {
        alert('Vui lòng nhập địa chỉ IP đầu ghi NVR!');
        return;
    }

    const loadingEl = document.getElementById('nvrProbeLoading');
    const resultsEl = document.getElementById('nvrProbeResults');
    const btnProbe = document.getElementById('btnProbeNVR');
    const btnSave = document.getElementById('btnSaveNvrImport');

    if (loadingEl) loadingEl.style.display = 'block';
    if (resultsEl) resultsEl.style.display = 'none';
    if (btnProbe) {
        btnProbe.disabled = true;
        btnProbe.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang quét...';
    }

    try {
        const payload = {
            ip_address,
            rtsp_port,
            username,
            password,
            brand,
            channels_count,
            naming_mode,
            custom_pattern
        };

        const res = await CameraAPI.probeNVR(payload);
        if (!res.success) {
            throw new Error(res.message || 'Quét NVR không thành công');
        }

        probedChannels = res.channels || [];
        renderNvrPreviewCards(probedChannels);

        const summaryEl = document.getElementById('nvrProbeSummary');
        if (summaryEl) {
            summaryEl.innerText = `${res.online_channels}/${res.total_channels} Kênh Online (${res.elapsed_seconds}s)`;
        }

        if (resultsEl) resultsEl.style.display = 'block';
        if (btnSave) btnSave.disabled = false;
        showToast(`Quét thành công ${probedChannels.length} kênh camera!`, 'success');
    } catch (err) {
        console.error('Lỗi khi thăm dò đầu ghi:', err);
        alert('Lỗi quét đầu ghi NVR: ' + (err.message || err));
    } finally {
        if (loadingEl) loadingEl.style.display = 'none';
        if (btnProbe) {
            btnProbe.disabled = false;
            btnProbe.innerHTML = '<i class="fa-solid fa-satellite-dish"></i> Quét Kênh Camera & Xem Trước Thumbnail';
        }
    }
}

function renderNvrPreviewCards(channels) {
    const container = document.getElementById('nvrChannelList');
    if (!container) return;
    container.innerHTML = '';

    channels.forEach((ch, idx) => {
        const card = document.createElement('div');
        card.className = `nvr-ch-card ${ch.is_selected ? 'selected' : ''}`;
        card.id = `nvr_preview_card_${ch.channel}`;

        const thumbHtml = ch.thumbnail
            ? `<img src="${ch.thumbnail}" alt="CH${ch.channel}">`
            : `<div style="text-align: center; color: #64748b; line-height: 65px;"><i class="fa-solid fa-video"></i></div>`;

        card.innerHTML = `
            <div style="display: flex; align-items: center;">
                <input type="checkbox" class="nvr-ch-select" data-ch="${ch.channel}" ${ch.is_selected ? 'checked' : ''} style="width: 17px; height: 17px; cursor: pointer;">
            </div>
            <div class="nvr-ch-thumb">
                ${thumbHtml}
                <span class="nvr-ch-badge">CH${String(ch.channel).padStart(2, '0')}</span>
            </div>
            <div class="nvr-ch-fields">
                <input type="text" class="nvr-ch-name" data-ch="${ch.channel}" value="${ch.name}" placeholder="Tên lớp (VD: Lớp 10A1)" title="Tên lớp học">
                <div style="display: flex; gap: 6px;">
                    <input type="text" class="nvr-ch-room" data-ch="${ch.channel}" value="${ch.room_number || ''}" placeholder="Phòng" style="width: 55%;" title="Số phòng học">
                    <input type="number" class="nvr-ch-std" data-ch="${ch.channel}" value="${ch.standard_count || 40}" min="1" max="60" style="width: 45%; font-weight: 700;" title="Sĩ số chuẩn">
                </div>
            </div>
        `;
        container.appendChild(card);
    });

    // Checkbox toggle sync card border
    container.querySelectorAll('.nvr-ch-select').forEach(cb => {
        cb.addEventListener('change', () => {
            const ch = cb.getAttribute('data-ch');
            const card = document.getElementById(`nvr_preview_card_${ch}`);
            if (card) {
                if (cb.checked) card.classList.add('selected');
                else card.classList.remove('selected');
            }
        });
    });
}

export function toggleAllNvrChannels(isSelected) {
    const container = document.getElementById('nvrChannelList');
    if (!container) return;
    container.querySelectorAll('.nvr-ch-select').forEach(cb => {
        cb.checked = isSelected;
        const ch = cb.getAttribute('data-ch');
        const card = document.getElementById(`nvr_preview_card_${ch}`);
        if (card) {
            if (isSelected) card.classList.add('selected');
            else card.classList.remove('selected');
        }
    });
}

export async function saveNvrImport() {
    const container = document.getElementById('nvrChannelList');
    if (!container || probedChannels.length === 0) return;

    const selectedChannels = [];
    probedChannels.forEach(ch => {
        const chNum = ch.channel;
        const cb = container.querySelector(`.nvr-ch-select[data-ch="${chNum}"]`);
        if (cb && cb.checked) {
            const nameInput = container.querySelector(`.nvr-ch-name[data-ch="${chNum}"]`);
            const roomInput = container.querySelector(`.nvr-ch-room[data-ch="${chNum}"]`);
            const stdInput = container.querySelector(`.nvr-ch-std[data-ch="${chNum}"]`);

            selectedChannels.push({
                channel: ch.channel,
                code: ch.code,
                name: nameInput ? nameInput.value.trim() : ch.name,
                room_number: roomInput ? roomInput.value.trim() : ch.room_number,
                standard_count: stdInput ? parseInt(stdInput.value) || 40 : ch.standard_count,
                rtsp_url: ch.rtsp_url,
                thumbnail: ch.thumbnail || '',
                is_selected: true
            });
        }
    });

    if (selectedChannels.length === 0) {
        alert('Vui lòng tích chọn ít nhất 1 kênh camera để lưu!');
        return;
    }

    const replace_existing = document.getElementById('nvrReplaceExisting')?.checked ?? true;
    const ip_address = document.getElementById('nvrIp')?.value.trim();
    const rtsp_port = parseInt(document.getElementById('nvrPort')?.value) || 554;
    const username = document.getElementById('nvrUsername')?.value.trim() || 'admin';
    const password = document.getElementById('nvrPassword')?.value.trim() || '';
    const brand = document.getElementById('nvrBrand')?.value || 'DAHUA';

    const btnSave = document.getElementById('btnSaveNvrImport');
    if (btnSave) {
        btnSave.disabled = true;
        btnSave.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu & khởi tạo vùng 30 camera...';
    }

    try {
        const importPayload = {
            nvr_name: `Đầu Ghi NVR Trường THPT Điều Cải (${ip_address})`,
            ip_address,
            rtsp_port,
            username,
            password,
            brand,
            channels_count: probedChannels.length,
            replace_existing,
            channels: selectedChannels
        };

        const res = await CameraAPI.batchImportNVR(importPayload);
        if (res.success) {
            closeNvrModal();
            showToast(res.message || `Đã nhập thành công ${res.imported_count} camera!`, 'success');
            await loadCameras();
        } else {
            alert('Lỗi khi lưu camera: ' + (res.message || res.detail));
        }
    } catch (err) {
        console.error('Lỗi lưu đồng bộ NVR:', err);
        alert('Lỗi kết nối lưu NVR: ' + (err.message || err));
    } finally {
        if (btnSave) {
            btnSave.disabled = false;
            btnSave.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> Lưu & Đồng Bộ 30 Camera Vào Hệ Thống';
        }
    }
}

// Expose to window for inline attributes if needed
window.selectWebcam = selectWebcam;
window.applyPreset = applyPreset;
window.switchSourceTab = switchSourceTab;
window.openDeleteModal = openDeleteModal;
window.closeDeleteModal = closeDeleteModal;
window.openNvrModal = openNvrModal;
window.closeNvrModal = closeNvrModal;
window.fillSchoolPreset = fillSchoolPreset;
window.probeNVRChannels = probeNVRChannels;
window.toggleAllNvrChannels = toggleAllNvrChannels;
window.saveNvrImport = saveNvrImport;
window.renderMatrixWall = renderMatrixWall;


