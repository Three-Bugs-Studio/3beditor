# 3beditor: dựng video chỉ bằng cách nói chuyện với Claude

**Tiếng Việt** · [English](README_en.md)

Plugin miễn phí cho Claude Code, biến các clip của bạn thành video ngắn hoàn chỉnh để đăng TikTok, Reels hoặc Shorts. Chọn phong cách (hoặc gửi một video bạn thích), duyệt bảng phân cảnh, và nhận file MP4. Dựng như dân chuyên: cắt gọn theo nhịp nhạc, chỉ thêm hiệu ứng khi clip hoặc nhạc thật sự cần.

Làm riêng cho video gym và tập luyện, nhưng dùng được với mọi loại clip. Nói được tiếng Việt và tiếng Anh, phụ đề được kiểm tra từng chữ có dấu nên không bao giờ bị lỗi font.

**Dùng trên điện thoại?** Tải `3beditor-skill.zip` ở [Releases](https://github.com/Three-Bugs-Studio/3beditor/releases/latest), thêm vào claude.ai (Settings → Customize → Skills → Upload skill), rồi gửi clip trong app Claude. Xem [hướng dẫn](PLAYBOOK_vi.md#dùng-trên-điện-thoại-không-cần-máy-tính).

**Mới dùng lần đầu? Đọc hướng dẫn dễ hiểu: [Hướng dẫn tiếng Việt](PLAYBOOK_vi.md) · [Playbook (English)](PLAYBOOK.md)**

## Cài đặt (2 phút)

1. **FFmpeg 7+** và **Python 3.10+**:

   | Máy | Lệnh cài |
   |---|---|
   | Windows | `winget install Gyan.FFmpeg Python.Python.3.12` |
   | macOS | `brew install ffmpeg python` |
   | Ubuntu/Debian | `sudo apt install ffmpeg python3` |

2. **Trong Claude Code:**
   ```
   /plugin marketplace add Three-Bugs-Studio/3beditor
   /plugin install 3beditor@3bstudio
   ```
   Khởi động lại Claude Code. Cập nhật bản mới: `/plugin marketplace update 3bstudio`.

3. *Không bắt buộc:* phụ đề tự động từ giọng nói và nhận nhịp nhạc:
   ```bash
   pip install faster-whisper librosa
   ```

Không chắc đã cài đúng chưa? Nhắn Claude "kiểm tra cài đặt 3beditor giúp mình". Claude sẽ kiểm tra và báo chính xác còn thiếu gì.

## Làm video

```
/video ./clip-cua-ban
```

Claude dẫn bạn từng bước, và bạn duyệt từng bước trước khi làm phần tốn thời gian:

1. **Vài câu hỏi:** đăng ở đâu, dài bao lâu, tiêu đề, nhạc.
2. **Phong cách:** xem **chính clip của bạn trong từng phong cách**, có đánh số. Hoặc tự gửi mẫu: một file video, hoặc link TikTok/YouTube (Claude xem trong trình duyệt, không tải về).
3. **Thẻ thiết lập** (không bắt buộc): font chữ (hiện đúng chữ của bạn trên từng font), chuyển cảnh và fps (24 kiểu phim, 30 mạng xã hội, 60 mượt).
4. **Bảng phân cảnh:** mỗi cảnh một hình. Trả lời "OK" hoặc số của cảnh muốn sửa.
5. **Video của bạn:** được xuất, đo lại so với phong cách đã chọn, và lưu ngay cạnh clip của bạn.

Các cách khác:
- `/edit-like https://www.tiktok.com/@someone/video/123 ./clip`: dựng clip của bạn giống phong cách video đó
- `/edit-like gym-cinematic ./clip`: dùng thẳng một phong cách có sẵn
- "Lên kế hoạch video gym trước khi mình quay": danh sách cảnh quay, kèm câu lệnh cho các công cụ video AI
- "Làm reel 20 giây từ mấy tấm ảnh này"

**Phong cách có sẵn:** Gym Montage · Gym Cinematic · TikTok Fast · Vlog · Cinematic · Podcast Clip. Phân tích bất kỳ video nào rồi nhờ Claude lưu thành phong cách của riêng bạn.

## Làm được gì

- **Cắt dựng:** chọn rep đẹp nhất, cắt ở khoảnh khắc đứng yên và theo nhịp nhạc, quay chậm (khung hình thật từ clip 60 fps), mở đầu từ màn đen, đổi khung hình 9:16 / 16:9 / 1:1.
- **Màu sắc:** chỉnh màu từ tự nhiên đến màu phim (xanh ngọc/cam, đen sâu, viền tối, hạt phim).
- **Chữ:** phụ đề với mọi font, kể cả file `.ttf`/`.otf` của bạn. Tiếng Việt được kiểm tra từng chữ có dấu. Viền, bóng, phát sáng; tô đậm từ khóa; hiệu ứng bật, mờ, zoom; hiện từng chữ và kiểu karaoke (giống phụ đề TikTok).
- **Chuyển cảnh:** 15 kiểu chuyển cảnh điện ảnh và TikTok (lia nhanh, zoom dồn, chớp sáng, glitch, mờ dần…), chọn riêng cho từng chỗ cắt, **chỉ khi phân tích thấy có lý do**.
- **Âm thanh:** tiếng liền mạch qua các chỗ cắt, trộn nhạc, năm hiệu ứng âm thanh miễn phí (boom, clang, whoosh, riser, glitch) chỉ dùng khi có ý nghĩa, âm lượng chuẩn cho điện thoại.
- **An toàn trên app:** chữ luôn tránh các nút và vùng chú thích của TikTok/Reels.
- **Kiểm tra:** mọi kết quả đều được đo (nhịp cắt, màu, âm lượng, khớp nhịp nhạc, thời gian chính xác từng khung hình) so với phong cách đã chọn.

Clip gốc của bạn không bao giờ bị thay đổi, và không có thư mục nào được tạo thêm: chỉ có video hoàn chỉnh `<tên>_3beditor.mp4` được lưu cạnh clip của bạn.

**Về nhạc:** khi đăng công khai, hãy xuất video không có nhạc rồi chọn nhạc thịnh hành ngay trong TikTok, Reels hoặc Shorts, như vậy nhạc có bản quyền sẵn. Chỉ dùng file nhạc riêng nếu bạn có quyền dùng bài đó.

## Dành cho lập trình viên

Phần kỹ thuật (các script, cách chạy test, đóng gói cho app điện thoại) xem trong [README tiếng Anh](README_en.md#how-it-works-for-developers). Chỉ cần thư viện chuẩn của Python và FFmpeg:

```bash
python -m pytest -q tests
```

## Cảm ơn

Hiệu ứng âm thanh và một số quy tắc dựng (vùng an toàn, chọn đoạn quay, dùng âm thanh tiết chế) lấy từ [ghost-editor](https://github.com/kurbaitaev/ghost-editor) (MIT). Âm thanh là CC0, xem `sfx/CREDITS.md`. Cách phân tích video mẫu từng cảnh (mạch câu chuyện, đoạn mở đầu, cách quay) dựa trên ý tưởng từ [rea-video](https://github.com/JuneYaooo/rea-video) (Apache-2.0).

## Đóng góp

Fork, sửa, rồi gửi pull request: xem [CONTRIBUTING.md](CONTRIBUTING.md). Vui lòng tuân thủ [Quy tắc ứng xử](CODE_OF_CONDUCT.md).

Thích 3beditor? [Ủng hộ @DongDuong2001](https://github.com/sponsors/DongDuong2001) để dự án luôn miễn phí.

## Giấy phép

MIT. Tự do sử dụng, chỉnh sửa và chia sẻ, miễn là giữ lại thông tin bản quyền.
Tạo bởi Duong Phu Dong ([@DongDuong2001](https://github.com/DongDuong2001)) tại Three Bugs Studio.
