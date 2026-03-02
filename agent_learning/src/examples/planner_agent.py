from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from core.agent import AgentConfig, SimpleAgent
from core.config import Settings
from core.llm_client import LLMClient
from core.tools import build_default_tools
from core.trace import TraceLogger


PLANNER_PROMPT = (
    "You are a planning agent. For each user task, decompose it into concise steps, "
    "use tools when helpful, and end with a clear final summary."
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple planner agent demo.")
    parser.add_argument("--model", type=str, default=None, help="Override model")
    parser.add_argument(
        "--task",
        type=str,
        default="帮我做一个今天晚上的学习计划，包含当前时间感知和两道口算练习。",
        help="Task for planner agent",
    )
    args = parser.parse_args()

    load_dotenv()
    settings = Settings.from_env()
    trace = TraceLogger()
    agent = SimpleAgent(
        llm_client=LLMClient(
            api_key=settings.api_key,
            base_url=settings.base_url,
            default_model=settings.model,
        ),
        tools=build_default_tools(),
        trace=trace,
        config=AgentConfig(
            system_prompt=PLANNER_PROMPT,
            model=args.model or settings.model,
            temperature=settings.temperature,
            max_steps=settings.max_steps,
        ),
    )

    answer = agent.run(args.task)
    print(answer)

    trace_path = Path("outputs/planner_agent_trace.json")
    trace.dump_json(trace_path)
    print(f"\nTrace saved to: {trace_path}")


if __name__ == "__main__":
    main()
