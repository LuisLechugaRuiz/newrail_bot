from colorama import Fore
import time
import openai
from openai.error import APIError, RateLimitError
from typing import List, Optional

from newrail.config.config import Config
import newrail.utils.token_counter as token_counter

openai.api_key = Config().openai_api_key


class Chat(object):
    @staticmethod
    def create_chat_message(role: str, content: str) -> dict[str, str]:
        """
        Create a chat message with the given role and content.

        Args:
        role (str): The role of the message sender, e.g., "system", "user", or "assistant".
        content (str): The content of the message.

        Returns:
        dict: A dictionary containing the role and content of the message.
        """
        return {"role": role, "content": content}

    @classmethod
    def get_response(cls, system: str, user: str, smart_llm=False, token_limit=None):
        messages = [
            cls.create_chat_message("user", user),
            cls.create_chat_message("system", system),
        ]
        model = ""
        if smart_llm:
            model = Config().smart_llm_model
            if not token_limit:
                token_limit = Config().smart_token_limit
        else:
            model = Config().fast_llm_model
            if not token_limit:
                token_limit = Config().fast_token_limit
        response = cls.create_chat_completion(messages, model, max_tokens=token_limit)
        return response

    @staticmethod
    def create_chat_completion(
        messages: List[dict[str, str]],
        model: str,
        temperature: float = Config().temperature,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Create a chat completion using the OpenAI API"""
        response = None
        num_retries = 5
        if Config().debug_mode:
            print(
                f"{Fore.GREEN}Creating chat completion with model {model},"
                + f"temperature {temperature}, max_tokens {max_tokens}"
                + Fore.RESET
            )
        message_tokens = token_counter.count_message_tokens(messages)
        if max_tokens and message_tokens < max_tokens:
            max_tokens = max_tokens - message_tokens
        for attempt in range(num_retries):
            try:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                break
            except RateLimitError:
                print(
                    Fore.RED + "Error: ",
                    "API Rate Limit Reached. Waiting 20 seconds..." + Fore.RESET,
                )
                time.sleep(20)
            except APIError as e:
                if e.http_status == 502:
                    print(
                        Fore.RED + "Error: ",
                        "API Bad gateway. Waiting 20 seconds..." + Fore.RESET,
                    )
                    time.sleep(20)
                else:
                    raise
                if attempt == num_retries - 1:
                    raise

        if response is None:
            raise RuntimeError("Failed to get response after 5 retries")

        return response.choices[0].message["content"]
