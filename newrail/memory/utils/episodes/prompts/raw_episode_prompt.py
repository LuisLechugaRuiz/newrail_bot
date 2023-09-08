DEF_RAW_EPISODE_PROMPT = """
=== TASK ===
Your task is to create an overview that contains a concise description of the action performed and the observation obtained. Start it always with the action performed.

Be mindful of the token limit - the overview should not exceed {max_overview_tokens} tokens.

=== TASK DESCRIPTION ===
The action was performed while pursuing the task:
{task_description}

=== ACTION ===
The action executed was: {action}

Observation: {observation}

===== OUTPUT INSTRUCTIONS =====
{format_instructions}"""
