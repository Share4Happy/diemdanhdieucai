"""
=============================================================================
HUẤN LUYỆN AI YOLO VỚI DỮ LIỆU CAMERA THỰC TẾ (THPT ĐIỀU CẢI)
Tập dữ liệu: studenthead1.v1-1.yolo26 (Trích xuất từ Camera 1 & Camera 2)
=============================================================================
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

# Đảm bảo đường dẫn gốc dự án có trong sys.path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BASE_DIR = PROJECT_ROOT
MODELS_DIR = BASE_DIR / "models"
DATASET_DIR = BASE_DIR / "dataset"
RUNS_DIR = BASE_DIR / "runs" / "train"

MODELS_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR.mkdir(parents=True, exist_ok=True)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import torch
from ultralytics import YOLO

def parse_args():
    default_checkpoint = str(MODELS_DIR / "classroom_best.pt")
    if not Path(default_checkpoint).exists():
        if (MODELS_DIR / "yolo26m.pt").exists():
            default_checkpoint = str(MODELS_DIR / "yolo26m.pt")
        elif (MODELS_DIR / "yolo26s.pt").exists():
            default_checkpoint = str(MODELS_DIR / "yolo26s.pt")
        else:
            default_checkpoint = "yolo26m.pt"

    default_data = str(DATASET_DIR / "datatraining.yaml")
    if not Path(default_data).exists():
        default_data = str(DATASET_DIR / "studenthead_real.yaml")

    parser = argparse.ArgumentParser(description="Huấn luyện mô hình YOLO trên dữ liệu camera thực tế THPT Điều Cải")
    parser.add_argument("--data", type=str, default=default_data, help="Đường dẫn file cấu hình dataset.yaml")
    parser.add_argument("--model", type=str, default=default_checkpoint, help="Mô hình checkpoint xuất phát")
    parser.add_argument("--epochs", type=int, default=30, help="Số lượt huấn luyện (epochs)")
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước phân giải ảnh huấn luyện")
    parser.add_argument("--batch", type=int, default=4, help="Kích thước batch (khuyến nghị 4 cho GPU 4GB VRAM)")
    parser.add_argument("--device", type=str, default="", help="Thiết bị: '0' (GPU CUDA) hoặc 'cpu'")
    parser.add_argument("--name", type=str, default="dieucai_datatraining", help="Tên thư mục output trong runs/train")
    parser.add_argument("--workers", type=int, default=2, help="Số worker nạp dữ liệu (mặc định 2)")
    parser.add_argument("--no-sync", action="store_true", help="Không tự động chép đè vào models/classroom_best.pt")
    parser.add_argument("--resume", action="store_true", help="Tiếp tục huấn luyện từ checkpoint last.pt đã lưu")
    return parser.parse_args()

def backup_current_model():
    """Tự động sao lưu mô hình hiện tại trước khi huấn luyện đè."""
    src = MODELS_DIR / "classroom_best.pt"
    backup = MODELS_DIR / "classroom_best_prev.pt"
    if src.exists():
        shutil.copy2(str(src), str(backup))
        print(f"[+] Đã tạo bản sao lưu mô hình cũ: {backup.name}")

def main():
    args = parse_args()

    print("=================================================================")
    print("   HUẤN LUYỆN AI ĐIỂM DANH BẰNG DỮ LIỆU CAMERA THỰC TẾ")
    print("   Trường THPT Điều Cải - Dataset: studenthead1.v1-1.yolo26")
    print("=================================================================")

    # 1. Kiểm tra phần cứng
    if not args.device:
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            device = "0"
            print(f"[*] Phát hiện GPU CUDA: {device_name} (Sử dụng device: 0)")
        else:
            device = "cpu"
            print("[!] Không tìm thấy GPU CUDA. Huấn luyện sẽ chạy trên CPU.")
    else:
        device = args.device
        print(f"[*] Thiết bị được chọn: {device}")

    # 2. Kiểm tra file cấu hình dataset
    yaml_path = Path(args.data)
    if not yaml_path.exists():
        print(f"[LỖI] Không tìm thấy file cấu hình: {yaml_path}")
        return

    # 3. Sao lưu checkpoint cũ
    backup_current_model()

    # 4. Tải mô hình nền tảng
    if args.resume:
        last_ckpt = RUNS_DIR / args.name / "weights" / "last.pt"
        if not last_ckpt.exists():
            print(f"[LỖI] Không tìm thấy checkpoint last.pt tại: {last_ckpt}")
            print("Vui lòng kiểm tra lại thư mục runs hoặc huấn luyện từ đầu.")
            return
        print(f"[*] Tiếp tục huấn luyện từ checkpoint gần nhất: {last_ckpt}")
        try:
            model = YOLO(str(last_ckpt))
        except Exception as e:
            print(f"[LỖI] Không thể nạp checkpoint {last_ckpt}: {e}")
            return
    else:
        print(f"[*] Đang tải mô hình checkpoint xuất phát: {args.model}...")
        try:
            model = YOLO(args.model)
        except Exception as e:
            print(f"[LỖI] Không thể nạp checkpoint {args.model}: {e}")
            return

    # 5. Khởi động huấn luyện
    if not args.resume:
        print("\n[*] THIẾT LẬP HUẤN LUYỆN:")
        print(f" - Dataset config: {yaml_path}")
        print(f" - Số epochs:      {args.epochs}")
        print(f" - Phân giải ảnh:  {args.imgsz}x{args.imgsz}")
        print(f" - Batch size:     {args.batch}")
        print(f" - Device:         {device}")
        print(f" - Run Name:       {args.name}")
        print(f" - Output dir:     {RUNS_DIR / args.name}\n")
    else:
        print(f"\n[*] Đang phục hồi trạng thái từ '{args.name}' và tiếp tục huấn luyện...")
        print(f" - Device:         {device}\n")

    try:
        if args.resume:
            results = model.train(resume=True, device=device)
        else:
            results = model.train(
                data=str(yaml_path),
                epochs=args.epochs,
                imgsz=args.imgsz,
                batch=args.batch,
                device=device,
                project=str(RUNS_DIR),
                name=args.name,
                exist_ok=True,
                pretrained=True,
                optimizer="AdamW",
                lr0=0.001,
                augment=True,
                single_cls=True,
                workers=args.workers,
                plots=True,
                verbose=True
            )

        # 6. Xuất và đồng bộ mô hình tối ưu
        best_weight = RUNS_DIR / args.name / "weights" / "best.pt"
        if best_weight.exists():
            if not args.no_sync:
                target_best = MODELS_DIR / "classroom_best.pt"
                shutil.copy2(str(best_weight), str(target_best))

                print("\n=================================================================")
                print("[THÀNH CÔNG RỰC RỠ] ĐÃ HUẤN LUYỆN XONG VỚI DỮ LIỆU CAMERA THỰC TẾ!")
                print(f"[+] File trọng số tối ưu (Camera thật): {target_best}")
                print("=================================================================")
                print("\nHệ thống điểm danh Điều Cải sẽ tự động nạp mô hình mới này.")
            else:
                print(f"\n[+] Huấn luyện xong. File trọng số tối ưu lưu tại: {best_weight}")
        else:
            print("[!] Quá trình hoàn tất nhưng không tìm thấy file best.pt đầu ra.")

    except Exception as e:
        print(f"\n[LỖI TRONG QUÁ TRÌNH HUẤN LUYỆN]: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
