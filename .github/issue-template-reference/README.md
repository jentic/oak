# Issue template reference (not picker templates)

These `.md` files are **not** GitHub issue templates and do **not** appear in the
*New issue* picker — that's intentional. They live here, outside
`.github/ISSUE_TEMPLATE/`, so the picker shows only the human-friendly issue
**forms** (`.github/ISSUE_TEMPLATE/*.yml`).

## Purpose

They document the canonical issue **body shape** for programmatic / agent
submissions. The import, replace, and Arazzo GitHub Actions workflows trigger on
and parse the issue body directly (line-anchored keys such as
`import_oas_url:`, `replace_oas_url:`, `vendor_name:`, `openapi_url:`) — an agent
opening an issue via the API or `gh` posts a body straight into the issue and
never uses the picker, so it needs a reference for the exact required lines.

## For humans

Use the issue forms on the *New issue* page instead:

- **Import OpenAPI to Jentic Public APIs** → `.github/ISSUE_TEMPLATE/import-openapi-to-jentic-public-apis.yml`
- **Replace OpenAPI in Jentic Public APIs** → `.github/ISSUE_TEMPLATE/replace-openapi-in-jentic-public-apis.yml`
- **Generate Arazzo Specification for Jentic OpenAPI** → `.github/ISSUE_TEMPLATE/generate-arazzo-spec.yml`

## Keeping these in sync

If a workflow's expected keys change, update **both** the form here's counterpart
in `ISSUE_TEMPLATE/*.yml` **and** the matching reference file in this directory.
