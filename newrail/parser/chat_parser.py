from typing import Generic, List, TypeVar, Type, Union, cast

from newrail.utils.chat.chat import Chat
from newrail.organization.utils.logger.agent_logger import AgentLogger
from newrail.organization.utils.logger.org_logger import OrgLogger
from newrail.parser.pydantic_parser import (
    get_format_instructions,
    parse,
    ParseResult,
)
from newrail.parser.loggable_base_model import LoggableBaseModel
from newrail.parser.fix_format_prompt import (
    DEF_FIX_FORMAT_PROMPT,
)

T = TypeVar("T", bound=LoggableBaseModel)


class ChatParser(Generic[T], Chat):
    def __init__(self, logger: Union[AgentLogger, OrgLogger]):
        self.logger = logger

    def get_parsed_response(
        self,
        system: str,
        user: str,
        containers: List[Type[T]],
        smart_llm=False,
        retries: int = 2,
        fix_retries: int = 1,
    ) -> List[T]:
        output = []
        response = self.get_response(system=system, user=user, smart_llm=smart_llm)
        for container in containers:
            success = False
            for _ in range(retries):
                parsed_response = self.parse_response(
                    response, container, fix_retries=fix_retries
                )
                if parsed_response.result:
                    self.logger.log(message=parsed_response.result, should_print=True)
                    parsed_response = cast(container, parsed_response.result)
                    output.append(parsed_response)
                    success = True
                    break
                else:
                    self.logger.log(
                        "Couldn't parse/fix response, getting new response.",
                        should_print=True,
                    )
                    response = self.get_response(
                        system=system, user=user, smart_llm=smart_llm
                    )
            if not success:
                self.logger.log(
                    message=f"Failed to get a valid response after {retries} retries and {fix_retries} fix retries. Returning None...",
                    log_level="critical",
                    should_print=True,
                )
                output.append(None)
        return output

    def parse_response(
        self, text: str, pydantic_object: Type[T], fix_retries=3
    ) -> ParseResult[T]:
        parsed_response = parse(text, pydantic_object)
        if parsed_response.result:
            return parsed_response
        else:
            error_msg = parsed_response.error_message
            self.logger.log(
                f"Failing parsing object: {pydantic_object.__name__}, trying to fix autonomously...",
                should_print=True,
            )
            # TODO: REMOVE ME LATER
            self.logger.log(
                "Response from the LLM: " + text + "error:" + error_msg,
                should_print=True,
            )
        while fix_retries > 0:
            response_fix = self.try_to_fix_format(text, error_msg, pydantic_object)
            if response_fix.result:
                self.logger.log("Response format was fixed.", should_print=True)
                return response_fix
            fix_retries -= 1
            self.logger.log(
                f"Couldn't fix format... remaining attempts to fix: {fix_retries}",
                should_print=True,
            )
        return ParseResult(error_message=error_msg)

    def try_to_fix_format(self, response, error_msg, pydantic_object):
        format_instructions = get_format_instructions([pydantic_object])
        fix_prompt = DEF_FIX_FORMAT_PROMPT.format(
            response=response,
            error_msg=error_msg,
            format_instructions=format_instructions,
        )
        fix_response = self.get_response(
            system=fix_prompt,
            user="Please provide the correct format!",
            smart_llm=False,
        )
        result = parse(fix_response, pydantic_object)
        return result
