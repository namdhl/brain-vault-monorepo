# Phase 6: Reverse Sync

## Mục tiêu
Phase 6 bổ sung khả năng **đồng bộ ngược từ Obsidian vault về server** để những chỉnh sửa do người dùng thực hiện trực tiếp trong Obsidian có thể được phản ánh trở lại hệ thống trung tâm.

## Trạng thái phạm vi
**Phase 6 không thuộc MVP.**  
Đây là giai đoạn mở rộng sau khi hệ thống MVP đã ổn định với mô hình đồng bộ **một chiều từ server -> vault**.

Trong phạm vi MVP:

- server là nguồn dữ liệu chuẩn duy nhất
- vault Obsidian là lớp xuất dữ liệu để đọc, duyệt, liên kết và chỉnh sửa thử nghiệm
- các thay đổi phát sinh trực tiếp trong vault **không bắt buộc** phải được nhập ngược về server
- không cam kết xử lý conflict hai chiều trong bản phát hành đầu tiên

## Vì sao không đưa vào MVP
Reverse sync làm tăng độ phức tạp đáng kể ở các phần sau:

1. **Phát hiện thay đổi trong vault**
   - chỉnh sửa nội dung note
   - đổi tên file
   - di chuyển thư mục
   - xóa file
   - thêm hoặc xóa attachment
   - sửa frontmatter
   - sửa wikilink và quan hệ giữa các note

2. **Đối chiếu danh tính tài liệu**
   - cần phân biệt note mới tạo với note đã có từ trước
   - cần nhận diện đúng tài liệu dù người dùng đổi tên file
   - cần giữ ổn định `id` nội bộ ngay cả khi đường dẫn thay đổi

3. **Giải quyết xung đột**
   - server đã thay đổi nhưng vault cũng đã thay đổi
   - nhiều client sửa cùng lúc
   - attachment bị thay thế nhưng metadata chưa cập nhật
   - user chỉnh sửa thủ công làm sai schema/frontmatter

4. **An toàn dữ liệu**
   - tránh overwrite nội dung thật
   - tránh xóa nhầm khi sync
   - cần version history, audit log, rollback

Vì các lý do trên, reverse sync chỉ nên triển khai khi:
- schema đã ổn định
- exporter một chiều đã chạy tin cậy
- định danh note và asset đã được chuẩn hóa
- hệ thống đã có versioning và conflict policy rõ ràng

## Điều kiện tiên quyết trước khi làm Phase 6
Phase 6 chỉ được triển khai sau khi hoàn tất và vận hành ổn định các phần sau:

- ingest pipeline cho text, link, image, video
- chuẩn hóa dữ liệu về Markdown + frontmatter
- object storage cho asset gốc
- metadata database ổn định
- export server -> vault ổn định
- indexing và query layer ổn định
- mọi note xuất ra đều có `id` bền vững
- attachment có mapping rõ giữa file vật lý và asset record trên server

## Phạm vi chức năng của Phase 6
Khi triển khai, reverse sync nên hỗ trợ các nhóm thay đổi sau:

### 1. Cập nhật note content
- người dùng chỉnh sửa nội dung Markdown trong Obsidian
- server nhận diff hoặc nội dung mới
- hệ thống cập nhật bản canonical và tăng version

### 2. Cập nhật frontmatter
- thay đổi title
- thay đổi tags
- thay đổi description
- thay đổi status hoặc custom fields được cho phép

### 3. Phát hiện rename / move
- file đổi tên nhưng giữ nguyên `id`
- file chuyển thư mục nhưng vẫn ánh xạ về cùng một bản ghi logic

### 4. Tạo note mới từ Obsidian
- người dùng tự tạo note mới trong vùng cho phép
- server import note đó thành tài liệu mới
- hệ thống gắn `source = obsidian_reverse_sync`

### 5. Cập nhật link graph
- bổ sung hoặc xóa wikilink
- cập nhật relation table hoặc edge index trên server

### 6. Attachment sync giới hạn
- thêm attachment mới từ vault vào server
- chỉ hỗ trợ trong các thư mục được whitelist
- file lớn hoặc loại file không hợp lệ có thể bị từ chối

## Những gì chưa nên hỗ trợ ở đợt đầu của Phase 6
Ngay cả khi bắt đầu làm reverse sync, bản đầu của Phase 6 vẫn nên giới hạn:

- chưa hỗ trợ merge tự động phức tạp theo đoạn văn
- chưa hỗ trợ collaborative editing real-time
- chưa hỗ trợ sync hai chiều cho mọi thư mục
- chưa hỗ trợ import ngược toàn bộ plugin data của Obsidian
- chưa hỗ trợ attachment rewrite hàng loạt
- chưa hỗ trợ xử lý mọi kiểu refactor do plugin bên thứ ba gây ra

