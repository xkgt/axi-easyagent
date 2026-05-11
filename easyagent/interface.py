class IContext:
    def add_message(self, message: dict):
        ...

    def get_messages(self) -> list[dict]:
        ...

    def get_new_messages(self) -> list[dict]:
        ...


class IMemory:
    def build_context(self, query: str, system: str) -> IContext:
        """根据query和system构建Context，会包含需要的记忆"""
        ...

    def store(self, context: IContext):
        """提炼Context中的内容，保存进记忆中"""
        ...

    def save(self, file: str):
        ...

    @classmethod
    def load(cls, file: str):
        ...