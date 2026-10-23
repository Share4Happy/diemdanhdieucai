/**
 * Legacy compatibility shim: users.js -> settings.js
 * Chuyển tiếp toàn bộ xử lý sang settings.js để đảm bảo tương thích ngược
 */
export * from './settings.js';
import './settings.js';
