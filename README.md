# Jentic Public APIs

[![Discord](https://img.shields.io/badge/JOIN%20OUR%20DISCORD-COMMUNITY-7289DA?style=plastic&logo=discord&logoColor=white)](https://discord.gg/yrxmDZWMqB)

> **Join our community!** Connect with contributors and users on [Discord](https://discord.gg/yrxmDZWMqB) to discuss ideas, ask questions, and collaborate on the Jentic Public APIs repository.

## Overview

[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-40c463.svg)](CODE_OF_CONDUCT.md)
[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-blue)](LICENSE.md)

### The agentic knowledge layer

AI agents depend on APIs. Their capabilities are defined by the APIs they know about, and their reliability is defined by the quality of that knowledge. Documentation was previously nice-to-have, but for AI it's a *need-to-have*. The goal of this project is to collate all knowledge about all the world's APIs into a communal, detailed, comprehensive, structured documentation catalog designed for use by AI.  This allows AI to accurately generate API integration code, and it allows agents to plan and interact with APIs reliably, without intermediaries.

### Open source and open standards

This communal effort requires a stable but extensible representation format that can describe all salient aspects of APIs and associated workflows in full detail. The [OpenAPI specifications](https://www.openapis.org/) provide the de-facto standard for formal API descriptions, are widely adopted, supported by a vast ecosystem of associated tooling, and governed by the Linux Foundation. Importantly, the OpenAPI Initiative's most recent specification, [Arazzo](https://www.openapis.org/arazzo), allows complex multi-API workflows to be described in a declarative format.

We previously launched the *OAK (Open Agentic Knowledge) initiative*, proposing a type of open-source catalog of API and workflow descriptions that builds upon these open standards to contribute API and workflow knowledge to AI agents. This repository is the first such OAK repository, and we welcome others to create their own. We will coordinate with the OpenAPI community, and propose an RFC containing various extensions to capture additional knowledge that is especially relevant in the context of AI agents (for example concerning authentication, rate limiting, pricing, governance and safety).  See [OAK.md](OAK.md) for more information about this initiative, and how to create your own OAK repository linked to this initiative. If you have suggestions to improve the OAK initiative, we welcome discussion on our Discord and PRs on the OAK.md file in this repository.

### AI-scale

Documenting all the world's API knowledge is made achievable by generative AI. Our starting point was OpenAPI documents provided by various vendors online (with special credit to the [APIs.guru](https://apis.guru/) repository). On top of this, we have generated thousands Arazzo workflows using AI. We are growing this repository using AI agents to import (and improve) existing OpenAPI documents and to generate new OpenAPI specifications where no structured documentation previously existed. Our AI agents are also discovering novel Arazzo workflows that can be performed on top of that API knowledge.  We will propose a scorecard evaluation to measure the quality of the generated documentation, allowing us to ensure that both the quantity and the quality of documentation increases as we progress.

We welcome all contributions from the community and from partners who want to accelerate this effort with their own resources and ingenuity. We will ensure that all contributions help the knowledge about each API and workflow in the repository to converge on the best canonical version.

### Repository Focus

The repository focuses on:
1. Standardized OpenAPI specifications for public APIs
2. Arazzo workflows that define composable operations across one or more APIs
3. Associated tooling, for example to help import and enrich documentation, or to convert it out into other formats (e.g., AI model provider's tool definition formats).
4. Evaluations and scorecards to measure API knowledge completeness, accuracy and AI-readiness
5. RFCs for extensions to open formats used in the repository, and any other proposals.

## Project Stage

> **Note:** This project is currently in ALPHA.

## Documentation

* [**OAK.md**](OAK.md) - The OAK manifesto: principles and vision behind the Open Agentic Knowledge (OAK) initiative.
* [**STRUCTURE.md**](STRUCTURE.md) - The OAK (Open Agentic Knowledge) Standard for repository structure
* [**FEEDBACK-FILES.md**](FEEDBACK-FILES.md) - Documentation of feedback.json files that track API specification repairs
* [**CONTRIBUTING.md**](CONTRIBUTING.md) - Guidelines for contributing to the repository
* [**CODE_OF_CONDUCT.md**](CODE_OF_CONDUCT.md) - Community standards and expectations
* [**LICENSE.md**](LICENSE.md) - CC0 1.0 License for this repository

## Repository Structure

This repository follows the OAK (Open Agentic Knowledge) Standard, which defines a standardized directory structure for organizing API specifications and workflows.

- API specifications are organized by vendor and version
- Workflows are organized to clearly show which APIs they reference
- Multi-API workflows demonstrate how different services can be orchestrated together

For detailed information, please refer to the [OAK Standard documentation](STRUCTURE.md).


## Acknowledgments

## Acknowledgments

The Jentic Public APIs project is built upon the foundation of open standards and community contributions. We extend our sincere gratitude to:

**The OpenAPI Initiative and Linux Foundation** - For creating, maintaining, and governing the OpenAPI Specification and Arazzo standards that form the backbone of this project. The OpenAPI Initiative's commitment to open standards, extensive ecosystem of tooling, and collaborative governance model directly enable our vision of a communal API knowledge layer. Special recognition goes to the technical steering committee and contributors who have developed these specifications to serve as the de-facto standard for API documentation, making structured, machine-readable API descriptions possible at scale.

**APIs.guru** - For providing the initial collection of OpenAPI specifications that helped bootstrap this repository. Their dedication to cataloging public APIs has been instrumental in our mission to create an open knowledge foundation for AI agents, and their pioneering work in API discovery laid important groundwork for projects like ours.

**The broader API community** - Including all the API providers, documentation authors, and open source contributors whose work makes comprehensive API knowledge possible. This project represents a continuation of the collaborative spirit that has driven API standardization and tooling development.

We are committed to contributing back to these communities through our proposed RFCs, quality improvements to existing specifications, and by demonstrating new applications of these open standards in the context of AI agents.

## Contributing

We welcome contributions from the community! Whether you're enhancing existing API specifications, creating new Arazzo workflows, or improving documentation, your contributions help build the open knowledge foundation for AI agents.

Please read our [Contributing Guidelines](CONTRIBUTING.md) for more information on how to get started.

## License

This project is licensed under the CC0 1.0 License - see the [LICENSE.md](LICENSE.md) file for details.

> **Disclaimer:** API specifications and workflows in this repository are based on publicly documented third-party APIs, with some modifications such as repairs to OpenAPI specs or creation of new specs from public API documentation. All **trademarks** and **service marks** are the property of their respective owners. This repository does **not** grant rights to use the underlying APIs.