# The Open Agentic Knowledge (OAK) repository

[![Discord](https://img.shields.io/badge/JOIN%20OUR%20DISCORD-COMMUNITY-7289DA?style=plastic&logo=discord&logoColor=white)](https://discord.gg/4BFEPssR5F)

> **Join our community!** Connect with contributors and users on [Discord](https://discord.gg/4BFEPssR5F) to discuss ideas, ask questions, and collaborate on the OAK repository.

## Overview

[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-40c463.svg)](CODE_OF_CONDUCT.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)

### The agentic knowedge layer

AI agents depend on APIs. Their capabilities are defined by the APIs they know about, and their reliability is defined by the quality of that knowledge. Documentation was previously nice-to-have, but for AI it's a *need-to-have*. The goal of this project is to collate all knowledge about all the world's APIs into a communal, detailed, comprehensive, structured documentation catalog designed for use by AI.  This allows AI to accurately generate API integration code, and it allows agents to plan and interact with APIs reliably, without intermediaries.

### Open source and open standards

This communal effort requires a stable but extensible representation format that can describe all salient aspects of APIs and associated workflows in full detail. The [OpenAPI specifications](https://www.openapis.org/) provide the de-facto standard for formal API descriptions, are widely adopted, supported by a vast ecosystem of associated tooling, and governed by the Linux Foundation. Importantly, the OpenAPI Initiative's most recent specification, [Arazzo](https://www.openapis.org/arazzo), allows complex multi-API workflows to be described in a declarative format. 

This repository represents API and workflow knowledge in these open-source formats. We will coordinate with the OpenAPI community, and propose an RFC containing various extensions to capture additional knowledge that is especially relevant in the context of AI agents (for example concerning authentication, rate limiting, pricing, governance and safety).

### AI-scale

Documenting all the world's API knowledge is made achievable by generative AI. Our starting point was OpenAPI documents provided by various vendors online (with special credit to the [APIs.guru](https://apis.guru/) repository). On top of this, we have generated many Arazzo workflows using AI. We will grow this repository using a research agent approach to pre-generate OpenAPI specifications where no structured documentation previously existed, and continue to discover new Arazzo workflows on top of that API knowledge.  We will propose a scorecard evaluation to measure the quality of the generated documentation, allowing us to ensure that both the quantity and the quality of documentation increases as we progress.

We welcome all contributions from the community and from partners who want to accelerate this effort with their own resources and ingenuity. We will ensure that all contributions help the knowledge about each API and workflow in the repository to converge on the best canonical version.

### Repository Focus

The repository focuses on:
1. Standardized OpenAPI specifications for public APIs
1. Arazzo workflows that define composable operations across one or more APIs
1. Associated tooling, for example to help import and enrich documentation, or to convert it out into other formats (e.g., AI model provider's tool definition formats).
1. Reference implementations of libraries to allow easy execution of API operations and workflows in this repository.
1. Evaluations and scorecards to measure API knowledge completeness, accuracy and AI-readiness
1. RFCs for extensions to open formats used in the repository, and any other proposals.

## Project Stage

> **Note:** This project is currently in ALPHA.

## Documentation

* [**MANIFESTO.md**](MANIFESTO.md) - The principles and vision behind The OAK Repository
* [**STRUCTURE.md**](STRUCTURE.md) - Detailed documentation of our standardized directory structure
* [**CONTRIBUTING.md**](CONTRIBUTING.md) - Guidelines for contributing to the repository
* [**CODE_OF_CONDUCT.md**](CODE_OF_CONDUCT.md) - Community standards and expectations
* [**LICENSE.md**](LICENSE.md) - MIT License for this repository

## Repository Structure

The OAK Repository organizes API specifications and workflows using a standardized directory structure:

- API specifications are organized by vendor and version
- Workflows are organized to clearly show which APIs they reference
- Multi-API workflows demonstrate how different services can be orchestrated together
- The `tools` directory contains supporting utilities like the [Jentic MCP Plugin](tools/jentic-mcp/README.md), the [Jentic SDK](tools/jentic-sdk/README.md), and the [OAK Runner](tools/oak-runner/README.md). See the [tools README](tools/README.md) for more details.

For detailed information on the directory structure, please refer to [STRUCTURE.md](STRUCTURE.md).

## OAK Runner

The **OAK Runner** is the reference tool for executing agentic workflows and API operations described in this repository. It provides a robust engine for running OpenAPI and Arazzo-based workflows, handling authentication, security requirements, and step orchestration for agents and developers alike.

- **Location:** The OAK Runner tool and its source code can be found in [`tools/oak-runner/`](tools/oak-runner/).

For setup and usage instructions, see the [`tools/oak-runner/README.md`](tools/oak-runner/README.md).

## Acknowledgments

The OAK Repository would like to express our sincere gratitude to [APIs.guru](https://apis.guru/) for providing the initial collection of OpenAPI specifications that helped bootstrap this repository. Their dedication to cataloging public APIs has been instrumental in our mission to create an open knowledge layer for AI agents.

OpenAPI etc.

## Contributing

We welcome contributions from the community! Whether you're enhancing existing API specifications, creating new Arazzo workflows, or improving documentation, your contributions help build the open knowledge foundation for AI agents.

Please read our [Contributing Guidelines](CONTRIBUTING.md) for more information on how to get started.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
