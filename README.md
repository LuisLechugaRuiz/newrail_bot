# New Rail

Our journey towards Artificial General Intelligence (AGI) is centered around crafting the optimal autonomous system using a multi-agent framework built upon Large Language Models (LLMs). LLMs have demonstrated remarkable aptitude in understanding natural language and constructing world models. In this project, we utilize these LLMs as controllers, comparable to the function of the prefrontal cortex in the human brain, to activate appropriate modules based on varying inputs.

## Understanding an Agent

An agent, within this context, is an entity characterized by:

### Description:

The description of an agent serves as its unique personality identifier. We employ the description as a classification tool to define the agent, with primary elements comprising its name, mission, and team.

### Capabilities:

Although capabilities could be incorporated in the previous description, they are presented as a distinct module due to their significance within our system. Capabilities denote the actions the agents can perform to interact with the real world. Initially referred to as plugins, we renamed them to "capabilities" as this term offers a broader connotation and is not confined to the concept of a plugin. Currently, capabilities operate locally, but we anticipate incorporating diverse means to run capabilities, including access to external APIs.

### Memory:

Memory is bifurcated into two segments:

#### Short-term memory:

Short-term memory stores the agent's most recent thought, a historical record of past actions, and some information such as recommendations from prior stages. This continuity of short-term memory fosters a coherent history, enabling the agent to execute sequential actions without losing track of preceding steps. Our short-term memory is referred to as "Episodic Memory."

In line with TaskManager, the agent is instructed to formulate a Goal, which is subsequently divided into Steps. Each step encapsulates the operations (Action - Feedback). Upon the completion of a step, it is condensed into a summary termed an "Episode." This episode serves as a descriptor of the current step, allowing it to guide the agent through subsequent logical steps towards achieving the goal. Once the goal is met, it is also converted into an Episode, thereby creating a chronicle of all the goals fulfilled by the agent.

Our aim is to establish hierarchical episodes stored in long-term memory.

#### Long-term memory:

Long-term memory serves as a repository for the agent's previous episodes and more pertinent information to be incorporated as our system evolves. It functions as a semantic database employing vector embeddings to store insights and past experiences, enabling the retrieval of relevant data when applicable to the current context. This segment facilitates the learning process. Although we have innovative plans for this module, the next steps involve determining its integration with our existing platform.

## Task Manager

Task Manager is the core module overseeing task progression. It houses the primary logic that the agent implements at each stage. This process entails:

-   Every stage possesses a prompt template comprising "references" to external sources, and each stage anticipates a particular output.
-   The prompt template is populated with data retrieved from different modules (primarily memory modules), resulting in a dynamic prompt.
-   This prompt is transmitted to the LLM, and the response is parsed according to the expected output.
-   The resulting output is segmented into information pieces, which are used to update the information stored in other modules (such as memory) for use in future stages.

This process can be distilled into a straightforward algorithm:

-   Stage -> Template Prompt.
-   Template Prompt -> Retrieve Info -> Dynamic prompt.
-   Dynamic Prompt -> LLM -> Output.
-   Output -> Update Info.

Our goal is to provide a user-friendly GUI wrapper to allow for easy modifications of the Template prompt (with references) and the stages (using a state machine). This feature would facilitate easy updates to the agent's logic without necessitating code refactoring, paving the way for user control over the agent's behavior, and marking a significant stride towards natural language programming!
