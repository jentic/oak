# Notion API

Create, read, update, and search pages, databases, and content blocks in Notion workspaces programmatically.

| | |
|---|---|
| **Base URL** | `https://api.notion.com` |
| **Version** | `2026-03-11` |
| **Auth** | Bearer token |
| **Endpoints** | 29 operations |

## What you can build with this API

- Create and update pages with structured content, properties, and nested blocks
- Query databases with filters, sorts, and pagination to retrieve structured data
- Search across an entire workspace by keyword to find pages and databases
- Manage comments on pages — add discussion threads, retrieve feedback, delete resolved comments
- Upload and manage files attached to pages and databases
- Create custom database views with filters and sorts, then query view-specific results
- Handle OAuth token exchange, refresh, and revocation for third-party integrations

## Key resources

- **Pages** — create, read, update, delete, and convert pages to Markdown
- **Databases** — create, update, and query structured data stores with typed properties
- **Blocks** — read and modify content blocks (text, headings, lists, embeds) within pages
- **Views** — create filtered/sorted views on databases and query their results
- **Users** — list workspace members and retrieve the current authenticated user
- **Comments** — add and manage discussion threads on pages
- **Files** — upload files in chunks, attach them to pages or databases
- **Search** — full-text search across all accessible pages and databases

## Use this API with Jentic

Add your Notion credentials to Jentic once. Your agent gets a scoped access key and can discover, inspect, and call any operation — raw secrets never enter the prompt chain.

**Get started free:**

| Path | Best for |
|------|----------|
| [Jentic Cloud](https://jentic.com) | Claude, Cursor, ChatGPT, Windsurf — connect via MCP or the Claude Connector |
| [Jentic Mini](https://github.com/jentic/jentic-mini) | Self-hosted, one Docker command, full control (Apache 2.0, free) |

[Python SDK](https://docs.jentic.com/reference/sdks/) · [Quickstart](https://docs.jentic.com/getting-started/quickstart/) · [MCP setup](https://docs.jentic.com/guides/mcp/remote-mcp/)

---

*Part of [Jentic Public APIs](https://github.com/jentic/jentic-public-apis) — the open catalog of machine-readable API specs. `notion.com/notion-api`*
