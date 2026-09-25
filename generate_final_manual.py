# -*- coding: utf-8 -*-
"""
Script chính tạo file USER MANUAL hoàn chỉnh:
- USER_MANUAL_THPT_DIEU_CAI_v1.0.docx
- USER_MANUAL_v1.0.docx
Đơn vị: TRƯỜNG THPT ĐIỀU CẢI (SỞ GD&ĐT TỈNH ĐỒNG NAI)
Hệ thống: HỆ THỐNG ĐIỂM DANH HỌC SINH TỰ ĐỘNG BẰNG AI CAMERA
"""

import os
import sys
from pathlib import Path

# Đảm bảo UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "docs"))

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL

from manual_helpers import (
    create_document,
    add_custom_heading,
    add_body_paragraph,
    add_bullet_item,
    add_callout,
    create_styled_table,
    add_screenshot_placeholder,
    add_embedded_image_if_exists,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_TEXT_DARK,
    COLOR_TEXT_MUTED,
    HEX_PRIMARY,
    HEX_LIGHT_BG
)

def build_manual():
    doc = create_document()

    # ==============================================================================
    # TRANG BÌA (COVER PAGE)
    # ==============================================================================
    p_org = doc.add_paragraph()
    p_org.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_org.paragraph_format.space_before = Pt(30)
    p_org.paragraph_format.space_after = Pt(2)
    r_so = p_org.add_run("SỞ GIÁO DỤC VÀ ĐÀO TẠO TỈNH ĐỒNG NAI\n")
    r_so.font.name = "Arial"
    r_so.font.size = Pt(11)
    r_so.font.bold = True
    r_so.font.color.rgb = COLOR_PRIMARY

    r_truong = p_org.add_run("TRƯỜNG THPT ĐIỀU CẢI")
    r_truong.font.name = "Arial"
    r_truong.font.size = Pt(13)
    r_truong.font.bold = True
    r_truong.font.color.rgb = COLOR_PRIMARY

    p_line = doc.add_paragraph()
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_line.paragraph_format.space_after = Pt(60)
    r_line = p_line.add_run("━━━━━━━━━━━━━━━━━━━")
    r_line.font.name = "Arial"
    r_line.font.size = Pt(11)
    r_line.font.color.rgb = COLOR_SECONDARY

    p_badge = doc.add_paragraph()
    p_badge.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_badge.paragraph_format.space_after = Pt(12)
    r_badge = p_badge.add_run("TÀI LIỆU BÀN GIAO & VẬN HÀNH CHÍNH THỨC")
    r_badge.font.name = "Arial"
    r_badge.font.size = Pt(10)
    r_badge.font.bold = True
    r_badge.font.color.rgb = COLOR_SECONDARY

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_after = Pt(10)
    r_title = p_title.add_run("SỔ TAY HƯỚNG DẪN SỬ DỤNG HỆ THỐNG\n(USER MANUAL)")
    r_title.font.name = "Arial"
    r_title.font.size = Pt(22)
    r_title.font.bold = True
    r_title.font.color.rgb = COLOR_PRIMARY

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(80)
    r_sub = p_sub.add_run("HỆ THỐNG ĐIỂM DANH HỌC SINH TỰ ĐỘNG BẰNG AI CAMERA\nQUY MÔ 30 LỚP HỌC TOÀN TRƯỜNG (1.246 HỌC SINH)")
    r_sub.font.name = "Arial"
    r_sub.font.size = Pt(12)
    r_sub.font.bold = True
    r_sub.font.color.rgb = COLOR_SECONDARY

    # Bảng siêu dữ liệu bìa
    meta_headers = ["THÔNG TIN HỆ THỐNG", "CHI TIẾT ÁP DỤNG"]
    meta_rows = [
        ["Tên dự án:", "Hệ thống Điểm danh Học sinh Tự động bằng AI Camera"],
        ["Đơn vị thụ hưởng:", "Trường THPT Điểu Cải, Tỉnh Đồng Nai"],
        ["Phiên bản tài liệu:", "Phiên bản chính thức v1.0 (Release Candidate)"],
        ["Ngày phát hành:", "Năm học 2025 - 2026"],
        ["Đối tượng áp dụng:", "Ban Giám Hiệu, Giám thị, Giáo viên chủ nhiệm, Quản trị viên"],
        ["Cơ quan quản lý:", "Sở Giáo dục và Đào tạo Tỉnh Đồng Nai"],
        ["Phạm vi triển khai:", "30 phòng học (Khối 10: 10A1-10A10, Khối 11: 11A1-11A10, Khối 12: 12A1-12A10)"]
    ]
    create_styled_table(doc, meta_headers, meta_rows, col_widths=[2.4, 4.07], alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])

    doc.add_page_break()

    # ==============================================================================
    # TRANG LỊCH SỬ CẬP NHẬT TÀI LIỆU
    # ==============================================================================
    add_custom_heading(doc, "LỊCH SỬ CẬP NHẬT TÀI LIỆU (REVISION HISTORY)", level=1)
    rev_headers = ["PHIÊN BẢN", "NGÀY CẬP NHẬT", "TÁC GIẢ / BỘ PHẬN", "NỘI DUNG THAY ĐỔI CHÍNH"]
    rev_rows = [
        ["v1.0", "24/09/2026", "Tổ Kỹ thuật & BA Dự án", "Phát hành tài liệu hoàn chỉnh bàn giao hệ thống: hướng dẫn toàn diện Dashboard, Quản lý Camera, Vùng nhận diện ROI (chỉ giữ Green Zone), Báo cáo Excel, Trung tâm Sao lưu & Phục hồi CSDL, Cấu hình Zalo Bot/Email và Quản lý Người dùng."],
        ["v0.9", "18/09/2026", "Đội ngũ Triển khai AI", "Bản dự thảo thử nghiệm các ca quét tự động 06:45 và tích hợp Zalo Bot Gateway nội bộ."],
        ["v0.5", "05/09/2026", "Nhóm Phát triển", "Khởi tạo tài liệu quy chuẩn kỹ thuật và kiểm tra tín hiệu luồng RTSP 30 phòng học."]
    ]
    create_styled_table(doc, rev_headers, rev_rows, col_widths=[1.0, 1.3, 1.8, 2.37], alignments=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])

    add_custom_heading(doc, "MỤC LỤC TÀI LIỆU (TABLE OF CONTENTS)", level=1)
    toc_items = [
        ("CHƯƠNG 1: THÔNG TIN TÀI LIỆU & QUY ƯỚC SỬ DỤNG", "Trang 3"),
        ("CHƯƠNG 2: TỔNG QUAN HỆ THỐNG ĐIỂM DANH AI THPT ĐIỀU CẢI", "Trang 4"),
        ("CHƯƠNG 3: YÊU CẦU MÔI TRƯỜNG & THIẾT BỊ VẬN HÀNH", "Trang 5"),
        ("CHƯƠNG 4: HƯỚNG DẪN ĐĂNG NHẬP, ĐĂNG XUẤT & BẢO MẬT TÀI KHOẢN", "Trang 6"),
        ("CHƯƠNG 5: TỔNG QUAN BỐ CỤC GIAO DIỆN HỆ THỐNG", "Trang 7"),
        ("CHƯƠNG 6: HƯỚNG DẪN CHI TIẾT TRUNG TÂM ĐIỀU HÀNH DASHBOARD", "Trang 8"),
        ("CHƯƠNG 7: QUẢN TRỊ CAMERA, ĐẦU GHI NVR & LƯỚI MA TRẬN TV WALL", "Trang 11"),
        ("CHƯƠNG 8: CẤU HÌNH VÙNG NHẬN DIỆN BÀN HỌC SINH (GREEN ZONE ROI)", "Trang 14"),
        ("CHƯƠNG 9: BÁO CÁO, KHO LƯU TRỮ EXCEL & TRUNG TÂM SAO LƯU CSDL", "Trang 16"),
        ("CHƯƠNG 10: CẤU HÌNH PHÂN PHỐI THÔNG BÁO TỰ ĐỘNG (ZALO & EMAIL)", "Trang 19"),
        ("CHƯƠNG 11: QUẢN LÝ TÀI KHOẢN NGƯỜI DÙNG & PHÂN QUYỀN (ADMIN ONLY)", "Trang 22"),
        ("CHƯƠNG 12: HƯỚNG DẪN CÁC QUY TRÌNH VẬN HÀNH NGHIỆP VỤ THỰC TẾ", "Trang 24"),
        ("CHƯƠNG 13: XỬ LÝ LỖI & SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)", "Trang 26"),
        ("CHƯƠNG 14: CÂU HỎI THƯỜNG GẶP (FAQ)", "Trang 28"),
        ("CHƯƠNG 15: THUẬT NGỮ CHUYÊN NGÀNH & BẢNG KÝ HIỆU (GLOSSARY)", "Trang 29"),
        ("CHƯƠNG 16: THÔNG TIN LIÊN HỆ & ĐẦU MỐI HỖ TRỢ KỸ THUẬT", "Trang 30"),
    ]
    for title, pg in toc_items:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2.5)
        p.paragraph_format.line_spacing = 1.15
        r_t = p.add_run(title)
        r_t.font.name = "Arial"
        r_t.font.size = Pt(9.5)
        r_t.font.bold = True if "CHƯƠNG" in title else False
        r_t.font.color.rgb = COLOR_TEXT_DARK
        
        # Thêm dấu chấm dẫn
        r_dots = p.add_run(" " + "." * max(5, int(65 - len(title) * 0.8)) + " ")
        r_dots.font.name = "Arial"
        r_dots.font.size = Pt(8.5)
        r_dots.font.color.rgb = COLOR_TEXT_MUTED

        r_pg = p.add_run(pg)
        r_pg.font.name = "Arial"
        r_pg.font.size = Pt(9.5)
        r_pg.font.bold = True
        r_pg.font.color.rgb = COLOR_PRIMARY

    doc.add_page_break()

    # ==============================================================================
    # CHƯƠNG 1: THÔNG TIN TÀI LIỆU & QUY ƯỚC SỬ DỤNG
    # ==============================================================================
    add_custom_heading(doc, "CHƯƠNG 1: THÔNG TIN TÀI LIỆU & QUY ƯỚC SỬ DỤNG", level=1)
    
    add_custom_heading(doc, "1.1. Mục Đích Của Tài Liệu", level=2)
    add_body_paragraph(doc, "Tài liệu này cung cấp hướng dẫn vận hành toàn diện và chi tiết nhất dành cho người dùng cuối của Hệ thống Điểm danh Học sinh Tự động bằng AI Camera tại Trường THPT Điểu Cải. Tài liệu tập trung vào các thao tác thực tế trên giao diện web, cách theo dõi số liệu sĩ số, tra cứu lịch sử, xuất báo cáo chuẩn GD&ĐT, quản lý thiết bị camera và bảo dưỡng dữ liệu an toàn mà không đòi hỏi người đọc phải có kiến thức chuyên sâu về lập trình.")

    add_custom_heading(doc, "1.2. Đối Tượng Sử Dụng & Trách Nhiệm", level=2)
    add_body_paragraph(doc, "Hệ thống phân chia 2 nhóm đối tượng người dùng với quyền hạn rõ ràng:")
    add_bullet_item(doc, "Có toàn quyền cấu hình các thông số hệ thống, thêm/sửa/xóa camera lớp học, vẽ và căn chỉnh vùng nhận diện ROI, cấu hình kết nối Zalo/Email, lập lịch quét tự động, quản lý tài khoản người dùng và thực hiện sao lưu/khôi phục cơ sở dữ liệu.", "1. Quản trị viên (Admin):")
    add_bullet_item(doc, "Bao gồm Ban Giám Hiệu, Cán bộ Giám thị, Giáo viên bộ môn và Giáo viên chủ nhiệm. Được quyền theo dõi trực quan bảng điểm danh trên Dashboard, kích hoạt quét kiểm tra sĩ số, phóng to đối chứng ảnh camera với kết quả khoanh vùng AI, tra cứu dữ liệu lịch sử các ngày học, tải file Excel và xem ma trận TV Wall camera.", "2. Cán bộ & Giáo viên (Staff):")

    add_custom_heading(doc, "1.3. Quy Ước Ký Hiệu & Cảnh Báo Trong Tài Liệu", level=2)
    add_body_paragraph(doc, "Trong suốt tài liệu, các hộp thông tin chỉ dẫn được quy ước bằng màu sắc và biểu tượng trực quan sau:")
    add_callout(doc, "GHI CHÚ HƯỚNG DẪN (NOTE):", [
        "Cung cấp thông tin bổ sung, giải thích nguyên lý hoạt động hoặc gợi ý thao tác tối ưu giúp người dùng thao tác nhanh chóng và thuận tiện hơn."
    ], "note")
    add_callout(doc, "LƯU Ý QUAN TRỌNG (TIP):", [
        "Nhắc nhở về quy định sư phạm, kinh nghiệm thiết lập vùng nhận diện hoặc thời điểm quét giúp đạt độ chính xác tối đa 100%."
    ], "tip")
    add_callout(doc, "CẢNH BÁO NGUY HIỂM (WARNING):", [
        "Các thao tác có tính ảnh hưởng dữ liệu (xóa camera, khôi phục bản sao lưu, đổi mật khẩu) đòi hỏi người dùng kiểm tra kỹ trước khi xác nhận."
    ], "warn")

    # ==============================================================================
    # CHƯƠNG 2: TỔNG QUAN HỆ THỐNG ĐIỂM DANH AI THPT ĐIỀU CẢI
    # ==============================================================================
    add_custom_heading(doc, "CHƯƠNG 2: TỔNG QUAN HỆ THỐNG ĐIỂM DANH AI THPT ĐIỀU CẢI", level=1)

    add_custom_heading(doc, "2.1. Đặt Vấn Đề & Mục Tiêu Chuyển Đổi Số", level=2)
    add_body_paragraph(doc, "Trước đây, công tác điểm danh đầu giờ tại Trường THPT Điểu Cải được thực hiện thủ công bởi cán bộ sao đỏ hoặc giáo viên bộ môn ghi nhận vào sổ đầu bài giấy. Quy trình này thường mất từ 15 đến 20 phút mỗi buổi, dễ xảy ra nhầm lẫn, mất tập trung đầu tiết học và Ban Giám Hiệu không thể nắm bắt tức thời tình hình chuyên cần toàn trường để kịp thời liên hệ phụ huynh.")
    add_body_paragraph(doc, "Hệ thống Điểm danh Học sinh Tự động bằng AI Camera giải quyết triệt để vấn đề trên bằng cách tự động hóa 100% quy trình quét sĩ số 30 lớp học (1.246 học sinh) chỉ trong vòng 30 đến 45 giây mỗi ca học, đối chứng minh bạch bằng hình ảnh và tự động gửi thông báo trực tiếp qua Zalo/Email.")

    add_custom_heading(doc, "2.2. Các Phân Hệ Chức Năng Nòng Cốt", level=2)
    core_features_headers = ["PHÂN HỆ CHỨC NĂNG", "VAI TRÒ TRONG HỆ THỐNG", "HIỆU QUẢ THỰC TẾ"]
    core_features_rows = [
        ["AI YOLO26m + STAL", "Thị giác máy tính AI thế hệ mới nhận diện đầu người và nửa thân trên của học sinh.", "Độ chính xác cao, không bị ảnh hưởng khi học sinh cúi đầu viết bài hoặc ngồi che khuất nhau."],
        ["Cân Bằng Sáng CLAHE", "Thuật toán lọc và cân bằng ánh sáng thích ứng cục bộ.", "Loại bỏ hoàn toàn hiện tượng ngược sáng từ dãy cửa sổ và chói lóa ánh nắng ban mai."],
        ["Vùng ROI Đa Giác (Green Zone)", "Phân vùng không gian bàn học sinh (khu vực tính sĩ số).", "Tự động loại bỏ người đứng ở bục giảng, bàn giáo viên hoặc đi ngoài hành lang."],
        ["Đèn Báo Bật Hồng Ngoại", "Kích hoạt đèn hồng ngoại camera báo hiệu 3 giây trước khi chụp ảnh màu.", "Tạo tín hiệu nhận biết giờ điểm danh, học sinh ngồi ngay ngắn vào vị trí chuẩn."],
        ["Lập Lịch Kép 06:45 & 12:45", "Bộ lập lịch nền tự động thực thi theo múi giờ chuẩn Việt Nam.", "Hoàn toàn tự động, vận hành ổn định Thứ 2 đến Thứ 7 mà không cần người bấm máy."],
        ["Zalo Bot & Email Tức Thời", "Phân phối bản tin chuyên cần ngay sau khi quét xong ca học.", "BGH nhận báo cáo toàn trường, GVCN nhận báo cáo lớp chủ nhiệm trong 1 phút."],
        ["Báo Cáo Excel Chuẩn Sở", "Tự động xuất bảng tổng hợp sĩ số 30 lớp định dạng chuẩn GD&ĐT.", "Đầy đủ công thức SUM, highlight lớp vắng, sẵn sàng in ấn lưu trữ hành chính."],
        ["Sao Lưu CSDL An Toàn", "Tự động đóng gói CSDL, cấu hình và báo cáo lúc 23:00 hàng ngày.", "Bảo toàn tuyệt đối dữ liệu lịch sử điểm danh qua nhiều năm học."]
    ]
    create_styled_table(doc, core_features_headers, core_features_rows, col_widths=[2.0, 2.3, 2.17], alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])

    add_custom_heading(doc, "2.3. Sơ Đồ Quy Trình Điểm Danh Tự Động Toàn Trường", level=2)
    add_body_paragraph(doc, "Toàn bộ chu trình điểm danh diễn ra hoàn toàn khép kín và tự động hóa theo lưu đồ nghiệp vụ sau:")
    add_embedded_image_if_exists(doc, "docs/manual_assets/img_workflow_diagram.png", "2.1", "Sơ đồ luồng vận hành điểm danh tự động tại THPT Điểu Cải", width_inches=6.2)

    # ==============================================================================
    # CHƯƠNG 3: YÊU CẦU MÔI TRƯỜNG & THIẾT BỊ VẬN HÀNH
    # ==============================================================================
    add_custom_heading(doc, "CHƯƠNG 3: YÊU CẦU MÔI TRƯỜNG & THIẾT BỊ VẬN HÀNH", level=1)

    add_custom_heading(doc, "3.1. Yêu Cầu Thiết Bị Phía Người Dùng Cuối", level=2)
    add_body_paragraph(doc, "Người dùng cuối có thể truy cập hệ thống điểm danh từ bất kỳ thiết bị nào có kết nối mạng nội bộ trường học:")
    add_bullet_item(doc, "Hệ điều hành Windows 10/11, macOS hoặc Ubuntu Linux. Màn hình khuyến nghị từ Full HD (1920x1080) trở lên để quan sát tốt nhất lưới TV Wall và bảng đối chứng ảnh.", "Máy tính để bàn / Laptop:")
    add_bullet_item(doc, "Google Chrome, Microsoft Edge, Mozilla Firefox hoặc Apple Safari (phiên bản cập nhật trong vòng 1 năm gần nhất). Bật JavaScript và Cookie.", "Trình duyệt Web:")
    add_bullet_item(doc, "iPad, máy tính bảng Android hoặc điện thoại thông minh (giao diện tự động co giãn theo chuẩn Responsive Design hiện đại).", "Thiết bị di động:")
    add_bullet_item(doc, "Cùng lớp mạng LAN trường học (dải IP nội bộ ví dụ 192.168.10.x) hoặc kết nối qua VPN trường.", "Môi trường mạng:")

    add_custom_heading(doc, "3.2. Yêu Cầu Hạ Tầng Camera & Máy Chủ", level=2)
    add_body_paragraph(doc, "Hạ tầng phục vụ điểm danh tại Trường THPT Điểu Cải bao gồm:")
    add_bullet_item(doc, "30 camera giám sát lắp đặt tại 30 phòng học (từ Phòng 101 đến Phòng 130), hỗ trợ chuẩn RTSP Full HD 1080p, kết nối về Đầu ghi NVR 32 kênh đặt tại phòng Server.", "Hệ thống Camera IP:")
    add_bullet_item(doc, "Máy chủ chạy Windows/Linux, cấu hình tối thiểu Intel Core i5/i7 thế hệ mới, RAM 16GB, ổ cứng SSD NVMe, card đồ họa NVIDIA RTX (khuyến nghị RTX 3050 trở lên) hỗ trợ tăng tốc AI.", "Máy chủ AI Server:")

    # ==============================================================================
    # CHƯƠNG 4: HƯỚNG DẪN ĐĂNG NHẬP, ĐĂNG XUẤT & BẢO MẬT TÀI KHOẢN
    # ==============================================================================
    add_custom_heading(doc, "CHƯƠNG 4: HƯỚNG DẪN ĐĂNG NHẬP, ĐĂNG XUẤT & BẢO MẬT TÀI KHOẢN", level=1)

    add_custom_heading(doc, "4.1. Quy Trình Đăng Nhập Hệ Thống", level=2)
    add_body_paragraph(doc, "Nhằm đảm bảo an toàn thông tin học sinh và bảo mật dữ liệu chuyên cần, hệ thống áp dụng cơ chế xác thực JWT bảo vệ qua Cookie HTTP-Only an toàn.")
    add_body_paragraph(doc, "Để đăng nhập, người dùng thực hiện theo các bước sau:")
    add_bullet_item(doc, "Mở trình duyệt web (Google Chrome hoặc Microsoft Edge) và nhập địa chỉ truy cập: http://localhost:8000/login (hoặc địa chỉ IP máy chủ trong mạng trường học: ví dụ http://192.168.10.200:8000/login).", "Bước 1:")
    add_bullet_item(doc, "Nhập chính xác Email công vụ (ví dụ: admin@truongdieucai.edu.vn hoặc email được nhà trường cấp) và Mật khẩu đăng nhập.", "Bước 2:")
    add_bullet_item(doc, "Nhấp chuột vào nút 'Đăng Nhập' (hoặc nhấn phím Enter). Hệ thống sẽ xác thực và chuyển hướng tự động về màn hình Trung tâm điều hành Dashboard.", "Bước 3:")

    add_screenshot_placeholder(doc, "4.1", "Màn hình Đăng nhập Hệ thống Điểm danh THPT Điểu Cải", "Trang login.html (Giao diện thẻ đăng nhập Glassmorphism)")

    add_callout(doc, "NGUYÊN TẮC BẢO MẬT TÀI KHOẢN:", [
        "Hệ thống KHÔNG mở chức năng đăng ký tài khoản tự do trên Internet.",
        "Mọi tài khoản đều do Quản trị viên nhà trường trực tiếp khởi tạo và phân quyền trên trang Quản Lý Tài Khoản.",
        "Phiên đăng nhập được duy trì tối đa 12 giờ qua cookie an toàn. Hết thời gian này, hệ thống sẽ tự động yêu cầu đăng nhập lại."
    ], "warn")

    add_custom_heading(doc, "4.2. Xử Lý Khi Quên Mật Khẩu (Khôi Phục Mật Khẩu)", level=2)
    add_body_paragraph(doc, "Trong trường hợp quên mật khẩu, người dùng có thể chủ động khôi phục thông qua hòm thư điện tử cá nhân:")
    add_bullet_item(doc, "Tại màn hình đăng nhập, nhấp chuột vào liên kết 'Quên mật khẩu?'. Giao diện sẽ chuyển tới trang forgot-password.html.", "Bước 1:")
    add_bullet_item(doc, "Nhập chính xác địa chỉ Email của tài khoản cần lấy lại mật khẩu và nhấp nút 'Gửi hướng dẫn'.", "Bước 2:")
    add_bullet_item(doc, "Hệ thống kiểm tra thông tin và tự động gửi một email chứa đường dẫn đặt lại mật khẩu an toàn (liên kết có hiệu lực trong vòng 1 giờ).", "Bước 3:")
    add_bullet_item(doc, "Mở hòm thư email, nhấp vào liên kết xác nhận và tiến hành nhập Mật khẩu mới (tối thiểu 8 ký tự, bao gồm chữ hoa, chữ thường và số). Nhấp 'Lưu mật khẩu' để hoàn tất.", "Bước 4:")

    add_custom_heading(doc, "4.3. Quy Trình Đăng Xuất An Toàn", level=2)
    add_body_paragraph(doc, "Khi kết thúc ca làm việc hoặc rời khỏi máy tính công cộng, người dùng bắt buộc phải đăng xuất để ngăn chặn việc người khác thao tác trái phép:")
    add_bullet_item(doc, "Di chuyển chuột xuống góc dưới cùng của thanh điều hướng Sidebar bên trái (nơi hiển thị tên và ảnh đại diện tài khoản).", "Bước 1:")
    add_bullet_item(doc, "Nhấp chuột vào biểu tượng nút Đăng Xuất (hình cánh cửa có mũi tên).", "Bước 2:")
    add_bullet_item(doc, "Hệ thống sẽ xóa sạch phiên làm việc trên máy tính và đưa người dùng quay trở lại màn hình đăng nhập.", "Bước 3:")

    # ==============================================================================
    # CHƯƠNG 5: TỔNG QUAN BỐ CỤC GIAO DIỆN HỆ THỐNG
    # ==============================================================================
    add_custom_heading(doc, "CHƯƠNG 5: TỔNG QUAN BỐ CỤC GIAO DIỆN HỆ THỐNG", level=1)
    add_body_paragraph(doc, "Giao diện hệ thống được thiết kế theo phong cách hiện đại Glassmorphism, tối ưu không gian làm việc và đồng nhất trên toàn bộ các màn hình theo cấu trúc chuẩn mực:")

    nav_table_headers = ["MỤC MENU", "BIỂU TƯỢNG", "ĐƯỜNG DẪN TRUY CẬP", "QUYỀN HẠN", "CHỨC NĂNG CHÍNH"]
    nav_table_rows = [
        ["Dashboard", "📈 Biểu đồ", "/ (index.html)", "Admin & Staff", "Giám sát thời gian thực sĩ số 30 lớp, xem xu hướng 7 ngày, đối chứng ảnh và quét thủ công."],
        ["Camera & Lớp Học", "📹 Video", "/cameras", "Admin & Staff", "Lưới ma trận TV Wall 30 camera, quản lý danh sách camera, nạp tự động 30 kênh từ NVR."],
        ["Vùng ROI", "📐 Đa giác", "/roi-config", "Admin & Staff", "Công cụ vẽ đa giác vùng bàn học sinh (Green Zone), tự động loại trừ bục giảng giáo viên."],
        ["Báo Cáo & Dữ Liệu", "📑 File Excel", "/reports", "Admin & Staff", "Tra cứu lịch sử CSDL, kho file Excel tổng hợp chuẩn GD&ĐT, sao lưu CSDL (Admin)."],
        ["Thông Báo", "🔔 Chuông/Gửi", "/notifications", "Admin & Staff", "Cấu hình gửi Zalo Bot Gateway, Email Hiệu trưởng, tùy chỉnh mẫu tin và giờ quét tự động."],
        ["Tài Khoản", "👥 Người dùng", "/users", "Chỉ Quản trị viên (Admin)", "Tạo mới tài khoản, phân quyền Admin/Staff, đặt lại mật khẩu và chuyển trạng thái hoạt động."]
    ]
    create_styled_table(doc, nav_table_headers, nav_table_rows, col_widths=[1.5, 1.0, 1.2, 1.3, 1.47], alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT])

    add_body_paragraph(doc, "Các khu vực điều khiển cố định trên thanh tiêu đề và thanh bên:")
    add_bullet_item(doc, "Hiển thị logo 'ĐC' và thương hiệu 'THPT ĐIỀU CẢI - AI CAMERA'.", "1. Đầu thanh bên (Sidebar Header):")
    add_bullet_item(doc, "Hiển thị đồng hồ thời gian thực tế (Live Clock), mã phiên điểm danh gần nhất, thời điểm quét và thời điểm cập nhật.", "2. Thanh thông tin trạng thái ca quét (Header Session Info):")
    add_bullet_item(doc, "Bao gồm các nút tắt nhanh: 'Làm Mới' (tải lại dữ liệu từ CSDL), 'Xuất Excel' (tải file báo cáo phiên mới nhất), 'Quét Điểm Danh' (kích hoạt chu trình quét toàn trường tức thì).", "3. Cụm nút tác vụ trên cùng (Page Actions):")

    # ==============================================================================
    # CHƯƠNG 6: HƯỚNG DẪN CHI TIẾT TRUNG TÂM ĐIỀU HÀNH DASHBOARD
    # ==============================================================================
    add_custom_heading(doc, "CHƯƠNG 6: HƯỚNG DẪN CHI TIẾT TRUNG TÂM ĐIỀU HÀNH DASHBOARD", level=1)
    add_body_paragraph(doc, "Màn hình Dashboard (Trang chủ) là trung tâm chỉ huy nơi Ban Giám Hiệu và Cán bộ Giám thị theo dõi sát sao tình hình hiện diện của học sinh toàn trường trong từng ca học.")

    add_screenshot_placeholder(doc, "6.1", "Tổng thể giao diện Trung tâm điều hành Dashboard", "Trang index.html (Bao gồm KPI, Trend Line 7 ngày và Bảng điểm danh hôm nay)")

    add_custom_heading(doc, "6.1. Bốn Thẻ Chỉ Số Trọng Yếu (KPI Cards)", level=2)
    add_body_paragraph(doc, "Ngay đầu màn hình là 4 thẻ chỉ số được cập nhật tự động sau mỗi ca quét:")
    add_bullet_item(doc, "Tổng quy mô học sinh toàn trường theo danh sách đăng bộ chính thức (Mặc định: 1.246 học sinh phân bổ trên 30 lớp học).", "Thẻ 1 - Tổng Học Sinh (Màu xanh dương):")
    add_bullet_item(doc, "Tổng số lượng học sinh thực tế đang có mặt tại các vị trí bàn học trong phòng học, được hệ thống AI quét và nhận diện hợp lệ.", "Thẻ 2 - Có Mặt (Màu xanh lá):")
    add_bullet_item(doc, "Tổng số học sinh vắng mặt toàn trường (= Sĩ số chuẩn trừ Số có mặt). Thẻ này được viền màu đỏ nổi bật để người quản lý nhận diện ngay mức độ chuyên cần.", "Thẻ 3 - Vắng Mặt (Màu đỏ cảnh báo):")
    add_bullet_item(doc, "Số lượng phòng học chưa quét hoặc camera bị mất tín hiệu kết nối mạng, đang chờ hệ thống xử lý lại.", "Thẻ 4 - Lớp Chưa Xử Lý (Màu vàng cam):")

    add_custom_heading(doc, "6.2. Biểu Đồ Xu Hướng Chuyên Cần 7 Ngày Gần Nhất (Trend Line)", level=2)
    add_body_paragraph(doc, "Hệ thống tích hợp biểu đồ đường chuyên sâu duy nhất giúp Ban Giám Hiệu đánh giá được xu thế biến động sĩ số học sinh qua các ngày trong tuần:")
    add_bullet_item(doc, "Hiển thị số lượng học sinh vắng thực tế được phát hiện trong ca quét của ngày hôm nay.", "Chip 'Hôm nay':")
    add_bullet_item(doc, "Số lượng học sinh vắng trung bình mỗi ngày trong vòng 7 ngày qua (giúp tạo thước đo cơ sở để so sánh).", "Chip 'Trung bình 7 ngày':")
    add_bullet_item(doc, "Hệ thống tự động phân tích độ lệch giữa hôm nay và mức trung bình tuần để đưa ra đánh giá trực quan: 'Bình thường' (màu xanh lá), 'Tăng nhẹ' (màu vàng), 'Cao bất thường cần lưu ý' (màu đỏ) hoặc 'Rất tốt' (màu xanh ngọc).", "Chip 'Đánh giá':")

    add_custom_heading(doc, "6.3. Bảng Nhật Ký Điểm Danh Chi Tiết 30 Lớp Hôm Nay", level=2)
    add_body_paragraph(doc, "Bảng nhật ký phản ánh chi tiết kết quả của từng phòng học trong ngày hôm nay:")
    add_bullet_item(doc, "Người dùng có thể nhấp chuột vào nút chuyển khối để lọc nhanh danh sách lớp theo 'Khối 10' (10A1-10A10), 'Khối 11' (11A1-11A10), 'Khối 12' (12A1-12A10) hoặc 'Tất Cả Lớp'. Có thể dùng phím mũi tên ◄ và ► trên bàn phím để chuyển khối nhanh.", "Bộ điều khiển chuyển khối (Grade Switcher):")
    add_bullet_item(doc, "Bộ tab cho phép lọc tức thì danh sách lớp theo tình trạng: 'Tất cả', 'Có vắng' (các lớp vắng học sinh cần theo dõi), 'Chưa xử lý' (lớp chưa có kết quả) và 'Đủ sĩ số' (lớp đi học 100%).", "Bộ lọc trạng thái (Segmented Tabs):")
    add_bullet_item(doc, "Nhập tên lớp (ví dụ: '10A1') hoặc số phòng ('Phòng 101') để tìm kiếm tức thì.", "Ô tìm kiếm nhanh:")

    add_body_paragraph(doc, "Ý nghĩa các cột dữ liệu trong bảng nhật ký:")
    db_col_headers = ["CỘT DỮ LIỆU", "Ý NGHĨA SỐ LIỆU", "MINH HỌA / MÀU SẮC"]
    db_col_rows = [
        ["STT & Lớp Học", "Số thứ tự và Tên lớp chính thức", "Ví dụ: Lớp 10A1, Lớp 11A5..."],
        ["Phòng", "Vị trí phòng học vật lý", "Ví dụ: Phòng 101, Phòng 204..."],
        ["Sĩ Số", "Sĩ số học sinh chuẩn của lớp", "39 đến 45 học sinh/lớp."],
        ["Có Mặt", "Số học sinh đang ngồi tại bàn do AI đếm", "Hiển thị số màu xanh lá cây."],
        ["Vắng", "Số học sinh vắng của lớp", "Nếu vắng >= 1 em: hiện số màu đỏ đậm."],
        ["Độ Tin Cậy AI", "Chỉ số độ tin cậy trung bình của AI", "Thường đạt từ 85% đến 96%."],
        ["Trạng Thái", "Đánh giá tình trạng lớp", "Huy hiệu xanh: 'Đủ sĩ số' / Huy hiệu đỏ: 'Vắng X em' / Vàng: 'Chưa xử lý'."],
        ["Ảnh Đối Chứng", "Nút xem hình ảnh chụp thực tế từ camera", "Nhấp nút 'Xem ảnh' để mở cửa sổ đối chứng."],
        ["Thao Tác", "Cột tác vụ điều khiển riêng từng lớp", "Nút 'Quét lại': cho phép ra lệnh cho AI chụp và nhận diện lại riêng lớp đó."]
    ]
    create_styled_table(doc, db_col_headers, db_col_rows, col_widths=[1.5, 2.5, 2.47], alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])

    add_custom_heading(doc, "6.4. Trình Xem Ảnh Đối Chứng Chi Tiết & Phóng To Zoom Lightbox", level=2)
    add_body_paragraph(doc, "Để đảm bảo tính minh bạch tuyệt đối và tránh tranh cãi về kết quả điểm danh, hệ thống hỗ trợ 2 chế độ soi ảnh trực quan:")
    add_bullet_item(doc, "Khi nhấp vào nút 'Xem ảnh' tại cột Ảnh Đối Chứng, một cửa sổ so sánh song song mở ra: Bên trái là 'Ảnh Gốc Camera' (toàn cảnh phòng học nguyên bản); Bên phải là 'Ảnh AI Khoanh Vùng Đối Chứng' (từng học sinh được đóng khung bounding box xanh và đánh số thứ tự #01, #02, #03... rõ ràng).", "1. Chế độ Xem Song Song Đối Chứng (Side-by-Side):")
    add_bullet_item(doc, "Người dùng có thể nhấp trực tiếp vào ảnh để mở trình soi ảnh toàn màn hình. Dùng con lăn chuột để phóng to thu nhỏ từ 60% đến 500%, giữ chuột trái kéo rê ảnh để quan sát rõ từng em học sinh ở dãy bàn cuối, nhấp nút Toàn màn hình hoặc nhấn phím Esc để đóng.", "2. Chế độ Phóng To Tương Tác (Zoom & Pan Lightbox):")

    add_embedded_image_if_exists(doc, "docs/manual_assets/img_ai_detect_demo.jpg", "6.2", "Minh họa ảnh AI khoanh vùng đánh số học sinh và nhận diện bàn trống", width_inches=6.0)

    # ==============================================================================
    # CHƯƠNG 7: QUẢN TRỊ CAMERA, ĐẦU GHI NVR & LƯỚI MA TRẬN TV WALL
    # ==============================================================================
    add_custom_heading(doc, "CHƯƠNG 7: QUẢN TRỊ CAMERA, ĐẦU GHI NVR & LƯỚI MA TRẬN TV WALL", level=1)
    add_body_paragraph(doc, "Phân hệ Camera & Lớp Học (truy cập qua menu 'Camera & Lớp Học' - đường dẫn /cameras) cho phép người quản lý giám sát hình ảnh trực tiếp toàn bộ 30 phòng học trên một màn hình duy nhất theo tiêu chuẩn TV Wall của các trung tâm an ninh hiện đại.")

    add_screenshot_placeholder(doc, "7.1", "Giao diện Lưới Ma Trận TV Wall 30 Camera Lớp Học", "Trang cameras.html (Hiển thị thẻ 30 camera kèm OSD, trạng thái Live và ảnh mới nhất)")

    add_custom_heading(doc, "7.1. Màn Hình Lưới Ma Trận TV Wall 30/32 Ô", level=2)
    add_body_paragraph(doc, "Mỗi thẻ phòng học trên lưới ma trận cung cấp đầy đủ thông tin giám sát:")
    add_bullet_item(doc, "Ảnh chụp khung hình mới nhất thu được từ nguồn camera của lớp học đó.", "Màn hình camera:")
    add_bullet_item(doc, "Mã lớp học (ví dụ: LOP_10A1) và chấm tròn trạng thái tín hiệu (Chấm xanh lá: kết nối tốt / Chấm đỏ: mất kết nối hoặc camera tắt).", "Dải OSD trên cùng:")
    add_bullet_item(doc, "Tên lớp học, số phòng, sĩ số chuẩn và nút menu ba chấm tác vụ.", "Chân thẻ phòng học:")
    add_bullet_item(doc, "Nhấp vào menu ba chấm trên từng thẻ để mở menu chức năng: 'Chỉnh sửa thông tin', 'Xem trực tiếp phóng to', 'Vẽ vùng ROI', 'Thử bật đèn hồng ngoại' hoặc 'Xóa camera'.", "Menu tác vụ nhanh:")

    add_custom_heading(doc, "7.2. Thao Tác Chọn Nhiều Phòng Học & Xóa Hàng Loạt (Batch Actions)", level=2)
    add_body_paragraph(doc, "Khi cần xử lý hoặc xóa đồng loạt nhiều phòng học, người dùng thực hiện:")
    add_bullet_item(doc, "Tích chọn vào ô vuông checkbox ở góc trên bên trái của các thẻ camera cần xử lý. Ngay lập tức, thanh công cụ tác vụ hàng loạt (Batch Action Bar) màu xanh đậm sẽ trượt xuống phía trên lưới.", "Bước 1:")
    add_bullet_item(doc, "Thanh tác vụ hiển thị số lượng phòng đã chọn. Người dùng có thể bấm 'Chọn tất cả', 'Bỏ chọn' hoặc bấm nút 'Xóa đã chọn' màu đỏ.", "Bước 2:")
    add_bullet_item(doc, "Hệ thống sẽ hiển thị hộp thoại xác nhận cảnh báo an toàn. Nhấp 'Xác nhận xóa' để hoàn tất.", "Bước 3:")

    add_custom_heading(doc, "7.3. Thêm Mới Camera Đơn Lẻ Hoặc Sử Dụng Webcam Máy Tính", level=2)
    add_body_paragraph(doc, "Để thêm một camera hoặc cấu hình lại một phòng học riêng lẻ:")
    add_bullet_item(doc, "Nhấp vào nút 'Thêm Camera / Lớp' ở góc trên bên phải màn hình. Hộp thoại cấu hình mở ra.", "Bước 1:")
    add_bullet_item(doc, "Điền các thông tin hành chính: Mã Lớp / Camera (ví dụ: LOP_10A1), Tên Lớp Học (Lớp 10A1), Phòng Học (Phòng 101), Sĩ Số Chuẩn (40).", "Bước 2:")
    add_bullet_item(doc, "Hệ thống hỗ trợ 3 nguồn cấp hình ảnh qua 3 tab chuyên biệt:", "Bước 3 - Chọn loại nguồn hình ảnh:")
    add_bullet_item(doc, "Tự động quét toàn bộ webcam vật lý và webcam ảo kết nối với máy tính, hiển thị khung ảnh xem trước. Người dùng chỉ cần nhấp chọn một thẻ webcam.", "• Tab Webcam Máy Tính (PC):")
    add_bullet_item(doc, "Dành cho camera IP của trường học. Có sẵn nút 'Mẫu nhanh' cho đầu ghi Dahua hoặc camera Hikvision. Nhập chuỗi RTSP chuẩn.", "• Tab Camera IP Trường (RTSP):")
    add_bullet_item(doc, "Dành cho kịch bản thử nghiệm ngoại tuyến hoặc diễn tập. Có sẵn các nút mẫu trỏ tới file video 15 giây hoặc ảnh mẫu chuẩn.", "• Tab Video / Ảnh Mẫu (File):")
    add_bullet_item(doc, "Nhấp nút 'Bắt Ảnh Xem Trước' để kiểm tra kết nối mạng. Nếu có trang bị relay/đèn camera, nhấp 'Thử Chu Trình: Bật Đèn Báo -> Bắt Ảnh Màu' để kiểm tra đèn sáng và ảnh chụp có đủ màu sắc.", "Bước 4 - Thử nghiệm tín hiệu:")
    add_bullet_item(doc, "Nhấp nút 'Lưu Camera'. Hệ thống sẽ tự động lưu vào CSDL và khởi tạo vùng nhận diện chuẩn cho lớp đó.", "Bước 5:")

    add_custom_heading(doc, "7.4. Thêm Tự Động 30 Camera Từ Đầu Ghi NVR (Quét Siêu Tốc)", level=2)
    add_body_paragraph(doc, "Đây là tính năng thông minh vượt trội giúp triển khai đồng loạt 30 lớp học chỉ trong 1 lần thiết lập duy nhất:")
    add_bullet_item(doc, "Nhấp nút 'Thêm Đầu Ghi' (màu xanh lá) trên thanh tiêu đề. Cửa sổ thiết lập NVR mở ra.", "Bước 1:")
    add_bullet_item(doc, "Nhấp nút 'Mẫu Chuẩn Điều Cải (192.168.10.200)'. Toàn bộ IP, cổng RTSP 554, hãng Dahua và 30 kênh sẽ được điền tự động chính xác.", "Bước 2:")
    add_bullet_item(doc, "Nhấp nút 'Quét Kênh Camera & Xem Trước Thumbnail'. Máy chủ sẽ sử dụng tiến trình đa luồng quét song song toàn bộ 30 kênh và hiển thị ảnh xem trước trực tiếp của từng phòng học trong 2-4 giây.", "Bước 3:")
    add_bullet_item(doc, "Người quản lý có thể điều chỉnh lại Tên lớp, Phòng hoặc Sĩ số trực tiếp trên từng ô nếu cần thiết.", "Bước 4:")
    add_bullet_item(doc, "Tích chọn ô 'Khởi tạo mới: Thay thế toàn bộ danh sách camera cũ' và nhấp nút 'Lưu & Đồng Bộ 30 Camera Vào Hệ Thống'. Toàn bộ 30 lớp học được nạp hoàn chỉnh vào CSDL.", "Bước 5:")

    # ==============================================================================
    # CHƯƠNG 8: CẤU HÌNH VÙNG NHẬN DIỆN BÀN HỌC SINH (GREEN ZONE ROI)
    # ==============================================================================
    add_custom_heading(doc, "CHƯƠNG 8: CẤU HÌNH VÙNG NHẬN DIỆN BÀN HỌC SINH (GREEN ZONE ROI)", level=1)

    add_custom_heading(doc, "8.1. Nguyên Lý Vùng Không Gian Nhận Diện (Spatial Masking)", level=2)
    add_body_paragraph(doc, "Trong một phòng học thông thường, có nhiều đối tượng xuất hiện không thuộc sĩ số học sinh ngồi học: Giáo viên đứng giảng bài tại bục giảng, giáo viên ngồi chấm bài ở bàn giáo viên, hoặc học sinh lớp khác đi lại ngoài hành lang sát cửa sổ.")
    add_body_paragraph(doc, "Để đảm bảo AI tính sĩ số chính xác 100%, hệ thống áp dụng nguyên tắc Vùng Nhận Diện Độc Quyền (Green Zone):")
    add_bullet_item(doc, "Người quản lý dùng chuột vẽ một đa giác màu xanh lá cây bao quanh toàn bộ khu vực các dãy bàn học sinh. AI chỉ quét, đếm và đánh số thứ tự cho những người ngồi bên trong vùng đa giác này.", "• Vùng Nhận Diện (Green Zone - Phần LẤY):")
    add_bullet_item(doc, "Toàn bộ khu vực nằm ngoài vùng xanh lá (bục giảng giáo viên, bàn giáo viên, cửa ra vào, cửa sổ ngoài hành lang) sẽ mặc định tự động bị bỏ qua 100%. Giáo viên có thể thoải mái giảng bài hoặc di chuyển mà không bao giờ bị tính nhầm vào sĩ số học sinh.", "• Mặc định Bỏ Qua Bên Ngoài (Phần BỎ ĐI):")

    add_embedded_image_if_exists(doc, "docs/manual_assets/img_roi_demo.jpg", "8.1", "Giao diện công cụ vẽ đa giác Vùng Nhận Diện (Bàn học sinh) trên nền ảnh thực tế", width_inches=6.0)

    add_custom_heading(doc, "8.2. Hướng Dẫn Thao Tác Vẽ & Căn Chỉnh Vùng Nhận Diện", level=2)
    add_body_paragraph(doc, "Truy cập màn hình 'Vùng ROI' (đường dẫn /roi-config) và thực hiện tuần tự theo các bước:")
    add_bullet_item(doc, "Tại hộp chọn 'Lớp Học' ở thanh công cụ trên cùng, chọn lớp học cần cấu hình (ví dụ: Lớp 10A1).", "Bước 1 - Chọn phòng học:")
    add_bullet_item(doc, "Nhấp nút 'Chụp Lại Ảnh' (hình camera). Hệ thống sẽ phát lệnh tới camera lớp học đó để lấy về khung hình trực tiếp sắc nét nhất.", "Bước 2 - Lấy khung hình mới nhất:")
    add_bullet_item(doc, "Bảo đảm nút 'Vẽ Vùng Nhận Diện (Bàn Học)' đang được kích hoạt (viền xanh lá). Nhấp chuột trái vào các góc quanh khu vực dãy bàn học sinh để tạo các điểm neo đa giác nối liền nhau.", "Bước 3 - Vẽ đa giác:")
    add_bullet_item(doc, "Người dùng có thể giữ chuột trái vào bất kỳ điểm neo nào để kéo điều chỉnh đường viền cho sát với dãy bàn. Nhấp chuột phải vào một điểm neo để xóa riêng điểm đó. Nhấn tổ hợp phím Ctrl + Z để hoàn tác điểm vừa vẽ nhầm. Nhấp 'Bắt 4 Góc Ảnh' nếu phòng học có góc camera nhìn trọn vẹn toàn bộ phòng.", "Bước 4 - Tinh chỉnh điểm neo:")
    add_bullet_item(doc, "Nhấp vào nút 'Lưu Tọa Độ Vùng' (màu xanh dương đậm).", "Bước 5 - Lưu và tự động đồng bộ AI:")

    add_callout(doc, "TÍNH NĂNG ĐỒNG BỘ AI TỨC THÌ:", [
        "Ngay sau khi người dùng nhấn 'Lưu Tọa Độ Vùng', hệ thống không chỉ lưu tọa độ vào CSDL mà còn TỰ ĐỘNG CHẠY LẠI AI (Rescan) trên khung hình mới nhất của lớp học đó.",
        "Kết quả sĩ số hiện diện mới và ảnh đối chứng khoanh vùng sẽ được đồng bộ ngay lập tức sang bảng Dashboard mà không cần người dùng phải bấm quét lại toàn trường."
    ], "tip")

    # ==============================================================================
    # CHƯƠNG 9: BÁO CÁO, KHO LƯU TRỮ EXCEL & TRUNG TÂM SAO LƯU CSDL
    # ==============================================================================
    add_custom_heading(doc, "CHƯƠNG 9: BÁO CÁO, KHO LƯU TRỮ EXCEL & TRUNG TÂM SAO LƯU CSDL", level=1)
    add_body_paragraph(doc, "Phân hệ Báo Cáo & Dữ Liệu (menu 'Báo Cáo & Dữ Liệu' - /reports) là kho lưu trữ dữ liệu trung tâm của trường học, bao gồm 3 tab chức năng nghiệp vụ chuyên biệt:")

    add_screenshot_placeholder(doc, "9.1", "Giao diện Trung tâm Dữ liệu & Báo cáo Điểm danh", "Trang reports.html (Bao gồm Tab CSDL, Tab Kho Excel và Tab Cài đặt lưu trữ / Backup)")

    add_custom_heading(doc, "9.1. Tab 1 - Lưu Trữ Kết Quả Điểm Danh CSDL", level=2)
    add_body_paragraph(doc, "Lưu giữ toàn bộ lịch sử điểm danh của từng lớp học qua các ngày với đầy đủ ảnh gốc và ảnh AI đối chứng:")
    add_bullet_item(doc, "Lọc theo Khối (10, 11, 12, Tất cả); Lọc theo Trạng thái (Tất cả, Có vắng, Đủ sĩ số); Lọc theo Ngày (chọn ngày cụ thể từ lịch, bấm 'Hôm nay' hoặc xóa lọc); Ô tìm kiếm lớp, phòng, mã phiên.", "Bộ lọc đa chiều đồng nhất:")
    add_bullet_item(doc, "STT, Ngày giờ quét, Mã phiên (ví dụ: SESSION_20260924_0645), Lớp học, Phòng, Sĩ số, Có mặt, Vắng, Ảnh gốc, Ảnh AI, Trạng thái.", "Các cột bảng:")
    add_bullet_item(doc, "Nhấp trực tiếp vào ảnh gốc hoặc ảnh AI để mở trình xem ảnh phóng to toàn màn hình (hỗ trợ lăn chuột zoom và kéo pan).", "Xem ảnh đối chứng:")
    add_bullet_item(doc, "Hỗ trợ phân trang 15, 30 (1 ca học), 60 (2 ca học) hoặc 100 dòng trên một trang.", "Phân trang thông minh:")

    add_custom_heading(doc, "9.2. Tab 2 - Kho Lưu Trữ File Excel Báo Cáo Tổng Hợp", level=2)
    add_body_paragraph(doc, "Hệ thống tự động biên soạn và lưu trữ các file Microsoft Excel (.xlsx) tổng hợp 30 lớp học theo đúng mẫu quy chuẩn của Sở GD&ĐT Đồng Nai:")
    add_bullet_item(doc, "Tiêu đề chuẩn mực của Trường THPT Điểu Cải, bảng tổng hợp sĩ số 30 lớp học theo ca học, công thức tính tổng tự động (SUM), highlight màu sắc cảnh báo các lớp có học sinh vắng, tỷ lệ chuyên cần và khung chữ ký người lập biểu cùng Ban Giám Hiệu.", "Định dạng file Excel:")
    add_bullet_item(doc, "Nhấp nút 'Xuất Báo Cáo Excel Ngay' ở góc phải để tạo ngay file báo cáo của ca điểm danh gần nhất.", "Xuất file tức thì:")
    add_bullet_item(doc, "Lọc danh sách file Excel theo Ngày tạo, theo Ca học (Tất cả, Ca Sáng, Ca Chiều) hoặc tìm kiếm theo tên file.", "Tra cứu file đã lưu:")
    add_bullet_item(doc, "Nhấp nút 'Tải về' (màu xanh lá) tại cột Thao Tác để lưu file .xlsx về máy tính cá nhân để in ấn hoặc nộp báo cáo.", "Tải file:")

    add_custom_heading(doc, "9.3. Tab 3 - Cài Đặt Lưu Trữ & Trung Tâm Sao Lưu CSDL (Backup & Restore)", level=2)
    add_body_paragraph(doc, "Tab này dành riêng cho công tác quản trị và bảo dưỡng dữ liệu hệ thống:")
    
    add_body_paragraph(doc, "Thiết lập thời gian bảo lưu dữ liệu điểm danh trong CSDL (30 ngày, 60 ngày, 90 ngày - khuyến nghị 1 học kỳ, 180 ngày hoặc 365 ngày). Công tắc tự động xóa CSDL cũ và file Excel cũ giúp giải phóng dung lượng ổ cứng máy chủ. Nút 'Dọn dẹp dữ liệu quá hạn ngay' cho phép chủ động dọn dẹp tức thì.", "1. Quy định thời hạn lưu trữ (Data Retention Policy):")

    add_body_paragraph(doc, "Chức năng tối quan trọng bảo vệ an toàn thông tin (Chỉ Quản trị viên Admin được thao tác):", "2. Trung Tâm Sao Lưu & Phục Hồi Dữ Liệu (Backup & Restore):")
    add_bullet_item(doc, "Máy chủ tự động nén toàn bộ CSDL và cấu hình thành file .zip vào lúc 23:00 mỗi đêm (lưu giữ 15 bản sao lưu gần nhất).", "• Tự động sao lưu hàng đêm:")
    add_bullet_item(doc, "Nhấp nút 'Tạo Bản Sao Lưu Ngay'. Hệ thống lập tức đóng gói CSDL hiện tại vào gói nén an toàn dạng backup_THPTDieuCai_YYYYMMDD_HHMMSS.zip.", "• Tạo bản sao lưu thủ công:")
    add_bullet_item(doc, "Tại bảng danh sách bản sao lưu, nhấp nút Tải xuống để lưu trữ file .zip về ổ cứng ngoài hoặc lưu trữ đám mây của nhà trường.", "• Tải file về máy tính:")
    add_bullet_item(doc, "Trong trường hợp máy chủ gặp sự cố hoặc cần khôi phục lại dữ liệu ngày trước, Quản trị viên chỉ cần nhấp nút 'Khôi phục' tại bản sao lưu mong muốn hoặc nhấp 'Tải Lên & Khôi Phục' để tải file .zip từ máy tính lên. Hệ thống sẽ kiểm tra tính toàn vẹn và phục hồi toàn bộ dữ liệu chỉ trong vài giây.", "• Phục hồi dữ liệu (Restore):")

    add_callout(doc, "LƯU Ý KHI PHỤC HỒI DỮ LIỆU:", [
        "Thao tác Khôi phục Dữ liệu (Restore) sẽ ghi đè CSDL hiện tại bằng dữ liệu của bản sao lưu.",
        "Trước khi phục hồi, hệ thống luôn tự động tạo một bản snapshot dự phòng để bảo vệ an toàn.",
        "Chỉ Quản trị viên hệ thống (Admin) mới có quyền truy cập và thực thi các thao tác này."
    ], "alert")

    # ==============================================================================
    # CHƯƠNG 10: CẤU HÌNH PHÂN PHỐI THÔNG BÁO TỰ ĐỘNG (ZALO & EMAIL)
    # ==============================================================================
    add_custom_heading(doc, "CHƯƠNG 10: CẤU HÌNH PHÂN PHỐI THÔNG BÁO TỰ ĐỘNG (ZALO & EMAIL)", level=1)
    add_body_paragraph(doc, "Phân hệ Thông Báo (menu 'Thông Báo' - /notifications) quản lý các kênh thông tin gửi báo cáo tức thời tới phụ trách nhà trường:")

    add_screenshot_placeholder(doc, "10.1", "Giao diện Cấu hình Thông báo Zalo, Email & Lịch trình", "Trang notifications.html (Bao gồm Tab Zalo, Tab Email, Tab Điều chỉnh mẫu và Tab Lịch trình)")

    add_custom_heading(doc, "10.1. Cấu Hình Gửi Tin Nhắn Zalo Bot Gateway (Khuyến Nghị)", level=2)
    add_body_paragraph(doc, "Zalo Bot Gateway là phương thức truyền tin hiện đại và ổn định nhất của hệ thống:")
    add_bullet_item(doc, "Chọn phương thức 'Zalo Bot Gateway (API Key + Bot ID) - Khuyến nghị'. Điền API Key, Bot ID và Base URL do đơn vị cung cấp gateway cấp.", "Cấu hình cổng kết nối:")
    add_bullet_item(doc, "Hệ thống hỗ trợ quản lý danh sách tối đa 30 số điện thoại người nhận phân loại theo 2 nhóm vai trò riêng biệt:", "Quản lý người nhận theo vai trò:")
    add_bullet_item(doc, "Nhận báo cáo tổng hợp sĩ số toàn bộ 30 lớp học và danh sách các lớp có học sinh vắng.", "• Ban Giám Hiệu (school):")
    add_bullet_item(doc, "Chọn lớp chủ nhiệm tương ứng (ví dụ: Lớp 10A1). Thầy/Cô chỉ nhận báo cáo chi tiết riêng của lớp mình quản lý (sĩ số, số vắng, danh sách em vắng), bảo đảm tính riêng tư và đúng đối tượng.", "• Giáo Viên Chủ Nhiệm (class):")
    add_bullet_item(doc, "Nhấp nút 'Lưu Cấu Hình' để áp dụng. Nhấp nút 'Gửi Tin Nhắn Báo Cáo Zalo Ngay' để kiểm tra tin nhắn gửi đến điện thoại thực tế.", "Kiểm tra và lưu trữ:")

    add_custom_heading(doc, "10.2. Cấu Hình Gửi Email Báo Cáo Cho Hiệu Trưởng", level=2)
    add_body_paragraph(doc, "Hệ thống tự động đính kèm file báo cáo Excel gửi về hộp thư điện tử của Ban Giám Hiệu:")
    add_bullet_item(doc, "Nhập địa chỉ hòm thư email của Hiệu trưởng hoặc hòm thư văn thư trường học (ví dụ: hieutruong@truongdieucai.edu.vn).", "Địa chỉ người nhận:")
    add_bullet_item(doc, "Hệ thống hiển thị đường dẫn thư mục lưu trữ bản sao dùng chung nội bộ (storage/reports/latest/).", "Thư mục dùng chung:")
    add_bullet_item(doc, "Nhấp 'Lưu Email Người Nhận'. Có thể nhấp nút 'Gửi Thử Email Báo Cáo Cho Hiệu Trưởng' để kiểm tra kết nối SMTP.", "Thao tác:")

    add_custom_heading(doc, "10.3. Tùy Biến Mẫu Tin Nhắn & Xem Trước Trực Tiếp (Phone Mockup)", level=2)
    add_body_paragraph(doc, "Tại tab 'Điều Chỉnh Thông Báo', nhà trường có thể toàn quyền tùy biến câu chữ và quy tắc phát tin:")
    add_bullet_item(doc, "Công tắc bật/tắt gửi Zalo; Công tắc bật/tắt gửi Email. Lựa chọn điều kiện gửi: 'Luôn phát thông báo sau mỗi ca quét' hoặc 'Chỉ gửi thông báo khi có học sinh vắng' (giúp tiết kiệm tin nhắn khi 100% học sinh đi học đủ).", "1. Quy tắc kích hoạt & Ngưỡng cảnh báo:")
    add_bullet_item(doc, "Cảnh báo đỏ toàn trường (mặc định vắng > 10%); Ngưỡng vắng riêng 1 lớp (mặc định vắng >= 3 em sẽ gắn cảnh báo riêng tới GVCN).", "2. Thiết lập ngưỡng báo động:")
    add_bullet_item(doc, "Nhà trường có thể chỉnh sửa mẫu văn bản cho từng đối tượng (Zalo BGH, Zalo GVCN, Email). Nhấp vào các thẻ biến dữ liệu bên trên để chèn tự động vào nội dung:", "3. Soạn thảo mẫu tin nhắn:")
    add_bullet_item(doc, "Thẻ biến {ngay} (ngày quét), {gio} (giờ quét), {tong_lop} (tổng số lớp), {si_so} (sĩ số chuẩn), {co_mat} (số học sinh có mặt), {vang_mat} (số học sinh vắng), {ty_le} (tỷ lệ chuyên cần %), {danh_sach_vang} (danh sách chi tiết lớp vắng), {lop} (tên lớp), {phong} (số phòng).", "• Danh mục biến dữ liệu:")
    add_bullet_item(doc, "Cột bên phải hiển thị một mô hình điện thoại thông minh mô phỏng giao diện Zalo thực tế. Khi người dùng chỉnh sửa câu chữ hoặc chèn biến, màn hình mô phỏng lập tức thay thế bằng số liệu điểm danh mới nhất để người dùng kiểm tra trước khi lưu.", "4. Màn hình mô phỏng trực tiếp (Live Phone Mockup):")

    add_custom_heading(doc, "10.4. Lập Lịch Quét & Phân Phối Tự Động (Ca Sáng 06:45 & Ca Chiều 12:45)", level=2)
    add_body_paragraph(doc, "Tại tab 'Lịch Trình Tự Động', hệ thống hiển thị thông tin tiến trình nền APScheduler chạy ngầm:")
    add_bullet_item(doc, "Tự động kích hoạt lúc 06:45 sáng (Thứ 2 đến Thứ 7 hàng tuần) trước giờ truy bài đầu giờ.", "• Ca Quét 1 (Đầu giờ sáng):")
    add_bullet_item(doc, "Tự động kích hoạt lúc 12:45 chiều (Thứ 2 đến Thứ 7 hàng tuần) phục vụ các khối lớp học ca chiều.", "• Ca Quét 2 (Đầu giờ chiều):")
    add_bullet_item(doc, "Nhấp nút 'Chỉnh Sửa Giờ Quét' để mở hộp thoại cấu hình. Người quản trị có thể thay đổi giờ quét sáng/chiều và chọn các ngày hoạt động trong tuần (Thứ 2 - Thứ 7, Thứ 2 - Thứ 6 hoặc Cả tuần). Nhấp 'Lưu Cài Đặt Lịch Trình' để cập nhật.", "• Thay đổi giờ quét:")

    # ==============================================================================
    # CHƯƠNG 11: QUẢN LÝ TÀI KHOẢN NGƯỜI DÙNG & PHÂN QUYỀN (ADMIN ONLY)
    # ==============================================================================
    add_custom_heading(doc, "CHƯƠNG 11: QUẢN LÝ TÀI KHOẢN NGƯỜI DÙNG & PHÂN QUYỀN (ADMIN ONLY)", level=1)
    add_body_paragraph(doc, "Trang Quản Lý Tài Khoản (menu 'Tài Khoản' - /users) là khu vực được bảo mật cao nhất, chỉ tài khoản có vai trò Quản Trị Viên (Admin) mới có quyền truy cập.")

    add_screenshot_placeholder(doc, "11.1", "Giao diện Quản lý Tài khoản & Phân quyền Người dùng", "Trang users.html (Bao gồm bảng danh sách, modal tạo tài khoản và modal chỉnh sửa thông tin)")

    add_custom_heading(doc, "11.1. Xem Danh Sách Tài Khoản & Thống Kê", level=2)
    add_body_paragraph(doc, "Màn hình cung cấp 4 thẻ thống kê: Tổng số tài khoản, Số quản trị viên, Số nhân viên và Số tài khoản đang hoạt động. Bảng dữ liệu hiển thị chi tiết: Họ tên cán bộ, Email đăng nhập, Vai trò (Quản trị viên / Nhân viên), Trạng thái (Hoạt động / Tạm khóa) và các nút thao tác.")

    add_custom_heading(doc, "11.2. Thêm Mới Tài Khoản Cho Cán Bộ / Giáo Viên", level=2)
    add_body_paragraph(doc, "Để cấp tài khoản mới cho cán bộ nhà trường:")
    add_bullet_item(doc, "Nhấp nút 'Thêm Tài Khoản' ở góc trên bên phải màn hình. Hộp thoại mở ra.", "Bước 1:")
    add_bullet_item(doc, "Nhập đầy đủ: Họ Tên (ví dụ: Thầy Nguyễn Văn A), Email Đăng Nhập (@truongdieucai.edu.vn), chọn Vai Trò ('Nhân Viên' hoặc 'Quản Trị Viên') và Mật Khẩu Khởi Tạo (tối thiểu 8 ký tự).", "Bước 2:")
    add_bullet_item(doc, "Nhấp nút 'Tạo Tài Khoản'. Người dùng có thể sử dụng thông tin này để đăng nhập ngay lập tức.", "Bước 3:")

    add_custom_heading(doc, "11.3. Chỉnh Sửa Thông Tin, Đặt Lại Mật Khẩu & Khóa Tài Khoản", level=2)
    add_bullet_item(doc, "Nhấp vào biểu tượng chiếc bút tại cột Thao Tác. Quản trị viên có thể cập nhật Họ tên, Email, đổi Vai trò hoặc gõ mật khẩu mới (nếu cần đặt lại mật khẩu cho cán bộ).", "Chỉnh sửa thông tin / Đổi mật khẩu:")
    add_bullet_item(doc, "Nhấp vào biểu tượng công tắc / ổ khóa tại cột Thao Tác để chuyển đổi giữa trạng thái Hoạt Động (Active) và Tạm Khóa (Inactive). Khi tài khoản bị tạm khóa, người đó không thể đăng nhập vào hệ thống.", "Tạm khóa / Kích hoạt lại tài khoản:")

    add_callout(doc, "RÀNG BUỘC BẢO VỆ AN TOÀN HỆ THỐNG:", [
        "Hệ thống KHÔNG cho phép Quản trị viên tự tắt hoặc tạm khóa tài khoản của chính mình khi đang đăng nhập.",
        "Hệ thống bắt buộc phải luôn duy trì ít nhất MỘT tài khoản Quản trị viên (Admin) đang hoạt động để tránh tình trạng hệ thống bị mất quyền điều khiển."
    ], "warn")

    # ==============================================================================
    # CHƯƠNG 12: HƯỚNG DẪN CÁC QUY TRÌNH VẬN HÀNH NGHIỆP VỤ THỰC TẾ
    # ==============================================================================
    add_custom_heading(doc, "CHƯƠNG 12: HƯỚNG DẪN CÁC QUY TRÌNH VẬN HÀNH NGHIỆP VỤ THỰC TẾ", level=1)
    add_body_paragraph(doc, "Dưới đây là các kịch bản vận hành thực tế tại Trường THPT Điểu Cải:")

    add_custom_heading(doc, "12.1. Quy Trình Vận Hành Điểm Danh Hàng Ngày (Ca Sáng 06:45 & Ca Chiều 12:45)", level=2)
    add_bullet_item(doc, "Đến đúng 06:45 (hoặc 12:45), tiến trình nền tự động kích hoạt đèn hồng ngoại camera lớp học trong 3 giây để báo hiệu giờ điểm danh, sau đó tự động chụp đồng loạt 30 luồng camera.", "1. Tự động quét:")
    add_bullet_item(doc, "Hệ thống AI áp dụng bộ lọc CLAHE chống ngược sáng, phân mảnh quét chi tiết SAHI và đếm số học sinh trong vùng nhận diện Green Zone.", "2. Phân tích AI:")
    add_bullet_item(doc, "Số liệu được lưu vào CSDL, file Excel được biên soạn tự động và tin nhắn thông báo tóm tắt được gửi thẳng tới điện thoại Zalo của Ban Giám Hiệu cùng GVCN.", "3. Xuất kết quả:")
    add_bullet_item(doc, "Cán bộ Giám thị hoặc BGH mở Dashboard để kiểm tra tổng quan toàn trường. Nếu phát hiện lớp có học sinh vắng, nhấp 'Xem ảnh' để đối chứng.", "4. Giám sát & Xử lý:")

    add_custom_heading(doc, "12.2. Quy Trình Kiểm Tra & Xử Lý Đối Chứng Khi Phát Hiện Lớp Có Học Sinh Vắng", level=2)
    add_bullet_item(doc, "Trên Dashboard, nhấp vào tab trạng thái 'Có vắng' để lọc danh sách các lớp có học sinh vắng.", "1. Lọc lớp vắng:")
    add_bullet_item(doc, "Tại dòng của lớp học cần kiểm tra, nhấp nút 'Xem ảnh' ở cột Ảnh Đối Chứng.", "2. Mở ảnh đối chứng:")
    add_bullet_item(doc, "Đối chiếu giữa ảnh gốc camera và ảnh AI khoanh vùng. Kiểm tra vị trí bàn trống và số lượng học sinh được đánh số thứ tự.", "3. Đối soát:")
    add_bullet_item(doc, "Nếu có học sinh vừa vào lớp sau giờ quét hoặc camera chụp lúc học sinh đứng lên phát biểu, Giám thị có thể nhấp nút 'Quét lại' ở cột Thao Tác. Hệ thống sẽ chụp lại ảnh mới nhất và nhận diện lại riêng cho lớp học đó trong 2 giây.", "4. Cập nhật lại (nếu cần):")

    add_custom_heading(doc, "12.3. Quy Trình Triển Khai Phòng Học Mới Hoặc Thay Đổi Vị Trí Bàn Ghế", level=2)
    add_bullet_item(doc, "Nếu trường bổ sung phòng học mới: Vào /cameras, nhấp 'Thêm Camera / Lớp', nhập thông tin và kiểm tra kết nối camera thành công.", "1. Thêm camera:")
    add_bullet_item(doc, "Nếu lớp học kê lại bàn ghế hoặc thay đổi góc quay camera: Vào /roi-config, chọn lớp học đó.", "2. Truy cập công cụ ROI:")
    add_bullet_item(doc, "Nhấp 'Chụp Lại Ảnh', sau đó dùng chuột vẽ lại đa giác Green Zone bao quanh toàn bộ khu vực bàn học sinh mới.", "3. Vẽ lại vùng nhận diện:")
    add_bullet_item(doc, "Nhấp 'Lưu Tọa Độ Vùng'. Hệ thống tự động phân tích lại và sẵn sàng cho các ca quét tiếp theo.", "4. Lưu và áp dụng:")

    add_custom_heading(doc, "12.4. Quy Trình Sao Lưu Định Kỳ & Bảo Trì Hệ Thống Cuối Học Kỳ", level=2)
    add_bullet_item(doc, "Vào /reports, chuyển sang tab 'Cài Đặt Lưu Trữ & CSDL'.", "1. Truy cập Trung tâm Backup:")
    add_bullet_item(doc, "Nhấp 'Tạo Bản Sao Lưu Ngay'. Tải file .zip về lưu trữ an toàn.", "2. Tạo bản sao lưu:")
    add_bullet_item(doc, "Kiểm tra thời hạn lưu trữ (khuyến nghị 90 hoặc 180 ngày). Nhấp 'Dọn Dẹp Dữ Liệu Quá Hạn Ngay' để dọn sạch các file ảnh cũ giải phóng ổ cứng cho học kỳ mới.", "3. Dọn dẹp ổ cứng:")

    # ==============================================================================
    # CHƯƠNG 13: XỬ LÝ LỖI & SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)
    # ==============================================================================
    add_custom_heading(doc, "CHƯƠNG 13: XỬ LÝ LỖI & SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)", level=1)
    add_body_paragraph(doc, "Bảng tổng hợp các tình huống sự cố thường gặp trong thực tế và biện pháp xử lý chuẩn xác:")

    trouble_headers = ["HIỆN TƯỢNG SỰ CỐ", "NGUYÊN NHÂN KHẢ DĨ", "HƯỚNG DẪN XỬ LÝ CHI TIẾT"]
    trouble_rows = [
        ["Không mở được trang web (báo Lỗi kết nối / This site can't be reached).", "Máy chủ chưa khởi động hoặc tiến trình phần mềm bị tắt ngoài ý muốn.", "Kiểm tra máy chủ tại trường. Nhấp đúp chuột vào tệp 'run.bat' trên màn hình Desktop máy chủ. Chờ cửa sổ thông báo chạy thành công tại cổng 8000, sau đó tải lại trình duyệt (nhấn F5)."],
        ["Đăng nhập thất bại (báo 'Email hoặc mật khẩu không đúng').", "Gõ sai email, mật khẩu hoặc đang bật phím CapsLock / gõ tiếng Việt.", "Tắt gõ tiếng Việt, kiểm tra kỹ chữ hoa chữ thường. Nếu vẫn không được, nhấp 'Quên mật khẩu' để nhận email khôi phục hoặc liên hệ Quản trị viên để đặt lại mật khẩu."],
        ["Thẻ camera báo chấm đỏ 'Mất kết nối' hoặc ảnh bị đen.", "Camera lớp học bị ngắt nguồn, lỏng dây mạng LAN hoặc đổi địa chỉ IP.", "Kiểm tra nguồn camera tại phòng học. Vào trang 'Camera & Lớp Học', nhấp menu ba chấm -> Chỉnh sửa -> Nhấp 'Bắt Ảnh Xem Trước' để kiểm tra kết nối mạng nội bộ."],
        ["AI đếm thiếu học sinh ở dãy bàn cuối phòng.", "Góc nhìn camera quá xa, học sinh cúi gục đầu hoặc vùng nhận diện ROI vẽ chưa trùm hết dãy bàn.", "Vào trang 'Vùng ROI', chọn lớp đó, kiểm tra xem đa giác xanh lá đã bao trọn dãy bàn cuối chưa. Kéo điểm neo nới rộng về phía cuối phòng và nhấp 'Lưu Tọa Độ Vùng'."],
        ["Giáo viên đứng trên bục giảng bị tính nhầm vào sĩ số học sinh.", "Vùng nhận diện Green Zone vô tình vẽ lấn lên khu vực bục giảng hoặc bàn giáo viên.", "Vào trang 'Vùng ROI', chọn lớp đó. Kéo các điểm neo của vùng đa giác xanh lá lùi xuống, cách bục giảng ít nhất 20-30cm. Mọi khu vực ngoài vùng xanh sẽ bị loại trừ 100%."],
        ["Không nhận được tin nhắn báo cáo qua Zalo.", "Chưa bật công tắc Zalo, sai số điện thoại hoặc Zalo Bot Gateway đang tạm dừng.", "Vào trang 'Thông Báo' -> Tab 'Tin Nhắn Zalo'. Kiểm tra số điện thoại người nhận đã đúng cú pháp chưa (ví dụ: 0334551531). Nhấp 'Gửi Tin Nhắn Báo Cáo Zalo Ngay' để kiểm tra phản hồi từ cổng gateway."],
        ["Không nhận được email đính kèm file Excel.", "Hòm thư nhận nhập sai hoặc dịch vụ máy chủ chưa cấu hình mật khẩu ứng dụng SMTP.", "Vào trang 'Thông Báo' -> Tab 'Email Báo Cáo'. Kiểm tra địa chỉ email Hiệu trưởng. Bấm 'Gửi Thử Email Báo Cáo' để kiểm tra hệ thống thư."],
        ["Đồng hồ Dashboard hoặc thời gian ca quét bị lệch giờ.", "Múi giờ máy chủ hoặc trình duyệt chưa đồng bộ múi giờ Việt Nam.", "Hệ thống đã chuẩn hóa múi giờ Asia/Ho_Chi_Minh (GMT+7). Kiểm tra lại cài đặt giờ trên máy tính của bạn."]
    ]
    create_styled_table(doc, trouble_headers, trouble_rows, col_widths=[1.8, 2.0, 2.67], alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])

    # ==============================================================================
    # CHƯƠNG 14: CÂU HỎI THƯỜNG GẶP (FAQ)
    # ==============================================================================
    add_custom_heading(doc, "CHƯƠNG 14: CÂU HỎI THƯỜNG GẶP (FAQ)", level=1)

    faq_list = [
        ("1. Hệ thống có điểm danh nhầm khi học sinh đổi chỗ ngồi cho nhau không?",
         "Không. Hệ thống hoạt động theo nguyên lý đếm sĩ số hiện diện thực tế (Head & Upper Body Detection) kết hợp phân vùng không gian bàn học. Miễn là học sinh ngồi đúng vào vị trí bàn học trong phòng, hệ thống sẽ ghi nhận đầy đủ hiện diện mà không phụ thuộc vào vị trí ngồi cụ thể."),
        ("2. Nếu học sinh lớp khác đứng ngoài hành lang nhìn vào phòng thì có bị tính không?",
         "Hoàn toàn không. Nhờ thuật toán phân vùng đa giác ROI (Green Zone), hệ thống chỉ tính những người nằm bên trong ranh giới đa giác bàn học. Mọi người đứng ở hành lang, ngoài cửa sổ hay cửa ra vào đều tự động bị loại trừ 100%."),
        ("3. Giáo viên đứng giảng bài hoặc đi lại trong lớp có bị tính vào sĩ số học sinh không?",
         "Không. Bục giảng và lối đi phía trước nằm ngoài vùng nhận diện Green Zone nên giáo viên sẽ không bị tính. Nếu giáo viên đi xuống giữa các dãy bàn trong lúc quét, trường học có thể bật tính năng nhận diện bục giảng hoặc bấm 'Quét lại' sau khi giáo viên trở về vị trí giảng dạy."),
        ("4. Tôi có thể bấm quét điểm danh bất kỳ lúc nào hay phải đợi đến 06:45?",
         "Quý Thầy/Cô có thể nhấp nút 'Quét Điểm Danh' trên thanh tiêu đề Dashboard bất kỳ lúc nào trong ngày để kiểm tra sĩ số đột xuất. Lịch 06:45 và 12:45 là lịch tự động chạy ngầm cố định."),
        ("5. Khi cúp điện hoặc mất kết nối camera thì dữ liệu cũ có bị mất không?",
         "Tuyệt đối không. Toàn bộ lịch sử điểm danh, ảnh đối chứng và file Excel đều được lưu trữ an toàn trong CSDL SQLite trên ổ đĩa cứng máy chủ. Khi có điện lại, hệ thống sẽ tiếp tục hoạt động bình thường."),
        ("6. File Excel báo cáo có thể mở bằng Microsoft Excel hoặc Google Sheets không?",
         "Có. File báo cáo được định dạng chuẩn .xlsx tương thích hoàn hảo với Microsoft Excel 2010 trở lên, Office 365, Google Sheets và WPS Office.")
    ]
    for q, a in faq_list:
        add_body_paragraph(doc, a, bold_prefix=q, space_after=6)

    # ==============================================================================
    # CHƯƠNG 15: THUẬT NGỮ CHUYÊN NGÀNH & BẢNG KÝ HIỆU (GLOSSARY)
    # ==============================================================================
    add_custom_heading(doc, "CHƯƠNG 15: THUẬT NGỮ CHUYÊN NGÀNH & BẢNG KÝ HIỆU (GLOSSARY)", level=1)
    
    glossary_headers = ["THUẬT NGỮ", "Ý NGHĨA DỄ HIỂU TRONG HỆ THỐNG"]
    glossary_rows = [
        ["AI (Trí Tuệ Nhân Tạo)", "Thuật toán máy tính tự động nhìn và đếm người thay cho con người."],
        ["YOLO26m", "Phiên bản mô hình thị giác máy tính AI hiện đại nhất được tinh chỉnh riêng cho lớp học THPT Điểu Cải."],
        ["Green Zone (Vùng Xanh)", "Vùng đa giác bao quanh dãy bàn học sinh - khu vực duy nhất AI quét và tính sĩ số."],
        ["Spatial ROI Masking", "Kỹ thuật phân vùng không gian giúp loại trừ bục giảng và hành lang ngoài cửa sổ."],
        ["RTSP", "Giao thức truyền luồng hình ảnh video trực tiếp từ camera trường học về máy chủ."],
        ["NVR / DVR", "Đầu ghi hình camera tập trung nơi tiếp nhận tín hiệu từ 30 camera lớp học."],
        ["TV Wall", "Màn hình hiển thị đồng thời lưới ma trận toàn bộ 30 camera như trung tâm an ninh."],
        ["CLAHE", "Thuật toán lọc và cân bằng ánh sáng cục bộ chống ngược sáng cửa sổ."],
        ["SAHI", "Thuật toán cắt lát ảnh đa tỷ lệ giúp nhận diện sắc nét học sinh ở các dãy bàn xa camera."],
        ["JWT Token", "Chứng chỉ bảo mật phiên đăng nhập được mã hóa an toàn qua Cookie."],
        ["Zalo Bot Gateway", "Cổng dịch vụ tự động chuyển đổi số điện thoại và phát tin nhắn Zalo hàng loạt."]
    ]
    create_styled_table(doc, glossary_headers, glossary_rows, col_widths=[2.0, 4.47], alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])

    # ==============================================================================
    # CHƯƠNG 16: THÔNG TIN LIÊN HỆ & ĐẦU MỐI HỖ TRỢ KỸ THUẬT
    # ==============================================================================
    add_custom_heading(doc, "CHƯƠNG 16: THÔNG TIN LIÊN HỆ & ĐẦU MỐI HỖ TRỢ KỸ THUẬT", level=1)
    add_body_paragraph(doc, "Trong quá trình vận hành, nếu Quý Thầy/Cô và Cán bộ quản lý cần hỗ trợ thêm về mặt kỹ thuật, vui lòng liên hệ theo các đầu mối sau:")

    contact_headers = ["ĐƠN VỊ TIẾP NHẬN", "THÔNG TIN LIÊN HỆ", "THỜI GIAN TIẾP NHẬN"]
    contact_rows = [
        ["Tổ Quản trị Mạng - THPT Điểu Cải", "Phòng Thiết bị Tin học - Trường THPT Điểu Cải\nEmail: quantri@truongdieucai.edu.vn", "Giờ hành chính các ngày trong tuần (Thứ 2 - Thứ 7)"],
        ["Đội ngũ Kỹ sư Phần mềm & AI", "Hotline / Zalo Hỗ trợ Kỹ thuật: 0987.xxx.xxx\nEmail hỗ trợ: support@truongdieucai.edu.vn", "Hỗ trợ 24/7 (Đặc biệt ưu tiên khung giờ điểm danh 06:30 - 07:15)"],
        ["Bảo trì & Nâng cấp Hệ thống", "Theo biên bản bàn giao và hợp đồng chuyển đổi số giáo dục", "Định kỳ hàng quý hoặc khi có phiên bản cập nhật mới"]
    ]
    create_styled_table(doc, contact_headers, contact_rows, col_widths=[2.1, 2.7, 1.67], alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER])

    add_callout(doc, "LỜI KẾT & CAM KẾT CHẤT LƯỢNG:", [
        "Hệ thống Điểm danh Học sinh Tự động bằng AI Camera là bước tiến vững chắc trong công cuộc chuyển đổi số giáo dục tại Trường THPT Điểu Cải.",
        "Chúng tôi cam kết không ngừng đồng hành, lắng nghe phản hồi thực tế từ Quý Thầy Cô để hệ thống ngày càng hoạt động thông minh, tin cậy và mang lại giá trị cao nhất cho nhà trường."
    ], "tip")

    # ==============================================================================
    # LƯU FILE TÀI LIỆU
    # ==============================================================================
    target_files = [
        PROJECT_ROOT / "USER_MANUAL_THPT_DIEU_CAI_v1.0.docx",
        PROJECT_ROOT / "USER_MANUAL_v1.0.docx",
        PROJECT_ROOT / "docs" / "USER_MANUAL_THPT_DIEU_CAI_v1.0.docx"
    ]

    saved = []
    for tf in target_files:
        try:
            doc.save(str(tf))
            saved.append(tf)
            print(f"-> Đã lưu thành công: {tf.name} ({os.path.getsize(str(tf)):,} bytes)")
        except Exception as e:
            print(f"Lỗi khi lưu {tf}: {e}")

    print(f"\nHOÀN THÀNH XUẤT BẢN USER MANUAL CHUẨN MỰC TẠI {len(saved)} ĐƯỜNG DẪN!")

if __name__ == "__main__":
    build_manual()
