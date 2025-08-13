# The Open Agentic Knowledge (OAK) Manifesto
**Version:** 0.1.0
**Date:** August 2025
**Status:** Draft

Agents depend on APIs as much as AI. Chatbots chat, but agents act, and they act through APIs: checking calendars, booking flights, analyzing data, reconciling accounts, and controlling smart buildings. To realize this potential, we must build a common knowledge foundation that empowers AI to interact with the world's APIs reliably and without artificial barriers or unnecessary intermediaries.

## Principles

1. **Documentation Is Essential Infrastructure**  
   While humans can work around incomplete API documentation through online research and experimentation, agent reliability depends on comprehensive documentation. API documentation is the map by which agents can navigate their action space. Good documentation was once a "nice-to-have", but is now a "need-to-have."

2. **Traditional API Integration Involved Middlemen**
   Before generative AI, the complexity of API integration gave rise to an ecosystem of intermediaries such as API marketplaces, aggregators, and integration platforms. These companies helped human developers integrate public APIs, while imposing additional costs and often creating vendor lock-in.

3. **AI Eliminates The Need For Intermediaries**  
   Unlike human developers, AI doesn't require APIs to be simplified or aggregated — it just needs good documentation. This fundamental shift eliminates the need for middlemen, since AI can go direct.

4. **AI Can Generate Documentation**  
   The same technology that demands better documentation also enables its creation. AI enables automatic pre-generation of high-quality documentation from code, web resources, PDFs, production telemetry, and even through experimentation. This will create a virtuous cycle of improvement.
   
5. **An Open Knowledge Layer Is Necessary**  
   This virtuous cycle will be maximised by a collective open-source movement to establish a comprehensive "knowledge layer" for agents: a communal repository of detailed, AI-optimized information about every public API in the world.

6. **Standards Prevent Fragmentation**  
   To avoid fragmentation and proprietary lock-in, we must build upon established, open standards. The [OpenAPI Specification](https://www.openapis.org/), owned by the Linux Foundation, already provides a robust foundation with its vibrant ecosystem of tools and services.

7. **Building on OpenAPI**  
   The OpenAPI Initiative's [Arazzo](https://www.openapis.org/arazzo) specification defines composable complex workflows built from OpenAPI operations, providing a timely declarative format needed for representing complex agentic tool knowledge. We will support these standards, and propose additional extensions as necessary to make them even more valuable to agents.

8. **MCP and OpenAPI Are Complementary**  
   The future of AI needs both [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/agents-and-tools/mcp) and OpenAPI standards working in tandem. While OpenAPI and Arazzo provide the standard declarative format for representing agentic tool knowledge, MCP offers an ergonomic format for agents to access this knowledge, creating a complete ecosystem for AI interaction with APIs.

9. **Open Standards Ensure Interoperability**  
   By embracing open standards like OpenAPI and Arazzo, we ensure AI agents can reliably discover, understand, and interact with APIs regardless of which model or platform they use, guaranteeing portability and longevity independent of any single company.

10. **Community Collaboration Accelerates Progress**  
    This knowledge layer must be community-driven, welcoming contributions and feedback from both humans and AI to rapidly expand, refine and converge API knowledge. Together, we will build the most complete and AI-optimal representation of the world's APIs.

11. **Growing the OAK network**  
    The OAK initiative will benefit from many interconnected OAK repositories, which should actively facilitate automated crawling, scraping and importing. To join the OAK network, your OAK repository should contain these essential files:
      - `OAK.md` - A copy of this manifesto in your repository root, serving as your declaration of participation in the open knowledge movement
      - `LICENSE.md` - A CC0 1.0 license (or equally permissive license) ensuring your API knowledge remains freely accessible to all
      - `oak.csv` - A registry of other OAK repositories you're connected to. Anyone starting a new OAK repository should submit a PR to add their new OAK repository to the `oak.csv` in all other OAK repositories that they know about.
      - a `STRUCTURE.md` that provides clear LLM-interpretable instructions on how the repository is structured and what file naming conventions are followed.

We invite developers, organizations, and AI builders to join this mission of creating an open-source knowledge layer for all the world's APIs, built on established open standards. Together, we will provide all agents with the knowledge necessary to reliably use the world's APIs, without vendor lock-in, risk of abandonment, or tolls paid to gatekeepers.

---

*Note on this repository: This repository is an instance of an Open Agentic Knowledge (OAK) repository, putting the principles of this manifesto into practice. We encourage other organizations to create their own OAK repositories and join the movement toward creating open, standardized, and machine-readable API knowledge for the benefit of all.*

*Note: This manifesto was created without the use of AI.*
