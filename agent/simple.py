import json

from engine import AgentEngine
from tools import AVAILABLE_FUNCTIONS, TOOLS_SCHEMA


class SimpleAgent:
    def __init__(self, engine: AgentEngine):
        self.engine = engine
        self.messages = [
            {"role": "system", "content": "你是一个严谨的助手。请善用工具回答问题。"}
        ]

    def handle_tool_calls(self, tool_calls):
        """专门处理工具调用的逻辑"""
        for tool_call in tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)

            print(f"🛠️  执行工具: {func_name} | 参数: {func_args}")

            # 动态调用函数并处理参数
            if func_name in AVAILABLE_FUNCTIONS:
                result = AVAILABLE_FUNCTIONS[func_name](**func_args)
            else:
                result = "错误：工具不存在"

            # 将结果加入消息历史
            self.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": result,
                }
            )

    def run(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        # 最大循环次数，防止死循环
        max_iterations = 5
        for _ in range(max_iterations):
            # 1. 询问模型
            response = self.engine.chat(self.messages, tools=TOOLS_SCHEMA)
            resp_msg = response.choices[0].message

            # 如果模型直接给出了文字回答，且没有工具调用，就结束循环
            if not resp_msg.tool_calls:
                return resp_msg.content

            # 2. 如果有工具请求，处理它们
            # 必须先存入模型产生的这个 tool_calls 消息，保持上下文一致
            self.messages.append(resp_msg)
            self.handle_tool_calls(resp_msg.tool_calls)

            # 继续下一次循环，把执行结果喂给模型，看它还需要做什么
            print("🔄 Agent 正在思考下一步...")

        return "达到最大任务循环次数, Agent 未能完成任务。"

