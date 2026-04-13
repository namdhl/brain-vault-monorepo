# Đặc tả tích hợp `obsidian-mind` vào dự án Brain Vault

- Tài liệu: `brain-vault-obsidian-mind-integration-spec.vi.md`
- Phiên bản tài liệu: `1.0.0`
- Ngày: `2026-04-13`
- Trạng thái: `Proposed`
- Phạm vi: monorepo hiện tại của dự án Brain Vault + profile vault theo `obsidian-mind`

---

## 1. Mục tiêu tài liệu

Tài liệu này mô tả cách tích hợp repo `breferrari/obsidian-mind` vào monorepo Brain Vault đang có, theo hướng:

1. **giữ server làm nguồn dữ liệu chuẩn**;
2. **dùng `obsidian-mind` làm profile vault / quy ước note / lớp bộ não tri thức**;
3. **giữ khả năng ingest từ web, PWA, app Windows và Telegram**;
4. **hỗ trợ truy vấn nhanh + trả lời tự nhiên** trên chính dữ liệu đã được chuẩn hóa và xuất ra vault.

Tài liệu này không chỉ trả lời câu hỏi “có tích hợp được không”, mà còn chốt luôn:

- mô hình tích hợp đúng;
- cấu trúc thư mục mục tiêu;
- schema frontmatter;
- luồng phân loại và định tuyến note;
- cách dùng `brain/`, `reference/`, `thinking/`, `work/`, `org/`, `bases/`;
- thay đổi cần làm trong API, worker, exporter, query engine và Telegram bot;
- lộ trình migrate từ skeleton hiện tại.

---

## 2. Kết luận kiến trúc

### 2.1. Kết luận ngắn

**Có thể tích hợp `obsidian-mind` vào dự án.**

Nhưng cách tích hợp đúng là:

- **không dùng `obsidian-mind` làm backend ingest trung tâm**;
- **không để Obsidian vault trở thành source of truth duy nhất ở phase đầu**;
- **dùng `obsidian-mind` như một “vault profile” có sẵn quy ước memory, link, template và base views**;
- **server Brain Vault vẫn giữ vai trò canonical system** cho ingest, normalize, classify, index và query.

### 2.2. Quyết định chính

Quyết định kiến trúc của dự án sau khi tích hợp:

- **Canonical layer**: API + metadata DB + object storage + job queue.
- **Knowledge projection layer**: exporter ghi note Markdown theo profile `obsidian-mind`.
- **Retrieval layer**: ưu tiên search trên metadata/index của server; có thể dùng thêm QMD như một sidecar hoặc local power-search.
- **Answer layer**: LLM Gateway (OpenAI/Gemini qua `api_key` + `base_url`) tạo câu trả lời tự nhiên, nhưng luôn grounded trên dữ liệu thật của vault / index.

### 2.3. Vì sao quyết định như vậy

`obsidian-mind` được thiết kế như một Obsidian vault template cho AI agents với persistent memory, hooks, commands, templates, bases và quy tắc liên kết note. Nó rất mạnh ở phần “bộ não bền vững trong vault”, nhưng không phải là một ingest backend đa nguồn cho web/PWA/Telegram/media pipeline. README của repo nhấn mạnh `vault-first memory`, QMD semantic search, các hook lifecycle và graph-first linking; còn `vault-manifest.json` lại mô tả rõ phần infrastructure file, scaffold file, version fingerprint và user content roots của template. Điều này rất hợp để dùng làm **profile đầu ra** cho hệ Brain Vault hơn là dùng làm **runtime core**.  

---

## 3. Bối cảnh monorepo hiện tại

Theo skeleton hiện có trong monorepo Brain Vault, dự án đang có:

```text
apps/
  web/
  desktop/
services/
  api/
  worker/
  telegram-bot/
packages/
  shared/
runtime/
  items/
  jobs/
vault/
  Inbox/
  Notes/
  Assets/
  Templates/
  .obsidian/
docs/
```

Hiện tại kiến trúc scaffold hoạt động theo kiểu:

1. client gửi item vào API;
2. API lưu item JSON vào `runtime/items`;
3. API xếp job vào `runtime/jobs/queued`;
4. worker đọc job;
5. worker xuất note Markdown vào `vault/Inbox/YYYY/MM/...md`.

Mô hình này rất phù hợp để **bổ sung thêm exporter theo profile `obsidian-mind`**, thay vì vứt bỏ và làm lại từ đầu.

---

## 4. Phân tích upstream `obsidian-mind`

## 4.1. Những gì repo upstream cung cấp sẵn

Theo README, `obsidian-mind` là một Obsidian vault dành cho persistent memory của AI agents, hoạt động với Claude Code, Codex CLI và Gemini CLI. Repo này đi theo triết lý:

- folders group by purpose;
- links group by meaning;
- mọi durable knowledge nằm trong vault;
- không nạp toàn bộ vault vào context, mà dùng loading theo tầng;
- ưu tiên QMD để tìm context liên quan trước khi đọc file sâu.

## 4.2. Cấu trúc thư mục gốc đáng tái sử dụng

Repo root hiện có các thư mục chính:

```text
bases/
brain/
org/
perf/
reference/
templates/
thinking/
work/
```

Đây là điểm rất hợp với Brain Vault vì nó tách bạch:

- tri thức bền vững (`brain/`);
- tri thức tham chiếu (`reference/`);
- suy nghĩ tạm / nháp (`thinking/`);
- công việc / project (`work/`);
- people / team (`org/`);
- views dạng database (`bases/`);
- template note (`templates/`).

