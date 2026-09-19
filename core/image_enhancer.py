import cv2
import numpy as np

class ImageEnhancer:
    """
    Module tối ưu hóa chất lượng hình ảnh & chống ngược sáng (Backlight / Glare compensation):
    Khắc phục tình trạng lớp học bị lóa sáng mạnh từ dãy cửa sổ bên phải làm mờ đầu/mặt học sinh.
    """

    @staticmethod
    def enhance_contrast_clahe(image: np.ndarray, clip_limit: float = 2.5, tile_grid_size: tuple = (8, 8)) -> np.ndarray:
        """
        Áp dụng thuật toán CLAHE (Contrast Limited Adaptive Histogram Equalization)
        lên kênh độ sáng Luminance (L channel) trong không gian màu LAB.
        Giữ nguyên màu sắc tự nhiên nhưng làm rõ chi tiết các vùng tối và cân bằng vùng lóa.
        """
        if image is None:
            return None

        # Chuyển từ BGR sang LAB
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        # Khởi tạo bộ CLAHE
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        enhanced_l = clahe.apply(l_channel)

        # Ghép lại các kênh và chuyển về BGR
        enhanced_lab = cv2.merge([enhanced_l, a_channel, b_channel])
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        return enhanced_bgr

    @staticmethod
    def reduce_window_glare(image: np.ndarray, threshold: int = 240) -> np.ndarray:
        """
        Phát hiện và làm dịu vùng chói lóa cực đại (như cửa sổ bị ánh nắng chiếu trực tiếp),
        ngăn AI bị nhiễu do viền phản quang của cửa sổ.
        """
        if image is None:
            return None

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Tạo mask các vùng quá sáng (> 240)
        _, glare_mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

        # Làm mờ vùng sáng để giảm bớt tương phản gắt
        blurred = cv2.GaussianBlur(image, (15, 15), 0)
        glare_mask_3ch = cv2.merge([glare_mask, glare_mask, glare_mask])

        # Hòa trộn nhẹ vùng lóa
        result = np.where(glare_mask_3ch == 255, cv2.addWeighted(image, 0.6, blurred, 0.4, 0), image)
        return result

    @classmethod
    def preprocess_classroom_frame(cls, image: np.ndarray) -> np.ndarray:
        """Tiền xử lý toàn diện cho khung hình camera lớp học trước khi đưa vào mô hình AI."""
        if image is None:
            return None
        # 1. Cân bằng tương phản chống ngược sáng
        enhanced = cls.enhance_contrast_clahe(image, clip_limit=2.0)
        # 2. Giảm chói lóa cửa sổ
        clean_frame = cls.reduce_window_glare(enhanced)
        return clean_frame
