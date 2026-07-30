# Contributing to the Jentic API Directory

Thank you for your interest in contributing to the Jentic API Directory! This document outlines the process for contributing to the repository.

## Our Mission

The Jentic API Directory aims to build an open knowledge foundation that empowers AI to interact with the world's APIs without artificial barriers or unnecessary intermediaries. By contributing, you're helping create a comprehensive "knowledge layer" for agents - a communal repository of detailed, AI-optimized information about public APIs.

> **Note:** We are actively developing tools to make the feedback and PR process easier for contributors. Stay tuned for updates that will streamline the contribution workflow to help you effortlessly participate in building the Jentic API Directory.

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [hello@jentic.com](mailto:hello@jentic.com).

## Getting Started

1. **Fork the Repository**: Start by forking the repository to your own GitHub account.
2. **Clone the Repository**: Clone your forked repository to your local machine.
3. **If preparing a contribution** review [Contribution Process](#contribution-process).

## What We're Looking For

We welcome contributions in the following areas:

1. **API Specifications Enhancements**: Improvements to the OpenAPI specifications contained in this repository, including new specifications, better descriptions, more comprehensive error handling, improved examples, and more accurate schema definitions.
2. **Arazzo Workflows**: New workflows or improvements to those listed in this repository, expressed as Arazzo specifications, which describe workflows composed of OpenAPI operations and other workflows.
3. **Documentation Improvements**: Enhancements documentation, examples, and guides.
4. **Tooling**: Tools that help with validation, generation, or management of API specifications.

## Quality Standards

### For OpenAPI Specifications

- Should be valid OpenAPI 3.0 or higher (OpenAPI 2.0 is accepted and converted during import)
- Must include comprehensive schema definitions
- All endpoints must have accurate descriptions and example responses
- Authentication methods must be clearly documented
- Rate limits and other important API behaviors should be noted

### For Arazzo Workflows

Arazzo workflows are a core focus of the Jentic API Directory. They define composable operations across one or more APIs. Contributed workflows:

- Must follow the OpenAPI Initiative's Arazzo specification
- Should include clear documentation of inputs, outputs, and purpose
- Provide meaningful descriptions for each step in the workflow
- Include example values to aid agent understanding
- Document any authentication requirements clearly
- Use a consistent, logical flow with clear transition conditions

#### Workflow Organization

Workflows should be structured according to our standardized directory structure:

- **Single API workflows**: Directory named after the API they reference
  - For primary APIs: just the vendor identifier (e.g., `stripe.com`)
  - For sub APIs: vendor~api-name (e.g., `microsoft.com~graph`)
- **Multi-API workflows**: Directory name combines APIs in alphabetical order
  - Uses `+` to separate different primary APIs (e.g., `stripe.com+twilio.com`)
  - Uses `+` and `~` to refer to sub APIs (e.g., `stripe.com+twilio.com~messaging`)
  - Uses `~` to refer to multiple sub APIs (e.g., `twilio.com~messaging~video`)

#### Workflow Files

Contribute Arazzo workflows as `.arazzo.json` files:

- `workflows.arazzo.json`: The default workflow file for general operations
- Purpose-specific workflow files with descriptive names:
  - `payment-flows.arazzo.json`
  - `auth-flows.arazzo.json`
  - `integration-flows.arazzo.json`

#### Cross-API Workflows

We particularly value contributions of cross-API workflows that demonstrate how multiple services can be orchestrated together. For these:

- Ensure directory names follow the multi-API convention with alphabetical ordering
- Document dependencies between API calls clearly
- Explain any data transformations needed between different APIs
- Provide example values that show realistic data flows
- Consider error handling and fallback strategies between services

#### Workflow Quality Guidelines

Effective Arazzo workflows should:

- Be modular and composable, allowing for reuse in different contexts
- Handle errors gracefully with appropriate recovery actions
- Include sufficient contextual information for AI agents to understand intent
- Use consistent parameter naming conventions across related operations
- Document any rate limiting or other API behavior considerations

## Contribution Process

1. **Create a Branch**: Create a branch in your forked repository for your contribution.
2. **Make Your Changes**: Implement your changes, following our style and quality guidelines.
3. **Test Your Changes**: Ensure your contributions validate against OpenAPI standards.
4. **Submit a Pull Request**: Open a pull request from your branch to our main repository.

## Pull Request Process

1. Update any relevant documentation with details of changes if appropriate.
2. Include a clear description of the changes and their benefits in your PR.
3. The PR will be reviewed by maintainers, who may request changes.
4. Once approved, your PR will be merged by a maintainer.

## Development Workflow

- **Branch Naming**: Use descriptive names: `feature/description`, `fix/issue-description`
- **Commit Messages**: Write clear, concise commit messages describing your changes
- **Documentation**: Update relevant documentation when making changes

## Directory Structure

When adding new API specifications or workflows, please follow our established directory structure as documented in [STRUCTURE.md](STRUCTURE.md). This document provides comprehensive guidance on:

- API organization by vendor and version
- Workflow file naming conventions
- Multi-API workflow organization
- Required metadata files

Please refer to this document before submitting any contributions to ensure your submissions follow our standardized structure.

## Validation

Before submitting, please validate your OpenAPI specifications using standard validation tools like:

- [Swagger Validator](https://validator.swagger.io/)
- [Spectral](https://github.com/stoplightio/spectral)
- [OpenAPI-Validator](https://github.com/IBM/openapi-validator)

## Community

- **Discussions**: [Insert forum/discussion board]
- **Questions**: Open an issue with a "question" label for any questions
- **Meetings**: [Insert information about community meetings if applicable]

## Recognition

Contributors will be recognized in our documentation and through appropriate credit mechanisms. We believe in acknowledging all forms of contribution.

Thank you for helping build the open knowledge foundation for AI agents!

---

*This document may be updated as the project evolves.*
