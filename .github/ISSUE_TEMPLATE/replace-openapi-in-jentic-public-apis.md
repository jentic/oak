---
name: Replace OpenAPI in Jentic Public APIs (raw / agent fallback)
about: Plain-markdown fallback for the Replace form. Prefer the "Replace OpenAPI in Jentic Public APIs" form; use this only for programmatic/agent submissions.
title: "[AUTO] Replace OpenAPI in Jentic Public APIs: "
labels: enhancement
assignees: ''

---

<!--
⚠️ DESTRUCTIVE OPERATION — READ FIRST

This is NOT an update or a merge. Use this template only when you are re-publishing
the SAME vendor/api with a brand-new version of the spec and want the whole prior
folder discarded.

When this issue is opened, the workflow will:
  1. COMPLETELY DELETE the existing 'apis/openapi/<vendor>/<api_name>/' folder —
     every version directory AND the api-level meta.json. Nothing from the old
     folder is preserved.
     - If that api was the only api under the vendor, the now-empty vendor folder
       'apis/openapi/<vendor>/' is deleted too.
  2. Run the import pipeline against the new URL below, which regenerates the
     ENTIRE folder structure from scratch: version directory, openapi.json,
     api-level and version-level meta/metadata, and the API scorecard/scoring.
  3. Open a PR against 'main' with the replacement so it can be reviewed before it
     merges.

If you only want to ADD a new version alongside existing ones (without deleting
anything), use the "Import OpenAPI to Jentic Public APIs" template instead — this
one throws the old folder away.
-->

## New OpenAPI Specification URL
<!--
REQUIRED: Provide the RAW URL to the NEW OpenAPI specification (.json or .yaml file)
that should replace the existing folder.

For GitHub repositories:
- CORRECT: https://raw.githubusercontent.com/.../openapi.json
- INCORRECT: https://github.com/.../blob/.../openapi.json

The URL should point directly to the spec file, not a web page.
-->
replace_oas_url: 

## Vendor / API Name (Required)
<!--
REQUIRED: Provide the fully-qualified '<vendor>/<api_name>' of the folder to
REPLACE (e.g., hashicorp.com/nomad, stripe.com/payments).
The workflow deletes 'apis/openapi/<vendor>/<api_name>/' before re-importing.

⚠️ The '/<api_name>' segment is MANDATORY for replace.
Unlike the import template, replace does NOT default a bare vendor to 'main'.
Because this operation deletes the target folder, a defaulted 'main' could
either create a spurious 'main' api or delete the wrong api on a vendor that has
several — so you must name the exact api folder.

Examples:
- hashicorp.com/nomad
//=> deletes apis/openapi/hashicorp.com/nomad/, then re-imports (api_name=nomad)
- stripe.com/payments
//=> deletes apis/openapi/stripe.com/payments/, then re-imports (api_name=payments)

Not allowed:
- hashicorp.com        (missing '/<api_name>' — the workflow will reject this)

⚠️ Double-check this value: an incorrect vendor/api will delete the wrong folder.
The deletion is reviewable in the resulting PR before it merges.
-->
vendor_name: 

## Confirm Replacement
<!--
Optional but recommended: confirm you understand the existing folder (all versions,
meta, and scoring) will be deleted and regenerated. e.g. "Confirmed — replacing the
old spec with vX.Y".
-->

## Additional Information
<!-- Optional: Add any additional context about this replacement that might be helpful -->
