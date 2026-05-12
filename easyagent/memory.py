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
    def __init__(self, messages: list[dict] | None = None, max_length: int = 70):
        self.messages = messages if messages is not None else []
        self.max_length = max_length

    def store_turn(self, user: str, assistant: str):
        """存储一轮对话，不会触发压缩逻辑"""
        self.messages.append({"role": "user", "content": user})
        self.messages.append({"role": "assistant", "content": assistant})

    def build_context(self, query: str, system: str | None = None) -> IContext:
        """根据query和system构建Context，会包含需要的记忆"""
        messages = [{"role": "system", "content": system}] if system is not None else []
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
        processed_messages = []
        # 1 删除前50%的工具调用和思维链    
        is_asst = True
        for index, message in enumerate(self.messages):
            if index < len(self.messages) * 0.5:
                if message["role"] == "assistant":
                    message.pop("tool_calls", None)
                    message.pop("reasoning_content", None)
                elif message["role"] == "tool":
                    continue
                processed_messages.append(message)
            else:
                # 避免残留tool消息
                if message["role"] == "tool" and is_asst:
                    continue
                is_asst = False
                processed_messages.append(message)
        # 2 删除15%的记忆
        i = 0
        while i < len(processed_messages) * 0.15:
            # messages第一条永远是user，直接跳过
            i += 1
            # 需要删除一条完整的对话轮（用户和助手的消息），也就是找到新的user消息
            while i < len(processed_messages) and processed_messages[i]["role"] != "user":
                i += 1
        self.messages = processed_messages[i:]


    def save(self, file: str):
        with open(file, "w", encoding="utf-8") as f:
            json.dump({"messages": self.messages, "max_length": self.max_length}, f, ensure_ascii=False, indent=4)

    @classmethod
    def load(cls, file: str) -> 'Memory':
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return cls(data["messages"], data["max_length"])
