# Enhanced Conversation Compaction Prompt

## Purpose
You are to create a comprehensive and detailed overview of the conversation history (all assistant and user dialog). The output should contain **one user entry** and **one assistant entry**. The assistant entry must thoroughly summarize the entire conversation in a detailed way that preserves nearly all important context, enabling the assistant to continue the conversation with minimal loss of information. Detail preservation is more important than brevity.

## Instructions
- Read the entire conversation history (alternating user and assistant messages).
- Retain all meaningful context, requests, clarifications, decisions, examples, and specifics from the conversation.
- Discard only clearly redundant information or off-topic tangents that don't contribute to the main threads.
- The **user** entry should provide a comprehensive overview of all the user's concerns, requests, questions, clarifications, and comments, preserving specific details, parameters, and requirements.
- The **assistant** entry should be an extensive and detailed overview of all the assistant's responses and actions, including all key information, explanations, clarifications, suggestions, or solutions provided.
- Include specific examples, code snippets, technical terms, numerical values, and named entities that were discussed.
- Preserve the chronological development of ideas and how the conversation evolved over time.
- Capture any shifts in focus, refinements of requirements, or iterations of ideas.
- The output must be in **JSON** format as shown below.
- The summary should prioritize completeness and detail retention over brevity.
- There should be a note which says it is compacted.
- Do not include any extra commentary or formatting outside the JSON.
- Do not include user's request to compact the conversation in the overview of the user's dialog summary
- Do not include the assistant's response to compacting the conversation as part of the assistant's dialog summary

## Output Format
```json
{
  "user": "[Note: this is a compacted version of dialog from user] <detailed user requests, concerns, questions, clarifications, and specific requirements throughout the conversation>",
  "assistant": "[Note: This is a compacted version of dialog with the assistant] <comprehensive summary of assistant's responses, explanations, solutions, and all key context provided throughout the conversation>"
}
```

## Guidelines
- **Prioritize detail over brevity**: Ensure that nearly all important context is preserved, even at the cost of a longer summary.
- **Be specific**: Include named entities, technical terms, specific requests, and exact parameters rather than generalizing.
- **Maintain contextual richness**: Preserve the nuance and depth of the original conversation.
- **Include all decision points**: Document how options were evaluated and choices were made.
- **Preserve chronology**: Maintain the sequence of how ideas developed and evolved.
- The output must be valid JSON and must not include any extra text or formatting.
- If files have been included in the context, retain detailed information about their contents, structure, and how they were used in the conversation.
- Explicitly name specific files, classes, code segments, variables, functions, and other technical elements that were discussed.
- Include any metrics, measurements, or numerical values that were mentioned.
- Capture the user's preferences, constraints, and priorities as expressed throughout the conversation.
- Document any challenges encountered and how they were addressed.