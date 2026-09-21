/**
 * =====================================================
 * SKELETON TEMPLATES - Reusable loading placeholders
 * =====================================================
 */

export const SkeletonTemplates = {
    /**
     * Table row skeleton
     */
    tableRow(columns = 5) {
        const cells = Array(columns).fill(null).map(() => 
            '<td class="skeleton-table-cell"><div class="skeleton skeleton-text"></div></td>'
        ).join('');
        return `<tr class="skeleton-table-row">${cells}</tr>`;
    },

    /**
     * Table skeleton with multiple rows
     */
    table(rows = 3, columns = 5) {
        return Array(rows).fill(null).map(() => this.tableRow(columns)).join('');
    },

    /**
     * Stat card skeleton
     */
    statCard() {
        return `
            <div class="skeleton-stat-card">
                <div class="skeleton skeleton-stat-icon"></div>
                <div class="skeleton-stat-content">
                    <div class="skeleton skeleton-stat-number"></div>
                    <div class="skeleton skeleton-stat-label"></div>
                </div>
            </div>
        `;
    },

    /**
     * Camera tile skeleton
     */
    cameraTile() {
        return `
            <div class="skeleton skeleton-camera-tile"></div>
        `;
    },

    /**
     * List item skeleton
     */
    listItem() {
        return `
            <div class="skeleton-list-item">
                <div class="skeleton skeleton-list-avatar"></div>
                <div class="skeleton-list-content">
                    <div class="skeleton skeleton-list-title"></div>
                    <div class="skeleton skeleton-list-subtitle"></div>
                </div>
            </div>
        `;
    },

    /**
     * Form field skeleton
     */
    formField() {
        return `
            <div class="skeleton-form-field">
                <div class="skeleton skeleton-form-label"></div>
                <div class="skeleton skeleton-form-input"></div>
            </div>
        `;
    },

    /**
     * Card skeleton
     */
    card() {
        return `<div class="skeleton skeleton-card"></div>`;
    },

    /**
     * Chart skeleton
     */
    chart() {
        return `<div class="skeleton skeleton-chart"></div>`;
    },

    /**
     * Text lines skeleton
     */
    textLines(count = 3) {
        return Array(count).fill(null).map(() => 
            '<div class="skeleton skeleton-text"></div>'
        ).join('');
    },

    /**
     * User table row skeleton (for users page)
     */
    userTableRow() {
        return `
            <tr class="skeleton-table-row">
                <td class="skeleton-table-cell">
                    <div class="skeleton skeleton-text" style="width: 150px;"></div>
                </td>
                <td class="skeleton-table-cell">
                    <div class="skeleton skeleton-text" style="width: 200px;"></div>
                </td>
                <td class="skeleton-table-cell">
                    <div class="skeleton skeleton-badge"></div>
                </td>
                <td class="skeleton-table-cell">
                    <div class="skeleton skeleton-badge"></div>
                </td>
                <td class="skeleton-table-cell cell-actions">
                    <div style="display: flex; gap: var(--space-2); justify-content: center;">
                        <div class="skeleton skeleton-button" style="width: 32px; height: 32px;"></div>
                        <div class="skeleton skeleton-button" style="width: 32px; height: 32px;"></div>
                    </div>
                </td>
            </tr>
        `;
    },

    /**
     * Reports table row skeleton (9 columns matching reports DB table)
     */
    reportTableRow() {
        return `
            <tr class="skeleton-table-row">
                <td class="skeleton-table-cell"><div class="skeleton" style="width: 90px; height: 16px;"></div></td>
                <td class="skeleton-table-cell"><div class="skeleton" style="width: 80px; height: 18px; border-radius: 4px;"></div></td>
                <td class="skeleton-table-cell"><div class="skeleton" style="width: 100px; height: 16px;"></div></td>
                <td class="skeleton-table-cell"><div class="skeleton" style="width: 32px; height: 16px;"></div></td>
                <td class="skeleton-table-cell"><div class="skeleton" style="width: 32px; height: 16px;"></div></td>
                <td class="skeleton-table-cell"><div class="skeleton" style="width: 32px; height: 16px;"></div></td>
                <td class="skeleton-table-cell"><div class="skeleton" style="width: 60px; height: 26px; border-radius: var(--radius-sm);"></div></td>
                <td class="skeleton-table-cell"><div class="skeleton" style="width: 60px; height: 26px; border-radius: var(--radius-sm);"></div></td>
                <td class="skeleton-table-cell"><div class="skeleton" style="width: 75px; height: 22px; border-radius: var(--radius-full);"></div></td>
            </tr>
        `;
    },

    /**
     * Excel files table row skeleton (5 columns matching reports Excel table)
     */
    excelTableRow() {
        return `
            <tr class="skeleton-table-row">
                <td class="skeleton-table-cell">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div class="skeleton" style="width: 18px; height: 18px; border-radius: 3px; flex-shrink: 0;"></div>
                        <div class="skeleton" style="width: 220px; height: 16px;"></div>
                    </div>
                </td>
                <td class="skeleton-table-cell"><div class="skeleton" style="width: 130px; height: 16px;"></div></td>
                <td class="skeleton-table-cell"><div class="skeleton" style="width: 60px; height: 16px;"></div></td>
                <td class="skeleton-table-cell"><div class="skeleton" style="width: 130px; height: 22px; border-radius: var(--radius-full);"></div></td>
                <td class="skeleton-table-cell"><div class="skeleton" style="width: 75px; height: 28px; border-radius: var(--radius-sm);"></div></td>
            </tr>
        `;
    },

    /**
     * Camera matrix card skeleton (matching .matrix-card 16:9 ratio and footer)
     */
    cameraMatrixCard() {
        return `
            <div class="matrix-card skeleton-matrix-card">
                <div class="matrix-card-screen skeleton">
                    <div class="matrix-osd-top">
                        <div class="skeleton" style="width: 44px; height: 18px; border-radius: 4px; background: rgba(255,255,255,0.3);"></div>
                        <div class="skeleton" style="width: 10px; height: 10px; border-radius: 50%; background: rgba(255,255,255,0.3);"></div>
                    </div>
                </div>
                <div class="matrix-card-footer">
                    <div style="flex: 1;">
                        <div class="skeleton" style="width: 80px; height: 14px; margin-bottom: 5px; border-radius: 3px;"></div>
                        <div class="skeleton" style="width: 55px; height: 11px; border-radius: 3px;"></div>
                    </div>
                    <div class="skeleton" style="width: 46px; height: 20px; border-radius: 999px;"></div>
                </div>
            </div>
        `;
    },

    /**
     * Camera grid skeleton
     */
    cameraGrid(count = 8) {
        return Array(count).fill(null).map(() => this.cameraMatrixCard()).join('');
    },

    /**
     * Camera matrix grid skeleton (alias for cameraGrid)
     */
    cameraMatrixGrid(count = 8) {
        return this.cameraGrid(count);
    },

    /**
     * Dashboard stats skeleton
     */
    dashboardStats(count = 4) {
        return Array(count).fill(null).map(() => this.statCard()).join('');
    },

    /**
     * Dashboard alert item skeleton
     */
    dashboardAlertItem() {
        return `
            <div class="skeleton-alert-item">
                <div class="skeleton" style="width: 20px; height: 20px; border-radius: 50%; flex-shrink: 0; margin-top: 2px;"></div>
                <div style="flex: 1;">
                    <div class="skeleton" style="width: 70%; height: 14px; margin-bottom: 6px;"></div>
                    <div class="skeleton" style="width: 40%; height: 12px;"></div>
                </div>
            </div>
        `;
    },

    /**
     * Dashboard alert list skeleton
     */
    dashboardAlertList(count = 2) {
        return Array(count).fill(null).map(() => this.dashboardAlertItem()).join('');
    },

    /**
     * KPI value placeholder
     */
    kpiValue(width = '80px') {
        return `<div class="skeleton skeleton-kpi-value" style="width: ${width};"></div>`;
    },

    /**
     * Message - centered loading indicator
     */
    centerMessage(message = 'Đang tải dữ liệu...', icon = 'fa-spinner fa-spin') {
        return `
            <div style="text-align: center; padding: var(--space-6); color: var(--text-muted);">
                <i class="fa-solid ${icon}"></i> ${message}
            </div>
        `;
    },

    /**
     * Empty state message
     */
    emptyState(message = 'Không có dữ liệu', icon = 'fa-inbox') {
        return `
            <div style="text-align: center; padding: var(--space-8); color: var(--text-muted);">
                <i class="fa-solid ${icon}" style="font-size: 3rem; margin-bottom: var(--space-4); opacity: 0.3;"></i>
                <p style="font-size: var(--text-lg); font-weight: var(--font-semibold);">${message}</p>
            </div>
        `;
    }
};

if (typeof window !== 'undefined') {
    window.SkeletonTemplates = SkeletonTemplates;
}

// Export for use in modules
export default SkeletonTemplates;
