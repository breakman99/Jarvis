from agent import SimpleAgent
from engine import AgentEngine


def main():
    # 初始化
    engine = AgentEngine(provider="deepseek")
    agent = SimpleAgent(engine)

    # 测试带有计算和时间的问题
    prompt = "你好，请问现在几点了？顺便帮我算一下 123.45 加 678.9 等于多少。然后向我问好"
    print(f"🚀 用户: {prompt}\n")

    result = agent.run(prompt)
    print(f"\n🤖 Agent: {result}")


if __name__ == "__main__":
    main()

