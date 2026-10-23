import { AuthAPI, SystemAPI, showToast } from './api.js?v=5.2';
import SkeletonTemplates from './components/skeleton-templates.js';

let usersCache = [];
let currentAiConfig = null;

// =========================================================================
// TIỆN ÍCH CHUNG
// =========================================================================
function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function roleLabel(role) {
    return role === 'admin' ? 'Quản Trị' : 'Nhân Viên';
}

function findUser(id) {
    return usersCache.find((u) => u.id === Number(id));
}

// Quản lý hiển thị các Tab trên trang cài đặt
export function switchTab(targetTabId) {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach((btn) => {
        const isMatch = btn.dataset.tab === targetTabId || btn.id === targetTabId;
        btn.classList.toggle('active', isMatch);
        btn.setAttribute('aria-selected', isMatch ? 'true' : 'false');
    });

    tabContents.forEach((content) => {
        const isMatch = content.id === targetTabId;
        content.classList.toggle('active', isMatch);
        if (isMatch) {
            content.removeAttribute('hidden');
        } else {
            content.setAttribute('hidden', '');
        }
    });

    if (targetTabId === 'tab-ai-service') {
        loadAiSettings();
    } else {
        renderUsersTable();
    }
}
window.switchTab = switchTab;

// =========================================================================
// TAB 1: QUẢN LÝ TÀI KHOẢN (ACCOUNTS)
// =========================================================================
function updateStats(users) {
    const total = users.length;
    const admins = users.filter((u) => u.role === 'admin').length;
    const staff = users.filter((u) => u.role !== 'admin').length;
    const active = users.filter((u) => u.is_active).length;

    const elTotal = document.getElementById('statTotalUsers');
    const elAdmin = document.getElementById('statAdminUsers');
    const elStaff = document.getElementById('statStaffUsers');
    const elActive = document.getElementById('statActiveUsers');

    if (elTotal) elTotal.textContent = total;
    if (elAdmin) elAdmin.textContent = admins;
    if (elStaff) elStaff.textContent = staff;
    if (elActive) elActive.textContent = active;
}

function getFilteredUsers() {
    const search = (document.getElementById('filterUsersInput')?.value || '').trim().toLowerCase();
    const roleFilter = document.getElementById('filterUserRole')?.value || 'all';

    return usersCache.filter((u) => {
        const matchName = (u.full_name || '').toLowerCase().includes(search);
        const matchEmail = (u.email || '').toLowerCase().includes(search);
        const matchesSearch = !search || matchName || matchEmail;

        const matchesRole = roleFilter === 'all' || u.role === roleFilter;

        return matchesSearch && matchesRole;
    });
}

function renderUsersTable() {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;

    const filtered = getFilteredUsers();

    if (!filtered.length) {
        tbody.innerHTML = `<tr><td colspan="5">${SkeletonTemplates.emptyState('Không tìm thấy tài khoản phù hợp', 'fa-users')}</td></tr>`;
        return;
    }

    const currentId = window.currentUser?.id;
    tbody.innerHTML = filtered
        .map((u) => {
            const active = !!u.is_active;
            const statusClass = active ? 'badge-success' : 'badge-gray';
            const statusText = active ? 'Hoạt Động' : 'Tạm Ngưng';
            const toggleTitle = active ? 'Tạm Ngưng Hoạt Động' : 'Kích Hoạt Lại';
            const toggleIcon = active ? 'fa-user-slash' : 'fa-user-check';
            const toggleExtraClass = active ? 'warning' : '';
            const isSelf = currentId === u.id;
            return `
            <tr class="${active ? '' : 'user-row-inactive'}">
                <td><strong>${escapeHtml(u.full_name || '—')}</strong></td>
                <td>${escapeHtml(u.email)}</td>
                <td><span class="badge ${u.role === 'admin' ? 'badge-primary' : 'badge-gray'}">${roleLabel(u.role)}</span></td>
                <td><span class="badge ${statusClass}">${statusText}</span></td>
                <td class="cell-actions">
                    <div class="table-actions">
                        <button type="button" class="action-btn-icon js-edit-user" data-id="${u.id}" title="Chỉnh Sửa Thông Tin">
                            <i class="fa-solid fa-pen-to-square"></i>
                        </button>
                        <button type="button" class="action-btn-icon ${toggleExtraClass} js-toggle-user" data-id="${u.id}" data-active="${active}" title="${toggleTitle}" ${isSelf && active ? 'disabled' : ''}>
                            <i class="fa-solid ${toggleIcon}"></i>
                        </button>
                    </div>
                </td>
            </tr>`;
        })
        .join('');
}

