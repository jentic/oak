# Jentic Developer Workflow Sequence Diagram - (Mostly) Static Agentic Development Process

The following sequence diagram illustrates the workflow of a developer working with the Jentic architecture to create an agent that uses external APIs:

```mermaid
sequenceDiagram
    actor Developer
    participant CodingAgent as Coding Agent
    participant LLM as Coding Agent LLM
    participant ARK² as Jentic ARK² Plugin
    participant DirectoryAPI as Jentic Directory API
    participant Repo as Knowledge Repository
    participant NewAgent as Resulting Agent
    participant ResultingLLM as Resulting LLM
    participant API as External APIs

    Developer->>CodingAgent: 1. Initiates agent development process
    CodingAgent->>LLM: 2. Describes agent's functionality and external API needs
    
    Note over LLM: 3. Identifies need for API capabilities
    LLM->>CodingAgent: 4. Requests description of relevant API capabilities via tool use
    CodingAgent->>ARK²: 5. Invokes ARK² plugin API search
    ARK²->>DirectoryAPI: 6. Queries for relevant API specs
    DirectoryAPI->>Repo: 7. Performs vector search for matching API specifications
    Repo-->>DirectoryAPI: 8. Returns matching APIs and their endpoints
    DirectoryAPI-->>ARK²: 9. Delivers API specifications
    ARK²-->>CodingAgent: 10. Returns API capabilities information
    CodingAgent-->>LLM: 11. Provides API capabilities data
    
    Note over LLM: 12. Analyzes API capabilities
    LLM->>CodingAgent: 13. Formats API integration suggestions
    CodingAgent->>Developer: 14. Presents API integration options
    
    Developer->>CodingAgent: 15. Requests refinement of API selection
    Note over CodingAgent,ARK²: 16. Iterative refinement of API selection
    CodingAgent->>ARK²: 17. Requests detailed specifications for selected APIs
    ARK²-->>CodingAgent: 18. Returns detailed API specifications
    CodingAgent->>Developer: 19. Shows detailed API capabilities
    Developer->>CodingAgent: 20. Finalizes API selection and defines agent behavior
    
    CodingAgent->>LLM: 21. Forwards selections and requirements
    
    Note over LLM: 22. Decides on runtime requirements
    LLM->>CodingAgent: 23. Requests tool use (Runtime Generation)
    CodingAgent->>ARK²: 24. Requests runtime generation
    ARK²->>NewAgent: 25. Generates runtime environment for agent
    ARK²->>NewAgent: 26. Creates prompt library with API knowledge
    
    Note over CodingAgent,ARK²: 27. Iterative refinement of runtime and prompts
    
    Note over ARK²,NewAgent: 28. Final runtime and prompt configurations applied
    
    Note over NewAgent: 29. Runtime execution
    NewAgent->>ResultingLLM: 30. Initializes with API-aware prompt library
    NewAgent->>DirectoryAPI: 31. Requests dynamic API configuration (if needed)
    DirectoryAPI-->>NewAgent: 32. Provides updated API configuration
    
    Note over ResultingLLM: 33. Makes API use decisions
    ResultingLLM->>NewAgent: 34. Requests API call
    NewAgent->>API: 35. Executes API calls through proxy or direct access
    API-->>NewAgent: 36. Returns API responses
    NewAgent-->>ResultingLLM: 37. Formats API response
    ResultingLLM->>NewAgent: 38. Integrates API data into response
    NewAgent-->>Developer: 39. Returns results to agent consumer
    
    Note over Developer,NewAgent: 40. Iterative improvement of agent and API interactions based on usage and feedback
    
    note over Developer,API: The workflow shows the explicit role of LLMs in tool use decisions and API interactions
