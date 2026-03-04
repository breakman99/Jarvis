import logging

from .agent import AgentApp, AgentAppConfig

# 统一日志格式与级别，便于观测与后续接入结构化日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    app = AgentApp(config=AgentAppConfig())

    print("🚀 Jarvis Agent 已启动，进入交互模式。")
    print("提示：输入内容后回车与 Agent 对话，输入 exit/quit/q 退出。\n")

    while True:
        try:
            user_input = input("🧑 用户> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit", "q"}:
            print("👋 再见！")
            break

        input_summary = user_input[:80] + "..." if len(user_input) > 80 else user_input
        logger.info("session=cli user_input_len=%s input_summary=%s", len(user_input), input_summary)
        result = app.chat(user_input)
        reply_summary = (result[:80] + "...") if len(result) > 80 else result
        logger.info("session=cli reply_len=%s reply_summary=%s", len(result), reply_summary)
        print(f"🤖 Agent> {result}\n")


if __name__ == "__main__":
    main()