## 4.3. Manifest và boundary của template

`vault-manifest.json` upstream hiện ghi `template: obsidian-mind`, `version: 4.0.0`, `released: 2026-04-09`, đồng thời phân biệt rất rõ:

- file nào là **infrastructure**;
- file nào là **scaffold**;
- root nào là **user_content_roots**.

Điểm này cực kỳ quan trọng cho tích hợp vì nó cho phép chúng ta giữ một ranh giới rõ giữa:

- phần profile template của upstream;
- phần nội dung do Brain Vault sinh ra;
- phần chỉnh sửa thủ công của người dùng.

## 4.4. Template note upstream

Upstream hiện có tối thiểu các template:

- `Work Note.md`
- `Decision Record.md`
- `Thinking Note.md`
- `Competency Note.md`
- `Review Template.md`

Các template này dùng YAML frontmatter rất gọn, ví dụ:

- `Work Note`: `date`, `description`, `project`, `status`, `tags`
- `Decision Record`: `date`, `description`, `status`, `tags`
- `Thinking Note`: `date`, `description`, `context`, `tags`

Điều này cho thấy upstream ưu tiên **frontmatter mỏng nhưng nhất quán**, còn phần ngữ nghĩa mạnh nằm ở link graph và views.

## 4.5. Bases và view layer

Upstream có sẵn các `.base` file như:

- `1-1 History.base`
- `Competency Map.base`
- `Incidents.base`
- `People Directory.base`
- `Review Evidence.base`
- `Templates.base`
- `Work Dashboard.base`

Điều này rất đáng tận dụng vì Obsidian Bases là core plugin cho phép tạo database-like views ngay trên frontmatter của Markdown notes.

## 4.6. Quy tắc rất đáng tái sử dụng

`CLAUDE.md` upstream có một số quy tắc nên được kế thừa gần như nguyên trạng:

- luôn ưu tiên `[[wikilinks]]` trong vault;
- “a note without links is a bug”;
- không đụng `.obsidian/` nếu không thật sự cần;
- preserve frontmatter khi edit note;
- nếu cần “remember”, hãy ghi vào `brain/` topic notes chứ không tạo memory rời ngoài vault;
- graph-first, không folder-first.

## 4.7. Điểm không thể bê nguyên xi

Upstream mặc định tối ưu cho workflow engineering/work:

- `work/active/`
- `work/archive/`
- `work/incidents/`
- `work/1-1/`
- `org/people/`
- `perf/`

Trong khi Brain Vault cần ingest dữ liệu tổng quát hơn:

- text tự do;
- link web;
- ảnh;
- video;
- Telegram message;
- câu hỏi truy vấn tự nhiên.

Vì vậy **cần mở rộng profile**, chứ không thể áp nguyên cấu trúc work-centric của upstream cho mọi item.

---

## 5. Nguyên tắc tích hợp bắt buộc

## 5.1. Server là nguồn dữ liệu chuẩn

Phase 1 phải giữ nguyên nguyên tắc:

- server nhận dữ liệu từ mọi client;
- server lưu metadata chuẩn;
- server lưu file gốc;
- server chạy pipeline normalize/enrich;
- server xuất sang vault.

**Không cho web app, Telegram bot hoặc Obsidian desktop ghi trực tiếp vào vault như nguồn chính** ở phase đầu.

## 5.2. Vault là projection có cấu trúc

Vault `obsidian-mind` được xem là một **projection layer có ngữ nghĩa cao** để:

- con người duyệt tri thức;
- Obsidian dùng được ngay;
- agent/LLM có thể truy vấn ngữ cảnh tốt hơn;
- các mối liên kết giữa note được bảo toàn.

## 5.3. Upstream profile được vendor hóa, không bị runtime overwrite

Dự án phải dùng cách sau:

- snapshot upstream `obsidian-mind` vào một profile versioned của dự án;
- bootstrap profile vào `vault/` khi khởi tạo;
- runtime chỉ tạo/cập nhật user content files;
- không overwrite ngẫu nhiên `CLAUDE.md`, `Home.md`, template và base files của người dùng.

## 5.4. Mọi note mới đều phải có metadata tối thiểu và link

Mọi note Brain Vault tạo ra trong profile này phải có tối thiểu:

- `description`
- `date`
- `status`
- `tags`
- ít nhất một `[[wikilink]]` sang note khác hoặc MOC/index note phù hợp.

## 5.5. Không phụ thuộc duy nhất vào QMD

QMD rất mạnh cho hybrid/local search, nhưng không nên là đường retrieval duy nhất của server.

Khuyến nghị:

- **server retrieval chính**: Postgres FTS + pgvector + metadata filters;
- **vault retrieval bổ sung**: QMD sidecar hoặc local mode;
- **fallback**: grep / filesystem scan / direct note read.

---

## 6. Mô hình tích hợp mục tiêu

## 6.1. Sơ đồ logic

```text
Web / PWA / Windows / Telegram
            |
            v
        API ingest
            |
            v
   Canonical metadata store
  + object storage + job queue
            |
            v
     normalize / classify /
    summarize / entity link /
        route / export
            |
            +--------------------+
            |                    |
            v                    v
   Search index / vector   Obsidian vault profile
            |              (obsidian-mind + extensions)
            v                    |
       Query engine              v
            |               Obsidian / agent / user
            v
      LLM grounded answer
```

## 6.2. Hai lớp cần tách rõ

### Lớp 1: Canonical layer

Chứa:

- item record
- asset record
- processing status
- classification result
- embeddings / search index
- audit log
- answer log

