/**
 * Constants for THPT Điều Cải Attendance System
 * Shared constants used across the application
 */

const CONSTANTS = {
  // Camera Types
  CAMERA_TYPES: {
    RTSP: 'rtsp',
    HTTP: 'http',
    USB: 'usb',
  },

  // Camera Status
  CAMERA_STATUS: {
    ACTIVE: 'active',
    INACTIVE: 'inactive',
    ERROR: 'error',
  },

  // Attendance Status
  ATTENDANCE_STATUS: {
    PRESENT: 'present',
    ABSENT: 'absent',
    LATE: 'late',
    EXCUSED: 'excused',
  },

  // Modal Types
  MODAL_TYPES: {
    INFO: 'info',
    SUCCESS: 'success',
    WARNING: 'warning',
    ERROR: 'error',
    CONFIRM: 'confirm',
  },

  // Modal Sizes
  MODAL_SIZES: {
    SMALL: 'modal-sm',
    MEDIUM: 'modal-md',
    LARGE: 'modal-lg',
    EXTRA_LARGE: 'modal-xl',
    FULL: 'modal-full',
  },

  // Status Badge Colors
  BADGE_COLORS: {
    SUCCESS: 'success',
    WARNING: 'warning',
    DANGER: 'danger',
    INFO: 'info',
    NEUTRAL: 'neutral',
  },

  // ROI Zone Types
  ROI_ZONES: {
    GREEN: 'green',
    RED: 'red',
  },

  // Date Formats
  DATE_FORMATS: {
    FULL: 'DD/MM/YYYY HH:mm:ss',
    DATE_ONLY: 'DD/MM/YYYY',
    TIME_ONLY: 'HH:mm:ss',
    SHORT: 'DD/MM HH:mm',
  },

  // HTTP Status Codes
  HTTP_STATUS: {
    OK: 200,
    CREATED: 201,
    NO_CONTENT: 204,
    BAD_REQUEST: 400,
    UNAUTHORIZED: 401,
    FORBIDDEN: 403,
    NOT_FOUND: 404,
    INTERNAL_SERVER_ERROR: 500,
  },

  // Events
  EVENTS: {
    CAMERA_ADDED: 'camera:added',
    CAMERA_UPDATED: 'camera:updated',
    CAMERA_DELETED: 'camera:deleted',
    ATTENDANCE_TRIGGERED: 'attendance:triggered',
    ATTENDANCE_COMPLETED: 'attendance:completed',
    SESSION_DELETED: 'session:deleted',
    ROI_SAVED: 'roi:saved',
    ROI_DELETED: 'roi:deleted',
  },

  // Local Storage Keys
  STORAGE_KEYS: {
    THEME: 'thpt_dc_theme',
    LANGUAGE: 'thpt_dc_language',
    USER_PREFERENCES: 'thpt_dc_preferences',
    LAST_SCAN_TIME: 'thpt_dc_last_scan',
  },

  // Error Messages
  ERROR_MESSAGES: {
    NETWORK_ERROR: 'Lỗi kết nối mạng. Vui lòng kiểm tra lại.',
    SERVER_ERROR: 'Lỗi server. Vui lòng thử lại sau.',
    INVALID_INPUT: 'Dữ liệu nhập không hợp lệ.',
    REQUIRED_FIELD: 'Trường này là bắt buộc.',
    INVALID_URL: 'URL không hợp lệ.',
    CAMERA_NOT_FOUND: 'Không tìm thấy camera.',
    OPERATION_FAILED: 'Thao tác thất bại.',
  },

  // Success Messages
  SUCCESS_MESSAGES: {
    CAMERA_ADDED: 'Đã thêm camera thành công!',
    CAMERA_UPDATED: 'Đã cập nhật camera thành công!',
    CAMERA_DELETED: 'Đã xóa camera thành công!',
    ATTENDANCE_TRIGGERED: 'Đã bắt đầu quét điểm danh!',
    SESSION_DELETED: 'Đã xóa phiên điểm danh thành công!',
    ROI_SAVED: 'Đã lưu cấu hình ROI thành công!',
    OPERATION_SUCCESS: 'Thao tác thành công!',
  },

  // Validation Patterns
  PATTERNS: {
    URL: /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/,
    RTSP: /^rtsp:\/\/.+/,
    IP_ADDRESS: /^(\d{1,3}\.){3}\d{1,3}$/,
    EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  },

  // Time Constants
  TIME: {
    SECOND: 1000,
    MINUTE: 60 * 1000,
    HOUR: 60 * 60 * 1000,
    DAY: 24 * 60 * 60 * 1000,
  },

  // Scan Schedule
  SCAN_SCHEDULE: {
    DEFAULT_TIME: '06:45',
    DAYS: [1, 2, 3, 4, 5, 6], // Monday to Saturday
  },
};

// Freeze to prevent modifications
Object.freeze(CONSTANTS);

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CONSTANTS;
}
