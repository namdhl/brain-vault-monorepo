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
- [x] Hoàn thiện capture form với UX phản hồi `queued` ngay.
- [x] Tạo trang danh sách item (`/items`) có filter cơ bản.
- [x] Tạo trang item detail (`/items/[id]`) hiển thị metadata + trạng thái.
- [x] Tạo trang jobs dashboard (`/jobs`) hiển thị job theo trạng thái.

### 1.5 Telegram MVP+
- [x] Mapping text thuần -> `type=text`.
- [x] Mapping message chỉ có URL -> `type=link`.
- [x] Trả response xác nhận gồm `item_id` + status `queued`.

---

## Phase 2 — Upload & asset pipeline

### 2.1 API uploads
- [x] Thêm `POST /v1/uploads/init` (metadata upload session).
- [x] Thêm `POST /v1/items/from-upload` để tạo item từ upload.
- [x] Giới hạn kích thước + MIME validation.

### 2.2 Asset modeling
- [x] Tạo model `Asset` tách khỏi `Item`.
- [x] Lưu path theo chuẩn `Assets/YYYY/MM/DD/<item_id>/...`.
- [x] Gắn quan hệ item-assets trong API response item detail.

### 2.3 Worker cho media cơ bản
- [x] Với image/video: lưu metadata tối thiểu (mime, size, duration/resolution nếu có).
- [x] Xuất note có mục `Assets` tham chiếu path.

---

## Phase 3 — Normalize/Enrichment

### 3.1 Normalize layer contract
- [x] Định nghĩa input/output contract versioned cho normalize.
- [x] Triển khai normalize cho text/link trước (HTML -> Markdown cho link).
- [x] Lưu artifact normalize để debug/reprocess.

### 3.2 Enrichment cơ bản
- [x] Summary ngắn cho text/link.
- [x] Auto-tag cơ bản.
- [x] Entity extraction cơ bản.

### 3.3 Dedupe & idempotency
- [x] Hỗ trợ `Idempotency-Key` trên `POST /v1/items`.
- [x] Dedupe key theo loại dữ liệu (text/link/media).
- [x] Định nghĩa chính sách `duplicate_of` và `force_save`.

---

## Phase 4 — Search, jobs control, observability

### 4.1 Jobs API
- [x] `GET /v1/jobs/{job_id}`.
- [x] `POST /v1/jobs/{job_id}/retry`.
- [x] Ghi lịch sử attempt/retry cho mỗi job.

### 4.2 Search
- [x] `GET /v1/search` với filter `q,type,tag,status,source,date_from,date_to`.
- [x] Trả về snippet/hightlight tối thiểu cho kết quả.

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
- 2026-04-13 | [Phase 1.4] | Web app screens | Status: [x] | Notes: Tạo Nav component (sticky, active link), /items (table + filter by status), /items/[id] (metadata + content + error detail), /jobs (stat cards + tab by status + refresh), globals.css bổ sung badge/table/filter/stat-card/detail styles. | Files: `apps/web/components/nav.tsx`, `apps/web/app/items/page.tsx`, `apps/web/app/items/[id]/page.tsx`, `apps/web/app/jobs/page.tsx`, `apps/web/app/layout.tsx`, `apps/web/app/page.tsx`, `apps/web/app/globals.css`
- 2026-04-13 | [Phase 4.2 Web] | Search UI | Status: [x] | Notes: /search page debounced input, type+status filter, snippet display, #tags. Nav thêm Search link. | Files: `apps/web/app/search/page.tsx`, `apps/web/components/nav.tsx`
- 2026-04-13 | [Phase 4.1+4.2] | Jobs API + Search API | Status: [x] | Notes: routes/jobs.py - GET /v1/jobs/{id}, POST /v1/jobs/{id}/retry (re-enqueue với attempt+1, archive old job), GET /v1/jobs list scan 3 dirs. routes/search.py - GET /v1/search với 7 filter params, snippet highlight quanh match, limit 20. | Files: `services/api/app/routes/jobs.py`, `services/api/app/routes/search.py`, `services/api/app/main.py`
- 2026-04-13 | [Phase 3.1+3.2+3.3] | Normalize, Enrichment, Dedupe | Status: [x] | Notes: pipeline/normalize.py - NormalizeInput/Output contract v1, _html_to_markdown() stdlib, _fetch_url_content() urllib, _detect_language(), save_normalize_artifact(). pipeline/enrich.py - _extract_summary(), _extract_keywords(), _extract_entities() (CamelCase+ACRONYM+known tech). dedup.py - Idempotency-Key store (file-based), dedupe index (JSON), build_dedupe_key() per type. routes/items.py - Idempotency-Key header + force_save param. | Files: `services/worker/app/pipeline/normalize.py`, `services/worker/app/pipeline/enrich.py`, `services/api/app/dedup.py`, `services/api/app/routes/items.py`, `services/worker/app/main.py`
- 2026-04-13 | [Phase 2.3] | Worker media support | Status: [x] | Notes: media.py - _probe_image() đọc PNG/JPEG header cho width/height, copy_asset_to_vault() copy file vào vault/Assets/YYYY/MM/DD/<item_id>/, process_assets_for_item() gọi trước export. markdown.py nhận asset_paths, render ## Assets section với wikilinks, frontmatter thêm asset_paths. | Files: `services/worker/app/media.py`, `services/worker/app/markdown.py`, `services/worker/app/main.py`, `services/worker/app/config.py`
- 2026-04-13 | [Phase 2.1+2.2] | Upload API + Asset modeling | Status: [x] | Notes: POST /v1/uploads/init (MIME+size validation), POST /v1/uploads/{id}/file (streaming multipart, chunk read), DELETE /v1/uploads/{id}, POST /v1/items/from-upload (create Item+Asset from session), GET /v1/items/{id}/assets. AssetRecord schema, UploadSession schema, ALLOWED_MIME_TYPES+MAX_UPLOAD_BYTES config. | Files: `services/api/app/config.py`, `services/api/app/schemas.py`, `services/api/app/storage.py`, `services/api/app/routes/uploads.py`, `services/api/app/routes/assets.py`, `services/api/app/main.py`
- 2026-04-13 | [Phase 1.5] | Telegram bot improvements | Status: [x] | Notes: _detect_type() tách riêng, set original_url cho link type, thêm _send_message() reply lại user (best-effort, cần TELEGRAM_BOT_TOKEN), response trả về item_id + status thay vì created_item object. | Files: `services/telegram-bot/app/main.py`