### Lớp 2: Knowledge vault layer

Chứa:

- note markdown đã chuẩn hóa
- note memory tổng hợp
- note reference
- note project/person/team
- base views
- home dashboard

---

## 7. Cấu trúc vault mục tiêu sau tích hợp

## 7.1. Quy tắc tổng quát

Để giảm công migrate từ skeleton hiện tại, phase đầu sẽ **giữ `Inbox/` và `Assets/`** thay vì đổi tên ngay. Đồng thời sẽ bổ sung đầy đủ các root quan trọng của `obsidian-mind`.

## 7.2. Cấu trúc thư mục mục tiêu

```text
vault/
  Home.md
  CLAUDE.md
  AGENTS.md
  GEMINI.md
  vault-manifest.json

  Inbox/
    2026/
      04/
        ... raw captured notes

  Assets/
    2026/
      04/
        ... binary assets / thumbnails / derived files

  brain/
    North Star.md
    Memories.md
    Key Decisions.md
    Patterns.md
    Gotchas.md
    Skills.md
    Voice.md
    Topics/

  reference/
    domains/
    concepts/
    entities/
    collections/
    sources/

  thinking/
    answer-drafts/
    routing-debug/
    session-logs/

  work/
    active/
    archive/
    incidents/
    1-1/
    Index.md

  org/
    people/
    teams/
    People & Context.md

  perf/
    brag/
    evidence/
    competencies/
    Brag Doc.md

  bases/
    Work Dashboard.base
    People Directory.base
    Capture Inbox.base
    Media Library.base
    Sources.base
    Brain Memory.base
    Recent Answers.base

  templates/
    Work Note.md
    Decision Record.md
    Thinking Note.md
    Capture Text Note.md
    Capture Link Note.md
    Capture Image Note.md
    Capture Video Note.md
    Telegram Message Note.md
    Query Answer Note.md

  .obsidian/
```

## 7.3. Tại sao vẫn giữ `Inbox/`

Giữ `Inbox/` ở phase đầu vì:

- exporter hiện tại đã ghi vào `vault/Inbox/YYYY/MM`;
- migrate ít rủi ro hơn;
- Telegram/web/PWA đã tư duy theo luồng inbox capture;
- sau này vẫn có thể chuyển sang `capture/` nếu cần.

## 7.4. Boundary runtime

Runtime worker **được phép** ghi vào:

- `Inbox/`
- `Assets/`
- `brain/`
- `reference/`
- `thinking/answer-drafts/`
- `work/`
- `org/`
- một số `.base` do dự án tự quản

Runtime worker **không được phép** tự ý sửa:

- `.obsidian/`
- file config của người dùng
- toàn bộ upstream instructions trừ khi có lệnh bootstrap / upgrade rõ ràng

---

## 8. Taxonomy note và quy tắc home folder

## 8.1. Note loại capture

Đây là note gốc cho mỗi item ingest.

Home folder mặc định:

- `Inbox/YYYY/MM/`

Các subtype:

- `capture-text`
- `capture-link`
- `capture-image`
- `capture-video`
- `telegram-message`

Mục đích:

- bảo toàn nguồn vào;
- giữ transcript / OCR / normalized content;
- làm nguồn trích dẫn cho query answer;
- làm điểm xuất phát để router sinh note bậc cao hơn.

## 8.2. Note loại reference

Home folder:

- `reference/domains/`
- `reference/concepts/`
- `reference/entities/`
- `reference/sources/`
- `reference/collections/`

Mục đích:

- chứa tri thức đã được chưng cất từ nhiều capture note;
- gom các link/article/video về cùng một chủ đề;
- làm evergreen knowledge notes.

## 8.3. Note loại brain

Home folder:

- `brain/`
- `brain/Topics/`

Mục đích:

- memory bền vững;
- patterns lặp lại;
- gotchas;
- key decisions;
- communication style / voice;
- topic summaries lâu dài.

## 8.4. Note loại work

Home folder:

- `work/active/`
- `work/archive/`
- `work/incidents/`
- `work/1-1/`

Mục đích:

- chỉ dùng khi capture có ý nghĩa project/work rõ ràng;
- không ép mọi item media vào `work/`.

## 8.5. Note loại org

Home folder:

- `org/people/`
- `org/teams/`

Mục đích:

- tách bạch people/team context khỏi project note;
- cập nhật từ Telegram/web/chat khi có thông tin liên quan tới con người / tổ chức.

## 8.6. Note loại thinking

Home folder:

- `thinking/answer-drafts/`
- `thinking/routing-debug/`
- `thinking/session-logs/`

Mục đích:

- lưu reasoning tạm được phép persist;
- lưu bản nháp trả lời;
- lưu vết routing/classification để audit.

---

## 9. Chuẩn frontmatter chung

## 9.1. Mục tiêu của frontmatter

Frontmatter phải đủ giàu để:

- query nhanh bằng metadata;
- build Bases views;
- link routing dễ;
- phục vụ answer grounding;
- vẫn giữ tinh thần gọn của `obsidian-mind`.

## 9.2. Schema chung bắt buộc cho mọi note do hệ thống sinh

```yaml
id: bv_01J...
date: 2026-04-13
description: Ghi chú ngắn khoảng 120-160 ký tự mô tả note.
status: active
tags:
  - brain-vault
  - capture
source: telegram
created_at: 2026-04-13T09:15:21Z
updated_at: 2026-04-13T09:15:21Z
vault_profile: obsidian-mind
profile_version: 4.0.0
canonical_item_id: item_01J...
```

