"""
Seed content for obsidian-mind vault templates.
These strings are written once during bootstrap (only if the file does not yet exist).
"""

WORK_NOTE = """\
---
id: "{{id}}"
date: "{{date}}"
description: "{{description}}"
status: active
tags:
  - brain-vault
  - work
source: "{{source}}"
project: "{{project}}"
vault_profile: obsidian-mind
profile_version: "4.0.0"
---

# {{title}}

## Summary
{{summary}}

## Details
{{content}}

## Action Items
- [ ]

## Related Links
- [[work/Index]]
"""

DECISION_RECORD = """\
---
id: "{{id}}"
date: "{{date}}"
description: "{{description}}"
status: decided
tags:
  - brain-vault
  - decision
source: "{{source}}"
vault_profile: obsidian-mind
profile_version: "4.0.0"
---

# Decision: {{title}}

## Context
{{context}}

## Decision
{{decision}}

## Consequences
{{consequences}}

## Related Links
- [[brain/Key Decisions]]
"""

THINKING_NOTE = """\
---
id: "{{id}}"
date: "{{date}}"
description: "{{description}}"
status: draft
tags:
  - brain-vault
  - thinking
context: "{{context}}"
vault_profile: obsidian-mind
profile_version: "4.0.0"
---

# {{title}}

## Context
{{context}}

## Hypothesis
{{hypothesis}}

## Notes
{{content}}

## Related Links
- [[brain/Patterns]]
"""

CAPTURE_TEXT_NOTE = """\
---
id: "{{id}}"
date: "{{date}}"
description: "{{description}}"
status: processed
tags:
  - brain-vault
  - capture
  - capture-text
source: "{{source}}"
capture_type: text
created_at: "{{created_at}}"
updated_at: "{{updated_at}}"
vault_profile: obsidian-mind
profile_version: "4.0.0"
canonical_item_id: "{{canonical_item_id}}"
language: "{{language}}"
entities: []
summary_ready: false
---

# {{title}}

## Summary
{{summary}}

## Normalized Content
{{content}}

## Extractions
- entities: {{entities}}
- tags: {{tags}}
- source: {{source}}

## Related Links
- [[brain/Memories]]
"""

CAPTURE_LINK_NOTE = """\
---
id: "{{id}}"
date: "{{date}}"
description: "{{description}}"
status: processed
tags:
  - brain-vault
  - capture
  - capture-link
source: "{{source}}"
capture_type: link
content_type: text/uri-list
created_at: "{{created_at}}"
updated_at: "{{updated_at}}"
vault_profile: obsidian-mind
profile_version: "4.0.0"
canonical_item_id: "{{canonical_item_id}}"
original_url: "{{original_url}}"
language: "{{language}}"
entities: []
summary_ready: false
embedding_ready: false
---

# {{title}}

## Summary
{{summary}}

## Normalized Content
{{content}}

## Extractions
- entities: {{entities}}
- tags: {{tags}}
- source: {{source}}

## Related Links
- [[brain/Memories]]
"""

CAPTURE_IMAGE_NOTE = """\
---
id: "{{id}}"
date: "{{date}}"
description: "{{description}}"
status: processed
tags:
  - brain-vault
  - capture
  - capture-image
source: "{{source}}"
capture_type: image
mime_type: "{{mime_type}}"
created_at: "{{created_at}}"
updated_at: "{{updated_at}}"
vault_profile: obsidian-mind
profile_version: "4.0.0"
canonical_item_id: "{{canonical_item_id}}"
asset_paths: []
ocr_text_available: false
caption_available: false
---

# {{title}}

## Summary
{{summary}}

## Assets
{{assets}}

## Normalized Content
{{content}}

## Related Links
- [[brain/Memories]]
"""

CAPTURE_VIDEO_NOTE = """\
---
id: "{{id}}"
date: "{{date}}"
description: "{{description}}"
status: processed
tags:
  - brain-vault
  - capture
  - capture-video
source: "{{source}}"
capture_type: video
mime_type: "{{mime_type}}"
created_at: "{{created_at}}"
updated_at: "{{updated_at}}"
vault_profile: obsidian-mind
profile_version: "4.0.0"
canonical_item_id: "{{canonical_item_id}}"
asset_paths: []
transcript_status: pending
duration_seconds: 0
speaker_count: 0
---

# {{title}}

## Summary
{{summary}}

## Transcript
{{transcript}}

## Related Links
- [[brain/Memories]]
"""

TELEGRAM_MESSAGE_NOTE = """\
---
id: "{{id}}"
date: "{{date}}"
description: "{{description}}"
status: processed
tags:
  - brain-vault
  - capture
  - telegram
source: telegram
capture_type: "{{capture_type}}"
created_at: "{{created_at}}"
updated_at: "{{updated_at}}"
vault_profile: obsidian-mind
profile_version: "4.0.0"
canonical_item_id: "{{canonical_item_id}}"
chat_id: "{{chat_id}}"
source_message_id: "{{source_message_id}}"
entities: []
---

# {{title}}

## Summary
{{summary}}

## Normalized Content
{{content}}

## Extractions
- entities: {{entities}}
- tags: {{tags}}

## Related Links
- [[brain/Memories]]
"""

QUERY_ANSWER_NOTE = """\
---
id: "{{id}}"
date: "{{date}}"
description: "{{description}}"
status: answered
tags:
  - brain-vault
  - query-answer
  - natural-answer
source: query
created_at: "{{created_at}}"
updated_at: "{{updated_at}}"
vault_profile: obsidian-mind
profile_version: "4.0.0"
query_text: "{{query_text}}"
answer_style: natural-grounded
retrieval_mode: hybrid
used_notes: []
---

# Query: {{query_text}}

## Answer
{{answer}}

## Citations
{{citations}}

## Related Notes
{{related_notes}}
"""

# Map: filename → content
ALL_TEMPLATES: dict[str, str] = {
    "Work Note.md": WORK_NOTE,
    "Decision Record.md": DECISION_RECORD,
    "Thinking Note.md": THINKING_NOTE,
    "Capture Text Note.md": CAPTURE_TEXT_NOTE,
    "Capture Link Note.md": CAPTURE_LINK_NOTE,
    "Capture Image Note.md": CAPTURE_IMAGE_NOTE,
    "Capture Video Note.md": CAPTURE_VIDEO_NOTE,
    "Telegram Message Note.md": TELEGRAM_MESSAGE_NOTE,
    "Query Answer Note.md": QUERY_ANSWER_NOTE,
}
