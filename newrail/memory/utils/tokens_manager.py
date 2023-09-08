from newrail.config.config import Config


class TokensManager:
    def __init__(self):
        self.max_tokens = 0

    @classmethod
    def calculate_max_tokens(cls, model: str, tokens_percentage: float) -> int:
        """Calculate the max tokens allowed"""

        if model == Config().fast_llm_model:
            return round(tokens_percentage * Config().fast_token_limit)
        else:
            return round(tokens_percentage * Config().smart_token_limit)