## 9.3. Frontmatter cho raw capture note

```yaml
id: bv_cap_01JABC...
date: 2026-04-13
description: Bản capture gốc từ Telegram, chứa link bài viết về Obsidian và MarkItDown.
status: processed
tags:
  - brain-vault
  - capture
  - capture-link
  - telegram
  - inbox
source: telegram
capture_type: link
content_type: text/uri-list
created_at: 2026-04-13T09:15:21Z
updated_at: 2026-04-13T09:16:02Z
vault_profile: obsidian-mind
profile_version: 4.0.0
canonical_item_id: item_01JABC...
original_url: https://example.com/article
asset_paths: []
language: vi
entities:
  - MarkItDown
  - Obsidian
summary_ready: true
embedding_ready: true
```

## 9.4. Frontmatter cho image note

```yaml
id: bv_cap_img_01J...
date: 2026-04-13
description: Ảnh chụp màn hình gửi từ PWA, đã OCR và gắn topic AI tools.
status: processed
tags:
  - brain-vault
  - capture
  - capture-image
  - pwa
  - inbox
source: pwa
capture_type: image
mime_type: image/jpeg
created_at: 2026-04-13T09:15:21Z
updated_at: 2026-04-13T09:18:10Z
vault_profile: obsidian-mind
profile_version: 4.0.0
canonical_item_id: item_01J...
asset_paths:
  - Assets/2026/04/13/01J/source.jpg
  - Assets/2026/04/13/01J/thumb.jpg
ocr_text_available: true
caption_available: true
```

## 9.5. Frontmatter cho video note

```yaml
id: bv_cap_vid_01J...
date: 2026-04-13
description: Video từ Telegram đã tách transcript, tóm tắt và link tới topic note liên quan.
status: processed
tags:
  - brain-vault
  - capture
  - capture-video
  - telegram
  - inbox
source: telegram
capture_type: video
mime_type: video/mp4
created_at: 2026-04-13T09:15:21Z
updated_at: 2026-04-13T09:25:41Z
vault_profile: obsidian-mind
profile_version: 4.0.0
canonical_item_id: item_01J...
asset_paths:
  - Assets/2026/04/13/01J/source.mp4
  - Assets/2026/04/13/01J/thumb.jpg
transcript_status: complete
duration_seconds: 142
speaker_count: 1
```

## 9.6. Frontmatter cho reference note

```yaml
id: bv_ref_01J...
date: 2026-04-13
description: Note tổng hợp về MarkItDown, gom link, video và các lần nhắc tới trong vault.
status: active
tags:
  - brain-vault
  - reference
  - concept
source: derived
created_at: 2026-04-13T09:20:00Z
updated_at: 2026-04-13T09:31:00Z
vault_profile: obsidian-mind
profile_version: 4.0.0
derived_from:
  - [[Inbox/2026/04/markitdown-link-abc123]]
  - [[Inbox/2026/04/telegram-video-def456]]
aliases:
  - Microsoft MarkItDown
```

## 9.7. Frontmatter cho query answer note

```yaml
id: bv_ans_01J...
date: 2026-04-13
description: Câu trả lời cho truy vấn người dùng về cách tích hợp obsidian-mind vào Brain Vault.
status: answered
tags:
  - brain-vault
  - query-answer
  - natural-answer
source: query
created_at: 2026-04-13T10:10:00Z
updated_at: 2026-04-13T10:10:02Z
vault_profile: obsidian-mind
profile_version: 4.0.0
query_text: tích hợp obsidian-mind vào dự án được không
answer_style: natural-grounded
retrieval_mode: hybrid
used_notes:
  - [[reference/concepts/Obsidian Mind]]
  - [[brain/Patterns]]
```

---

## 10. Quy tắc body Markdown cho từng loại note

## 10.1. Raw capture note

Body tối thiểu nên có cấu trúc:

```md
# {{title}}

## Tóm tắt
...

## Nội dung chuẩn hóa
...

## Trích xuất
- entities: ...
- tags: ...
- source: ...

## Liên kết liên quan
- [[reference/concepts/MarkItDown]]
- [[brain/Patterns]]
```

## 10.2. Decision Record

Nếu classifier phát hiện một quyết định rõ ràng, hệ thống phải tạo riêng một note từ template `Decision Record.md`, thay vì chỉ nhét quyết định vào raw capture note.

## 10.3. Thinking note

Dùng để lưu:

- query decomposition;
- hypothesis;
- so sánh câu trả lời;
- answer draft cần audit.

Không dùng `thinking/` làm nơi chứa mọi dữ liệu tạm vô tổ chức.

---

## 11. Quy tắc routing và classify

## 11.1. Router phải tạo ra nhiều lớp đầu ra

Một input có thể sinh ra nhiều cập nhật:

- 1 raw capture note bắt buộc;
- 0 hoặc 1 decision record;
- 0 hoặc 1 update vào `brain/Key Decisions.md`;
- 0 hoặc 1 update vào `brain/Patterns.md`;
- 0 hoặc N update/link tới `reference/`;
- 0 hoặc N update/link tới `org/people/`;
- 0 hoặc N update/link tới `work/active/`.

## 11.2. Output chuẩn của classifier

Classifier nội bộ nên trả về payload chuẩn như sau:

