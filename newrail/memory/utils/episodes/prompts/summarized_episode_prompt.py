DEF_SUMMARIZED_EPISODE_PROMPT = """
=== TASK ===
Your task is to create an episode from the action performed and the observation obtained, for this you should provide a summary and an overview of the content.
The content of the episode should incorporate all crucial details including, but not limited to, relevant citations, names, links, and any other pertinent information.
The overview field should contain a concise description of the action performed and a brief outline of the created content. Start it always with the action performed.

Be mindful of the token limit - the content should not exceed {max_content_tokens} tokens and the overview should not exceed {max_overview_tokens} tokens.

=== TASK DESCRIPTION ===
The action was performed while pursuing the task:
{task_description}

=== ACTION ===
The action executed was: {action}

Observation: {observation}

===== OUTPUT INSTRUCTIONS =====
{format_instructions}"""
