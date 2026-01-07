# AGENTS.md

This repository contains OpenAPI specifications and Arazzo workflows for 1,500+ public APIs. It follows the OAK (Open Agentic Knowledge) standard.

## Repository structure

- `/apis/openapi/{vendor}/{api}/{version}/` — OpenAPI specs (JSON/YAML)
- `/workflows/{vendor}/{api}/` — Arazzo workflow definitions
- `oak.csv` — Registry of connected OAK repositories
- `STRUCTURE.md` — Detailed file naming conventions

## For AI coding agents

When working with this repository:

1. **Finding specs**: Search `/apis/openapi/` by vendor name. Each vendor folder contains versioned API specifications.

2. **Finding workflows**: Arazzo workflows are in `/workflows/` and reference OpenAPI specs via `sourceDescriptions`.

3. **File formats**: OpenAPI specs are OpenAPI 3.x (JSON or YAML). Workflows follow the Arazzo 1.0 specification.

4. **Do not modify specs directly** unless fixing validation errors. Submit issues for content changes.

5. **Validation**: Run OpenAPI specs through a validator before committing. Arazzo workflows should reference valid `operationId` values from their source specs.

## Contributing

- New API specs: Submit via GitHub issue using the "Add API Integration" template
- New workflows: Use the "Generate Arazzo Specification" issue template
- Spec fixes: PRs welcome for validation errors or broken references

## Related standards

- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html)
- [Arazzo Specification](https://spec.openapis.org/arazzo/latest.html)
- [OAK Standard](./OAK.md)