```json
{
  "primary_note_type": "capture-link",
  "secondary_actions": [
    "create_reference_note",
    "update_brain_patterns"
  ],
  "tags": ["markitdown", "obsidian", "telegram"],
  "entities": [
    {"name": "MarkItDown", "kind": "tool"},
    {"name": "Obsidian", "kind": "tool"}
  ],
  "suggested_links": [
    "[[reference/concepts/MarkItDown]]",
    "[[reference/concepts/Obsidian]]",
    "[[brain/Patterns]]"
  ],
  "confidence": 0.91
}
```

## 11.3. Routing rule chi tiết

### Text tự do

- luôn tạo raw capture note trong `Inbox/`
- nếu có topic lâu dài → link hoặc cập nhật `reference/`
- nếu là insight lặp lại → cập nhật `brain/Patterns.md`
- nếu là lỗi/hạn chế → cập nhật `brain/Gotchas.md`

### Link web

- luôn tạo raw capture note trong `Inbox/`
- normalize HTML sang Markdown
- nếu domain quan trọng → tạo hoặc cập nhật `reference/sources/<domain>.md`
- nếu nội dung là tri thức lâu dài → tạo `reference/concepts/...`

### Ảnh

- lưu asset vào `Assets/`
- OCR/caption
- tạo raw capture note trong `Inbox/`
- nếu ảnh liên quan tới project/person → link sang `work/` hoặc `org/`

### Video

- lưu asset vào `Assets/`
- tạo transcript + summary
- tạo raw capture note trong `Inbox/`
- nếu có quyết định hoặc lesson learned → tách Decision/Pattern/Gotcha riêng

### Telegram message

- luôn giữ note gốc
- nếu là query thay vì capture → chuyển sang query flow thay vì ingest flow thuần túy

## 11.4. Luật link tối thiểu

Mọi note mới phải có ít nhất một outbound wikilink tới một trong các đích sau:

- topic note ở `brain/`
- concept/entity/source note ở `reference/`
- MOC/index note như `work/Index.md` hoặc `People & Context.md`
- note project/person liên quan

Nếu router chưa tìm được đích phù hợp, note vẫn phải link về:

- `[[brain/Memories]]` hoặc
- `[[reference/collections/Capture Inbox Index]]`

để tránh orphan note.

---

## 12. Query nhanh và trả lời tự nhiên

## 12.1. Mục tiêu

Cho phép người dùng hỏi bằng ngôn ngữ tự nhiên trên web, PWA, desktop hoặc Telegram như:

- “những link về Obsidian mình lưu tháng này”
- “video nào nói về Telegram bot”
- “tóm tắt các note liên quan đến MarkItDown”
- “hôm trước mình quyết định gì về cấu trúc vault”

## 12.2. Hai lớp truy vấn

### Lớp A: Query nhanh bằng filter + index

Hỗ trợ các filter như:

- `type:video`
- `source:telegram`
- `tag:obsidian`
- `status:processed`
- `after:2026-04-01`
- `before:2026-04-30`
- `folder:reference/concepts`

Lớp này dùng:

- metadata DB
- Postgres FTS
- pgvector
- hoặc QMD/grep như fallback hoặc power mode

### Lớp B: Query tự nhiên có answer synthesis

Luồng:

1. parse ý định + filter;
2. chạy fast filter retrieval;
3. chạy semantic / hybrid retrieval nếu cần;
4. lấy top-k note;
5. build answer context;
6. gọi LLM Gateway để tạo câu trả lời tự nhiên;
7. gắn citations từ note path / excerpt;
8. optional “humanize” pass theo voice preference.

## 12.3. Mô hình retrieval khuyến nghị

### MVP

- metadata filter trên DB
- full text search trên DB
- vector similarity trên DB
- answer synthesis từ LLM Gateway

### Optional power mode

- QMD sidecar index trên toàn bộ vault xuất ra
- dùng `qmd search`, `qmd vsearch`, `qmd query` cho local/hybrid retrieval chất lượng cao
- dùng QMD khi chạy desktop/local knowledge mode hoặc khi operator muốn search thẳng trên vault

## 12.4. Vì sao không dùng QMD làm duy nhất

QMD được thiết kế như một on-device search engine cho markdown/docs/meeting notes, kết hợp BM25, vector semantic search và reranking cục bộ. Mô hình này rất hợp cho local vault mode và agent workflows, nhưng với server đa client thì metadata DB + vector DB vẫn là đường chính dễ scale và dễ audit hơn.

## 12.5. Câu trả lời tự nhiên phải grounded

Câu trả lời sinh ra phải dựa trên note thật, không được trả lời “bịa theo trí nhớ model”.

Cấu trúc response logic:

```json
{
  "answer": "...",
  "citations": [
    {
      "note_path": "reference/concepts/MarkItDown.md",
      "excerpt": "..."
    }
  ],
  "related_notes": [
    "Inbox/2026/04/markitdown-link-abc123.md",
    "brain/Patterns.md"
  ],
  "answer_style": "natural-grounded"
}
```

## 12.6. Áp dụng ý tưởng `/om-humanize`

`obsidian-mind` có command `/om-humanize` để chỉnh văn phong gần hơn với giọng người dùng. Dự án Brain Vault nên học đúng ý tưởng này bằng cách:

- tạo `brain/Voice.md`;
- lưu preference như ngôn ngữ, độ ngắn dài, mức thân mật, từ ngữ ưa dùng;
- answer synthesis pass 1 = factual grounded answer;
- answer synthesis pass 2 = voice adaptation nhưng không làm mất nghĩa.

---

## 13. Thay đổi cần làm trong monorepo

## 13.1. Thay đổi ở `services/api`

Cần thêm:

- `POST /v1/query`
- `GET /v1/notes/{id}`
- `POST /v1/profile/bootstrap`
- `GET /v1/profile/status`
- `POST /v1/reindex`

