# Brain Vault - Implementation Task Board

**Nguồn kế hoạch:** `brain-vault-detailed-spec.vi.md`  
**Mục tiêu:** chia nhỏ công việc để làm từng phần một, có thể tick/check và cập nhật tiến độ ngay trong file này.

---

## Cách dùng file này

- Mỗi task có trạng thái checkbox:
  - `[ ]` chưa làm
  - `[~]` đang làm
  - `[x]` hoàn tất
- Khi bắt đầu task: đổi `[ ]` -> `[~]` và thêm log vào mục **Nhật ký triển khai**.
- Khi xong task: đổi `[~]` -> `[x]`, ghi ngày + kết quả + link file/PR (nếu có).
- Làm theo thứ tự Phase để giảm rủi ro phụ thuộc.

---

## Phase 1 — MVP usable (nền tảng bắt buộc)

### 1.1 Backend schema & contracts
- [x] Mở rộng `ItemRecord` theo spec (status, processed_at, language, canonical_hash, error fields cơ bản).
- [x] Chuẩn hóa enum `ItemType`, `ItemSource`, `ItemStatus` dùng nhất quán API/worker.
- [x] Bổ sung validate payload chặt hơn cho `POST /v1/items`.
- [x] Thêm chuẩn response lỗi thống nhất (`error.code`, `error.message`, `details`).

### 1.2 Worker pipeline local
- [x] Chuẩn hóa stage pipeline: `ingest_received -> raw_persisted -> normalized -> enriched -> vault_exported -> completed`.
- [x] Bổ sung phân loại lỗi (`transient/permanent/unsupported/...`) và lưu `error_code`, `error_message`, `failed_stage`.
- [x] Đảm bảo idempotency tối thiểu (rerun không tạo note trùng khi output đã hợp lệ).

### 1.3 Vault exporter
- [x] Chuẩn hóa frontmatter tối thiểu: `id,type,source,created_at,updated_at,status,tags,original_url`.
- [x] Chuẩn hóa naming file note (sanitize + slug + suffix item id).
- [x] Ghi note vào đúng cấu trúc `vault/Inbox/YYYY/MM`.

### 1.4 Web app screens tối thiểu
- [ ] Hoàn thiện capture form với UX phản hồi `queued` ngay.
- [ ] Tạo trang danh sách item (`/items`) có filter cơ bản.
- [ ] Tạo trang item detail (`/items/[id]`) hiển thị metadata + trạng thái.
- [ ] Tạo trang jobs dashboard (`/jobs`) hiển thị job theo trạng thái.

### 1.5 Telegram MVP+
- [ ] Mapping text thuần -> `type=text`.
- [ ] Mapping message chỉ có URL -> `type=link`.
- [ ] Trả response xác nhận gồm `item_id` + status `queued`.

---

## Phase 2 — Upload & asset pipeline

### 2.1 API uploads
- [ ] Thêm `POST /v1/uploads/init` (metadata upload session).
- [ ] Thêm `POST /v1/items/from-upload` để tạo item từ upload.
- [ ] Giới hạn kích thước + MIME validation.

### 2.2 Asset modeling
- [ ] Tạo model `Asset` tách khỏi `Item`.
- [ ] Lưu path theo chuẩn `Assets/YYYY/MM/DD/<item_id>/...`.
- [ ] Gắn quan hệ item-assets trong API response item detail.

### 2.3 Worker cho media cơ bản
- [ ] Với image/video: lưu metadata tối thiểu (mime, size, duration/resolution nếu có).
- [ ] Xuất note có mục `Assets` tham chiếu path.

---

## Phase 3 — Normalize/Enrichment

### 3.1 Normalize layer contract
- [ ] Định nghĩa input/output contract versioned cho normalize.
- [ ] Triển khai normalize cho text/link trước (HTML -> Markdown cho link).
- [ ] Lưu artifact normalize để debug/reprocess.

