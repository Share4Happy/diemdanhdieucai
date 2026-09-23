import os
import shutil
import zipfile
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from config.settings import settings
from config.logging_config import logger
from core.timezone_utils import get_now, get_app_timezone

class BackupService:
    """
    Dịch vụ Quản lý Sao lưu & Phục hồi Dữ liệu Hệ Thống (THPT Điều Cải):
    - Sao lưu an toàn CSDL SQLite (dùng SQLite Online Backup API tránh khóa file / hỏng dữ liệu).
    - Đóng gói file CSDL (.db), cấu hình thông báo (runtime JSON), và tùy chọn file Excel vào gói nén .zip.
    - Phục hồi an toàn: tự động tạo snapshot trước khi ghi đè, kiểm tra tính toàn vẹn.
    - Quản lý vòng đời backup: tải xuống, xóa, tự dọn dẹp các bản sao lưu cũ.
    """

    def __init__(self):
        self.backups_dir = settings.BACKUPS_DIR
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = settings.BASE_DIR / "database" / "attendance.db"

    def _get_sqlite_backup_copy(self, dest_db_path: Path) -> bool:
        """Sao lưu CSDL SQLite an toàn qua API sqlite3.backup để không ảnh hưởng phiên đang ghi."""
        if not self.db_path.exists():
            return False
        try:
            dest_db_path.parent.mkdir(parents=True, exist_ok=True)
            src_conn = sqlite3.connect(str(self.db_path))
            dest_conn = sqlite3.connect(str(dest_db_path))
            with dest_conn:
                src_conn.backup(dest_conn)
            dest_conn.close()
            src_conn.close()
            return True
        except Exception as e:
            logger.error(f"Lỗi khi copy SQLite qua backup API: {e}")
            try:
                shutil.copy2(str(self.db_path), str(dest_db_path))
                return True
            except Exception as e2:
                logger.error(f"Lỗi khi sao chép trực tiếp file db: {e2}")
                return False

    def create_backup(self, note: str = "Sao lưu thủ công", backup_type: str = "FULL", include_excel: bool = False) -> Dict[str, Any]:
        """
        Tạo gói sao lưu hệ thống:
        - Tên file dạng: backup_THPTDieuCai_YYYYMMDD_HHMMSS.zip
        - Chứa:
          + attendance.db (CSDL chính)
          + metadata.json (thông tin phiên, ghi chú, thống kê số lớp, phiên điểm danh)
          + notification_settings.json (nếu có)
          + zalo_runtime.json (nếu có)
          + [tùy chọn] Các file báo cáo excel gần nhất
        """
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        now = get_now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        date_readable = now.strftime("%d/%m/%Y %H:%M:%S")
        filename = f"backup_THPTDieuCai_{timestamp_str}.zip"
        zip_path = self.backups_dir / filename

        temp_db_copy = self.backups_dir / f"_temp_{timestamp_str}.db"
        if not self._get_sqlite_backup_copy(temp_db_copy):
            return {"success": False, "message": "Không thể sao lưu file Cơ sở dữ liệu attendance.db"}

        # Đọc thống kê nhanh từ CSDL backup
        total_sessions = 0
        total_details = 0
        total_classes = 0
        try:
            conn = sqlite3.connect(str(temp_db_copy))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM attendance_sessions")
            total_sessions = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM attendance_details")
            total_details = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM classrooms")
            total_classes = cur.fetchone()[0]
            conn.close()
        except Exception as e:
            logger.warning(f"Lỗi đọc thống kê CSDL backup: {e}")

        # Chuẩn bị metadata
        meta = {
            "backup_name": filename,
            "created_at": now.isoformat(),
            "created_at_readable": date_readable,
            "backup_type": backup_type,
            "note": note or "Bản sao lưu dữ liệu hệ thống",
            "stats": {
                "total_sessions": total_sessions,
                "total_details": total_details,
                "total_classes": total_classes,
                "db_size_bytes": temp_db_copy.stat().st_size if temp_db_copy.exists() else 0
            },
            "system": {
                "app_name": settings.APP_NAME,
                "app_version": settings.APP_VERSION,
                "timezone": "Asia/Ho_Chi_Minh (GMT+7)"
            }
        }

        # Nén vào file .zip
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(temp_db_copy, arcname="attendance.db")
                zf.writestr("metadata.json", json.dumps(meta, ensure_ascii=False, indent=2))

                # Đính kèm file cấu hình nếu có
                cfg_files = [
                    (settings.BASE_DIR / "config" / "notification_settings.json", "config/notification_settings.json"),
                    (settings.BASE_DIR / "config" / "zalo_runtime.json", "config/zalo_runtime.json"),
                ]
                for src_f, arc_name in cfg_files:
                    if src_f.exists():
                        zf.write(src_f, arcname=arc_name)

                # Tùy chọn gom 10 file Excel gần nhất
                if include_excel and settings.REPORTS_DIR.exists():
                    excel_files = sorted(settings.REPORTS_DIR.glob("*.xlsx"), key=lambda f: f.stat().st_mtime, reverse=True)[:10]
                    for ef in excel_files:
                        zf.write(ef, arcname=f"reports/{ef.name}")

            zip_size_bytes = zip_path.stat().st_size
            meta["zip_size_bytes"] = zip_size_bytes
            meta["zip_size_mb"] = round(zip_size_bytes / (1024 * 1024), 2)

            logger.info(f"Đã tạo bản sao lưu thành công: {filename} ({meta['zip_size_mb']} MB)")
            return {
                "success": True,
                "message": f"Tạo bản sao lưu thành công ({meta['zip_size_mb']} MB)",
                "data": meta
            }
        except Exception as e:
            logger.error(f"Lỗi khi đóng gói file backup zip: {e}")
            if zip_path.exists():
                zip_path.unlink(missing_ok=True)
            return {"success": False, "message": f"Lỗi đóng gói file nén backup: {str(e)}"}
        finally:
            if temp_db_copy.exists():
                try:
                    temp_db_copy.unlink(missing_ok=True)
                except Exception:
                    pass

    def list_backups(self) -> List[Dict[str, Any]]:
        """Lấy danh sách tất cả các bản sao lưu hiện có trong storage/backups/."""
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        results = []

        for p in self.backups_dir.glob("*.zip"):
            try:
                stat = p.stat()
                size_mb = round(stat.st_size / (1024 * 1024), 2)
                created_dt = datetime.fromtimestamp(stat.st_mtime, tz=get_app_timezone())
                created_str = created_dt.strftime("%d/%m/%Y %H:%M:%S")

                item = {
                    "filename": p.name,
                    "size_mb": size_mb,
                    "size_bytes": stat.st_size,
                    "created_at": created_str,
                    "created_timestamp": stat.st_mtime,
                    "note": "Bản sao lưu hệ thống",
                    "backup_type": "FULL",
                    "total_sessions": "--",
                    "total_details": "--"
                }

                # Đọc metadata nếu có bên trong zip
                try:
                    with zipfile.ZipFile(p, "r") as zf:
                        if "metadata.json" in zf.namelist():
                            with zf.open("metadata.json") as mf:
                                meta = json.loads(mf.read().decode("utf-8"))
                                item["note"] = meta.get("note", item["note"])
                                item["backup_type"] = meta.get("backup_type", item["backup_type"])
                                if "stats" in meta:
                                    item["total_sessions"] = meta["stats"].get("total_sessions", "--")
                                    item["total_details"] = meta["stats"].get("total_details", "--")
                                if "created_at_readable" in meta:
                                    item["created_at"] = meta["created_at_readable"]
                except Exception:
                    pass

                results.append(item)
            except Exception as e:
                logger.warning(f"Lỗi khi đọc thông tin backup {p.name}: {e}")

        # Sắp xếp mới nhất lên đầu
        results.sort(key=lambda x: x.get("created_timestamp", 0), reverse=True)
        return results

    def restore_backup(self, filename: str) -> Dict[str, Any]:
        """
        Phục hồi hệ thống từ bản sao lưu đã có trong thư mục storage/backups/:
        1. Kiểm tra tính toàn vẹn của file zip và file CSDL bên trong.
        2. Tự động tạo 1 bản snapshot cứu hộ khẩn cấp của CSDL hiện tại.
        3. Ghi đè file attendance.db và các file cấu hình.
        """
        zip_path = self.backups_dir / filename
        if not zip_path.exists():
            return {"success": False, "message": "File bản sao lưu không tồn tại."}

        # 1. Kiểm tra bên trong zip
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                if "attendance.db" not in names:
                    return {"success": False, "message": "Bản sao lưu không hợp lệ (thiếu file attendance.db)."}
        except Exception as e:
            return {"success": False, "message": f"File zip bị hỏng: {str(e)}"}

        # 2. Tạo snapshot cứu hộ trước khi ghi đè
        now = get_now()
        emergency_snap = self.backups_dir / f"_pre_restore_snapshot_{now.strftime('%Y%m%d_%H%M%S')}.db"
        if self.db_path.exists():
            self._get_sqlite_backup_copy(emergency_snap)

        # 3. Phục hồi
        try:
            temp_extract = self.backups_dir / f"_extract_{now.strftime('%Y%m%d_%H%M%S')}"
            temp_extract.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(temp_extract)

            extracted_db = temp_extract / "attendance.db"
            if not extracted_db.exists():
                return {"success": False, "message": "Không tìm thấy file CSDL trong dữ liệu giải nén."}

            # Kiểm tra CSDL giải nén có mở được không
            test_conn = sqlite3.connect(str(extracted_db))
            test_cur = test_conn.cursor()
            test_cur.execute("SELECT COUNT(*) FROM classrooms")
            class_count = test_cur.fetchone()[0]
            test_conn.close()

            # Ghi đè an toàn vào database/attendance.db
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(extracted_db), str(self.db_path))

            # Khôi phục file cấu hình nếu có trong gói
            for rel_cfg in ["config/notification_settings.json", "config/zalo_runtime.json"]:
                extracted_cfg = temp_extract / rel_cfg
                target_cfg = settings.BASE_DIR / rel_cfg
                if extracted_cfg.exists():
                    target_cfg.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(extracted_cfg), str(target_cfg))

            # Dọn thư mục tạm giải nén
            shutil.rmtree(temp_extract, ignore_errors=True)

            logger.info(f"Phục hồi thành công hệ thống từ bản sao lưu: {filename}")
            return {
                "success": True,
                "message": f"Đã phục hồi dữ liệu thành công từ bản sao lưu ({class_count} lớp học).",
                "emergency_snapshot": emergency_snap.name if emergency_snap.exists() else None
            }
        except Exception as e:
            logger.error(f"Lỗi nghiêm trọng khi phục hồi: {e}")
            # Nếu lỗi và có bản snapshot khẩn cấp, khôi phục lại
            if emergency_snap.exists():
                try:
                    shutil.copy2(str(emergency_snap), str(self.db_path))
                    logger.info("Đã rollback lại trạng thái CSDL trước khi phục hồi lỗi.")
                except Exception:
                    pass
            return {"success": False, "message": f"Lỗi khi khôi phục dữ liệu: {str(e)}"}

    def delete_backup(self, filename: str) -> Dict[str, Any]:
        """Xóa file bản sao lưu."""
        # Chặn path traversal
        clean_name = Path(filename).name
        target = self.backups_dir / clean_name
        if not target.exists():
            return {"success": False, "message": "File bản sao lưu không tồn tại."}
        try:
            target.unlink()
            return {"success": True, "message": f"Đã xóa bản sao lưu {clean_name}"}
        except Exception as e:
            return {"success": False, "message": f"Lỗi xóa file: {str(e)}"}

    def cleanup_old_backups(self, keep_count: int = 15):
        """Giữ lại tối đa keep_count bản sao lưu gần nhất, dọn các bản cũ hơn để tiết kiệm dung lượng đĩa."""
        backups = self.list_backups()
        if len(backups) > keep_count:
            to_delete = backups[keep_count:]
            for b in to_delete:
                try:
                    f = self.backups_dir / b["filename"]
                    if f.exists():
                        f.unlink()
                        logger.info(f"Tự động dọn dẹp bản sao lưu cũ: {b['filename']}")
                except Exception:
                    pass

backup_service = BackupService()