Cần mở rộng `CreateItemInput`:

- `mime_type`
- `language`
- `channel_id`
- `chat_id`
- `asset_refs`
- `source_message_id`
- `external_ids`
- `metadata`

## 13.2. Thay đổi ở `services/worker`

Cần tách worker hiện tại thành các module rõ hơn:

```text
services/worker/app/
  classify.py
  route_obsidian_mind.py
  export_obsidian_mind.py
  update_brain.py
  update_reference.py
  build_bases.py
  query_index.py
  answer_writer.py
```

Trách nhiệm:

- `classify.py`: gán note type, tags, entities, suggested links
- `route_obsidian_mind.py`: quyết định tạo/sửa note nào
- `export_obsidian_mind.py`: render Markdown theo template profile
- `update_brain.py`: cập nhật `brain/*`
- `update_reference.py`: cập nhật topic/source/entity notes
- `build_bases.py`: tạo/cập nhật `.base`
- `query_index.py`: update search index
- `answer_writer.py`: persist answer notes nếu bật

## 13.3. Thay đổi ở `services/telegram-bot`

Bot hiện chỉ forward text/link đơn giản. Sau tích hợp cần hỗ trợ:

- tải attachment từ Telegram;
- gửi file sang API ingest;
- nếu message là câu hỏi → gọi `/v1/query`;
- trả câu trả lời ngắn + link note liên quan;
- nếu user yêu cầu lưu vào vault → tạo capture note;
- nếu user yêu cầu hỏi đáp → không lưu raw note trùng lặp nếu đó chỉ là query.

## 13.4. Thay đổi ở `apps/web`

Web app cần có 2 mode rõ ràng:

- **Capture mode**: gửi text/link/file
- **Ask mode**: hỏi dữ liệu đã lưu

UI nên có:

- ô nhập tự nhiên
- filter chips (`type`, `source`, `tag`, `date`)
- danh sách note liên quan
- citations click-through

## 13.5. Thay đổi ở `apps/desktop`

Desktop app có thể dùng lại web UI, nhưng nên thêm:

- chế độ mở nhanh vault/home note
- deep link tới note path
- local QMD mode nếu cần

## 13.6. Thay đổi ở `packages/shared`

Cần thêm các kiểu dùng chung:

- `NoteKind`
- `ClassifierOutput`
- `QueryRequest`
- `QueryResponse`
- `Citation`
- `VaultProfile`
- `NaturalAnswerStyle`

---

## 14. Bootstrap profile `obsidian-mind`

## 14.1. Nguyên tắc cài profile

Không clone thẳng repo upstream vào runtime mỗi lần chạy.

Thay vào đó:

1. vendor snapshot upstream theo version;
2. bootstrap profile một lần vào `vault/`;
3. ghi metadata cài đặt vào file riêng.

## 14.2. File metadata cài profile

Khuyến nghị tạo:

```text
vault/.brain-vault/profile.json
```

Nội dung ví dụ:

```json
{
  "profile": "obsidian-mind",
  "upstream_version": "4.0.0",
  "installed_at": "2026-04-13T10:20:00Z",
  "local_extensions_version": "1.0.0"
}
```

## 14.3. Những file bootstrap bắt buộc

Bootstrap cần đảm bảo các file này tồn tại:

- `Home.md`
- `CLAUDE.md`
- `AGENTS.md`
- `GEMINI.md`
- `vault-manifest.json`
- `brain/North Star.md`
- `brain/Memories.md`
- `brain/Key Decisions.md`
- `brain/Patterns.md`
- `brain/Gotchas.md`
- `work/Index.md`
- `org/People & Context.md`
- `perf/Brag Doc.md`
- `templates/*`
- `bases/*`

## 14.4. Local extension layer

Ngoài upstream files, dự án sẽ thêm extension files riêng:

- `brain/Voice.md`
- `templates/Capture Text Note.md`
- `templates/Capture Link Note.md`
- `templates/Capture Image Note.md`
- `templates/Capture Video Note.md`
- `templates/Telegram Message Note.md`
- `templates/Query Answer Note.md`
- `bases/Capture Inbox.base`
- `bases/Media Library.base`
- `bases/Sources.base`
- `bases/Brain Memory.base`
- `bases/Recent Answers.base`

---

## 15. Quy tắc update `brain/` và `reference/`

## 15.1. `brain/` không phải dump tất cả mọi thứ

Không được lấy mọi raw capture note rồi append bừa vào `brain/Memories.md`.

`brain/` chỉ nên chứa:

- patterns lặp lại nhiều lần;
- gotchas có giá trị lâu dài;
- quyết định quan trọng;
- note topic tóm tắt;
- voice preference;
- north star / goals.

## 15.2. `reference/` là lớp knowledge ổn định hơn capture

`reference/` nên được cập nhật khi:

- cùng một entity/concept xuất hiện nhiều lần;
- có đủ nội dung để tạo note tổng hợp;
- cần một “node trung tâm” để link các raw notes.

## 15.3. Luật promote note

### Capture → Reference

Promote khi:

- entity/concept xuất hiện từ 2 nguồn trở lên; hoặc
- một note có chất lượng đủ cao để thành canonical reference.

### Capture → Brain

Promote khi:

- đó là pattern/gotcha/decision lâu dài; hoặc
- nó ảnh hưởng tới cách hệ thống vận hành / trả lời / lưu trữ.

### Capture → Work

Promote khi:

- có project context rõ ràng;
- có task/action items;
- có decision/project evidence.

