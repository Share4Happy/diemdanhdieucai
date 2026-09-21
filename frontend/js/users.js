import { AuthAPI, showToast } from './api.js';
import SkeletonTemplates from './components/skeleton-templates.js';

let usersCache = [];

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

async function loadUsers() {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;

    // Show skeleton loading
    tbody.innerHTML = SkeletonTemplates.userTableRow().repeat(3);

    try {
        const data = await AuthAPI.listUsers();
        usersCache = data.users || [];
        if (!usersCache.length) {
            tbody.innerHTML = `<tr><td colspan="5">${SkeletonTemplates.emptyState('Chưa có tài khoản', 'fa-users')}</td></tr>`;
            return;
        }
        const currentId = window.currentUser?.id;
        tbody.innerHTML = usersCache.map((u) => {
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
        }).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: var(--space-6); color: var(--danger);">${escapeHtml(err.message)}</td></tr>`;
    }
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
        btn.disabled = true;
        try {
            await AuthAPI.createUser(payload);
            showToast('Đã tạo tài khoản mới thành công.', 'success');
            form.reset();
            closeCreateModal();
            await loadUsers();
        } catch (err) {
            showToast(err.message || 'Không tạo được tài khoản.', 'danger');
        } finally {
            btn.disabled = false;
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
        btn.disabled = true;
        try {
            await AuthAPI.updateUser(id, payload);
            showToast('Đã cập nhật thông tin tài khoản.', 'success');
            closeEditModal();
            await loadUsers();
        } catch (err) {
            showToast(err.message || 'Không cập nhật được tài khoản.', 'danger');
        } finally {
            btn.disabled = false;
        }
    });
}

loadUsers();
bindCreateForm();
bindTableActions();
bindEditModal();
