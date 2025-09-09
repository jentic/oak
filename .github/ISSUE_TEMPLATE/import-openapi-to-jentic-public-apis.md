---
name: Import OpenAPI to Jentic Public APIs
about: Request import of OpenAPI spec to Jentic Public APIs from an OpenAPI URL.
title: "[AUTO] Import OpenAPI to Jentic Public APIs: "
labels: enhancement
assignees: ''

---

## OpenAPI Specification URL
<!-- 
REQUIRED: Please provide the RAW URL to the OpenAPI specification (.json or .yaml file).
The workflow will download this URL, unzip the contents into the repository, and create a PR.

For GitHub repositories:
- CORRECT: https://raw.githubusercontent.com/.../openapi.json
- INCORRECT: https://github.com/.../blob/.../openapi.json

The URL should point directly to the spec file, not a web page.
-->
import_oas_url: 

## Vendor Name (Required)
<!-- 
REQUIRED: Provide the vendor name (e.g., github.com, stripe.com).
The workflow will place the *contents* of this directory under 'apis/openapi/vendor_name/'.

Vendor name is parsed into `vendor` (vendor identifier) and `api_name`.

Examples:
- hashicorp.com
//=> vendor=hashicorp.com; api_name=main
- hashicorp.com/nomad 
//=> vendor=hashicorp.com; api_name=nomad
-->
vendor_name: 

## Additional Information
<!-- Optional: Add any additional context about this API that might be helpful -->
