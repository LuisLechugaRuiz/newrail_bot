import abc
import os

import yaml
import openai
from dotenv import load_dotenv

from newrail.utils.storage import get_permanent_storage_path

# Load environment variables from .env file
load_dotenv()


class Singleton(abc.ABCMeta, type):
    """
    Singleton metaclass for ensuring only one instance of a class.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class AbstractSingleton(abc.ABC, metaclass=Singleton):
    pass


class Config(metaclass=Singleton):
    """
    Configuration class to store the state of bools for different scripts access.
    """

    def __init__(self):
        # SUPABASE
        self.supabase_url = os.getenv("SUPABASE_URL", "Please_fill_me")
        self.supabase_key = os.getenv("SUPABASE_KEY", "Please_fill_me")
        self.user_id = os.getenv(
            "USER_ID", "ea59a018-2cd1-4faf-a0c6-f54ca092b7a1"
        )  # TODO: REMOVE THIS, save only at dev container.
        # HOST
        self.host_url = os.getenv("HOST_URL", "http://localhost:8000")
        self.host_port = os.getenv("HOST_PORT", 8000)
        # WEB
        self.web_url = os.getenv("WEB_URL", "http://localhost:8000")
        self.web_port = os.getenv("WEB_PORT", 8000)
        # ORGANIZATION
        self.organization_id = os.getenv(
            "ORGANIZATION_ID", "7775ba9a-1b78-4011-bf98-eac65efed99e"
        )
        self.team_id = os.getenv("TEAM_ID", "2a560de3-d5c8-4913-8426-28b8b9579d0c")
        self.permanent_storage = get_permanent_storage_path()
        self.organization_data = ""
        self.organizations_folder = os.path.join(
            self.permanent_storage, "organizations"
        )
        self.max_concurrent_agents = int(
            os.getenv("MAX_CONCURRENT_AGENTS", "8")
        )  # Maximum number of agents that can be created in an organization, we can do something more complex based on priorities.
        # CONFIG
        self.continuous_mode = os.getenv("CONTINUOUS", "False") == "True"
        self.speak_mode = os.getenv("SPEAK_MODE", "False") == "True"
        self.debug_mode = os.getenv("DEBUG_MODE", "False") == "True"
        self.fast_llm_model = os.getenv("FAST_LLM_MODEL", "gpt-3.5-turbo")
        self.fast_token_limit = int(os.getenv("FAST_TOKEN_LIMIT", 4000))
        self.smart_llm_model = os.getenv(
            "SMART_LLM_MODEL", "gpt-3.5-turbo"
        )  # TODO: Switch to GPT-4 when we have the key for newrail
        # self.smart_llm_model = os.getenv("SMART_LLM_MODEL", "gpt-4")
        # self.smart_token_limit = int(os.getenv("SMART_TOKEN_LIMIT", 4000))
        self.smart_token_limit = int(os.getenv("SMART_TOKEN_LIMIT", 8000))

        # TODO: REFACTOR THIS:
        self.memory_step_episodes_tokens_percentage = float(
            os.getenv("STEP_EPISODES_TOKENS_PERCENTAGE", 0.2)
        )
        self.memory_goal_episodes_tokens_percentage = float(
            os.getenv("GOAL_EPISODES_TOKENS_PERCENTAGE", 0.2)
        )
        self.memory_operations_tokens_percentage = float(
            os.getenv("OPERATION_TOKENS_PERCENTAGE", 0.2)
        )

        self.browse_spacy_language_model = os.getenv(
            "BROWSE_SPACY_LANGUAGE_MODEL", "en_core_web_sm"
        )
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")

        # TODO: GET ONE FOR THE COMPANY
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.custom_search_engine_id = os.getenv("CUSTOM_SEARCH_ENGINE_ID")

        self.image_provider = os.getenv("IMAGE_PROVIDER")
        self.huggingface_api_token = os.getenv("HUGGINGFACE_API_TOKEN")

        self.huggingface_api_token = os.getenv("HUGGINGFACE_API_TOKEN")

        # User agent headers to use when browsing web
        # Some websites might just completely deny request with an error code if no user agent was found.
        self.user_agent_header = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36"
        }
        self.memory_index = os.getenv("MEMORY_INDEX", "newrail")
        self.long_term_memory_backend = os.getenv(
            "LONG_TERM_MEMORY_BACKEND", "weaviate"
        )

        # MEMORY MANAGEMENT

        self.episodes_overlap_tokens = int(os.getenv("EPISODES_OVERLAP_TOKENS", 100))

        self.step_episodes_max_tokens = int(os.getenv("STEP_EPISODES_MAX_TOKENS", 400))
        self.goal_episodes_max_tokens = int(os.getenv("GOAL_EPISODES_MAX_TOKENS", 200))
        self.operations_max_tokens = int(os.getenv("OPERATIONS_MAX_TOKENS", 600))
        # TODO: Deprecate this as we are not using thought buffer anymore
        self.thoughts_max_tokens = int(os.getenv("THOUGHTS_MAX_TOKENS", 700))
        self.thoughts_min_tokens = int(os.getenv("THOUGHTS_MIN_TOKENS", 300))
        self.temperature = float(os.getenv("TEMPERATURE", "0.0"))
        # Play with this values to adjust the context length
        self.context_queries = int(os.getenv("CONTEXT_QUERIES", "3"))
        self.context_relevant_information_tokens = int(
            os.getenv("CONTEXT_RELEVANT_INFORMATION_TOKENS", "500")
        )
        # Weaviate
        self.weaviate_url = os.getenv("WEAVIATE_URL", "http://weaviate")
        self.local_weaviate_url = os.getenv(
            "LOCAL_WEAVIATE_URL", "http://weaviate"
        )  # TODO: Remove after moving to cloud
        self.weaviate_port = os.getenv("WEAVIATE_PORT", "8080")
        self.weaviate_key = os.getenv("WEAVIATE_KEY")
        # Not tested yet, please use with caution
        self.autonomous_mode = os.getenv("AUTONOMOUS_MODE", "False") == "True"
        # Initialize the OpenAI API client
        openai.api_key = self.openai_api_key
        # Network user - org
        self.user_network_port = int(os.getenv("USER_NETWORK_PORT", "8887"))
        self.org_network_port = int(os.getenv("ORG_NETWORK_PORT", "8888"))
        self.director_personal_port = int(os.getenv("DIRECTOR_PERSONAL_PORT", "8889"))
        self.headless_web_browser = os.getenv("HEADLESS_WEB_BROWSER", "True") == "True"
        self.restrict_to_workspace = (
            os.getenv("RESTRICT_TO_WORKSPACE", "False") == "True"
        )
        self.image_provider = os.getenv("IMAGE_PROVIDER")
        self.image_size = int(os.getenv("IMAGE_SIZE", 256))
        self.huggingface_api_token = os.getenv("HUGGINGFACE_API_TOKEN")
        self.huggingface_image_model = os.getenv(
            "HUGGINGFACE_IMAGE_MODEL", "CompVis/stable-diffusion-v1-4"
        )
        self.huggingface_audio_to_text_model = os.getenv(
            "HUGGINGFACE_AUDIO_TO_TEXT_MODEL"
        )
        # Goal info # TODO: Adapt this when budget is added to constrain the number of iterations of the agent for each goal.
        self.max_goal_iterations = int(os.getenv("MAX_GOAL_ITERATIONS", "10"))
        # Architecture and goals
        self.architecture_filename = os.getenv(
            "ARCHITECTURE_FILENAME", "documentation_research_code.yaml"
        )
        self.goals_filename = os.getenv("GOALS_FILENAME", "image_to_text.yaml")
        # NOT VERIFIED / IMPLEMENTED YET - REQUIRES AUTONOMOUS CREATION OF AGENTS.
        self.start_from_scratch = os.getenv("START_FROM_SCRATCH", "False") == "True"

    def get_azure_deployment_id_for_model(self, model: str) -> str:
        """
        Returns the relevant deployment id for the model specified.
        Parameters:
            model(str): The model to map to the deployment id.
        Returns:
            The matching deployment id if found, otherwise an empty string.
        """
        if model == self.fast_llm_model:
            return self.azure_model_to_deployment_id_map[
                "fast_llm_model_deployment_id"
            ]  # type: ignore
        elif model == self.smart_llm_model:
            return self.azure_model_to_deployment_id_map[
                "smart_llm_model_deployment_id"
            ]  # type: ignore
        elif model == "text-embedding-ada-002":
            return self.azure_model_to_deployment_id_map[
                "embedding_model_deployment_id"
            ]  # type: ignore
        else:
            return ""

    AZURE_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "azure.yaml")

    def load_azure_config(self, config_file: str = AZURE_CONFIG_FILE) -> None:
        """
        Loads the configuration parameters for Azure hosting from the specified file
          path as a yaml file.
        Parameters:
            config_file(str): The path to the config yaml file. DEFAULT: "../azure.yaml"
        Returns:
            None
        """
        try:
            with open(config_file) as file:
                config_params = yaml.load(file, Loader=yaml.FullLoader)
        except FileNotFoundError:
            config_params = {}
        self.openai_api_type = config_params.get("azure_api_type") or "azure"
        self.openai_api_base = config_params.get("azure_api_base") or ""
        self.openai_api_version = (
            config_params.get("azure_api_version") or "2023-03-15-preview"
        )
        self.azure_model_to_deployment_id_map = config_params.get("azure_model_map", [])
