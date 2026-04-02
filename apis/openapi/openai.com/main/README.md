# OpenAI API

Generate text, images, audio, embeddings, and structured outputs using GPT, DALL-E, Whisper, and other OpenAI models.

| | |
|---|---|
| **Base URL** | `https://api.openai.com/v1` |
| **Version** | `2.3.0` |
| **Auth** | Bearer token |
| **Endpoints** | 85 operations |

## What you can build with this API

- Generate text completions and chat responses using GPT models with function calling and structured outputs
- Create and manage persistent assistants with instructions, tools, and file access
- Generate images from text prompts and edit existing images with DALL-E
- Transcribe and translate audio files using Whisper, or generate speech from text
- Create vector embeddings for semantic search, clustering, and classification
- Run batch jobs to process large volumes of requests asynchronously at reduced cost
- Fine-tune models on custom datasets to improve performance on specific tasks

## Key resources

- **Chat Completions** — send messages, receive model responses, stream tokens, use tools
- **Assistants** — create stateful agents with instructions, code interpreter, and file search
- **Images** — generate, edit, and create variations of images
- **Audio** — speech-to-text (transcription), text-to-speech, and translation
- **Embeddings** — convert text to vector representations for search and similarity
- **Files** — upload training data, batch inputs, and assistant knowledge files
- **Fine-tuning** — customize models with your own training examples
- **Batch** — submit large request sets for async processing

## Use this API with Jentic

Jentic sits between your agent and this API. The agent searches by intent, loads operation details, and executes — while credentials stay encrypted in the vault, isolated from the agent.

**Get started free:**

| Path | Best for |
|------|----------|
| [Jentic Cloud](https://jentic.com) | Claude, Cursor, ChatGPT, Windsurf — connect via MCP or the Claude Connector |
| [Jentic Mini](https://github.com/jentic/jentic-mini) | Self-hosted, one Docker command, full control (Apache 2.0, free) |

[MCP setup](https://docs.jentic.com/guides/mcp/remote-mcp/) · [Python SDK](https://docs.jentic.com/reference/sdks/) · [Quickstart](https://docs.jentic.com/getting-started/quickstart/)

---

*Part of [Jentic Public APIs](https://github.com/jentic/jentic-public-apis) — the open catalog of machine-readable API specs. `openai.com/main`*
