# Hướng dẫn dùng 3beditor

[English](PLAYBOOK.md) · **Tiếng Việt**

Hướng dẫn đơn giản để làm video đầu tiên. Không cần biết dựng phim: bạn chỉ cần nói với Claude, Claude sẽ dựng cho bạn.

---

## 1. Cài đặt (chỉ một lần, khoảng 5 phút)

Bạn cần có **Claude Code** ([tải tại đây](https://claude.com/claude-code)) trên máy tính.

**Bước 1. Cài hai công cụ miễn phí mà 3beditor dùng.** Mở Terminal (trên Windows: bấm phím Windows, gõ `Terminal`, bấm Enter) rồi dán dòng lệnh cho máy của bạn:

| Máy | Dán dòng này |
|---|---|
| Windows | `winget install Gyan.FFmpeg Python.Python.3.12` |
| Mac | `brew install ffmpeg python` |

Cài xong thì đóng Terminal rồi mở lại.

**Bước 2. Thêm 3beditor vào Claude Code.** Trong Claude Code, gõ lần lượt hai dòng này:

```
/plugin marketplace add Three-Bugs-Studio/3beditor
```
```
/plugin install 3beditor@3bstudio
```

Khởi động lại Claude Code.

**Bước 3. Kiểm tra.** Gõ: `kiểm tra cài đặt 3beditor giúp mình`. Claude sẽ báo còn thiếu gì và cách sửa.

---

## 2. Làm video đầu tiên

1. Bỏ hết clip vào một thư mục, ví dụ `D:\gym-clips`.
2. Trong Claude Code, gõ:
   ```
   /video D:\gym-clips
   ```
3. Trả lời vài câu hỏi của Claude: đăng ở đâu (TikTok, Reels, YouTube), dài bao lâu, có chữ tiêu đề không.
4. **Chọn phong cách.** Claude cho xem clip của chính bạn trong từng phong cách, có đánh số. Trả lời bằng một con số.
5. **Duyệt bảng phân cảnh.** Mỗi cảnh là một hình. Trả lời `OK`, hoặc số của cảnh muốn sửa.
6. Đợi một hai phút. Video được lưu trong thư mục `3beditor_work` ngay cạnh clip của bạn.

Clip gốc của bạn không bao giờ bị thay đổi.

---

## 3. Những câu bạn có thể nói

Cứ nói tự nhiên, tiếng Việt hay tiếng Anh đều được:

| Bạn muốn | Hãy nói |
|---|---|
| Làm video từ clip | `làm video TikTok 30 giây từ D:\gym-clips` |
| Giống một video bạn thích | `dựng clip của mình giống video này https://www.tiktok.com/@someone/video/123` |
| Dùng phong cách có sẵn | `/edit-like gym-cinematic D:\gym-clips` |
| Lên kế hoạch trước khi quay | `lên kế hoạch video gym trước khi mình quay` |
| Làm video từ ảnh | `làm reel 20 giây từ mấy tấm ảnh này` |
| Sửa nhỏ | `mở đầu nhanh hơn`, `chữ to hơn`, `nhạc nhỏ lại`, `bỏ hiệu ứng` |
| Lưu phong cách để dùng lại | `lưu phong cách này tên là my-style` |

**Phong cách có sẵn:** Gym Montage · Gym Cinematic · TikTok Fast · Vlog · Cinematic · Podcast Clip.

---

## 4. Mẹo quay video gym

- **Kê điện thoại hoặc dùng chân máy.** Khung hình đứng yên trông chuyên nghiệp hơn.
- **Quay 60 fps** nếu muốn quay chậm rep nặng nhất.
- **Quay từ 2-3 góc:** toàn thân, bên hông và cận cảnh (tay cầm, phấn, gương mặt ở rep cuối).
- **Bấm quay trước khi vào set 2 giây, dừng sau khi xong 2 giây.**
- **Cùng một chỗ, cùng một ánh sáng** cho mọi set.

---

## 5. Trước khi đăng

- **Nhạc:** xuất video không có nhạc, rồi chọn nhạc đang thịnh hành ngay trong TikTok, Reels hoặc Shorts. Nhạc trong app có bản quyền sẵn và giúp video được đề xuất nhiều hơn. Chỉ dùng file nhạc riêng nếu bạn có quyền dùng bài đó.
- Chữ đã được đặt tránh các nút của app.
- Âm lượng đã được chỉnh chuẩn để nghe trên điện thoại.

---

## 6. Khi gặp lỗi

| Lỗi | Cách sửa |
|---|---|
| Claude báo thiếu FFmpeg hoặc Python | Làm lại bước 1, rồi đóng và mở lại Terminal và Claude Code |
| Không thấy lệnh `/video` | Làm lại bước 2 rồi khởi động lại Claude Code |
| Link TikTok không phát được | Đăng nhập TikTok trong trình duyệt của Claude, hoặc gửi file video |
| Chữ tiếng Việt bị lỗi dấu | Chọn font khác trong danh sách Claude đưa, hoặc font "Việt hóa" |
| Chưa ưng kết quả | Cứ nói muốn sửa gì: `nhanh hơn`, `màu ấm hơn`, `bỏ cảnh 3` |

**Cập nhật bản mới nhất:** gõ `/plugin marketplace update 3bstudio`, rồi khởi động lại Claude Code.

---

## Cần giúp đỡ?

Đặt câu hỏi hoặc báo lỗi tại [GitHub Issues](https://github.com/Three-Bugs-Studio/3beditor/issues).

3beditor miễn phí. Nếu thấy hữu ích, bạn có thể [ủng hộ tác giả](https://github.com/sponsors/DongDuong2001).