## Chính sách nhận diện note
Mỗi note phải có một định danh bền vững trong frontmatter, ví dụ:

```yaml
id: note_01HXYZ...
origin: server
sync_direction: bidirectional
version: 12
last_synced_at: 2026-04-14T10:00:00Z
```

Quy tắc:

- `id` là khóa định danh logic, không phụ thuộc filename
- filename có thể đổi mà không đổi `id`
- nếu note không có `id`, hệ thống coi là note ngoài quản lý hoặc note mới cần review
- thư mục chỉ là thông tin tổ chức, không phải danh tính tài liệu

## Mô hình đồng bộ đề xuất
Reverse sync nên đi theo mô hình sau:

1. file watcher hoặc scan định kỳ phát hiện thay đổi trong vault
2. sync service lập danh sách note changed / added / removed
3. parser đọc Markdown, frontmatter, links, attachments
4. validator kiểm tra schema
5. diff engine so sánh với canonical record trên server
6. conflict resolver áp dụng policy
7. nếu hợp lệ thì ghi vào database + object storage metadata
8. re-index search
9. ghi sync log và version history
10. nếu cần thì export ngược lại để chuẩn hóa format

## Conflict policy đề xuất
Bản đầu của Phase 6 nên dùng conflict policy đơn giản, dễ giải thích:

### Trường hợp không conflict
- chỉ vault thay đổi kể từ lần sync gần nhất  
=> chấp nhận thay đổi từ vault

### Trường hợp có conflict
- cả server và vault đều thay đổi trên cùng note  
=> không auto-merge toàn phần  
=> chuyển trạng thái `conflicted`  
=> lưu cả hai bản để người dùng review

### Trường hợp schema lỗi
- frontmatter thiếu field bắt buộc
- YAML hỏng
- type không hợp lệ  
=> không import trực tiếp  
=> tạo sync error record

## Khu vực được phép reverse sync
Không phải mọi thư mục trong vault đều nên cho sync ngược.

Nên chia thành 3 mức:

### A. Cho phép sync ngược
- `Inbox/`
- `Notes/`
- `reference/curated/`
- `brain/capture/`

### B. Chỉ đọc từ server, không nhận sync ngược
- thư mục export hệ thống
- thư mục generated summaries
- thư mục machine annotations
- thư mục index / views sinh tự động

### C. Không quản lý
- thư mục cá nhân do user tự thêm ngoài chuẩn
- thư mục plugin local
- cache và file tạm

## API dự kiến
Phase 6 có thể cần các endpoint sau:

- `POST /v1/sync/reverse/scan`
- `POST /v1/sync/reverse/import-note`
- `POST /v1/sync/reverse/import-batch`
- `GET /v1/sync/conflicts`
- `POST /v1/sync/conflicts/{id}/resolve`
- `GET /v1/sync/history/{note_id}`

## Bảng dữ liệu cần bổ sung
Ngoài schema hiện có, có thể cần thêm:

### `sync_state`
Lưu trạng thái sync hiện tại của từng note:
- note_id
- vault_path
- last_synced_hash
- last_synced_version
- last_synced_at

### `sync_events`
Lưu event reverse sync:
- event_id
- note_id
- event_type
- source
- payload_summary
- created_at

### `sync_conflicts`
Lưu conflict cần xử lý:
- conflict_id
- note_id
- server_version
- vault_version
- status
- resolution

### `note_versions`
Lưu lịch sử version:
- version_id
- note_id
- content_snapshot
- metadata_snapshot
- created_at
- source

## Bảo mật và an toàn
Phase 6 phải có ít nhất các cơ chế sau:

- whitelist thư mục được phép import ngược
- giới hạn loại file attachment
- kiểm tra kích thước file
- validate YAML/frontmatter
- sanitize path để tránh path traversal
- audit log cho mọi thao tác import / delete / conflict resolve
- backup hoặc snapshot trước khi áp dụng thay đổi lớn

## Tiêu chí hoàn thành
Phase 6 chỉ được coi là hoàn thành khi đạt các tiêu chí sau:

- sửa note trong Obsidian và sync ngược thành công về server
- rename note không làm mất liên kết với bản ghi cũ
- conflict được phát hiện đúng và không làm mất dữ liệu
- note lỗi schema không phá pipeline
- attachment hợp lệ được import đúng
- toàn bộ thay đổi có audit trail và version history

## Kết luận
**Phase 6 là giai đoạn hậu MVP. Không thuộc phạm vi MVP.**

Bản MVP chỉ cần:
- ingest đa nguồn
- chuẩn hóa dữ liệu
- phân tích đầu vào
- truy vấn nhanh
- trả lời tự nhiên
- export một chiều từ server sang vault Obsidian

Chỉ sau khi các phần trên ổn định mới nên bắt đầu reverse sync.
