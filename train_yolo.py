"""
Script Huấn Luyện & Tinh Chỉnh (Fine-tuning) Mô Hình AI YOLOv8
Chuyên Biệt Cho Lớp Học Trường THPT Điều Cải
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
import torch
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
DATASET_DIR = BASE_DIR / "dataset"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def parse_args():
    parser = argparse.ArgumentParser(description="Huấn luyện mô hình YOLOv8 nhận diện học sinh lớp học Điều Cải")
    parser.add_argument("--data", type=str, default=str(DATASET_DIR / "classroom.yaml"), help="Đường dẫn file cấu hình dataset.yaml")
    parser.add_argument("--model", type=str, default="yolov8s.pt", help="Mô hình checkpoint ban đầu (yolov8n.pt hoặc yolov8s.pt)")
    parser.add_argument("--epochs", type=int, default=50, help="Số lượt huấn luyện (epochs)")
    parser.add_argument("--imgsz", type=int, default=1280, help="Kích thước phân giải ảnh huấn luyện (khuyến nghị 1280 cho camera 2K)")
    parser.add_argument("--batch", type=int, default=8, help="Kích thước batch (giảm xuống 4 nếu thiếu VRAM GPU)")
    parser.add_argument("--device", type=str, default="", help="Thiết bị: '0' (GPU CUDA) hoặc 'cpu'")
    parser.add_argument("--prepare-sample", action="store_true", help="Tự động tạo khung thư mục dataset mẫu nếu chưa có dữ liệu gán nhãn")
    return parser.parse_args()

def prepare_sample_dataset_structure():
    """Tạo sẵn cấu trúc thư mục dataset/classroom_data nếu người dùng chưa tải về từ Roboflow."""
    target_dir = DATASET_DIR / "classroom_data"
    for sub in ["images/train", "images/val", "labels/train", "labels/val"]:
        (target_dir / sub).mkdir(parents=True, exist_ok=True)

    print(f"[THÔNG BÁO] Đã tạo khung thư mục chuẩn tại: {target_dir}")
    print("Bạn có thể tải dữ liệu ảnh & nhãn từ Roboflow/Label Studio vào:")
    print(f" - Ảnh train: {target_dir / 'images/train'}")
    print(f" - Nhãn train: {target_dir / 'labels/train'}")
    print(f" - Ảnh val: {target_dir / 'images/val'}")
    print(f" - Nhãn val: {target_dir / 'labels/val'}")

def main():
    args = parse_args()

    print("=================================================================")
    print("   CHƯƠNG TRÌNH HUẤN LUYỆN AI ĐIỂM DANH LỚP HỌC - THPT ĐIỀU CẢI")
    print("=================================================================")

    if args.prepare_sample:
        prepare_sample_dataset_structure()
        return

    # 1. Kiểm tra môi trường phần cứng (GPU CUDA vs CPU)
    if not args.device:
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            device = "0"
            print(f"[*] Phát hiện GPU CUDA: {device_name} -> Sử dụng GPU để tăng tốc huấn luyện.")
        else:
            device = "cpu"
            print("[!] Không tìm thấy GPU CUDA. Huấn luyện sẽ chạy trên CPU (khuyến nghị đặt batch nhỏ: 4, epochs: 20-30).")
    else:
        device = args.device

    # 2. Kiểm tra file cấu hình dataset
    yaml_path = Path(args.data)
    if not yaml_path.exists():
        print(f"[LỖI] Không tìm thấy file cấu hình: {yaml_path}")
        print("Đang tự động khởi tạo cấu trúc thư mục...")
        prepare_sample_dataset_structure()
        return

    # 3. Nạp mô hình gốc
    print(f"[*] Đang tải mô hình nền tảng checkpoint: {args.model}...")
    try:
        model = YOLO(args.model)
    except Exception as e:
        print(f"[LỖI] Không thể tải checkpoint {args.model}: {e}")
        return

    # 4. Bắt đầu quá trình huấn luyện (Fine-tuning)
    print("\n[*] Bắt đầu quá trình huấn luyện tự động...")
    print(f" - Dataset config: {yaml_path}")
    print(f" - Số epochs: {args.epochs}")
    print(f" - Phân giải ảnh: {args.imgsz}x{args.imgsz}")
    print(f" - Batch size: {args.batch}")
    print(f" - Device: {device}\n")

    try:
        results = model.train(
            data=str(yaml_path),
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            device=device,
            project=str(BASE_DIR / "runs" / "train"),
            name="dieucai_classroom",
            exist_ok=True,
            pretrained=True,
            optimizer="AdamW",
            lr0=0.001,
            augment=True, # Tự động tăng cường dữ liệu (lật ngang, xoay nhẹ, đổi sáng)
            verbose=True
        )

        # 5. Xuất mô hình tốt nhất vào thư mục models/
        best_weight = BASE_DIR / "runs" / "train" / "dieucai_classroom" / "weights" / "best.pt"
        if best_weight.exists():
            target_model_path = MODELS_DIR / "classroom_best.pt"
            shutil.copy2(str(best_weight), str(target_model_path))
            print("\n=================================================================")
            print(f"[THÀNH CÔNG] Đã huấn luyện xong mô hình AI cho trường Điều Cải!")
            print(f"[+] File trọng số tối ưu đã được lưu tại: {target_model_path}")
            print("\nCÁCH KÍCH HOẠT MÔ HÌNH MỚI:")
            print("1. Mở file 'config/settings.py'")
            print("2. Đổi dòng cấu hình:")
            print('   YOLO_MODEL_NAME: str = "models/classroom_best.pt"')
            print("3. Khởi động lại hệ thống bằng 'run.bat' để tận hưởng độ chính xác cao nhất!")
            print("=================================================================")
        else:
            print("[!] Hoàn tất nhưng không tìm thấy file best.pt đầu ra.")

    except Exception as e:
        print(f"\n[LỖI TRONG QUÁ TRÌNH HUẤN LUYỆN]: {e}")
        print("\nGỢI Ý KHẮC PHỤC:")
        print("1. Đảm bảo bạn đã có ảnh trong thư mục 'dataset/classroom_data/images/train'")
        print("2. Nếu bị lỗi Out of Memory (OOM), hãy giảm batch size: python train_yolo.py --batch 4 --imgsz 640")

if __name__ == "__main__":
    main()
