/**
 * Configuration for THPT Điều Cải Attendance System
 * Centralized configuration management
 */

const CONFIG = {
  // API Base URL (adjust based on environment)
  API_BASE_URL: window.location.origin,

  // API Endpoints
  API_ENDPOINTS: {
    // Attendance
    ATTENDANCE_TRIGGER: '/api/attendance/trigger',
    ATTENDANCE_SESSIONS: '/api/attendance/sessions',
    ATTENDANCE_LATEST: '/api/attendance/latest',
    ATTENDANCE_DOWNLOAD: '/api/attendance/download-excel',
    ATTENDANCE_DELETE: (sessionId) => `/api/attendance/session/${sessionId}`,
    
    // Cameras
    CAMERAS_LIST: '/api/cameras',
    CAMERAS_ADD: '/api/cameras',
    CAMERAS_UPDATE: (cameraId) => `/api/cameras/${cameraId}`,
    CAMERAS_DELETE: (cameraId) => `/api/cameras/${cameraId}`,
    CAMERAS_SNAPSHOT: (cameraId) => `/api/cameras/${cameraId}/snapshot`,
    
    // Test Sources
    TEST_SOURCES_LIST: '/api/test-sources',
    TEST_SOURCES_ADD: '/api/test-sources',
    TEST_SOURCES_DELETE: (sourceId) => `/api/test-sources/${sourceId}`,
    
    // ROI Configuration
    ROI_LIST: '/api/roi',
    ROI_SAVE: '/api/roi',
    ROI_DELETE: (cameraId) => `/api/roi/${cameraId}`,
    
    // Reports
    REPORTS_QUERY: '/api/reports/query',
    REPORTS_IMAGE: (imageId) => `/api/reports/image/${imageId}`,
  },

  // Application Settings
  APP: {
    NAME: 'THPT Điều Cải - Hệ Thống Điểm Danh AI',
    SHORT_NAME: 'THPT ĐC',
    VERSION: '1.0.0',
    DEFAULT_SCAN_TIME: '06:45',
  },

  // UI Settings
  UI: {
    TOAST_DURATION: 3000, // milliseconds
    MODAL_ANIMATION_DURATION: 300, // milliseconds
    DEBOUNCE_DELAY: 300, // milliseconds
    TABLE_PAGE_SIZE: 20,
  },

  // Camera Settings
  CAMERA: {
    DEFAULT_TYPE: 'rtsp',
    SNAPSHOT_TIMEOUT: 10000, // milliseconds
    STREAM_RETRY_ATTEMPTS: 3,
  },

  // Validation Rules
  VALIDATION: {
    CAMERA_NAME: {
      MIN_LENGTH: 3,
      MAX_LENGTH: 100,
    },
    URL: {
      MAX_LENGTH: 500,
    },
  },

  // Feature Flags
  FEATURES: {
    ENABLE_AUTO_REFRESH: true,
    ENABLE_REAL_TIME_UPDATES: false,
    ENABLE_DEBUG_MODE: false,
  },
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CONFIG;
}
