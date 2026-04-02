# Stripe API

Accept payments, manage subscriptions, handle payouts, and build financial workflows for any business model.

| | |
|---|---|
| **Base URL** | `https://api.stripe.com/` |
| **Version** | `2026-03-25.dahlia` |
| **Auth** | HTTP Basic or Bearer token |
| **Endpoints** | 414 operations |

## What you can build with this API

- Accept one-time and recurring payments using cards, bank transfers, wallets, and 40+ local payment methods
- Create and manage subscriptions with metered billing, usage-based pricing, trials, and automatic invoicing
- Set up multi-party payments with Connect — split funds between platforms and sellers, handle onboarding and verification
- Issue virtual and physical cards, manage cardholders, and control spending with Issuing
- Verify customer identities using government-issued documents and biometric checks
- Automate tax calculation, reporting, and collection across jurisdictions
- Manage disputes, refunds, and fraud prevention with Radar rules

## Key resources

- **Payment Intents** — create, confirm, capture, and cancel payments across any payment method
- **Customers** — store payment methods, track purchase history, manage billing details
- **Subscriptions** — recurring billing with plans, prices, coupons, and usage records
- **Invoices** — generate, send, finalize, and void invoices with line items and tax
- **Connect Accounts** — onboard sellers and service providers, manage payouts and transfers
- **Refunds** — issue full or partial refunds on charges and payment intents
- **Products & Prices** — define what you sell and how much it costs
- **Checkout Sessions** — hosted payment pages with built-in conversion optimization

## Use this API with Jentic

Three steps: search for what you need, load the operation schema, execute. Your agent calls this API through Jentic without touching API keys — credentials are injected server-side at runtime.

**Get started free:**

| Path | Best for |
|------|----------|
| [Jentic Cloud](https://jentic.com) | Claude, Cursor, ChatGPT, Windsurf — connect via MCP or the Claude Connector |
| [Jentic Mini](https://github.com/jentic/jentic-mini) | Self-hosted, one Docker command, full control (Apache 2.0, free) |

[Quickstart](https://docs.jentic.com/getting-started/quickstart/) · [MCP setup](https://docs.jentic.com/guides/mcp/remote-mcp/) · [Python SDK](https://docs.jentic.com/reference/sdks/)

---

*Part of [Jentic Public APIs](https://github.com/jentic/jentic-public-apis) — the open catalog of machine-readable API specs. `stripe.com/stripe-api`*