### 3.2 Enrichment cơ bản
- [ ] Summary ngắn cho text/link.
- [ ] Auto-tag cơ bản.
- [ ] Entity extraction cơ bản.

### 3.3 Dedupe & idempotency
- [ ] Hỗ trợ `Idempotency-Key` trên `POST /v1/items`.
- [ ] Dedupe key theo loại dữ liệu (text/link/media).
- [ ] Định nghĩa chính sách `duplicate_of` và `force_save`.

---

## Phase 4 — Search, jobs control, observability

### 4.1 Jobs API
- [ ] `GET /v1/jobs/{job_id}`.
- [ ] `POST /v1/jobs/{job_id}/retry`.
- [ ] Ghi lịch sử attempt/retry cho mỗi job.

### 4.2 Search
- [ ] `GET /v1/search` với filter `q,type,tag,status,source,date_from,date_to`.
- [ ] Trả về snippet/hightlight tối thiểu cho kết quả.

### 4.3 Logging & metrics
- [ ] Structured logs với `request_id,item_id,job_id,stage,status,duration_ms,error_code`.
- [ ] Metrics cơ bản: created items, queue depth, processing time, failure rate.

---

## Phase 5 — Productionize

### 5.1 Storage & queue migration
- [ ] Metadata sang Postgres.
- [ ] Assets sang S3/MinIO.
- [ ] Queue bền vững (Redis/RabbitMQ/Temporal).

### 5.2 Security & auth
- [ ] JWT/session auth cho web/desktop.
- [ ] API key hoặc OAuth proxy cho API public.
- [ ] Rate limit endpoint public + secret management.

### 5.3 Reliability
- [ ] Backup policy cho metadata/assets.
- [ ] Retry/backoff + DLQ.
- [ ] Dashboard theo dõi lỗi theo stage.

---

## Definition of Done (DoD)

Một phase được xem là hoàn thành khi:
- Toàn bộ task trong phase được `[x]`.
- Có test tương ứng (unit/integration hoặc e2e tùy task).
- Có cập nhật **Nhật ký triển khai** với kết quả, lỗi gặp, quyết định kỹ thuật.

---

## Nhật ký triển khai

> Mẫu ghi log mỗi lần cập nhật:
>
> `- YYYY-MM-DD | [Phase X] | Task: ... | Status: [~]/[x] | Notes: ... | Files/PR: ...`

- 2026-04-13 | [Planning] | Tạo task board ban đầu từ detailed spec | Status: [x] | Notes: Chia theo 5 phase để triển khai tuần tự, có checkpoint và DoD. | Files/PR: `docs/tasks.md`
- 2026-04-13 | [Phase 1.1] | Backend schema & contracts | Status: [x] | Notes: Mở rộng ItemRecord (processed_at, language, canonical_hash, summary, error fields), thêm ItemStatus enum, validate payload (title max 500, content max 50000, tags max 20), tạo errors.py với api_error helper, job schema cập nhật stage/status/attempt. | Files: `services/api/app/schemas.py`, `services/api/app/errors.py`, `services/api/app/routes/items.py`
- 2026-04-13 | [Phase 1.2] | Worker pipeline stages + error handling | Status: [x] | Notes: Thêm PermanentError/TransientError class, stage tracking (raw_persisted→normalized→vault_exported→completed), idempotency check (skip nếu note đã tồn tại + status=processed), lưu error_code/error_message/failed_stage vào item và job khi fail. | Files: `services/worker/app/main.py`
- 2026-04-13 | [Phase 1.3] | Vault exporter improvements | Status: [x] | Notes: _slugify() dùng unicodedata NFKD+ASCII để tạo slug an toàn, giới hạn 80 ký tự trước suffix, frontmatter đầy đủ (status, processed_at, language, canonical_hash, summary khi có), body thêm Summary section và Entities placeholder, Processing Notes cập nhật. | Files: `services/worker/app/markdown.py`
