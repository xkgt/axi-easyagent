import json

from easyagent.interface import IMemory, IContext


class Context(IContext):
    def __init__(self, messages: list[dict]):
        self.messages = messages
        self.new_message_index = len(messages) - 1

    def add_message(self, message: dict):
        self.messages.append(message)

    def get_messages(self) -> list[dict]:
        return self.messages

    def get_new_messages(self) -> list[dict]:
        return self.messages[self.new_message_index:]


class Memory(IMemory):
    def __init__(self, messages: list[dict] = None, max_length: int = 70):
        self.messages = messages if messages is not None else []
        self.max_length = max_length

    def store_turn(self, user: str, assistant: str):
        """存储一轮对话"""
        self.messages.append({"role": "user", "content": user})
        self.messages.append({"role": "assistant", "content": assistant})

    def build_context(self, query: str, system: str) -> IContext:
        """根据query和system构建Context，会包含需要的记忆"""
        messages = [{"role": "system", "content": system}]
        messages.extend(self.messages)
        messages.append({"role": "user", "content": query})
        return Context(messages)

    def store(self, context: IContext):
        """对话结束时调用，提炼Context中的内容，保存进记忆中"""
        self.messages.extend(context.get_new_messages())
        if len(self.messages) > self.max_length:
            self.compress()

    def compress(self):
        """压缩记忆"""
        # 1 删除前50%的工具调用和思维链
        # 2 删除15%的记忆
        length = len(self.messages)
        for index, record in enumerate(self.messages.copy()):
            # 只有assistant会存在工具调用和思维链，删除了工具调用请求后
            # 对应的工具调用记录也需要删除
            if index < length // 2:
                continue
            if record['role'] == "assistant":
                record.pop("reasoning_content", None)
                record.pop("tool_calls", None)
            elif record['role'] == 'tool':
                self.messages.remove(record)
        # 删除15%的记忆


    def save(self, file: str):
        with open(file, "w", encoding="utf-8") as f:
            json.dump({"messages": self.messages, "max_length": self.max_length}, f, ensure_ascii=False, indent=4)

    @classmethod
    def load(cls, file: str):
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return cls(data["messages"], data["max_length"])