---

## 16. Bases cần có trong phase đầu

## 16.1. `Capture Inbox.base`

Mục tiêu:

- xem toàn bộ raw capture notes theo thời gian;
- filter theo `capture_type`, `source`, `tags`, `status`.

Thuộc tính cần hiển thị:

- `date`
- `capture_type`
- `source`
- `status`
- `entities`
- `original_url`

## 16.2. `Media Library.base`

Mục tiêu:

- xem riêng ảnh/video/audio có asset path;
- hỗ trợ card view với thumbnail.

## 16.3. `Sources.base`

Mục tiêu:

- xem các domain/source note trong `reference/sources/`;
- biết nguồn nào được lưu nhiều nhất.

## 16.4. `Brain Memory.base`

Mục tiêu:

- xem các note `brain/` như một database nhẹ;
- filter theo loại (`pattern`, `decision`, `gotcha`, `voice`).

## 16.5. `Recent Answers.base`

Mục tiêu:

- theo dõi những câu trả lời gần đây;
- audit chất lượng retrieval;
- xem answer nào dùng note nào.

---

## 17. Ví dụ `.base` cho `Capture Inbox.base`

```yaml
filters:
  and:
    - file.inFolder("Inbox")
    - file.hasTag("capture")
views:
  - type: table
    name: Inbox
    order:
      - date
      - source
      - capture_type
      - status
    properties:
      date:
        displayName: Date
      source:
        displayName: Source
      capture_type:
        displayName: Type
      status:
        displayName: Status
      original_url:
        displayName: URL
```

Lưu ý: `.base` là YAML, và toàn bộ dữ liệu vẫn nằm trong local Markdown files + properties của note.

---

## 18. Truy vấn nhanh: cú pháp đề xuất cho người dùng

Ngoài ngôn ngữ tự nhiên, query engine nên hỗ trợ mini syntax:

```text
type:video source:telegram tag:ai
folder:reference/concepts markitdown
status:processed after:2026-04-01 obsidian
entity:"MarkItDown" source:web
```

## 18.1. Quy tắc parse

- token có dạng `key:value` → filter metadata
- phần còn lại → keyword / semantic query
- nếu user không ghi filter → system tự đoán từ intent

## 18.2. Fast path

Nếu query chỉ là filter metadata, không cần gọi LLM. Chỉ trả danh sách note/record.

Ví dụ:

- `type:video source:telegram after:2026-04-01`

trả ngay danh sách note.

## 18.3. Answer path

Nếu query có tính hỏi đáp, hệ thống mới chạy answer synthesis.

Ví dụ:

- `mình đã quyết định gì về cấu trúc vault?`
- `tóm tắt những gì mình lưu về obsidian-mind`

---

## 19. Trả lời tự nhiên: style pipeline

## 19.1. Mục tiêu

Câu trả lời phải:

- tự nhiên;
- ngắn gọn vừa đủ;
- đúng dữ liệu;
- có thể kiểm tra lại bằng note nguồn.

## 19.2. Hai bước sinh câu trả lời

### Bước 1: factual grounded answer

Model tạo câu trả lời dựa trên:

- truy vấn người dùng
- top-k note excerpts
- metadata và citations

Output chưa cần “đẹp văn”.

### Bước 2: naturalization / voice adaptation

Model thứ hai hoặc pass thứ hai sẽ:

- làm câu trả lời mượt hơn;
- giữ nguyên nghĩa;
- không được thêm fact mới;
- tham chiếu `brain/Voice.md` nếu có.

## 19.3. `brain/Voice.md`

Khuyến nghị schema:

```md
# Voice Preferences

- Ngôn ngữ mặc định: tiếng Việt
- Phong cách: tự nhiên, rõ ý, không quá trang trọng
- Độ dài: ngắn đến trung bình
- Ưu tiên: kết luận trước, chi tiết sau
- Tránh: quá nhiều thuật ngữ nếu không cần
```

---

## 20. Lộ trình migrate

## 20.1. Phase 1 — Bootstrap profile

Mục tiêu:

- thêm các file/folder của `obsidian-mind` vào `vault/`
- giữ nguyên `Inbox/` và `Assets/`
- chưa thay đổi query engine quá sâu

Done khi:

- mở vault trong Obsidian được;
- có `Home.md`, `brain/`, `reference/`, `work/`, `org/`, `thinking/`, `bases/`, `templates/`.

## 20.2. Phase 2 — Exporter theo profile

Mục tiêu:

- worker tạo note đúng schema/frontmatter mới;
- mọi raw note có `description` + wikilink;
- sinh các template mở rộng cho capture note.

## 20.3. Phase 3 — Classification + promotion

Mục tiêu:

- detect entity/topic/decision/pattern;
- promote vào `reference/` và `brain/`;
- tạo Decision Record khi cần.

## 20.4. Phase 4 — Query + answer

Mục tiêu:

- thêm `/v1/query`;
- trả lời grounded + citations;
- Telegram và web app hỏi được bằng ngôn ngữ tự nhiên.

## 20.5. Phase 5 — Optional QMD mode

Mục tiêu:

- bổ sung QMD sidecar cho local/power search;
- dùng hybrid retrieval theo đúng tinh thần `obsidian-mind`.

## 20.6. Phase 6 — Reverse sync (tùy chọn)

Chỉ làm sau khi hệ thống ổn định.

Mục tiêu:

- đọc chỉnh sửa thủ công từ vault rồi sync ngược về canonical DB;
- có conflict policy rõ ràng.

