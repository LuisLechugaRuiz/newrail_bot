from newrail.organization.utils.mockeds.mocked_request_manager import (
    MockedRequestManager,
)


def main():
    while True:
        agent_name = input("Sending message to agent: ")
        message = input("Message: ")
        mocked_request_manager = MockedRequestManager(agent_name="mocked_agent")
        result = mocked_request_manager.send_message_to_agent(
            agent_name=agent_name, message=message
        )
        print(result)


if "__main__" == __name__:
    main()
