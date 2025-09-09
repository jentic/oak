# Feedback Files

## Overview

The OAK repository includes `feedback.json` files that document repairs and improvements made to OpenAPI specifications. These files provide create an audit trail for API specification quality improvements intended for future human and LLM use.

## Purpose

Feedback files serve several important purposes:

1. **Documentation**: Track what changes were made to API specifications and why.
2. **Prevention**: Ensure that when future API changes are made, we don't reintroduce previous issues.

## File Structure

Feedback files are JSON arrays containing repair records. Each record documents a set of repairs made to a specification file.

### Schema

```json
[
  {
    "repaired_file": "string",
    "repairs": [
      {
        "issue": {
          "message": "string",
          "level": "error|warning|improvement",
          "location": {
            "jsonPath": "string"
          }
        },
        "action_taken": "string",
        "source": "human|LLM-suggestion|automated-tool",
        "timestamp": "ISO 8601 timestamp"
      }
    ]
  }
]
```

### Field Descriptions

- **repaired_file**: Name of the file that was repaired (typically "openapi.json")
- **repairs**: Array of individual repair operations
  - **issue**: Description of the problem that was found
    - **message**: Human-readable description of the issue
    - **level**: Severity level (error, warning, improvement)
    - **location**: Where the issue was found
      - **jsonPath**: JSON Path to the specific location in the file
  - **action_taken**: Description of what was done to fix the issue
  - **source**: Who or what made the repair (human, LLM-suggestion, automated-tool)
  - **timestamp**: When the repair was made

## Location

Feedback files are placed in the same directory as the OpenAPI specification they document, following this pattern:

```
apis/openapi/{vendor}/{service}/{version}/feedback.json
```

For example:
```
apis/openapi/atlassian.com/jira/1001.0.0-SNAPSHOT-636312f2dc6e26921216979d4ae12655beeff255/feedback.json
```

## Example

```json
[
  {
    "repaired_file": "openapi.json",
    "repairs": [
      {
        "issue": {
          "message": "Basic auth security scheme description lacks important information about API key usage",
          "level": "warning",
          "location": {
            "jsonPath": "#/components/securitySchemes/basicAuth/description"
          }
        },
        "action_taken": "Updated description to include: 'You can access this resource via basic auth. Important - An API key can be used as a password.'",
        "source": "human",
        "timestamp": "2025-05-23T09:50:50.000000"
      }
    ]
  }
]
```