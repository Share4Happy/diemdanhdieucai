/**
 * cameras.js - Camera Management Page Controller
 * THPT Điều Cải - Attendance System
 */
import { CameraAPI, showToast, API_BASE } from './api.js?v=2.1';

let allCameras = [];
let availableWebcams = [];
let selectedWebcamId = '0';
let currentSourceType = 'WEBCAM';

document.addEventListener('DOMContentLoaded', () => {
    loadCameras();
    loadAvailableWebcams();

    // Event listeners
    const btnRefresh = document.getElementById('btnRefreshList');
    if (btnRefresh) btnRefresh.addEventListener('click', loadCameras);

    const filterInput = document.getElementById('filterCameraInput');
    if (filterInput) filterInput.addEventListener('input', renderTable);

    const filterSource = document.getElementById('filterSourceSelect');
    if (filterSource) filterSource.addEventListener('change', renderTable);

    const btnAdd = document.getElementById('btnOpenAddModal');
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
});

// Load available webcams
export async function loadAvailableWebcams(forceRefresh = false) {
    const icon = document.getElementById('webcamRefreshIcon');
    const btn = document.getElementById('btnRefreshWebcams');
    if (icon) icon.classList.add('fa-spin');
    if (btn) btn.disabled = true;

    const container = document.getElementById('webcamListContainer');
    if (container && forceRefresh) {
        container.innerHTML = `<div class="webcam-empty-box"><i class="fa-solid fa-spinner fa-spin"></i> Đang quét lại các cổng camera trên máy...</div>`;
    }

    try {
        let data = null;
        const apiObj = window.CameraAPI || CameraAPI;
        if (apiObj && typeof apiObj.getWebcams === 'function') {
            data = await apiObj.getWebcams(forceRefresh);
        } else if (apiObj && typeof apiObj.getAvailableWebcams === 'function') {
            data = await apiObj.getAvailableWebcams(forceRefresh);
        } else {
            const base = (typeof window !== 'undefined' && window.API_BASE !== undefined) ? window.API_BASE : (API_BASE || '');
            const res = await fetch(`${base}/api/cameras/available-webcams?refresh=${forceRefresh}`);
            data = await res.json();
        }

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
            renderTable();
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
    try {
        const data = await CameraAPI.getAll();
        allCameras = data.cameras || [];
        renderKPIs();
        renderTable();
    } catch (err) {
        console.error('Lỗi tải danh sách camera:', err);
        showToast('Không thể tải danh sách camera', 'error');
    }
}

function renderKPIs() {
    const totalEl = document.getElementById('statTotalCameras');
    if (totalEl) totalEl.innerText = allCameras.length;

    const activeCount = allCameras.filter(c => c.is_active).length;
    const activeEl = document.getElementById('statActiveCameras');
    if (activeEl) activeEl.innerText = activeCount;

    const roiCount = allCameras.filter(c => c.has_roi).length;
    const roiEl = document.getElementById('statRoiConfigured');
    if (roiEl) roiEl.innerText = roiCount;

    const totalStd = allCameras.reduce((sum, c) => sum + (c.standard_count || 0), 0);
    const stdEl = document.getElementById('statTotalStudents');
    if (stdEl) stdEl.innerText = totalStd;
}

function renderTable() {
    const filterInput = document.getElementById('filterCameraInput');
    const filterText = filterInput ? filterInput.value.toLowerCase().trim() : '';
    const filterSource = document.getElementById('filterSourceSelect')?.value || 'ALL';

    const tbody = document.getElementById('cameraTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const filtered = allCameras.filter(c => {
        const matchText = (c.name || '').toLowerCase().includes(filterText) ||
                          (c.code || '').toLowerCase().includes(filterText) ||
                          (c.room_number || '').toLowerCase().includes(filterText) ||
                          (c.rtsp_url || '').toLowerCase().includes(filterText);
        const matchSource = filterSource === 'ALL' || c.source_type === filterSource;
        return matchText && matchSource;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 2rem; color: var(--text-muted);">Không tìm thấy camera nào phù hợp.</td></tr>`;
        return;
    }

    filtered.forEach((c, idx) => {
        const tr = document.createElement('tr');

        let sourceBadge = `<span class="badge-source badge-unknown">${c.source_type}</span>`;
        let displayUrl = (c.rtsp_url && c.rtsp_url.length > 35) ? c.rtsp_url.substring(0, 32) + '...' : c.rtsp_url;

        if (c.source_type === 'WEBCAM') {
            sourceBadge = `<span class="badge-source badge-webcam"><i class="fa-solid fa-camera"></i> WEBCAM ${c.rtsp_url}</span>`;
            const matchedWebcam = availableWebcams.find(w => String(w.id) === String(c.rtsp_url));
            const camName = matchedWebcam ? (matchedWebcam.short_name || matchedWebcam.name) : `Webcam Thiết Bị ${c.rtsp_url}`;
            displayUrl = `📷 Webcam ${c.rtsp_url}: ${camName}`;
        } else if (c.source_type === 'FILE') {
            sourceBadge = `<span class="badge-source badge-file"><i class="fa-solid fa-film"></i> FILE</span>`;
        } else if (c.source_type === 'RTSP') {
            sourceBadge = `<span class="badge-source badge-rtsp"><i class="fa-solid fa-server"></i> RTSP</span>`;
        } else if (c.source_type === 'HTTP') {
            sourceBadge = `<span class="badge-source badge-http"><i class="fa-solid fa-globe"></i> HTTP</span>`;
        }

        const statusBadge = c.is_active
            ? `<span style="color: #10b981; font-weight: 700;"><i class="fa-solid fa-circle" style="font-size: 0.6rem;"></i> Hoạt động</span>`
            : `<span style="color: #94a3b8; font-weight: 600;"><i class="fa-regular fa-circle" style="font-size: 0.6rem;"></i> Tạm dừng</span>`;

        const roiBadge = c.has_roi
            ? `<span style="color: #2563eb; font-weight: 600;"><i class="fa-solid fa-check-double"></i> Đã cấu hình</span>`
            : `<span style="color: #f59e0b; font-weight: 600;"><i class="fa-solid fa-triangle-exclamation"></i> Mặc định</span>`;

        tr.innerHTML = `
            <td>${idx + 1}</td>
            <td><strong>${c.code}</strong></td>
            <td style="font-weight: 600;">${c.name}</td>
            <td>${c.room_number || '--'}</td>
            <td>${sourceBadge}</td>
            <td title="${c.rtsp_url || ''}"><code style="font-size: 0.8rem; background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">${displayUrl}</code></td>
            <td><strong>${c.standard_count}</strong> em</td>
            <td>${statusBadge}</td>
            <td>${roiBadge}</td>
            <td>
                <div class="action-btns">
                    <button class="btn btn-secondary btn-sm" title="Xem thử kết nối" data-action="test" data-url="${encodeURIComponent(c.rtsp_url)}" data-name="${encodeURIComponent(c.name)}">
                        <i class="fa-solid fa-eye"></i> Test
                    </button>
                    <a href="roi-config.html?class_id=${c.id}&refresh=true" class="btn btn-secondary btn-sm" title="Vẽ vùng ROI">
                        <i class="fa-solid fa-draw-polygon"></i> ROI
                    </a>
                    <button class="btn btn-secondary btn-sm" title="Chỉnh sửa" data-action="edit" data-id="${c.id}">
                        <i class="fa-solid fa-pen"></i>
                    </button>
                    <button class="btn btn-danger btn-sm" title="Xóa" data-action="delete" data-id="${c.id}" data-name="${encodeURIComponent(c.name)}">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </td>
        `;

        tbody.appendChild(tr);
    });

    // Attach row button events
    tbody.querySelectorAll('button[data-action="test"]').forEach(btn => {
        btn.addEventListener('click', () => {
            const url = decodeURIComponent(btn.dataset.url);
            const name = decodeURIComponent(btn.dataset.name);
            testCameraDirectly(url, name);
        });
    });

    tbody.querySelectorAll('button[data-action="edit"]').forEach(btn => {
        btn.addEventListener('click', () => {
            editCamera(parseInt(btn.dataset.id));
        });
    });

    tbody.querySelectorAll('button[data-action="delete"]').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = parseInt(btn.dataset.id);
            const name = decodeURIComponent(btn.dataset.name);
            deleteCamera(id, name);
        });
    });
}

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
            btn.innerHTML = '<i class="fa-solid fa-play"></i> Kiểm Tra Kết Nối Ngay';
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
            closeLiveModal();
        }
    } catch (err) {
        alert('Lỗi kết nối kiểm tra camera: ' + (err.message || err));
        closeLiveModal();
    }
}

export function closeLiveModal() {
    document.getElementById('liveViewModal')?.classList.remove('active');
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
    if (!confirm(`Bạn có chắc chắn muốn xóa Camera/Lớp "${name}" khỏi hệ thống? Dữ liệu ROI của camera này cũng sẽ bị xóa.`)) {
        return;
    }

    try {
        const result = await CameraAPI.delete(id);
        await loadCameras();
        showToast(result.message || 'Đã xóa camera', 'info');
    } catch (err) {
        alert('Lỗi kết nối máy chủ: ' + (err.message || err));
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

    if (!confirm(`Bạn có chắc chắn muốn xóa ${count} camera (${names}) khỏi hệ thống? Dữ liệu ROI của các lớp này cũng sẽ bị xóa.`)) {
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

// Expose to window for inline attributes if needed
window.selectWebcam = selectWebcam;
window.applyPreset = applyPreset;
window.switchSourceTab = switchSourceTab;
window.closeLiveModal = closeLiveModal;
window.openDeleteModal = openDeleteModal;
window.closeDeleteModal = closeDeleteModal;
