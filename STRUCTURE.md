# OAK Repository Structure

This document describes the standardized directory structure for OpenAPI specifications and workflows in the OAK repository.

## Overview

The repository uses a structured approach to organize:
1. API specifications - standardized OpenAPI documents organized by vendor
2. Workflows - collections of operations that may reference one or more APIs

## Directory Structure

```
__data__/
  ├── apis/                            # All API-related files
  │   └── openapi/                     # OpenAPI specifications
  │       ├── vendor.com/              # Vendor directory (usually domain name)
  │       │   ├── main/                # Default API for vendors with single API
  │       │   │   ├── meta.json        # API metadata with vendor/api_name/friendly_id fields
  │       │   │   └── 1.0.0/           # Version directory
  │       │   │       ├── openapi.json # Standardized OpenAPI spec with source URL in info section
  │       │   │       └── orig/        # Original files directory
  │       │   │           └── spec.yaml # Original spec file as downloaded
  │       │   └── other-api/           # Additional APIs for vendor if present
  │       │       ├── meta.json
  │       │       └── 2.0.0/
  │       │           ├── openapi.json # Standardized OpenAPI spec
  │       │           └── orig/        # Original files directory
  │       │               └── spec.yaml # Original spec file
  ├── workflows/                       # All workflow-related files
      ├── vendor1.com/                 # Vendor's main API workflows 
      │   ├── workflows.arrazo.json    # Default workflow file for this API
      │   └── payment-flows.arrazo.json # Purpose-specific workflow file
      ├── vendor2.com~api3/            # Non-main API with ~ separator
      │   ├── workflows.arrazo.json    # Default workflow file for this API
      │   └── custom-flows.arrazo.json # Custom workflow file
      └── vendor1.com+vendor2.com~api3/ # Multi-API workflows (alphabetical ordering)
          ├── workflows.arrazo.json    # Default workflows for these APIs
          └── integration-flows.arrazo.json # Specific integration workflows
tools/
  ├── jentic-mcp/
  ├── jentic-sdk/
  └── oak-runner/
```

## API Structure Details

### Vendor Organization

APIs are organized by vendor identifier first, allowing multiple APIs from the same vendor to be grouped together:

- **Vendor directory**: The top level is the vendor identifier, usually a domain name but not necessarily (e.g., `microsoft.com`, `googleapis.com`, `stripe.com`)
- **API directories**: Within each vendor directory, one or more API directories exist:
  - **main**: For vendors with only one API, the API is stored in the `main` directory
  - **specific-api-name**: For vendors with multiple APIs, each API gets its own directory with a descriptive name

### Version Management

Each API is versioned:

- Version directories are named according to the version in the OpenAPI spec (`info.version`)
- Each version contains:
  - `openapi.json`: The standardized OpenAPI specification in JSON format
  - `orig/`: A directory containing the original specification file as it was downloaded

### Metadata

Each API has a `meta.json` file at the API directory level containing:

```json
{
  "oak_meta": "1.0.0",
  "api_info": {
    "id": "md5hash",
    "format": "openapi",
    "vendor": "vendor",
    "api_name": "api_name",
    "friendly_id": "vendor" or "vendor/api_name"
  }
}
```

- **id**: An MD5 hash of "vendor/api_name" for unique identification
- **format**: The specification format (typically "openapi")
- **vendor**: The vendor identifier (usually a domain name)
- **api_name**: The API name (or "main" for single APIs)
- **friendly_id**: A human-readable identifier:
  - For main APIs: just the vendor identifier (e.g., "microsoft.com")
  - For non-main APIs: vendor/api_name (e.g., "microsoft.com/graph")

The source URL is stored as `x-jentic-source-url` in the `info` section of the standardized OpenAPI spec. This provides traceability back to the original source of the API specification.

## Workflow Structure Details

Workflows are organized to clearly indicate which APIs they reference:

### Directory Naming Conventions

- **Single API workflows**: Directory named after the API they reference
  - For main APIs: just the vendor identifier (e.g., `stripe.com`)
  - For non-main APIs: vendor~api-name (e.g., `microsoft.com~graph`)
- **Multi-API workflows**: Directory name combines APIs in alphabetical order
  - Uses `+` to separate different APIs (e.g., `stripe.com+twilio.com~messaging`)
  - Uses `~` to separate vendor and API name for non-main APIs

### Workflow Files

Each workflow directory can contain multiple `.arrazo.json` files:

- `workflows.arrazo.json`: The default workflow file
- Additional named workflow files for specific purposes:
  - `payment-flows.arrazo.json`
  - `auth-flows.arrazo.json`
  - `integration-flows.arrazo.json`
  - etc.

## Tools Directory

The `tools/` directory contains supporting utilities and libraries developed as part of the OAK initiative:

- **`jentic-mcp/`**: Contains the Jentic MCP Plugin, which allows IDEs and agents to interact with the Jentic platform for API discovery and workflow generation via the Model Context Protocol.
- **`jentic-sdk/`**: Provides the Jentic SDK, a Python library for generating LLM-compatible tools and executing OAK workflows and API operations within agentic applications.
- **`oak-runner/`**: Houses the OAK Runner, a reference execution engine for Arazzo workflows and OpenAPI operations defined in the repository.

Each tool subdirectory contains its own `README.md` with specific usage and development instructions. A summary can also be found in [`tools/README.md`](../tools/README.md).