async function loadUsers() {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;

    tbody.innerHTML = SkeletonTemplates.userTableRow().repeat(3);

    try {
        const data = await AuthAPI.listUsers();
        usersCache = data.users || [];
        updateStats(usersCache);
        renderUsersTable();
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: var(--space-6); color: var(--danger);">${escapeHtml(err.message)}</td></tr>`;
    }
}

function bindFilterEvents() {
    const searchInput = document.getElementById('filterUsersInput');
    const roleSelect = document.getElementById('filterUserRole');

    if (searchInput) {
        searchInput.addEventListener('input', () => {
            renderUsersTable();
        });
    }

    if (roleSelect) {
        roleSelect.addEventListener('change', () => {
            renderUsersTable();
        });
    }
}

function closeEditModal() {
    document.getElementById('editUserModal')?.classList.remove('active');
}

function openEditModal(user) {
    document.getElementById('editUserId').value = user.id;
    document.getElementById('editUserFullName').value = user.full_name || '';
    document.getElementById('editUserEmail').value = user.email || '';
    document.getElementById('editUserRole').value = user.role === 'admin' ? 'admin' : 'staff';
    document.getElementById('editUserPassword').value = '';
    document.getElementById('editUserModal')?.classList.add('active');
    document.getElementById('editUserFullName')?.focus();
}

function openCreateModal() {
    const form = document.getElementById('createUserForm');
    if (form) form.reset();
    document.getElementById('createUserModal')?.classList.add('active');
    setTimeout(() => {
        document.getElementById('userFullName')?.focus();
    }, 100);
}

function closeCreateModal() {
    document.getElementById('createUserModal')?.classList.remove('active');
}

function bindCreateForm() {
    const btnOpen = document.getElementById('btnOpenCreateUserModal');
    if (btnOpen) {
        btnOpen.addEventListener('click', openCreateModal);
    }

    const modal = document.getElementById('createUserModal');
    if (modal) {
        modal.querySelectorAll('[data-close-create-modal]').forEach((el) => {
            el.addEventListener('click', closeCreateModal);
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeCreateModal();
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal?.classList.contains('active')) {
            closeCreateModal();
        }
    });

    const form = document.getElementById('createUserForm');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            full_name: document.getElementById('userFullName')?.value.trim(),
            email: document.getElementById('userEmail')?.value.trim(),
            password: document.getElementById('userPassword')?.value,
            role: document.getElementById('userRole')?.value || 'staff'
        };
        const btn = form.querySelector('button[type="submit"]');
        if (btn) btn.disabled = true;
        try {
            await AuthAPI.createUser(payload);
            showToast('Đã tạo tài khoản mới thành công.', 'success');
            form.reset();
            closeCreateModal();
            await loadUsers();
        } catch (err) {
            showToast(err.message || 'Không tạo được tài khoản.', 'danger');
        } finally {
            if (btn) btn.disabled = false;
        }
    });
}