Phase này **không thuộc MVP**.

---

## 21. Acceptance criteria

## 21.1. Vault profile

- [ ] chạy bootstrap tạo đủ file profile
- [ ] không ghi đè file người dùng đã sửa nếu không có cờ `--upgrade`
- [ ] `Home.md` mở được và embed được `.base` file

## 21.2. Capture pipeline

- [ ] text/link/image/video từ web/PWA/Telegram tạo raw note thành công
- [ ] asset lưu đúng vào `Assets/`
- [ ] raw note có `description`, `tags`, `status`, `source`
- [ ] raw note có ít nhất 1 wikilink

## 21.3. Promotion pipeline

- [ ] detect entity/concept và tạo/cập nhật reference note
- [ ] detect decision và tạo Decision Record
- [ ] detect pattern/gotcha và cập nhật `brain/`

## 21.4. Query pipeline

- [ ] query filter nhanh trả kết quả không cần LLM
- [ ] query tự nhiên trả answer grounded
- [ ] answer có citations tới note nguồn
- [ ] Telegram bot hỏi đáp được trên dữ liệu đã lưu

---

## 22. Rủi ro và cách giảm rủi ro

## 22.1. Rủi ro: vault bị biến thành “dump file” vô tổ chức

Giảm rủi ro bằng cách:

- raw capture luôn vào `Inbox/`
- chỉ promote lên `brain/`/`reference/` khi có rule rõ ràng
- thêm base views để kiểm tra orphan và stale note

## 22.2. Rủi ro: ghi đè file upstream / người dùng

Giảm rủi ro bằng cách:

- bootstrap một lần
- runtime không sửa infrastructure file
- upgrade có diff + backup

## 22.3. Rủi ro: answer nghe tự nhiên nhưng thiếu grounding

Giảm rủi ro bằng cách:

- answer generation bắt buộc dùng citations
- `humanize` chỉ chạy sau grounded draft
- không cho pass 2 thêm fact mới

## 22.4. Rủi ro: quá phụ thuộc vào Obsidian local behavior

Giảm rủi ro bằng cách:

- server search/index là đường chính
- Obsidian/QMD là layer bổ sung
- canonical DB vẫn tồn tại độc lập

---

## 23. Đề xuất triển khai thực tế trong repo hiện tại

## 23.1. Cây file đề xuất

```text
services/worker/app/
  classify.py
  route_obsidian_mind.py
  export_obsidian_mind.py
  update_brain.py
  update_reference.py
  build_bases.py
  query_index.py
  answer_writer.py

services/api/app/routes/
  health.py
  items.py
  query.py
  profile.py

packages/shared/src/
  note-types.ts
  query.ts
  citations.ts
  vault-profile.ts

vault/
  Home.md
  brain/
  reference/
  thinking/
  work/
  org/
  perf/
  bases/
  templates/
```

## 23.2. Tên adapter/exporter đề xuất

Tên chuẩn nên dùng trong code:

- `ObsidianMindProfile`
- `ObsidianMindExporter`
- `ObsidianMindRouter`
- `ObsidianMindBootstrapper`

## 23.3. Cờ cấu hình đề xuất

```env
BRAINVAULT_VAULT_PROFILE=obsidian-mind
BRAINVAULT_VAULT_PROFILE_VERSION=4.0.0
BRAINVAULT_QMD_ENABLED=false
BRAINVAULT_PERSIST_ANSWER_NOTES=true
BRAINVAULT_PROMOTE_TO_REFERENCE=true
BRAINVAULT_PROMOTE_TO_BRAIN=true
```

---

## 24. Kết luận cuối cùng

Cách tích hợp đúng không phải là “copy repo `obsidian-mind` vào dự án rồi dùng luôn như backend”.

Cách đúng là:

1. **Brain Vault server vẫn là canonical system**;
2. **`obsidian-mind` được dùng làm profile vault có cấu trúc**;
3. **giữ `Inbox/` và `Assets/` để không phá skeleton hiện tại**;
4. **thêm `brain/`, `reference/`, `thinking/`, `work/`, `org/`, `bases/`, `templates/` theo upstream**;
5. **dùng rule-based + LLM classification để promote từ raw capture sang memory/reference/work notes**;
6. **xây query engine grounded, có citations, và optional humanize theo `brain/Voice.md`**.

Nếu đi đúng theo đặc tả này, dự án sẽ có cả ba thứ cùng lúc:

- ingest backend đa nguồn;
- Obsidian vault dùng được thật;
- memory/query/answer layer có cấu trúc và mở rộng tốt.

---

## 25. Tài liệu tham khảo

1. `breferrari/obsidian-mind` README — persistent memory, tiered loading, hooks, commands, QMD-first retrieval.
2. `breferrari/obsidian-mind` `vault-manifest.json` — version `4.0.0`, released `2026-04-09`, infrastructure files, scaffold files, user content roots.
3. `breferrari/obsidian-mind` templates — `Work Note.md`, `Decision Record.md`, `Thinking Note.md`.
4. `breferrari/obsidian-mind` `CLAUDE.md` — graph-first linking, preserve frontmatter, `description` requirement, prefer `[[wikilinks]]`, prefer Obsidian CLI when app đang chạy.
5. Obsidian Help — Create a vault.
6. Obsidian Help — Import Markdown files.
7. Obsidian Help — Introduction to Bases.
8. Obsidian Help — Bases syntax.
9. `tobi/qmd` README — on-device search engine cho docs/markdown/meeting notes, hỗ trợ BM25 + vector search + hybrid query + reranking.
