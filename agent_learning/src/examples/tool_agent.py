from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from core.agent import AgentConfig, SimpleAgent
from core.config import Settings
from core.llm_client import LLMClient
from core.tools import build_default_tools
from core.trace import TraceLogger


def main() -> None:
    parser = argparse.ArgumentParser(description="Tool-enabled agent demo.")
    parser.add_argument("--model", type=str, default=None, help="Override model")
    parser.add_argument(
        "--task",
        type=str,
        default="请告诉我现在时间，并计算 12*(8+3)，最后总结一句话。",
        help="Task for the tool agent",
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
            model=args.model or settings.model,
            temperature=settings.temperature,
            max_steps=settings.max_steps,
        ),
    )
    answer = agent.run(args.task)
    print(answer)

    trace_path = Path("outputs/tool_agent_trace.json")
    trace.dump_json(trace_path)
    print(f"\nTrace saved to: {trace_path}")


if __name__ == "__main__":
    main()
