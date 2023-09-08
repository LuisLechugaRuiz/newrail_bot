DEF_GUIDED_META_EPISODE_PROMPT = """
=== TASK ===
Your task is to create an episode merging the new content with the previous content to construct a detailed summary at content field.
This content field should incorporate all crucial details including, but not limited to, relevant citations, names, links, and any other pertinent information.
The overview field should contain a concise description of the generated content.

Give priority to details that answer the answering the following question:
{question}

Be mindful of the token limit - the summary should not exceed {max_tokens} tokens.

=== PREVIOUS CONTENT ===
{previous_content}

=== NEW CONTENT ===
{new_content}

===== OUTPUT INSTRUCTIONS =====
{format_instructions}"""
