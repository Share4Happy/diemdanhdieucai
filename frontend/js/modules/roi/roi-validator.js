/**
 * ROI Validator - Kiểm tra tính hợp lệ của vùng đa giác bàn học sinh & bục giảng
 */

export function validatePolygon(points, minPoints = 3) {
    if (!Array.isArray(points)) {
        return { valid: false, message: 'Dữ liệu đa giác không hợp lệ (không phải mảng).' };
    }
    if (points.length < minPoints) {
        return { valid: false, message: `Đa giác cần ít nhất ${minPoints} điểm neo để tạo vùng khép kín.` };
    }
    for (const pt of points) {
        if (!Array.isArray(pt) || pt.length < 2 || isNaN(pt[0]) || isNaN(pt[1])) {
            return { valid: false, message: 'Tọa độ điểm neo không hợp lệ.' };
        }
    }
    return { valid: true, message: 'Đa giác hợp lệ.' };
}

export function isPointInsidePolygon(point, polygon) {
    const [x, y] = point;
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const [xi, yi] = polygon[i];
        const [xj, yj] = polygon[j];
        const intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
        if (intersect) inside = !inside;
    }
    return inside;
}
