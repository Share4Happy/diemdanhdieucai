/**
 * ===================================================================
 * stream-profiles.js - Module Quản Lý Luồng Chính / Luồng Phụ (CH01 & CH02)
 * THPT Điều Cải - Attendance System
 * ===================================================================
 */

import { CameraAPI, showToast, escapeHtml } from '../../api.js?v=9.0';

let streamData = [];
let currentFilter = 'all';
let currentSearch = '';
let activeCompareCamId = null;
let activeQuickCaptureCamId = null;
let simPollInterval = null;

const esc = (v) => escapeHtml(v);

/**
 * Khởi tạo Controller cho Tab Quản Lý Luồng
 */
export function initStreamProfilesTab() {
    initStreamToolbarEvents();
    initStreamPolicyEvents();
    loadStreamProfiles();
}

/**
 * Tải danh sách thông số luồng thực tế và KPI
 */
export async function loadStreamProfiles(forceRefresh = false) {
    const tableBody = document.getElementById('streamTableBody');
    if (!tableBody) return;

    if (forceRefresh || streamData.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 36px 16px; color: #64748b;">
                    <i class="fa-solid fa-circle-notch fa-spin" style="font-size: 1.5rem; color: #2563eb; margin-bottom: 8px;"></i>
                    <p style="margin: 0; font-weight: 600;">Đang quét và đo lường thông số luồng 32 camera...</p>
                </td>
            </tr>
        `;
    }

    try {
        const res = await CameraAPI.getStreamProfiles();
        if (res && res.success) {
            streamData = res.cameras || [];
            updateStreamKPIs(res.kpi || {});
            updateStreamPolicyUI(res.policy || {});
            renderStreamTable();
        } else {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 24px; color: #dc2626;">
                        <i class="fa-solid fa-triangle-exclamation" style="margin-right: 6px;"></i>
                        Không thể tải thông tin luồng: ${esc(res?.message || 'Lỗi kết nối')}
                    </td>
                </tr>
            `;
        }
    } catch (err) {
        console.error('Lỗi khi tải stream profiles:', err);
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 24px; color: #dc2626;">
                    <i class="fa-solid fa-triangle-exclamation" style="margin-right: 6px;"></i>
                    Lỗi kết nối tới máy chủ khi lấy dữ liệu luồng camera.
                </td>
            </tr>
        `;
    }
}

/**
 * Cập nhật các thẻ KPI trên đầu trang
 */
function updateStreamKPIs(kpi) {
    const elMain = document.getElementById('kpiStreamMainCount');
    const elSub = document.getElementById('kpiStreamSubCount');
    const elDistorted = document.getElementById('kpiStreamDistortedCount');
    const elBandwidth = document.getElementById('kpiStreamBandwidth');
    const tabBadge = document.getElementById('tabBadgeDistorted');

    const total = kpi.total_cameras || 32;
    const mainCount = kpi.main_stream_count || 0;
    const subCount = kpi.sub_stream_count || 0;
    const distortedCount = kpi.distorted_count || 0;
    const bandwidth = kpi.estimated_bandwidth_mbps || 0;

    if (elMain) elMain.textContent = `${mainCount} / ${total}`;
    if (elSub) elSub.textContent = `${subCount} / ${total}`;
    if (elDistorted) elDistorted.textContent = `${distortedCount} Kênh`;
    if (elBandwidth) elBandwidth.textContent = `${bandwidth} Mbps`;

    // Cập nhật huy hiệu cảnh báo trên tab navigation nếu có camera bị bóp méo
    if (tabBadge) {
        if (distortedCount > 0) {
            tabBadge.style.display = 'inline-block';
            tabBadge.textContent = `⚠️ ${distortedCount} lệch 4:3`;
        } else {
            tabBadge.style.display = 'none';
        }
    }
}

/**
 * Cập nhật form Cấu hình Chính sách Dự phòng
 */
function updateStreamPolicyUI(policy) {
    const elFallback = document.getElementById('policyAutoFallback');
    const elTimeout = document.getElementById('policyTimeout');
    const elAspect = document.getElementById('policyAutoAspect');

    if (elFallback) elFallback.checked = policy.auto_fallback !== false;
    if (elTimeout) elTimeout.value = policy.timeout_seconds || 3.5;
}

/**
 * Render Bảng Ma Trận Luồng
 */
export function renderStreamTable() {
    const tableBody = document.getElementById('streamTableBody');
    if (!tableBody) return;

    let filtered = streamData.filter(cam => {
        // Lọc theo chế độ tab
        if (currentFilter === 'main' && cam.stream_type !== 'main') return false;
        if (currentFilter === 'sub' && cam.stream_type !== 'sub') return false;
        if (currentFilter === 'distorted' && !cam.is_distorted) return false;

        // Lọc theo từ khóa tìm kiếm
        if (currentSearch) {
            const query = currentSearch.toLowerCase();
            const matchName = (cam.name || '').toLowerCase().includes(query);
            const matchRoom = (cam.room_number || '').toLowerCase().includes(query);
            const matchIp = (cam.ip_address || '').toLowerCase().includes(query);
            const matchCode = (cam.code || '').toLowerCase().includes(query);
            if (!matchName && !matchRoom && !matchIp && !matchCode) return false;
        }
        return true;
    });

    if (filtered.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 32px 16px; color: #64748b;">
                    <i class="fa-solid fa-filter" style="font-size: 1.3rem; margin-bottom: 6px; opacity: 0.5;"></i>
                    <p style="margin: 0; font-weight: 600;">Không có camera nào khớp với bộ lọc hiện tại.</p>
                </td>
            </tr>
        `;
        return;
    }

    let html = '';
    filtered.forEach((cam, idx) => {
        const isMain = cam.stream_type === 'main';
        const chLabel = `D${String(cam.channel_number || cam.id).padStart(2, '0')}`;
        const isDistorted = cam.is_distorted;

        html += `
            <tr id="streamRow_${cam.id}">
                <td style="font-weight: 700; color: #64748b; text-align: center; width: 44px;">${idx + 1}</td>
                <td>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="background: #0f172a; color: #38bdf8; font-weight: 800; font-size: 0.76rem; padding: 2px 7px; border-radius: 5px;">${chLabel}</span>
                        <div>
                            <div style="font-weight: 700; color: #0f172a; font-size: 0.92rem;">${esc(cam.name)}</div>
                            <div style="font-size: 0.78rem; color: #64748b;">${esc(cam.room_number || 'Phòng học')}</div>
                        </div>
                    </div>
                </td>
                <td>
                    <div style="font-family: monospace; font-size: 0.82rem; color: #1e293b; font-weight: 600;">${esc(cam.ip_address)}:${cam.port || 554}</div>
                    <div style="font-size: 0.74rem; color: #64748b;">Chuẩn nén: <strong style="color: #0f172a;">${esc(cam.codec || 'H.264')}</strong></div>
                </td>
                <td>
                    ${isMain 
                        ? `<span class="stream-badge-pill main"><i class="fa-solid fa-circle-check"></i> CH01 - Chính (1080P)</span>` 
                        : `<span class="stream-badge-pill sub"><i class="fa-solid fa-triangle-exclamation"></i> CH02 - Phụ (VGA)</span>`}
                </td>
                <td>
                    <div class="stream-segmented-toggle">
                        <button type="button" class="stream-seg-btn ${isMain ? 'active-main' : ''}" onclick="window.switchSingleStream && window.switchSingleStream(${cam.id}, 'main')" title="Đặt làm Luồng Chính 1080P">
                            <i class="fa-solid fa-bolt"></i> CH01
                        </button>
                        <button type="button" class="stream-seg-btn ${!isMain ? 'active-sub' : ''}" onclick="window.switchSingleStream && window.switchSingleStream(${cam.id}, 'sub')" title="Đặt làm Luồng Phụ VGA">
                            <i class="fa-solid fa-compress"></i> CH02
                        </button>
                    </div>
                </td>
                <td>
                    <div style="font-weight: 700; font-size: 0.86rem; color: #0f172a;">${esc(cam.resolution || '1920x1080')}</div>
                    ${isDistorted
                        ? `<span class="stream-badge-pill distorted" style="padding: 2px 6px; font-size: 0.72rem; margin-top: 3px;"><i class="fa-solid fa-triangle-exclamation"></i> 4:3 Méo Hình</span>`
                        : `<span style="font-size: 0.75rem; color: #059669; font-weight: 600;"><i class="fa-solid fa-check"></i> 16:9 Chuẩn</span>`}
                </td>
                <td>
                    <div style="font-weight: 700; font-size: 0.84rem; color: #334155;">${cam.bitrate_kbps || 2048} Kbps</div>
                    <div style="font-size: 0.75rem; color: #64748b;">Độ trễ: ~${cam.latency_ms || 30}ms</div>
                </td>
                <td>
                    <div style="display: flex; gap: 6px;">
                        <button type="button" class="btn btn-secondary btn-sm" onclick="window.openStreamCompareModal && window.openStreamCompareModal(${cam.id})" style="padding: 5px 9px; font-size: 0.78rem; font-weight: 700;" title="Soi so sánh đồng thời 2 luồng">
                            <i class="fa-solid fa-code-compare" style="color: #2563eb;"></i> Soi A/B
                        </button>
                        <button type="button" class="btn btn-secondary btn-sm" onclick="window.quickCaptureStreamPreview && window.quickCaptureStreamPreview(${cam.id})" style="padding: 5px 9px; font-size: 0.78rem;" title="Chụp thử khung hình">
                            <i class="fa-solid fa-camera"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });

    tableBody.innerHTML = html;
}

/**
 * Chuyển đổi luồng cho 1 camera đơn lẻ
 */
export async function switchSingleStream(classroomId, targetStream) {
    try {
        const res = await CameraAPI.switchCameraStream(classroomId, targetStream);
        if (res && res.success) {
            showToast(res.message || 'Đã chuyển đổi luồng camera thành công!', 'success');
            // Cập nhật trực tiếp vào mảng data local
            const item = streamData.find(c => c.id === classroomId);
            if (item) {
                item.stream_type = targetStream;
                item.resolution = targetStream === 'main' ? '1920x1080' : '640x480';
                item.aspect_ratio = targetStream === 'main' ? '16:9 (Chuẩn Widescreen)' : '4:3 (Bị bóp méo)';
                item.is_distorted = targetStream === 'sub';
                item.bitrate_kbps = targetStream === 'main' ? 2048 : 320;
            }
            recalcLocalKPIs();
            renderStreamTable();
        } else {
            showToast(res?.message || 'Không thể đổi luồng camera', 'danger');
        }
    } catch (err) {
        console.error('Lỗi switchSingleStream:', err);
        showToast('Lỗi khi gửi yêu cầu chuyển đổi luồng', 'danger');
    }
}

/**
 * Tính toán lại KPI nhanh sau khi người dùng đổi luồng lẻ
 */
function recalcLocalKPIs() {
    let mainCount = 0;
    let subCount = 0;
    let distortedCount = 0;

    streamData.forEach(c => {
        if (c.stream_type === 'sub') {
            subCount++;
            distortedCount++;
        } else {
            mainCount++;
        }
    });

    updateStreamKPIs({
        total_cameras: streamData.length,
        main_stream_count: mainCount,
        sub_stream_count: subCount,
        distorted_count: distortedCount,
        estimated_bandwidth_mbps: (mainCount * 2.048 + subCount * 0.320).toFixed(1)
    });
}

/**
 * Chuyển đổi đồng loạt toàn bộ camera
 */
export async function batchSwitchAllStreams(targetStream) {
    const isMain = targetStream === 'main';
    const label = isMain ? 'Luồng Chính (CH01 - 1080P 16:9)' : 'Luồng Phụ (CH02 - VGA 4:3)';
    const note = isMain 
        ? 'Toàn bộ 32 camera sẽ được nâng cấp lên Full HD 16:9 sắc nét, giúp AI điểm danh chính xác tuyệt đối và xóa bỏ hoàn toàn viền đen.'
        : 'Toàn bộ camera sẽ chuyển sang luồng nén thấp 480p để tiết kiệm tối đa băng thông mạng trong giờ cao điểm.';

    if (!confirm(`XÁC NHẬN CHUYỂN ĐỔI ĐỒNG LOẠT:\n\nBạn có chắc chắn muốn chuyển TOÀN BỘ camera sang ${label} không?\n\n${note}`)) {
        return;
    }

    try {
        showToast(`Đang chuyển đổi toàn bộ camera sang ${label}...`, 'info');
        const res = await CameraAPI.batchSwitchStream(targetStream);
        if (res && res.success) {
            showToast(res.message || `Đã chuyển đổi toàn bộ camera sang ${label}!`, 'success');
            await loadStreamProfiles(true);
        } else {
            showToast(res?.message || 'Không thể chuyển đổi hàng loạt', 'danger');
        }
    } catch (err) {
        console.error('Lỗi batchSwitchAllStreams:', err);
        showToast('Lỗi khi thực hiện thao tác hàng loạt', 'danger');
    }
}

/**
 * Mở Modal Soi Luồng Song Song A/B
 */
export async function openStreamCompareModal(classroomId) {
    activeCompareCamId = classroomId;
    const modal = document.getElementById('streamCompareModal');
    if (!modal) return;

    modal.classList.add('active');

    const titleEl = document.getElementById('abModalTitle');
    const mainViewEl = document.getElementById('abMainView');
    const subViewEl = document.getElementById('abSubView');

    if (titleEl) titleEl.textContent = 'Đang tải thông số và chụp ảnh trực tiếp 2 luồng...';

    if (mainViewEl) {
        mainViewEl.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 260px; color: #94a3b8;">
                <i class="fa-solid fa-circle-notch fa-spin" style="font-size: 2rem; color: #10b981; margin-bottom: 12px;"></i>
                <span>Đang kết nối Luồng Chính CH01 (1080P)...</span>
            </div>
        `;
    }

    if (subViewEl) {
        subViewEl.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 260px; color: #94a3b8;">
                <i class="fa-solid fa-circle-notch fa-spin" style="font-size: 2rem; color: #f59e0b; margin-bottom: 12px;"></i>
                <span>Đang kết nối Luồng Phụ CH02 (VGA)...</span>
            </div>
        `;
    }

    try {
        const res = await CameraAPI.compareStreams(classroomId);
        if (res && res.success) {
            const cam = res.classroom;
            const main = res.main_stream;
            const sub = res.sub_stream;

            if (titleEl) {
                titleEl.innerHTML = `
                    <i class="fa-solid fa-code-compare" style="color: #38bdf8; margin-right: 8px;"></i>
                    So Sánh Trực Quan: <strong>${esc(cam.name)}</strong> (${esc(cam.room_number || '')})
                `;
            }

            renderABPane('abMainView', main, cam.id, 'main', cam.current_stream === 'main');
            renderABPane('abSubView', sub, cam.id, 'sub', cam.current_stream === 'sub');
        } else {
            showToast(res?.message || 'Không thể so sánh luồng', 'danger');
        }
    } catch (err) {
        console.error('Lỗi openStreamCompareModal:', err);
        showToast('Lỗi kết nối khi so sánh luồng', 'danger');
    }
}

/**
 * Render 1 bên của Modal So Sánh A/B
 */
function renderABPane(containerId, data, camId, type, isCurrent) {
    const el = document.getElementById(containerId);
    if (!el) return;

    const isMain = type === 'main';
    const isSuccess = data.success;
    const previewImg = data.preview_url 
        ? `<img src="${data.preview_url}" class="ab-preview-img" alt="${data.label}" />`
        : `<div style="color: #64748b; text-align: center; padding: 40px 10px;">
             <i class="fa-solid fa-video-slash" style="font-size: 2rem; margin-bottom: 8px;"></i>
             <p style="margin: 0;">Chưa nhận được khung hình</p>
           </div>`;

    el.innerHTML = `
        <div class="ab-stream-pane ${isMain ? 'featured-main' : 'featured-sub'}">
            <div class="ab-pane-header">
                <div class="ab-pane-title">
                    <i class="fa-solid ${isMain ? 'fa-bolt' : 'fa-compress'}" style="color: ${isMain ? '#10b981' : '#f59e0b'};"></i>
                    <span>${data.label}</span>
                </div>
                ${isCurrent 
                    ? `<span style="background: #38bdf8; color: #0f172a; font-weight: 800; font-size: 0.72rem; padding: 2px 8px; border-radius: 999px;">ĐANG SỬ DỤNG</span>` 
                    : ''}
            </div>

            <div class="ab-preview-viewport">
                ${previewImg}
            </div>

            <div class="ab-specs-table">
                <div class="ab-spec-row">
                    <span>Độ Phân Giải:</span>
                    <strong style="color: #f8fafc;">${esc(data.resolution || 'N/A')}</strong>
                </div>
                <div class="ab-spec-row">
                    <span>Tỷ Lệ Khung Hình:</span>
                    <strong style="color: ${isMain ? '#34d399' : '#fbbf24'};">${esc(data.aspect_ratio || 'N/A')}</strong>
                </div>
                <div class="ab-spec-row">
                    <span>Tốc Độ Bitrate:</span>
                    <span>${data.bitrate_kbps || 0} Kbps</span>
                </div>
                <div class="ab-spec-row">
                    <span>Tốc Độ Khung Hình:</span>
                    <span>${data.fps || 25} FPS</span>
                </div>
                <div class="ab-spec-row">
                    <span>Độ Trễ Phản Hồi:</span>
                    <span>~${data.latency_ms || 0} ms</span>
                </div>
                <div class="ab-spec-row" style="border: none;">
                    <span>Chuẩn Mã Hóa:</span>
                    <span>${esc(data.codec || 'H.264')}</span>
                </div>

                <div class="ab-verdict-box ${isMain ? 'success' : 'warning'}">
                    <i class="fa-solid ${isMain ? 'fa-circle-check' : 'fa-triangle-exclamation'}"></i>
                    <span>${esc(data.ai_verdict || '')}</span>
                </div>
            </div>

            <div class="ab-pane-footer">
                <button type="button" class="btn ${isMain ? 'btn-success' : 'btn-warning'}" style="width: 100%; font-weight: 700; padding: 9px;" onclick="window.applyStreamFromABModal && window.applyStreamFromABModal(${camId}, '${type}')">
                    <i class="fa-solid fa-check"></i> ${isCurrent ? 'Đang Dùng Luồng Này' : `Áp Dụng ${isMain ? 'Luồng Chính (1080P)' : 'Luồng Phụ (VGA)'}`}
                </button>
            </div>
        </div>
    `;
}

/**
 * Đóng Modal A/B
 */
export function closeStreamCompareModal() {
    const modal = document.getElementById('streamCompareModal');
    if (modal) modal.classList.remove('active');
    activeCompareCamId = null;
}

/**
 * Áp dụng luồng trực tiếp từ Modal A/B
 */
export async function applyStreamFromABModal(classroomId, streamType) {
    await switchSingleStream(classroomId, streamType);
    closeStreamCompareModal();
}

/**
 * Chụp & Xem thử khung hình camera (Instant Snapshot Preview Modal)
 */
export async function quickCaptureStreamPreview(classroomId) {
    const cam = streamData.find(c => c.id === classroomId);
    if (!cam) return;

    activeQuickCaptureCamId = classroomId;

    const modal = document.getElementById('streamQuickCaptureModal');
    if (!modal) return;

    const titleEl = document.getElementById('qcCamTitle');
    const loadingEl = document.getElementById('qcLoading');
    const imgEl = document.getElementById('qcImg');
    const badgeEl = document.getElementById('qcStreamBadge');
    const resEl = document.getElementById('qcResolution');
    const aspectEl = document.getElementById('qcAspectRatio');
    const statusEl = document.getElementById('qcStreamStatus');
    const timeEl = document.getElementById('qcTimestamp');
    const noticeEl = document.getElementById('qcNotice');

    if (titleEl) titleEl.innerText = `${cam.name} (${cam.room_number || 'Phòng học'})`;
    if (loadingEl) loadingEl.style.display = 'flex';
    if (imgEl) {
        imgEl.style.display = 'none';
        imgEl.src = '';
    }
    if (badgeEl) badgeEl.style.display = 'none';
    if (noticeEl) noticeEl.style.display = 'none';

    if (resEl) resEl.innerText = cam.resolution || '--';
    if (aspectEl) {
        aspectEl.innerText = cam.aspect_ratio || '--';
        aspectEl.style.color = (cam.stream_type === 'main') ? '#34d399' : '#fbbf24';
    }
    if (statusEl) {
        statusEl.innerHTML = cam.stream_type === 'sub'
            ? `<span style="color: #fbbf24;"><i class="fa-solid fa-compress"></i> Luồng Phụ CH02</span>`
            : `<span style="color: #34d399;"><i class="fa-solid fa-bolt"></i> Luồng Chính CH01</span>`;
    }
    if (timeEl) timeEl.innerText = 'Đang trích xuất...';

    // Gán nút chụp lại trong modal
    const btnRecapture = document.getElementById('btnQcRecapture');
    if (btnRecapture) {
        btnRecapture.onclick = () => quickCaptureStreamPreview(classroomId);
    }
    // Gán nút mở modal so sánh A/B
    const btnCompare = document.getElementById('btnQcCompareAB');
    if (btnCompare) {
        btnCompare.onclick = () => {
            closeQuickCaptureModal();
            openStreamCompareModal(classroomId);
        };
    }

    modal.classList.add('active');

    try {
        const res = await CameraAPI.refreshClassroomSnapshot(classroomId);
        const snapUrl = res?.snapshot_url || cam.snapshot_url || `/storage/captures/latest/Lop_${classroomId}.jpg?t=${Date.now()}`;
        
        if (imgEl) {
            imgEl.onload = () => {
                if (loadingEl) loadingEl.style.display = 'none';
                imgEl.style.display = 'block';

                const naturalW = imgEl.naturalWidth || 1920;
                const naturalH = imgEl.naturalHeight || 1080;
                if (resEl) resEl.innerText = `${naturalW} x ${naturalH} px`;

                const ratio = naturalW / naturalH;
                const isWide = ratio >= 1.55;
                if (aspectEl) {
                    aspectEl.innerText = isWide ? '16:9 (Chuẩn Widescreen)' : '4:3 (Tỷ lệ hẹp)';
                    aspectEl.style.color = isWide ? '#34d399' : '#fbbf24';
                }

                if (badgeEl) {
                    badgeEl.style.display = 'block';
                    badgeEl.innerHTML = (cam.stream_type === 'sub' || !isWide)
                        ? `<span style="background: #f59e0b; color: #0f172a; font-weight: 800; font-size: 0.72rem; padding: 4px 10px; border-radius: 999px; box-shadow: 0 4px 12px rgba(0,0,0,0.5);"><i class="fa-solid fa-compress"></i> LUỒNG PHỤ CH02 (VGA)</span>`
                        : `<span style="background: #10b981; color: #0f172a; font-weight: 800; font-size: 0.72rem; padding: 4px 10px; border-radius: 999px; box-shadow: 0 4px 12px rgba(0,0,0,0.5);"><i class="fa-solid fa-bolt"></i> LUỒNG CHÍNH CH01 (1080P)</span>`;
                }

                if (statusEl) {
                    statusEl.innerHTML = res?.success 
                        ? `<span style="color: #34d399;"><i class="fa-solid fa-circle-check"></i> Trích xuất thành công</span>`
                        : `<span style="color: #38bdf8;"><i class="fa-solid fa-image"></i> Khung hình lưu trữ</span>`;
                }

                if (timeEl) timeEl.innerText = new Date().toLocaleTimeString('vi-VN');
            };

            imgEl.onerror = () => {
                if (loadingEl) loadingEl.style.display = 'none';
                if (noticeEl) {
                    noticeEl.style.display = 'flex';
                    noticeEl.style.background = 'rgba(239, 68, 68, 0.15)';
                    noticeEl.style.border = '1px solid rgba(239, 68, 68, 0.3)';
                    noticeEl.style.color = '#fca5a5';
                    noticeEl.innerHTML = `<i class="fa-solid fa-triangle-exclamation" style="color: #ef4444; font-size: 1.1rem;"></i> <span>Camera ${cam.name} hiện chưa kết nối RTSP hoặc luồng đang tải. Vui lòng kiểm tra lại địa chỉ IP NVR.</span>`;
                }
            };

            imgEl.src = snapUrl;
        }

        if (res && res.success) {
            showToast(`Đã bắt khung hình mới cho ${cam.name}`, 'success');
        } else {
            if (noticeEl) {
                noticeEl.style.display = 'flex';
                noticeEl.style.background = 'rgba(56, 189, 248, 0.12)';
                noticeEl.style.border = '1px solid rgba(56, 189, 248, 0.3)';
                noticeEl.style.color = '#bae6fd';
                noticeEl.innerHTML = `<i class="fa-solid fa-circle-info" style="color: #38bdf8; font-size: 1.1rem;"></i> <span>${esc(res?.message || 'Đang hiển thị khung hình snapshot mới nhất của camera.')}</span>`;
            }
        }
    } catch (err) {
        console.error('Lỗi quickCaptureStreamPreview:', err);
        if (loadingEl) loadingEl.style.display = 'none';
        showToast('Lỗi khi chụp thử camera', 'danger');
    }
}

/**
 * Đóng modal xem trước khung hình nhanh
 */
export function closeQuickCaptureModal() {
    const modal = document.getElementById('streamQuickCaptureModal');
    if (modal) modal.classList.remove('active');
    const imgEl = document.getElementById('qcImg');
    if (imgEl) imgEl.src = '';
}

/**
 * Chạy mô phỏng lấy hình & đo lường độ ổn định toàn trường (Dry-Run Stability Test)
 */
export async function startCaptureSimulation(scope = 'all') {
    const modal = document.getElementById('streamSimulationModal');
    if (!modal) return;

    modal.classList.add('active');

    const progressBar = document.getElementById('simProgressBar');
    const percentBadge = document.getElementById('simPercentBadge');
    const statusPill = document.getElementById('simStatusPill');
    const statusText = document.getElementById('simStatusText');
    const currentItem = document.getElementById('simCurrentItem');
    const scorecard = document.getElementById('simScorecard');
    const tableBody = document.getElementById('simTableBody');
    const countDone = document.getElementById('simCountDone');

    if (progressBar) progressBar.style.width = '0%';
    if (percentBadge) percentBadge.innerText = '0%';
    if (statusPill) {
        statusPill.style.background = 'rgba(56, 189, 248, 0.12)';
        statusPill.style.color = '#38bdf8';
    }
    if (statusText) statusText.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Đang kết nối đầu ghi NVR và khởi tạo mô phỏng...';
    if (currentItem) currentItem.innerText = '';
    if (scorecard) scorecard.style.display = 'none';
    if (countDone) countDone.innerText = '0/32 hoàn thành';
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 30px; color: #64748b;">
                    <i class="fa-solid fa-circle-notch fa-spin" style="font-size: 1.4rem; color: #38bdf8; margin-bottom: 8px;"></i>
                    <p style="margin: 0; font-weight: 600;">Đang kết nối NVR và kiểm tra luồng từng camera...</p>
                </td>
            </tr>
        `;
    }

    // Polling progress thời gian thực
    if (simPollInterval) clearInterval(simPollInterval);
    simPollInterval = setInterval(async () => {
        try {
            const prog = await CameraAPI.getProgress();
            if (prog && prog.action === 'SIMULATE_CAPTURE') {
                const pct = Math.min(100, Math.max(0, prog.percent || 0));
                if (progressBar) progressBar.style.width = `${pct}%`;
                if (percentBadge) percentBadge.innerText = `${pct}%`;
                if (statusText) statusText.innerText = prog.step_title || 'Đang mô phỏng...';
                if (currentItem) currentItem.innerText = prog.current_item || '';
                if (countDone && prog.total_items) {
                    countDone.innerText = `${prog.current_item_index || 0}/${prog.total_items} hoàn thành`;
                }
            }
        } catch (e) {
            // ignore
        }
    }, 350);

    try {
        const res = await CameraAPI.simulateCaptureTest({ scope: scope });
        if (simPollInterval) {
            clearInterval(simPollInterval);
            simPollInterval = null;
        }

        if (res && res.success) {
            const s = res.summary || {};
            const details = res.details || [];

            if (progressBar) progressBar.style.width = '100%';
            if (percentBadge) percentBadge.innerText = '100%';
            if (statusPill) {
                statusPill.style.background = 'rgba(16, 185, 129, 0.15)';
                statusPill.style.color = '#10b981';
            }
            if (statusText) statusText.innerHTML = '<i class="fa-solid fa-circle-check"></i> Hoàn thành kiểm tra độ ổn định!';
            if (currentItem) currentItem.innerText = `Đã kiểm tra ${s.total_cameras} camera trong ${s.total_time_sec}s`;
            if (countDone) countDone.innerText = `${s.total_cameras}/${s.total_cameras} hoàn thành`;

            // Điền Scorecard
            if (scorecard) {
                const scoreCircle = document.getElementById('simScoreCircle');
                const scoreEl = document.getElementById('simHealthScore');
                const verdictTitle = document.getElementById('simVerdictTitle');
                const verdictDesc = document.getElementById('simVerdictDesc');
                const kpiSuccess = document.getElementById('simKpiSuccess');
                const kpiLatency = document.getElementById('simKpiLatency');
                const kpiAspect = document.getElementById('simKpiAspect');
                const kpiTotalTime = document.getElementById('simKpiTotalTime');

                if (scoreEl) scoreEl.innerText = s.health_score || 95;
                const scoreColor = (s.health_score >= 90) ? '#10b981' : ((s.health_score >= 75) ? '#fbbf24' : '#ef4444');
                if (scoreCircle) {
                    scoreCircle.style.borderColor = scoreColor;
                    scoreCircle.style.background = `${scoreColor}18`;
                }
                if (scoreEl) scoreEl.style.color = scoreColor;

                if (verdictTitle) {
                    verdictTitle.innerText = s.verdict_level === 'success' ? 'HỆ THỐNG ĐẠT CHUẨN XUẤT SẮC' : (s.verdict_level === 'warning' ? 'HỆ THỐNG ĐẠT YÊU CẦU' : 'CẦN LƯU Ý KIỂM TRA ĐƯỜNG TRUYỀN');
                    verdictTitle.style.color = scoreColor;
                }
                if (verdictDesc) verdictDesc.innerText = s.verdict || '';

                if (kpiSuccess) kpiSuccess.innerText = `${s.success_count}/${s.total_cameras} (${Math.round((s.success_count / s.total_cameras) * 100)}%)`;
                if (kpiLatency) kpiLatency.innerText = `~${s.avg_latency_ms} ms`;
                if (kpiAspect) kpiAspect.innerText = `${s.aspect_16_9_count}/${s.total_cameras} phòng`;
                if (kpiTotalTime) kpiTotalTime.innerText = `${s.total_time_sec}s`;

                scorecard.style.display = 'block';
            }

            // Điền bảng chi tiết từng camera
            if (tableBody) {
                tableBody.innerHTML = details.map(item => {
                    const isMain = item.stream_type === 'main';
                    const is169 = item.aspect_ratio.includes('16:9');
                    const latencyColor = item.latency_ms < 100 ? '#10b981' : (item.latency_ms < 400 ? '#fbbf24' : '#ef4444');
                    return `
                        <tr style="border-bottom: 1px solid #1e293b; transition: background 0.15s;">
                            <td style="padding: 10px 14px; font-weight: 600; color: #f8fafc;">
                                ${esc(item.name)}
                                <div style="font-size: 0.72rem; color: #64748b; font-weight: 400;">${esc(item.room_number)}</div>
                            </td>
                            <td style="padding: 10px 14px;">
                                <span style="display: inline-flex; align-items: center; gap: 5px; font-weight: 700; font-size: 0.75rem; color: ${isMain ? '#34d399' : '#fbbf24'};">
                                    <i class="fa-solid ${isMain ? 'fa-bolt' : 'fa-compress'}"></i>
                                    CH${String(item.channel_number).padStart(2, '0')} (${isMain ? 'CH01 Main' : 'CH02 Sub'})
                                </span>
                            </td>
                            <td style="padding: 10px 14px; color: #cbd5e1; font-weight: 600;">
                                ${esc(item.resolution)}
                            </td>
                            <td style="padding: 10px 14px;">
                                <span style="display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.72rem; font-weight: 700; background: ${is169 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)'}; color: ${is169 ? '#34d399' : '#fbbf24'};">
                                    ${esc(item.aspect_ratio)}
                                </span>
                            </td>
                            <td style="padding: 10px 14px; font-weight: 700; color: ${latencyColor};">
                                ~${item.latency_ms} ms
                            </td>
                            <td style="padding: 10px 14px;">
                                <span style="display: inline-flex; align-items: center; gap: 5px; font-size: 0.75rem; font-weight: 600; color: ${item.success ? '#10b981' : '#ef4444'};">
                                    <i class="fa-solid ${item.success ? 'fa-circle-check' : 'fa-circle-xmark'}"></i>
                                    ${item.success ? 'Ổn định' : 'Mất kết nối'}
                                </span>
                            </td>
                            <td style="padding: 10px 14px; text-align: right;">
                                <button type="button" class="btn btn-secondary btn-sm" onclick="window.quickCaptureStreamPreview && window.quickCaptureStreamPreview(${item.id})" style="padding: 3px 8px; font-size: 0.75rem;" title="Xem phóng to ảnh">
                                    <i class="fa-solid fa-eye"></i> Xem
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }

            showToast(`Mô phỏng lấy hình hoàn tất: ${s.success_count}/${s.total_cameras} camera đạt chuẩn!`, 'success');
        } else {
            showToast(res?.message || 'Lỗi khi chạy mô phỏng lấy hình', 'danger');
        }
    } catch (err) {
        if (simPollInterval) {
            clearInterval(simPollInterval);
            simPollInterval = null;
        }
        console.error('Lỗi startCaptureSimulation:', err);
        showToast('Lỗi kết nối khi chạy mô phỏng lấy hình', 'danger');
    }
}

/**
 * Đóng modal mô phỏng
 */
export function closeSimulationModal() {
    if (simPollInterval) {
        clearInterval(simPollInterval);
        simPollInterval = null;
    }
    const modal = document.getElementById('streamSimulationModal');
    if (modal) modal.classList.remove('active');
}

/**
 * Đăng ký sự kiện trên thanh công cụ & bộ lọc
 */
function initStreamToolbarEvents() {
    // Nút chuyển tất cả sang Luồng Chính
    const btnAllMain = document.getElementById('btnBatchSwitchMainAll');
    if (btnAllMain) {
        btnAllMain.onclick = () => batchSwitchAllStreams('main');
    }

    // Nút chuyển tất cả sang Luồng Phụ
    const btnAllSub = document.getElementById('btnBatchSwitchSubAll');
    if (btnAllSub) {
        btnAllSub.onclick = () => batchSwitchAllStreams('sub');
    }

    // Nút test mô phỏng lấy hình
    const btnSimulate = document.getElementById('btnSimulateCaptureTest');
    if (btnSimulate) {
        btnSimulate.onclick = () => startCaptureSimulation('all');
    }

    // Nút làm mới dữ liệu
    const btnRefresh = document.getElementById('btnRefreshStreamProfiles');
    if (btnRefresh) {
        btnRefresh.onclick = () => loadStreamProfiles(true);
    }

    // Ô tìm kiếm
    const searchInput = document.getElementById('streamSearchInput');
    if (searchInput) {
        searchInput.oninput = (e) => {
            currentSearch = (e.target.value || '').trim();
            renderStreamTable();
        };
    }

    // Nhóm nút lọc
    const filterBtns = document.querySelectorAll('.stream-filter-btn');
    filterBtns.forEach(btn => {
        btn.onclick = () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.getAttribute('data-filter') || 'all';
            renderStreamTable();
        };
    });

    // Phím ESC đóng các modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeQuickCaptureModal();
            closeSimulationModal();
        }
    });
}

/**
 * Đăng ký sự kiện cho Form Cấu hình Chính sách Dự phòng
 */
function initStreamPolicyEvents() {
    const btnSavePolicy = document.getElementById('btnSaveStreamPolicy');
    if (!btnSavePolicy) return;

    btnSavePolicy.onclick = async () => {
        const autoFallback = document.getElementById('policyAutoFallback')?.checked ?? true;
        const timeoutSeconds = parseFloat(document.getElementById('policyTimeout')?.value || '3.5');

        try {
            btnSavePolicy.disabled = true;
            btnSavePolicy.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...`;

            const res = await CameraAPI.updateStreamPolicy({
                auto_fallback: autoFallback,
                timeout_seconds: timeoutSeconds
            });

            if (res && res.success) {
                showToast(res.message || 'Đã lưu chính sách quản lý luồng!', 'success');
            } else {
                showToast(res?.message || 'Không thể lưu chính sách', 'danger');
            }
        } catch (err) {
            console.error('Lỗi khi lưu chính sách luồng:', err);
            showToast('Lỗi kết nối khi lưu chính sách', 'danger');
        } finally {
            btnSavePolicy.disabled = false;
            btnSavePolicy.innerHTML = `<i class="fa-solid fa-floppy-disk"></i> Lưu Cấu Hình Chính Sách`;
        }
    };
}

// Gán các hàm global để gọi từ HTML inline events
if (typeof window !== 'undefined') {
    window.switchSingleStream = switchSingleStream;
    window.batchSwitchAllStreams = batchSwitchAllStreams;
    window.openStreamCompareModal = openStreamCompareModal;
    window.closeStreamCompareModal = closeStreamCompareModal;
    window.applyStreamFromABModal = applyStreamFromABModal;
    window.quickCaptureStreamPreview = quickCaptureStreamPreview;
    window.closeQuickCaptureModal = closeQuickCaptureModal;
    window.startCaptureSimulation = startCaptureSimulation;
    window.closeSimulationModal = closeSimulationModal;
    window.loadStreamProfiles = loadStreamProfiles;
}