function bindTableActions() {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;
    tbody.addEventListener('click', async (e) => {
        const editBtn = e.target.closest('.js-edit-user');
        if (editBtn) {
            const user = findUser(editBtn.dataset.id);
            if (user) openEditModal(user);
            return;
        }
        const toggleBtn = e.target.closest('.js-toggle-user');
        if (!toggleBtn || toggleBtn.disabled) return;
        const user = findUser(toggleBtn.dataset.id);
        if (!user) return;
        const nextActive = !user.is_active;
        const confirmed = window.ConfirmationDialog
            ? await ConfirmationDialog.confirm({
                title: nextActive ? 'Kích Hoạt Lại Tài Khoản' : 'Tạm Ngưng Hoạt Động',
                message: nextActive
                    ? `Bật lại tài khoản <strong>${escapeHtml(user.full_name || user.email)}</strong>?<br><small style="color: var(--text-muted);">Tài khoản sẽ có thể đăng nhập lại vào hệ thống.</small>`
                    : `Tạm ngưng tài khoản <strong>${escapeHtml(user.full_name || user.email)}</strong>?<br><small style="color: var(--text-muted);">Tài khoản sẽ không thể đăng nhập cho đến khi được kích hoạt lại.</small>`,
                confirmText: nextActive ? '<i class="fa-solid fa-user-check"></i> Kích Hoạt' : '<i class="fa-solid fa-user-slash"></i> Tạm Ngưng',
                cancelText: 'Hủy',
                type: nextActive ? 'info' : 'warning',
                confirmClass: nextActive ? 'btn-success' : 'btn-warning'
            })
            : window.confirm(nextActive ? 'Kích hoạt tài khoản này?' : 'Tạm ngưng hoạt động của tài khoản này?');
        if (!confirmed) return;
        toggleBtn.disabled = true;
        try {
            await AuthAPI.setUserStatus(user.id, nextActive);
            showToast(
                nextActive
                    ? '✅ Đã kích hoạt lại tài khoản thành công.'
                    : '⏸️ Đã tạm ngưng tài khoản.',
                'success'
            );
            await loadUsers();
        } catch (err) {
            showToast(err.message || 'Không cập nhật được trạng thái.', 'danger');
            toggleBtn.disabled = false;
        }
    });
}

function bindEditModal() {
    const modal = document.getElementById('editUserModal');
    const form = document.getElementById('editUserForm');
    if (!modal || !form) return;

    modal.querySelectorAll('[data-close-modal]').forEach((el) => {
        el.addEventListener('click', closeEditModal);
    });
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeEditModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) closeEditModal();
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = Number(document.getElementById('editUserId').value);
        const password = document.getElementById('editUserPassword')?.value || '';
        const payload = {
            full_name: document.getElementById('editUserFullName')?.value.trim(),
            email: document.getElementById('editUserEmail')?.value.trim(),
            role: document.getElementById('editUserRole')?.value || 'staff'
        };
        if (password) payload.password = password;
        const btn = form.querySelector('button[type="submit"]');
        if (btn) btn.disabled = true;
        try {
            await AuthAPI.updateUser(id, payload);
            showToast('Đã cập nhật thông tin tài khoản.', 'success');
            closeEditModal();
            await loadUsers();
        } catch (err) {
            showToast(err.message || 'Không cập nhật được tài khoản.', 'danger');
        } finally {
            if (btn) btn.disabled = false;
        }
    });
}


// =========================================================================
// TAB 2: CẤU HÌNH KẾT NỐI AI SERVICE & CHẠY THỬ NGHIỆM TRỰC TIẾP
// =========================================================================

function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.tab;
            if (target) {
                switchTab(target);
                // Cập nhật hash trên URL mà không reload trang
                if (window.history && window.history.replaceState) {
                    window.history.replaceState(null, '', `#${target.replace('tab-', '')}`);
                }
            }
        });
    });

    // Kích hoạt tab tương ứng nếu URL có hash (#ai-service hoặc #accounts)
    if (window.location.hash === '#ai-service') {
        switchTab('tab-ai-service');
    }
}

