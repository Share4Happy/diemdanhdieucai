"""
=============================================================================
BỘ QUẢN LÝ NGUỒN CAMERA & BÀN GIAO ĐẦU GHI NVR (CAMERA SOURCE MANAGER)
Trường THPT Điều Cải - Hệ Thống Điểm Danh AI
=============================================================================
Chức năng:
1. Quản lý linh hoạt nguồn camera:
   - MOCK_IMAGE: Chế độ thử nghiệm với thư mục ảnh tự chọn (camera/, dataset/samples, hoặc đường dẫn máy tính bất kỳ)
   - REAL_NVR: Chế độ bàn giao thực tế dùng luồng RTSP từ Đầu Ghi NVR
2. Cho phép người dùng tùy chọn hoặc nhập bất kỳ thư mục chứa ảnh camera nào.
3. Cho phép chuyển đổi đồng loạt toàn bộ 30 camera chỉ với 1 click.
4. Tự động hóa xóa / dọn dẹp thư mục ảnh test khi bàn giao cho khách.
5. Đảm bảo hệ thống KHÔNG BAO GIỜ bị lỗi nếu thư mục ảnh test bị xóa.
=============================================================================
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import quote
from sqlalchemy.orm import Session

from config.settings import settings
from config.logging_config import logger
from database.models import Classroom, ROIPolygon

DEFAULT_MOCK_FOLDER = settings.BASE_DIR / "camera"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

def natural_sort_key(s: str):
    """Sắp xếp chuỗi theo số tự nhiên (1.jpg, 2.jpg ... 10.jpg thay vì 1, 10, 2)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


