from typing import Union, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from newrail.execution.actions.plugins.plugin import Plugin


class Helper:
    def __init__(self, plugin_cls: Union[Type["Plugin"], "Plugin"]):
        self.name = plugin_cls.get_name()
        self.description = plugin_cls.get_description()
        self.plugin_cls = plugin_cls

    def get_capabilitiy_description(self, detailed: bool = False) -> str:
        desc = (
            f"Name: {self.name}" + f"\nDescription: {self.description}\n"
            if self.description
            else ""
        )

        if detailed:
            action_descriptions = "\n".join(
                f"- {action}: {self.plugin_cls.get_action_doc(action)}\n"
                for action in self.plugin_cls.get_actions()
            )
        else:
            action_descriptions = "".join(
                f"- {action}: {self.plugin_cls.get_action_description(action)}"
                for action in self.plugin_cls.get_actions()
            )
        return desc + f"Actions:\n{action_descriptions}"

    def get_action_doc(self, action: str) -> str:
        doc = self.plugin_cls.get_action_doc(action=action)
        if not doc:
            raise ValueError(f"Unknown action: {action}")
        return doc

    def get_context(self) -> str:
        context_function_name = self.plugin_cls.get_context()
        if context_function_name:
            context_function = getattr(self.plugin_cls, context_function_name)
            if context_function:
                return (lambda: context_function())()
        return ""
