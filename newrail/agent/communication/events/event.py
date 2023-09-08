# TODO: This class can be improved when we get more complex events as the ones comming from plugins!
class Event:
    def __init__(self, type: str, content: str):
        self.type = type
        self.content = content

    def to_dict(self):
        return {
            "type": self.type,
            "content": self.content,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(type=data["type"], content=data["content"])

    def __str__(self):
        return f"Event: {self.type}: {self.content}"

    def __repr__(self):
        return self.__str__()
