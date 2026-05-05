import json
from typing import Any


class Memory(list[dict[str, Any]]):
    max_length = 70

    def add_user_message(self, message: str):
        self.append({"role": "user", "content": message})

    def add_assistant_message(self, message: str):
        self.append({"role": "assistant", "content": message})

    @classmethod
    def load(cls, json_file: str):
        with open(json_file, "r", encoding="utf-8") as f:
            return cls(json.load(f))

    def save(self, json_file: str):
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self, f, ensure_ascii=False, indent=4)

    def copy(self) -> "Memory":
        m = type(self)(self)
        m.max_length = self.max_length
        return m

    def need_compress(self) -> bool:
        return len(self) > self.max_length

    def compress(self):
        # 剔除前50%的记忆中的深度思考记录，工具调用记录
        for index, record in enumerate(self.copy()):
            if record['role'] == "assistant":
                record.pop("reasoning_content")
            elif record['role'] == 'tool':
                self.remove(record)
        # 删除25%的记忆
        for i in range(len(self) // 4):
            self.pop(0)