class CameraSourceManager:
    """Quản lý chuyển đổi giữa Chế độ Giả lập Ảnh mẫu (Test) và Đầu Ghi NVR Thật (Bàn giao)."""

    @classmethod
    def resolve_folder_path(cls, folder_str: Optional[str]) -> Path:
        """Chuẩn hóa đường dẫn thư mục: hỗ trợ đường dẫn tương đối dự án hoặc đường dẫn tuyệt đối máy tính."""
        if not folder_str or not str(folder_str).strip():
            return DEFAULT_MOCK_FOLDER
        clean = str(folder_str).strip().replace("\\", "/")
        p = Path(clean)
        if p.is_absolute():
            return p
        return settings.BASE_DIR / clean

    @classmethod
    def get_image_files(cls, folder_path: Path) -> List[Path]:
        """Lấy danh sách tất cả file ảnh trong thư mục và sắp xếp tự nhiên."""
        if not folder_path.exists() or not folder_path.is_dir():
            return []
        files = []
        try:
            for item in folder_path.iterdir():
                if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS:
                    files.append(item)
            files.sort(key=lambda x: natural_sort_key(x.name))
        except Exception as e:
            logger.warning(f"Lỗi khi đọc file trong thư mục {folder_path}: {e}")
        return files

    @classmethod
    def inspect_folder(cls, folder_str: str) -> Dict[str, Any]:
        """Kiểm tra sự tồn tại và phân tích số lượng ảnh trong thư mục chỉ định."""
        p = cls.resolve_folder_path(folder_str)
        exists = p.exists()
        is_dir = p.is_dir() if exists else False
        files = cls.get_image_files(p) if is_dir else []

        # Hiển thị đường dẫn đẹp cho người dùng
        try:
            display_path = p.relative_to(settings.BASE_DIR).as_posix()
        except ValueError:
            display_path = str(p)

        if not exists:
            message = f"Thư mục không tồn tại: {display_path}"
        elif not is_dir:
            message = f"Đường dẫn không phải là thư mục: {display_path}"
        elif len(files) == 0:
            message = f"Thư mục '{display_path}' tồn tại nhưng chưa có file ảnh (.jpg, .png, .jpeg)"
        else:
            message = f"Thư mục '{display_path}' sẵn sàng với {len(files)} ảnh camera."

        return {
            "exists": exists,
            "is_dir": is_dir,
            "folder_path": folder_str,
            "resolved_path": str(p),
            "display_path": display_path,
            "images_count": len(files),
            "sample_files": [f.name for f in files[:8]],
            "message": message
        }

    @classmethod
    def get_source_status(cls, db: Session, folder_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Kiểm tra trạng thái nguồn của toàn bộ camera trong hệ thống.
        Tự động nhận diện thư mục ảnh đang được dùng và trả về chi tiết.
        """
        classrooms = db.query(Classroom).order_by(Classroom.id).all()
        total_cams = len(classrooms)

        mock_count = 0
        rtsp_count = 0
        webcam_count = 0
        other_count = 0
        detected_folder = "camera"

        for c in classrooms:
            url = (c.rtsp_url or "").strip()
            url_lower = url.lower()
            if any(url_lower.endswith(ext) for ext in IMAGE_EXTENSIONS):
                mock_count += 1
                # Lấy thư mục cha của ảnh làm detected_folder
                try:
                    p = Path(url)
                    if p.parent and str(p.parent) != ".":
                        detected_folder = str(p.parent).replace("\\", "/")
                except Exception:
                    pass
            elif url_lower.startswith("rtsp://"):
                rtsp_count += 1
            elif url.isdigit():
                webcam_count += 1
            else:
                other_count += 1

        # Xác định chế độ chủ đạo
        if rtsp_count > mock_count and rtsp_count > webcam_count:
            current_mode = "REAL_NVR"
            mode_display = "Đầu Ghi NVR Thực Tế (Production)"
        elif mock_count > 0:
            current_mode = "MOCK_IMAGE"
            mode_display = "Ảnh Mẫu Thử Nghiệm (Test Mode)"
        elif webcam_count > 0:
            current_mode = "WEBCAM"
            mode_display = "Webcam Máy Tính"
        else:
            current_mode = "UNKNOWN"
            mode_display = "Tùy Chỉnh Hỗn Hợp"

        # Kiểm tra chi tiết thư mục cần kiểm tra
        target_folder = folder_str if folder_str else detected_folder
        folder_info = cls.inspect_folder(target_folder)

        dvr_host = getattr(settings, "DVR_HOST", getattr(settings, "NVR_HOST", "192.168.10.200"))
        dvr_port = getattr(settings, "DVR_PORT", getattr(settings, "NVR_PORT", 554))
        dvr_user = getattr(settings, "DVR_USER", getattr(settings, "NVR_USER", "admin"))
        dvr_pass = getattr(settings, "DVR_PASSWORD", getattr(settings, "NVR_PASSWORD", "DieuCai@2026"))

        return {
            "current_mode": current_mode,
            "mode_display": mode_display,
            "total_cameras": total_cams,
            "mock_cameras_count": mock_count,
            "rtsp_cameras_count": rtsp_count,
            "webcam_cameras_count": webcam_count,
            "other_cameras_count": other_count,
            "active_mock_folder": detected_folder,
            "folder_details": folder_info,
            "nvr_config": {
                "host": dvr_host,
                "port": dvr_port,
                "user": dvr_user,
                "password": dvr_pass,
                "channel_start": 1,
                "channel_end": total_cams
            }
        }

    @classmethod
    def switch_to_real_nvr(
        cls,
        db: Session,
        nvr_ip: str,
        nvr_port: int = 554,
        nvr_user: str = "admin",
        nvr_pass: str = "DieuCai@2026",
        nvr_brand: str = "DAHUA",
        channel_start: int = 1,
        cleanup_mock_images: bool = False,
        mock_folder: str = "camera"
    ) -> Dict[str, Any]:
        """
        Chuyển đổi toàn bộ camera sang luồng RTSP của Đầu Ghi NVR thực tế.
        Dành cho giai đoạn BÀN GIAO KHÁCH HÀNG.
        """
        nvr_ip = nvr_ip.strip()
        nvr_user = nvr_user.strip()
        nvr_pass = nvr_pass.strip()
        encoded_pass = quote(nvr_pass)

        classrooms = db.query(Classroom).order_by(Classroom.id).all()
        if not classrooms:
            return {"success": False, "message": "Không tìm thấy camera nào trong CSDL để cấu hình!"}

        updated_list = []
        for idx, cls_obj in enumerate(classrooms):
            ch = channel_start + idx
            # Tạo đường dẫn RTSP chuẩn hóa theo từng hãng đầu ghi
            if nvr_brand.upper() == "HIKVISION":
                rtsp_url = f"rtsp://{nvr_user}:{encoded_pass}@{nvr_ip}:{nvr_port}/Streaming/Channels/{ch}01"
            elif nvr_brand.upper() == "KBVISION":
                rtsp_url = f"rtsp://{nvr_user}:{encoded_pass}@{nvr_ip}:{nvr_port}/cam/realmonitor?channel={ch}&subtype=0"
            else:  # Mặc định DAHUA (THPT Điều Cải sử dụng)
                rtsp_url = f"rtsp://{nvr_user}:{encoded_pass}@{nvr_ip}:{nvr_port}/cam/realmonitor?channel={ch}&subtype=0"

            cls_obj.rtsp_url = rtsp_url
            cls_obj.relay_ip = nvr_ip
            cls_obj.channel_number = ch
            updated_list.append({"id": cls_obj.id, "name": cls_obj.name, "rtsp_url": rtsp_url})

        # Lưu cài đặt NVR vào cấu hình runtime
        settings.DVR_HOST = nvr_ip
        settings.DVR_PORT = nvr_port
        settings.DVR_USER = nvr_user
        settings.DVR_PASSWORD = nvr_pass

        # Cập nhật file .env để lưu vĩnh viễn
        cls._update_env_file({
            "DVR_HOST": nvr_ip,
            "DVR_PORT": str(nvr_port),
            "DVR_USER": nvr_user,
            "DVR_PASSWORD": nvr_pass
        })

        db.commit()

        # Dọn dẹp thư mục ảnh test nếu người dùng yêu cầu
        cleaned_up = False
        target_mock_dir = cls.resolve_folder_path(mock_folder)
        if cleanup_mock_images and target_mock_dir.exists():
            try:
                shutil.rmtree(target_mock_dir)
                cleaned_up = True
                logger.info(f"[CAMERA-DEPLOY]: Đã xóa sạch thư mục ảnh test {target_mock_dir} theo yêu cầu bàn giao.")
            except Exception as e:
                logger.warning(f"[CAMERA-DEPLOY]: Không thể xóa thư mục {target_mock_dir}: {e}")

        logger.info(
            f"[CAMERA-DEPLOY]: Đã chuyển đổi thành công {len(updated_list)} camera sang Đầu Ghi NVR {nvr_brand} ({nvr_ip}:{nvr_port})."
        )

        return {
            "success": True,
            "message": f"Đã chuyển đổi thành công {len(updated_list)} camera sang luồng RTSP của Đầu Ghi NVR ({nvr_ip})!",
            "brand": nvr_brand,
            "nvr_ip": nvr_ip,
            "updated_count": len(updated_list),
            "cleanup_mock_images": cleaned_up,
            "current_mode": "REAL_NVR"
        }

    @classmethod
    def switch_to_mock_images(
        cls,
        db: Session,
        folder_path: str = "camera",
        channel_start: int = 1
    ) -> Dict[str, Any]:
        """
        Chuyển đổi toàn bộ camera sang chế độ Thử Nghiệm với thư mục ảnh người dùng chọn.
        Hỗ trợ bất kỳ thư mục nào (ví dụ 'camera', 'dataset/samples', hoặc 'D:/AnhTest').
        """
        target_dir = cls.resolve_folder_path(folder_path)
        
        # Nếu là thư mục mặc định camera mà chưa tồn tại thì tạo mới
        if not target_dir.exists():
            if str(folder_path).strip().lower() in ("camera", "camera/"):
                target_dir.mkdir(parents=True, exist_ok=True)
            else:
                return {
                    "success": False,
                    "message": f"Thư mục '{folder_path}' không tồn tại trên máy tính! Vui lòng kiểm tra lại đường dẫn."
                }

        image_files = cls.get_image_files(target_dir)
        if not image_files:
            return {
                "success": False,
                "message": f"Thư mục '{folder_path}' không chứa file ảnh nào (.jpg, .png, .jpeg). Vui lòng thêm ảnh vào thư mục."
            }

        classrooms = db.query(Classroom).order_by(Classroom.id).all()
        if not classrooms:
            return {"success": False, "message": "Không có camera nào trong hệ thống!"}

        # Lưu ảnh mới nhất vào thư mục latest để UI cập nhật ngay
        latest_dir = settings.CAPTURES_DIR / "latest"
        latest_dir.mkdir(parents=True, exist_ok=True)

        # Xây dựng từ điển tra cứu nhanh theo số thứ tự kênh (1.jpg, 2.jpg ...)
        channel_file_map: Dict[int, Path] = {}
        for f in image_files:
            stem = f.stem.lower()
            # Tìm số trong tên file
            nums = re.findall(r'\d+', stem)
            if nums:
                channel_file_map[int(nums[0])] = f

        updated_list = []
        for idx, cls_obj in enumerate(classrooms):
            ch = channel_start + idx
            
            # Ưu tiên 1: file có số trùng số kênh (ví dụ 1.jpg cho kênh 1)
            chosen_file = channel_file_map.get(ch)
            # Ưu tiên 2: chia theo modulo số lượng file
            if not chosen_file:
                chosen_file = image_files[idx % len(image_files)]

            # Tạo đường dẫn lưu trong CSDL: tương đối nếu nằm trong thư mục dự án
            try:
                rel_path = chosen_file.relative_to(settings.BASE_DIR).as_posix()
            except ValueError:
                rel_path = str(chosen_file)

            cls_obj.rtsp_url = rel_path
            cls_obj.channel_number = ch

            # Copy đồng bộ ảnh sang latest để xem trước
            try:
                dest_latest = latest_dir / f"Lop_{cls_obj.id}.jpg"
                shutil.copy2(chosen_file, dest_latest)
            except Exception as e:
                logger.debug(f"Không thể copy ảnh latest cho lớp {cls_obj.id}: {e}")

            updated_list.append({"id": cls_obj.id, "name": cls_obj.name, "rtsp_url": rel_path})

        db.commit()
        logger.info(f"[CAMERA-SOURCE]: Đã liên kết {len(updated_list)} camera với thư mục ảnh '{folder_path}' ({len(image_files)} ảnh).")

        return {
            "success": True,
            "message": f"Đã kích hoạt Chế Độ Thử Nghiệm! {len(updated_list)} camera đã được liên kết với thư mục '{folder_path}' ({len(image_files)} ảnh).",
            "folder_path": folder_path,
            "images_count": len(image_files),
            "updated_count": len(updated_list),
            "current_mode": "MOCK_IMAGE"
        }

    @classmethod
    def cleanup_mock_folder(cls, folder_path: str = "camera") -> Dict[str, Any]:
        """Xóa hoàn toàn thư mục ảnh test giả lập sau khi đã bàn giao đầu ghi thực tế."""
        target_dir = cls.resolve_folder_path(folder_path)
        if not target_dir.exists():
            return {"success": True, "message": f"Thư mục '{folder_path}' đã được xóa trước đó (không tồn tại)."}

        try:
            shutil.rmtree(target_dir)
            logger.info(f"[CAMERA-SOURCE]: Đã dọn dẹp sạch thư mục ảnh test {target_dir}.")
            return {"success": True, "message": f"Đã xóa sạch thư mục '{folder_path}' thành công!"}
        except Exception as e:
            return {"success": False, "message": f"Lỗi khi xóa thư mục: {str(e)}"}

    @classmethod
    def _update_env_file(cls, key_values: Dict[str, str]):
        """Cập nhật các biến cấu hình vào file .env an toàn."""
        env_path = settings.BASE_DIR / ".env"
        if not env_path.exists():
            return
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
            new_lines = []
            seen_keys = set()
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k, _ = stripped.split("=", 1)
                    k = k.strip()
                    if k in key_values:
                        new_lines.append(f"{k}={key_values[k]}")
                        seen_keys.add(k)
                        continue
                new_lines.append(line)

            for k, v in key_values.items():
                if k not in seen_keys:
                    new_lines.append(f"{k}={v}")

            env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        except Exception as e:
            logger.warning(f"Lỗi cập nhật .env: {e}")

camera_source_manager = CameraSourceManager()
