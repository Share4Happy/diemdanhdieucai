/**
 * ===================================================================
 * CAMERA CRUD MODULE - THPT ĐIỀU CẢI AI CAMERA
 * Quản lý Thêm/Sửa/Xóa Camera, Dò Webcam USB, Kiểm Tra Nguồn Stream & Wizard
 * ===================================================================
 */

import { CameraAPI, showToast, escapeHtml } from '../../api.js';

const esc = (v) => escapeHtml(v);

let availableWebcams = [];
let selectedWebcamId = '0';
let currentSourceType = 'WEBCAM';
let crudCameras = [];

let externalCallbacks = {
    onRefreshCameras: null
};

export function setCrudCallbacks(callbacks) {
    externalCallbacks = { ...externalCallbacks, ...callbacks };
}

export function setCrudCameras(cams) {
    crudCameras = cams || [];
}

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
                    <span style="font-size: 0.85rem; color: #64748b;">${esc(err.message || err)}</span>
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

export function updateBannerWebcamStatus() {
    const badge = document.getElementById('webcamBannerText');
    if (!badge) return;
    if (availableWebcams.length > 0) {
        badge.innerHTML = `Webcam máy: <strong>${availableWebcams.length} camera</strong> sẵn sàng`;
    } else {
        badge.innerText = 'Chưa phát hiện Webcam máy';
    }
}