function updateAiStatusPill(isOnline, latencyMs = null, checking = false) {
    const pill = document.getElementById('aiStatusPill');
    const tabPill = document.getElementById('tabAiStatusPill');
    const textEl = document.getElementById('aiStatusText');

    if (!pill) return;

    if (checking) {
        pill.className = 'ai-status-pill checking';
        if (textEl) textEl.textContent = 'Đang kiểm tra kết nối...';
        if (tabPill) {
            tabPill.innerHTML = '<i class="fa-solid fa-spinner fa-spin" style="font-size: 0.55rem;"></i> Đang kiểm tra';
            tabPill.style.background = 'rgba(56, 189, 248, 0.15)';
            tabPill.style.color = '#0284c7';
        }
        return;
    }

    if (isOnline) {
        pill.className = 'ai-status-pill online';
        const latStr = latencyMs ? `${latencyMs} ms` : 'Sẵn sàng';
        pill.innerHTML = `<i class="fa-solid fa-circle-check"></i> <span id="aiStatusText">Đã kết nối (${latStr})</span>`;
        if (tabPill) {
            tabPill.innerHTML = `<i class="fa-solid fa-circle" style="font-size: 0.55rem; color: #16a34a;"></i> Sẵn sàng`;
            tabPill.style.background = 'rgba(22, 163, 74, 0.12)';
            tabPill.style.color = '#15803d';
        }
    } else {
        pill.className = 'ai-status-pill offline';
        pill.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> <span id="aiStatusText">Mất kết nối</span>`;
        if (tabPill) {
            tabPill.innerHTML = `<i class="fa-solid fa-circle" style="font-size: 0.55rem; color: #dc2626;"></i> Mất kết nối`;
            tabPill.style.background = 'rgba(220, 38, 38, 0.12)';
            tabPill.style.color = '#b91c1c';
        }
    }
}

async function loadAiSettings() {
    try {
        updateAiStatusPill(false, null, true);
        const res = await SystemAPI.getAiEndpoint();
        currentAiConfig = res;

        const inputUrl = document.getElementById('aiApiUrl');
        if (inputUrl && (res.current_url || res.target_url)) {
            inputUrl.value = res.current_url || res.target_url;
        }

        const inputPasses = document.getElementById('inputNumPasses');
        if (inputPasses && res.num_passes !== undefined) {
            inputPasses.value = res.num_passes;
        }

        const inputDelay = document.getElementById('inputDelaySeconds');
        if (inputDelay && res.delay_seconds !== undefined) {
            inputDelay.value = res.delay_seconds;
        }

        const selectMode = document.getElementById('selectScanMode');
        if (selectMode && res.scan_mode) {
            selectMode.value = res.scan_mode;
        }

        updateAiStatusPill(!!res.is_connected, res.latency_ms);
    } catch (err) {
        console.warn('[AI Config] Không thể tải trạng thái AI:', err);
        updateAiStatusPill(false);
    }
}

async function pingAiEndpoint() {
    const inputUrl = document.getElementById('aiApiUrl');
    const hintEl = document.getElementById('aiPingResultHint');
    const btnPing = document.getElementById('btnAiPingTest');
    const url = (inputUrl?.value || '').trim();

    if (!url) {
        showToast('Vui lòng nhập đường dẫn API AI Service', 'warning');
        return;
    }

    updateAiStatusPill(false, null, true);
    if (btnPing) {
        btnPing.disabled = true;
        btnPing.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang test...';
    }

    try {
        const res = await SystemAPI.pingAiEndpoint(url);
        if (res.is_connected) {
            updateAiStatusPill(true, res.latency_ms);
            if (hintEl) {
                hintEl.innerHTML = `<span style="color: #16a34a; font-weight: 600;"><i class="fa-solid fa-circle-check"></i> Kết nối thành công tới ${escapeHtml(url)} (Độ trễ: ${res.latency_ms || '<50'} ms)</span>`;
            }
            showToast('✅ Kết nối máy chủ AI thành công!', 'success');
        } else {
            updateAiStatusPill(false);
            if (hintEl) {
                hintEl.innerHTML = `<span style="color: #dc2626; font-weight: 600;"><i class="fa-solid fa-circle-xmark"></i> Không thể kết nối tới ${escapeHtml(url)}. Lỗi: ${escapeHtml(res.error || 'Server không phản hồi')}</span>`;
            }
            showToast('⚠️ Không thể kết nối tới AI Microservice!', 'warning');
        }
    } catch (err) {
        updateAiStatusPill(false);
        if (hintEl) {
            hintEl.innerHTML = `<span style="color: #dc2626; font-weight: 600;"><i class="fa-solid fa-circle-xmark"></i> Lỗi kiểm tra kết nối: ${escapeHtml(err.message)}</span>`;
        }
        showToast('⚠️ Lỗi kết nối: ' + err.message, 'danger');
    } finally {
        if (btnPing) {
            btnPing.disabled = false;
            btnPing.innerHTML = '<i class="fa-solid fa-bolt"></i> Test Kết Nối';
        }
    }
}

async function saveAiSettings() {
    const inputUrl = document.getElementById('aiApiUrl');
    const inputPasses = document.getElementById('inputNumPasses');
    const inputDelay = document.getElementById('inputDelaySeconds');
    const selectMode = document.getElementById('selectScanMode');
    const btnSave = document.getElementById('btnSaveAiConfig');
    const url = (inputUrl?.value || '').trim();

    if (!url) {
        showToast('Vui lòng nhập đường dẫn API AI Service hợp lệ', 'warning');
        return;
    }

    const numPasses = parseInt(inputPasses?.value, 10) || 10;
    const delaySec = parseFloat(inputDelay?.value) || 10.0;
    const scanMode = selectMode?.value || 'round_robin';

    if (btnSave) {
        btnSave.disabled = true;
        btnSave.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';
    }

    try {
        await SystemAPI.updateAiEndpoint({
            api_url: url,
            num_passes: numPasses,
            delay_seconds: delaySec,
            scan_mode: scanMode
        });
        showToast(`✅ Đã lưu cấu hình AI (${numPasses} lần quét, nghỉ ${delaySec}s, ${scanMode === 'round_robin' ? 'xoay vòng' : 'tuần tự'})!`, 'success');
        await pingAiEndpoint();
    } catch (err) {
        showToast('❌ Không thể lưu cấu hình: ' + err.message, 'danger');
    } finally {
        if (btnSave) {
            btnSave.disabled = false;
            btnSave.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Lưu Cấu Hình';
        }
    }
}

function bindAiSettingsEvents() {
    const btnPing = document.getElementById('btnAiPingTest');
    const btnSave = document.getElementById('btnSaveAiConfig');

    btnPing?.addEventListener('click', pingAiEndpoint);
    btnSave?.addEventListener('click', saveAiSettings);
}

// =========================================================================
// MODAL TÀI LIỆU ĐẶC TẢ API (/api/predict)
// =========================================================================
export function openApiDocModal() {
    const modal = document.getElementById('modalApiDoc');
    if (modal) {
        modal.classList.add('active');
        modal.style.display = 'flex';
        modal.style.opacity = '1';
        modal.style.visibility = 'visible';
    }
}
window.openApiDocModal = openApiDocModal;

export function closeApiDocModal() {
    const modal = document.getElementById('modalApiDoc');
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }
}
window.closeApiDocModal = closeApiDocModal;

function setupApiDocModal() {
    const modal = document.getElementById('modalApiDoc');
    const btnOpen = document.getElementById('btnOpenApiDocModal');
    const btnClose = document.getElementById('btnCloseApiDocModal');
    const btnCopyJson = document.getElementById('btnCopyJsonSample');
    const btnCopySnippet = document.getElementById('btnCopySnippet');

    const btnCurl = document.getElementById('btnTabCurl');
    const btnPython = document.getElementById('btnTabPython');
    const btnJs = document.getElementById('btnTabJs');
    const codeSnippet = document.getElementById('codeSnippetContent');

    if (btnOpen) {
        btnOpen.addEventListener('click', openApiDocModal);
    }

    if (btnClose) {
        btnClose.addEventListener('click', closeApiDocModal);
    }

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeDocModal();
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.classList.contains('active')) {
                closeDocModal();
            }
        });
    }

    if (btnCopyJson) {
        btnCopyJson.addEventListener('click', async () => {
            const code = document.getElementById('codeApiDocSample')?.textContent || '';
            try {
                await navigator.clipboard.writeText(code);
                const orig = btnCopyJson.innerHTML;
                btnCopyJson.innerHTML = '<i class="fa-solid fa-check"></i> Đã chép!';
                setTimeout(() => { btnCopyJson.innerHTML = orig; }, 2000);
            } catch (e) {
                showToast('Không thể sao chép vào clipboard', 'warning');
            }
        });
    }

    const snippets = {
        curl: `curl -X POST "http://localhost:8010/api/predict" \\
  -H "accept: application/json" \\
  -H "Content-Type: multipart/form-data" \\
  -F "image=@data/samples/classroom.png;type=image/png"`,
        python: `import requests

url = "http://localhost:8010/api/predict"
with open("data/samples/classroom.png", "rb") as f:
    files = {"image": ("classroom.png", f, "image/png")}
    response = requests.post(url, files=files)

data = response.json()
print(f"Số lượng học sinh: {data['people_count']}")
for det in data["detections"]:
    if det["kept"]:
        print(f"Box #{det['box_id']}: bbox={det['bbox']}, depth={det['depth']:.3f}")`,
        js: `const formData = new FormData();
// fileInput là phần tử <input type="file">
formData.append("image", fileInput.files[0]);

const response = await fetch("http://localhost:8010/api/predict", {
    method: "POST",
    body: formData
});

const data = await response.json();
console.log("Số lượng học sinh đếm được:", data.people_count);`
    };

    function switchSnippetTab(tabKey) {
        [btnCurl, btnPython, btnJs].forEach((b) => b?.classList.remove('active'));
        if (tabKey === 'curl' && btnCurl) btnCurl.classList.add('active');
        if (tabKey === 'python' && btnPython) btnPython.classList.add('active');
        if (tabKey === 'js' && btnJs) btnJs.classList.add('active');
        if (codeSnippet) codeSnippet.textContent = snippets[tabKey] || snippets.curl;
    }

    btnCurl?.addEventListener('click', () => switchSnippetTab('curl'));
    btnPython?.addEventListener('click', () => switchSnippetTab('python'));
    btnJs?.addEventListener('click', () => switchSnippetTab('js'));

    if (btnCopySnippet) {
        btnCopySnippet.addEventListener('click', async () => {
            const code = codeSnippet?.textContent || '';
            try {
                await navigator.clipboard.writeText(code);
                const orig = btnCopySnippet.innerHTML;
                btnCopySnippet.innerHTML = '<i class="fa-solid fa-check"></i> Đã chép!';
                setTimeout(() => { btnCopySnippet.innerHTML = orig; }, 2000);
            } catch (e) {
                showToast('Không thể sao chép code vào clipboard', 'warning');
            }
        });
    }
}

// =========================================================================
// CHẠY THỬ NGHIỆM AI TRỰC TIẾP (LIVE TEST SANDBOX)
// =========================================================================
let liveTestState = {
    file: null,
    blob: null,
    samplePath: null
};

function setupLiveAiTest() {
    const fileInput = document.getElementById('aiTestFileInput');
    const btnSelectFile = document.getElementById('btnSelectCustomImage');
    const btnSample = document.getElementById('btnLoadSampleImage');
    const btnRun = document.getElementById('btnRunLiveAiTest');

    const placeholder = document.getElementById('liveTestPlaceholder');
    const resultImg = document.getElementById('liveTestResultImg');
    const spinner = document.getElementById('liveTestSpinner');
    const statusRow = document.getElementById('liveTestStatusRow');

    const peopleCountEl = document.getElementById('liveTestPeopleCount');
    const timingEl = document.getElementById('liveTestTiming');
    const totalEl = document.getElementById('liveTestTotal');
    const keptEl = document.getElementById('liveTestKept');
    const suppressedEl = document.getElementById('liveTestSuppressed');

    // 1. Tải ảnh tuỳ chỉnh từ máy tính
    btnSelectFile?.addEventListener('click', () => {
        fileInput?.click();
    });

    fileInput?.addEventListener('change', (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        liveTestState.file = file;
        liveTestState.blob = null;
        liveTestState.samplePath = null;

        const reader = new FileReader();
        reader.onload = (event) => {
            if (resultImg) {
                resultImg.src = event.target.result;
                resultImg.style.display = 'block';
            }
            if (placeholder) placeholder.style.display = 'none';
            if (statusRow) statusRow.style.display = 'none';
        };
        reader.readAsDataURL(file);
        showToast(`Đã chọn ảnh: ${file.name}`, 'info');
    });

    // 2. Dùng ảnh mẫu phòng học có sẵn
    btnSample?.addEventListener('click', async () => {
        try {
            if (btnSample) {
                btnSample.disabled = true;
                btnSample.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tải...';
            }
            const samplePath = 'dataset/samples/classroom_predict_sample.jpg';
            const sampleUrl = `/api/system/sample-frame-preview?path=${encodeURIComponent(samplePath)}`;

            const resp = await fetch(sampleUrl);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const blob = await resp.blob();

            liveTestState.file = null;
            liveTestState.blob = blob;
            liveTestState.samplePath = samplePath;

            const objectUrl = URL.createObjectURL(blob);
            if (resultImg) {
                resultImg.src = objectUrl;
                resultImg.style.display = 'block';
            }
            if (placeholder) placeholder.style.display = 'none';
            if (statusRow) statusRow.style.display = 'none';

            showToast('Đã tải ảnh mẫu phòng học chuẩn.', 'info');
        } catch (err) {
            showToast('Không thể tải ảnh mẫu: ' + err.message, 'danger');
        } finally {
            if (btnSample) {
                btnSample.disabled = false;
                btnSample.innerHTML = '<i class="fa-solid fa-image"></i> Dùng Ảnh Mẫu';
            }
        }
    });

    // 3. Bấm Chạy Thử Nghiệm AI
    btnRun?.addEventListener('click', async () => {
        // Nếu người dùng chưa chọn ảnh nào, tự động nạp ảnh mẫu
        if (!liveTestState.file && !liveTestState.blob && !liveTestState.samplePath) {
            btnSample?.click();
            await new Promise((r) => setTimeout(r, 600));
        }

        const formData = new FormData();
        if (liveTestState.file) {
            formData.append('file', liveTestState.file);
        } else if (liveTestState.blob) {
            formData.append('file', liveTestState.blob, 'classroom_sample.jpg');
        } else if (liveTestState.samplePath) {
            formData.append('sample_path', liveTestState.samplePath);
        } else {
            formData.append('sample_path', 'dataset/samples/classroom_predict_sample.jpg');
        }

        formData.append('visual_mode', 'dot');
        formData.append('check_mode', 'predict_api');

        if (spinner) spinner.style.display = 'flex';
        if (btnRun) btnRun.disabled = true;

        try {
            const data = await SystemAPI.testRawAI(formData);

            const count = data.valid_count ?? data.people_count ?? 0;
            const timeMs = data.inference_time_ms ?? '--';
            const total = data.total_detections ?? count;
            const kept = data.kept_count ?? count;
            const suppressed = data.suppressed_count ?? Math.max(0, total - count);

            if (peopleCountEl) peopleCountEl.textContent = count;
            if (timingEl) timingEl.textContent = `Thời gian: ${timeMs} ms`;
            if (totalEl) totalEl.textContent = total;
            if (keptEl) keptEl.textContent = kept;
            if (suppressedEl) suppressedEl.textContent = suppressed;
            if (statusRow) statusRow.style.display = 'block';

            const renderedSrc = data.annotated_b64 || data.roi_annotated_b64;
            if (renderedSrc && resultImg) {
                resultImg.src = renderedSrc;
                resultImg.style.display = 'block';
                if (placeholder) placeholder.style.display = 'none';
            }

            showToast(`🎉 Nhận diện thành công: ${count} học sinh!`, 'success');
        } catch (err) {
            showToast('❌ Thử nghiệm AI thất bại: ' + (err.message || err), 'danger');
        } finally {
            if (spinner) spinner.style.display = 'none';
            if (btnRun) btnRun.disabled = false;
        }
    });
}

// =========================================================================
// KHỞI CHẠY TRANG CÀI ĐẶT
// =========================================================================
function initSettingsPage() {
    try {
        setupTabs();
        loadUsers();
        bindFilterEvents();
        bindCreateForm();
        bindTableActions();
        bindEditModal();
        bindAiSettingsEvents();
        setupApiDocModal();
        setupLiveAiTest();
        // Nạp trạng thái kết nối AI lên badge
        loadAiSettings();
    } catch (e) {
        console.warn("[Settings] Lỗi khởi tạo trang cài đặt:", e);
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSettingsPage);
} else {
    initSettingsPage();
}
