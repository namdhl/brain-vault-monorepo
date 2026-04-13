"""
Seed content for obsidian-mind vault .base files.
Written once during bootstrap (only if file does not yet exist).
"""

CAPTURE_INBOX_BASE = """\
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
      entities:
        displayName: Entities
"""

MEDIA_LIBRARY_BASE = """\
filters:
  or:
    - file.hasTag("capture-image")
    - file.hasTag("capture-video")
views:
  - type: table
    name: Media Library
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
      asset_paths:
        displayName: Assets
      status:
        displayName: Status
"""

SOURCES_BASE = """\
filters:
  and:
    - file.inFolder("reference/sources")
views:
  - type: table
    name: Sources
    order:
      - date
      - status
    properties:
      date:
        displayName: Date
      description:
        displayName: Description
      status:
        displayName: Status
      tags:
        displayName: Tags
"""

BRAIN_MEMORY_BASE = """\
filters:
  and:
    - file.inFolder("brain")
views:
  - type: table
    name: Brain Memory
    order:
      - date
      - status
    properties:
      date:
        displayName: Date
      description:
        displayName: Description
      status:
        displayName: Status
      tags:
        displayName: Tags
"""

RECENT_ANSWERS_BASE = """\
filters:
  and:
    - file.hasTag("query-answer")
views:
  - type: table
    name: Recent Answers
    sortBy:
      - property: date
        direction: desc
    order:
      - date
      - query_text
      - answer_style
      - status
    properties:
      date:
        displayName: Date
      query_text:
        displayName: Query
      answer_style:
        displayName: Style
      status:
        displayName: Status
      used_notes:
        displayName: Sources
"""

WORK_DASHBOARD_BASE = """\
filters:
  and:
    - file.inFolder("work")
    - file.hasTag("work")
views:
  - type: table
    name: Work Dashboard
    order:
      - date
      - status
      - project
    properties:
      date:
        displayName: Date
      description:
        displayName: Description
      status:
        displayName: Status
      project:
        displayName: Project
"""

PEOPLE_DIRECTORY_BASE = """\
filters:
  and:
    - file.inFolder("org/people")
views:
  - type: table
    name: People Directory
    order:
      - date
      - status
    properties:
      date:
        displayName: Date
      description:
        displayName: Description
      status:
        displayName: Status
      tags:
        displayName: Tags
"""

# Map: filename → content
ALL_BASES: dict[str, str] = {
    "Capture Inbox.base": CAPTURE_INBOX_BASE,
    "Media Library.base": MEDIA_LIBRARY_BASE,
    "Sources.base": SOURCES_BASE,
    "Brain Memory.base": BRAIN_MEMORY_BASE,
    "Recent Answers.base": RECENT_ANSWERS_BASE,
    "Work Dashboard.base": WORK_DASHBOARD_BASE,
    "People Directory.base": PEOPLE_DIRECTORY_BASE,
}