export function renderWebcamCards() {
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
            ? `<img src="${cam.thumbnail}" class="webcam-thumb-img" alt="${esc(cam.name)}">`
            : `<div style="text-align: center; color: #64748b;"><i class="fa-solid fa-camera" style="font-size: 1.8rem;"></i></div>`;

        card.innerHTML = `
            <div class="webcam-thumb-box">
                ${thumbHtml}
                <span class="webcam-badge-id">Cổng ${cam.id}</span>
                <span class="webcam-badge-res">${esc(cam.resolution)}</span>
                <div class="webcam-selected-check"><i class="fa-solid fa-check"></i></div>
            </div>
            <div class="webcam-card-info">
                <div class="webcam-card-title" title="${esc(cam.name)}">${esc(cam.short_name || cam.name)}</div>
                <div class="webcam-card-sub"><i class="fa-solid fa-circle-check"></i> ${esc(cam.quality_label || 'Hoạt động')}</div>
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
            testMsg.innerHTML = `<span style="color: #10b981; font-weight: 700;"><i class="fa-solid fa-circle-check"></i> Đã chọn ${esc(cam.name)} (${esc(cam.resolution)})</span>`;
        }

        const nameInput = document.getElementById('formName');
        const codeInput = document.getElementById('formCode');
        const isEdit = !!document.getElementById('formCamId')?.value;
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

export function switchSourceTab(type = 'RTSP') {
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
    if (type === 'RTSP') {
        const val = (document.getElementById('inputRtsp')?.value || '').trim();
        if (rtspInput) rtspInput.value = val;
    } else if (type === 'WEBCAM') {
        if (rtspInput) rtspInput.value = selectedWebcamId || '0';
        renderWebcamCards();
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
}

export function openModal(camera = null) {
    const formCamId = document.getElementById('formCamId');
    if (formCamId) formCamId.value = camera ? camera.id : '';

    const modalTitle = document.getElementById('modalTitle');
    if (modalTitle) modalTitle.innerText = camera ? `Chỉnh Sửa Camera: ${camera.name}` : 'Thêm Camera Mới';

    const codeInput = document.getElementById('formCode');
    if (codeInput) {
        codeInput.value = camera ? camera.code : '';
        codeInput.disabled = !!camera;
    }

    const formName = document.getElementById('formName');
    if (formName) formName.value = camera ? camera.name : '';

    const formRoom = document.getElementById('formRoom');
    if (formRoom) formRoom.value = camera ? camera.room_number : '';

    const formStd = document.getElementById('formStandard');
    if (formStd) formStd.value = camera ? camera.standard_count : 40;

    const formRelay = document.getElementById('formRelayIp');
    if (formRelay) formRelay.value = camera ? (camera.relay_ip || '') : '';

    const formActive = document.getElementById('formActive');
    if (formActive) formActive.checked = camera ? camera.is_active : true;

    const previewImg = document.getElementById('testPreviewImg');
    if (previewImg) {
        previewImg.style.display = 'none';
        previewImg.src = '';
    }
    const statusMsg = document.getElementById('testStatusMsg');
    if (statusMsg) statusMsg.innerHTML = 'Bấm nút để thử kết nối và chụp 1 ảnh xem trước từ nguồn camera trên.';

    const url = camera ? (camera.rtsp_url || '').trim() : '';

    switchSourceTab('RTSP');
    const rInput = document.getElementById('inputRtsp');
    if (rInput) rInput.value = url;
    syncManualUrl(url);

    document.getElementById('cameraModal')?.classList.add('active');
}

export function closeModal() {
    document.getElementById('cameraModal')?.classList.remove('active');
}

export async function editCamera(id) {
    const cam = crudCameras.find(c => c.id === id);
    if (cam) {
        try {
            const raw = await CameraAPI.getRawRtsp(id);
            if (raw && raw.success && typeof raw.rtsp_url === 'string' && raw.rtsp_url !== '') {
                openModal({ ...cam, rtsp_url: raw.rtsp_url });
                return;
            }
        } catch (e) {
            // Dùng URL đã che nếu không lấy được URL raw
        }
        openModal(cam);
    }
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
            if (msg) msg.innerHTML = `<span style="color: #10b981; font-weight: 700;"><i class="fa-solid fa-circle-check"></i> ${esc(data.message)}</span>`;
            if (data.preview_url && img) {
                img.src = data.preview_url;
                img.style.display = 'inline-block';
            }
            showToast('Kết nối thành công', 'success');
        } else {
            if (msg) msg.innerHTML = `<span style="color: #ef4444; font-weight: 600;"><i class="fa-solid fa-circle-xmark"></i> ${esc(data.message)}</span>`;
            showToast(data.message || 'Kết nối thất bại', 'error');
        }
    } catch (err) {
        if (msg) msg.innerHTML = `<span style="color: #ef4444;">Lỗi khi gửi yêu cầu kiểm tra: ${esc(err.message || err)}</span>`;
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
    const relayIp = document.getElementById('formRelayIp')?.value?.trim() || '';
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
                msg.innerHTML = `<span style="color: #10b981; font-weight: 700;"><i class="fa-solid fa-circle-check"></i> ${esc(res.message || 'Đèn hồng ngoại đã kích hoạt thành công (tự động tắt sau 4s)!')}</span>`;
            }
            showToast(res.message || 'Đã kích hoạt đèn hồng ngoại camera!', 'success');
        } else {
            const errMsg = (res && res.message) ? res.message : 'Không thể gửi lệnh điều khiển tới camera!';
            if (msg) {
                msg.innerHTML = `<span style="color: #ef4444; font-weight: 700;"><i class="fa-solid fa-triangle-exclamation"></i> ${esc(errMsg)}</span>`;
            }
            showToast(errMsg, 'warning');
        }
    } catch (err) {
        if (msg) msg.innerHTML = `<span style="color: #ef4444;"><i class="fa-solid fa-triangle-exclamation"></i> Lỗi: ${esc(err.message || err)}</span>`;
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
    const relayIp = document.getElementById('formRelayIp')?.value?.trim() || '';
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
            if (msg) msg.innerHTML = `<span style="color: #ef4444; font-weight: 600;"><i class="fa-solid fa-circle-xmark"></i> ${esc(data.message)}</span>`;
            showToast(data.message || 'Thử chu trình thất bại', 'error');
        }
    } catch (err) {
        if (msg) msg.innerHTML = `<span style="color: #ef4444;">Lỗi: ${esc(err.message || err)}</span>`;
        showToast('Lỗi thử chu trình: ' + (err.message || err), 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Bật Đèn Báo -> Bắt Ảnh';
        }
    }
}

export async function runCameraValidationWizard() {
    const url = document.getElementById('formRtspUrl')?.value.trim();
    const relayIp = document.getElementById('formRelayIp')?.value?.trim() || '';
    const stdCount = parseInt(document.getElementById('formStandard')?.value) || 40;
    const btn = document.getElementById('btnWizardValidateCamera');
    const resBox = document.getElementById('wizardResultBox');
    const img = document.getElementById('testPreviewImg');

    if (!url) {
        showToast('Vui lòng chọn hoặc nhập nguồn Camera trước khi chạy Wizard kiểm định!', 'warning');
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang chạy Wizard 5 bước...';
    }
    if (resBox) {
        resBox.style.display = 'block';
        resBox.innerHTML = `
            <div style="font-size: 0.88rem; font-weight: 700; color: #4338ca; margin-bottom: 8px;">
                <i class="fa-solid fa-microchip"></i> Đang thực hiện quy trình kiểm định 5 bước...
            </div>
            <ul style="list-style: none; padding: 0; margin: 0; font-size: 0.82rem; line-height: 1.8;">
                <li><i class="fa-solid fa-spinner fa-spin" style="color: #6366f1;"></i> Bước 1: Kiểm tra kết nối mạng & bắt tay thiết bị...</li>
                <li style="color: #94a3b8;"><i class="fa-regular fa-clock"></i> Bước 2: Thu nhận 5 frame liên tiếp & kiểm tra độ ổn định</li>
                <li style="color: #94a3b8;"><i class="fa-regular fa-clock"></i> Bước 3: Thẩm định độ phân giải & phân tích kích thước đầu học sinh</li>
                <li style="color: #94a3b8;"><i class="fa-regular fa-clock"></i> Bước 4: Kiểm tra và định vị vùng đa giác ROI</li>
                <li style="color: #94a3b8;"><i class="fa-regular fa-clock"></i> Bước 5: Chạy thử nghiệm AI YOLO nhận diện sĩ số</li>
            </ul>
        `;
    }

    try {
        const data = await CameraAPI.validateNewCamera(url, relayIp, null, null, stdCount);
        if (data.success) {
            const s1 = data.step1_connection;
            const s2 = data.step2_frames;
            const s3 = data.step3_resolution;
            const s4 = data.step4_roi;
            const s5 = data.step5_ai;

            const s1Icon = s1.ok ? '<i class="fa-solid fa-circle-check" style="color: #10b981;"></i>' : '<i class="fa-solid fa-circle-xmark" style="color: #ef4444;"></i>';
            const s2Icon = s2.ok ? '<i class="fa-solid fa-circle-check" style="color: #10b981;"></i>' : '<i class="fa-solid fa-circle-xmark" style="color: #ef4444;"></i>';
            const s3Icon = s3.ok ? '<i class="fa-solid fa-circle-check" style="color: #10b981;"></i>' : '<i class="fa-solid fa-triangle-exclamation" style="color: #f59e0b;"></i>';
            const s4Icon = s4.ok ? '<i class="fa-solid fa-circle-check" style="color: #10b981;"></i>' : '<i class="fa-solid fa-circle-xmark" style="color: #ef4444;"></i>';
            const s5Icon = s5.ok ? '<i class="fa-solid fa-circle-check" style="color: #10b981;"></i>' : '<i class="fa-solid fa-circle-xmark" style="color: #ef4444;"></i>';

            let html = `
                <div style="font-size: 0.92rem; font-weight: 700; color: ${data.ready_for_save ? '#059669' : '#d97706'}; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                    <i class="fa-solid ${data.ready_for_save ? 'fa-badge-check' : 'fa-triangle-exclamation'}"></i> ${esc(data.message)}
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.82rem; margin-bottom: 10px;">
                    <div style="background: #fff; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0;">
                        ${s1Icon} <strong>Bước 1: Kết nối</strong>: ${s1.latency_ms}ms (${esc(s1.message || 'Tốt')})
                    </div>
                    <div style="background: #fff; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0;">
                        ${s2Icon} <strong>Bước 2: Mẫu 5 frames</strong>: Đọc được ${s2.frames_read}/5 frame (TB: ${s2.avg_latency_ms}ms)
                    </div>
                    <div style="background: #fff; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0;">
                        ${s3Icon} <strong>Bước 3: Độ phân giải</strong>: ${esc(s3.resolution || 'N/A')} (Kích thước đầu TB: ${s3.avg_head_px}px)
                    </div>
                    <div style="background: #fff; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0;">
                        ${s4Icon} <strong>Bước 4: Vùng ROI</strong>: ${s4.green_zone_points} điểm Bàn học, ${s4.red_zone_points} điểm Bục giảng
                    </div>
                </div>
                <div style="background: #eff6ff; border: 1px solid #bfdbfe; padding: 8px 12px; border-radius: 6px; font-size: 0.84rem; color: #1e40af; margin-bottom: 8px;">
                    ${s5Icon} <strong>Bước 5: Thử nghiệm AI</strong>: Phát hiện <strong>${s5.students_detected}</strong> học sinh (Độ tin cậy TB: <strong>${Math.round(s5.confidence_avg * 100)}%</strong>)
                </div>
            `;

            if (resBox) resBox.innerHTML = html;

            if (s5.annotated_preview_url && img) {
                img.src = s5.annotated_preview_url;
                img.style.display = 'inline-block';
            } else if (s4.preview_url && img) {
                img.src = s4.preview_url;
                img.style.display = 'inline-block';
            }

            if (data.ready_for_save) {
                showToast('Camera đạt chuẩn 5 bước! Bạn có thể nhấn Lưu Camera để hoàn tất.', 'success');
            } else {
                showToast('Camera đã kiểm định kèm một số lưu ý kỹ thuật', 'warning');
            }
        } else {
            if (resBox) {
                resBox.innerHTML = `
                    <div style="color: #ef4444; font-weight: 700; font-size: 0.88rem;">
                        <i class="fa-solid fa-circle-xmark"></i> ${esc(data.message || 'Kiểm định thất bại')}
                    </div>
                `;
            }
            showToast(data.message || 'Kiểm định camera thất bại', 'error');
        }
    } catch (err) {
        if (resBox) {
            resBox.innerHTML = `
                <div style="color: #ef4444; font-size: 0.84rem;">
                    <i class="fa-solid fa-triangle-exclamation"></i> Lỗi thực thi Wizard: ${esc(err.message || err)}
                </div>
            `;
        }
        showToast('Lỗi gửi yêu cầu kiểm định: ' + (err.message || err), 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-clipboard-check"></i> Wizard Kiểm Định 5 Bước';
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
            document.getElementById('liveViewModal')?.classList.remove('active');
        }
    } catch (err) {
        alert('Lỗi kết nối kiểm tra camera: ' + (err.message || err));
        document.getElementById('liveViewModal')?.classList.remove('active');
    }
}

export async function saveCamera() {
    const id = document.getElementById('formCamId')?.value;
    const code = document.getElementById('formCode')?.value.trim();
    const name = document.getElementById('formName')?.value.trim();
    const room_number = document.getElementById('formRoom')?.value.trim();
    const standard_count = parseInt(document.getElementById('formStandard')?.value) || 40;
    const rtsp_url = document.getElementById('formRtspUrl')?.value.trim();
    const relay_ip = document.getElementById('formRelayIp')?.value?.trim() || '';
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
            if (typeof externalCallbacks.onRefreshCameras === 'function') {
                await externalCallbacks.onRefreshCameras();
            }
            showToast(result.message || 'Lưu thành công', 'success');
        } else {
            alert('Lỗi: ' + (result.detail || result.message || 'Không thể lưu camera.'));
        }
    } catch (err) {
        alert('Lỗi kết nối máy chủ: ' + (err.message || err));
    }
}

export async function deleteCamera(id, name) {
    let confirmed = false;
    if (window.ConfirmationDialog && typeof window.ConfirmationDialog.delete === 'function') {
        confirmed = await window.ConfirmationDialog.delete(name);
    } else {
        confirmed = window.confirm(`Bạn có chắc chắn muốn xóa camera ${name}?`);
    }
    if (!confirmed) return;

    try {
        const result = await CameraAPI.delete(id);
        if (typeof externalCallbacks.onRefreshCameras === 'function') {
            await externalCallbacks.onRefreshCameras();
        }
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

    if (selectQuick) {
        selectQuick.innerHTML = '<option value="">-- Bấm vào đây để chọn camera --</option>' +
            crudCameras.map(c => `
                <option value="${c.id}">${esc(c.name)} (${esc(c.room_number || 'Phòng ' + c.id)}) - Mã: ${esc(c.code)}</option>
            `).join('');
    }

    if (checklist) {
        if (!crudCameras || crudCameras.length === 0) {
            checklist.innerHTML = '<div style="text-align: center; color: #94a3b8; padding: 16px; font-size: 0.85rem;"><i class="fa-solid fa-circle-info"></i> Hiện không có camera nào trong danh sách</div>';
        } else {
            checklist.innerHTML = crudCameras.map(c => `
                <label class="delete-cam-item">
                    <input type="checkbox" value="${c.id}" class="cam-del-cb" data-name="${encodeURIComponent(c.name)}">
                    <span style="flex: 1; font-weight: 500;">
                        <strong style="color: #0f172a;">${esc(c.code)}</strong> - ${esc(c.name)} 
                        <span style="color: #64748b; font-size: 0.8rem;">(${esc(c.room_number || '--')})</span>
                    </span>
                    <span class="badge ${c.source_type === 'WEBCAM' ? 'badge-warning' : (c.source_type === 'FILE' ? 'badge-primary' : 'badge-success')}" style="font-size: 0.72rem;">
                        ${c.source_type || 'RTSP'}
                    </span>
                </label>
            `).join('');

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
    if (typeof externalCallbacks.onRefreshCameras === 'function') {
        await externalCallbacks.onRefreshCameras();
    }

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
        if (typeof externalCallbacks.onRefreshCameras === 'function') {
            await externalCallbacks.onRefreshCameras();
        }
        showToast(result.message || 'Đã khôi phục mặc định', 'success');
    } catch (err) {
        alert('Lỗi kết nối máy chủ: ' + (err.message || err));
    }
}
