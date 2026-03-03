from .agent import AgentApp, AgentAppConfig


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

        result = app.chat(user_input)
        print(f"🤖 Agent> {result}\n")


if __name__ == "__main__":
    main()

