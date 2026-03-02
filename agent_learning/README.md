# Agent Learning (Python)

一个用于学习 Agent 的最小 Python 框架，支持：
- LLM 调用（OpenAI 兼容接口）
- Tool 注册与调用
- 多步 Agent Loop（含 `max_steps`）
- 会话记忆（短期）
- Trace 日志（便于调试）
- 模型可切换（配置或 CLI）

## 1. 安装

```bash
cd agent_learning
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：
- `OPENAI_API_KEY`: 你的密钥
- `OPENAI_BASE_URL`: 兼容接口地址
- `OPENAI_MODEL`: 默认模型
- `AGENT_TEMPERATURE`: 温度
- `AGENT_MAX_STEPS`: 最大步数

## 3. 运行示例

### 纯对话 Agent
```bash
python -m examples.chat_agent --task "解释一下什么是Agent"
```

### Tool Agent
```bash
python -m examples.tool_agent --task "告诉我现在时间并计算 9*(7+2)"
```

### Planner Agent
```bash
python -m examples.planner_agent --task "给我做一个今晚学习计划并附带两道口算"
```

你也可以用 `--model` 覆盖默认模型：
```bash
python -m examples.tool_agent --model gpt-4o-mini
```

## 4. 跑测试

```bash
pytest
```

## 5. 学习建议（两周）

1. Day 1-2: 读 `core/llm_client.py`，跑通 chat agent  
2. Day 3-4: 读 `core/tools.py`，新增一个工具并测试  
3. Day 5-6: 读 `core/agent.py`，理解多步循环  
4. Day 7-8: 调整 `memory.py` 的保留策略  
5. Day 9-10: 打开 `outputs/*trace.json` 看每步轨迹  
6. Day 11-12: 比较不同 `model` 的行为差异  
7. Day 13-14: 改造 planner agent 做你的真实任务
