from __future__ import annotations

import argparse

from dotenv import load_dotenv

from core.agent import AgentConfig, SimpleAgent
from core.config import Settings
from core.llm_client import LLMClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal chat agent demo.")
    parser.add_argument("--model", type=str, default=None, help="Override model name")
    parser.add_argument("--task", type=str, default=None, help="Single-shot task")
    args = parser.parse_args()

    load_dotenv()
    settings = Settings.from_env()
    client = LLMClient(
        api_key=settings.api_key,
        base_url=settings.base_url,
        default_model=settings.model,
    )
    config = AgentConfig(
        model=args.model or settings.model,
        temperature=settings.temperature,
        max_steps=settings.max_steps,
    )
    agent = SimpleAgent(llm_client=client, config=config)

    if args.task:
        print(agent.run(args.task))
        return

    print("Chat agent started. Type 'exit' to quit.")
    while True:
        user_input = input("You> ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        print(f"Agent> {agent.run(user_input)}")


if __name__ == "__main__":
    main()
