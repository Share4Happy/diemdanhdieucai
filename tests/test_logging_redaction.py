import logging
import pytest
from config.logging_config import RedactFilter

def test_redact_filter_masks_rtsp_credentials():
    logger = logging.getLogger("test_redact")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # Capture log output
    class ListHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.records = []

        def emit(self, record):
            self.records.append(self.format(record))

    handler = ListHandler()
    handler.addFilter(RedactFilter())
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    # Test RTSP URL with username and password
    test_msg = "Kết nối tới camera: rtsp://admin:Dieucai1982@192.168.1.200:554/Streaming/Channels/101"
    logger.info(test_msg)

    # Test password in parameter
    test_pwd = "Xác thực với password=MySecretPass123 và token=eyJhbGciOiJIUzI1NiJ9"
    logger.info(test_pwd)

    assert len(handler.records) == 2
    # Verify RTSP password was redacted
    assert "Dieucai1982" not in handler.records[0]
    assert "admin:***" in handler.records[0] or "admin:****" in handler.records[0] or "***@" in handler.records[0]

    # Verify secret / token was redacted
    assert "MySecretPass123" not in handler.records[1]
