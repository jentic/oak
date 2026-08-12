---
name: Replace OpenAPI in Jentic Public APIs
about: Completely delete an existing API folder and re-import it fresh from a new OpenAPI URL.
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

## Vendor Name (Required)
<!--
REQUIRED: Provide the vendor name of the folder to REPLACE (e.g., github.com, stripe.com).
The workflow deletes 'apis/openapi/<vendor>/<api_name>/' before re-importing.

Vendor name is parsed into vendor (vendor identifier) and api_name.

Examples:
- hashicorp.com
//=> deletes apis/openapi/hashicorp.com/main/, then re-imports (api_name=main)
- hashicorp.com/nomad
//=> deletes apis/openapi/hashicorp.com/nomad/, then re-imports (api_name=nomad)

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
