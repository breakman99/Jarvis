# Jarvis

Personal intelligent assistant — 面向生产可用的本地 Agent 框架：结构化编排、可扩展工具层、命令行交互、可插拔长期记忆与 LLM 网关。

## 能力概览

- **Agent 编排**：`AgentApp` 统一装配 `AgentCoordinator`，由 `BaseAgent(Template)` + `PlannerStrategy` + `ExecutorStrategy` 协作执行，`AgentSession` / `AgentResponse` 管理会话与输出。
- **工具框架**：`ToolRegistry` 统一注册与查询，`ToolExecutor` 统一执行与异常归一化；仅支持类 + 显式注册；内置时间、加法、HTTP GET/POST（含参数校验与基础 SSRF 防护）。
- **LLM 网关**：`LLMGateway` 统一封装模型调用，屏蔽 provider 差异。
- **长期记忆**：`MemoryService` + 可插拔存储（文件 / SQLite 等），持久化用户画像与偏好，注入 system prompt。
- **可观测性**：CLI / AgentApp / Orchestrator / ToolExecutor / LLMGateway / Memory 层打点，见 `docs/OBSERVABILITY.md`。

## 商业级特性

- **分层架构**：Interface / Application / Domain / Infrastructure 清晰分离，便于扩展与测试。
- **错误与重试**：LLM 与工具层支持可配置重试、退避与错误分类；CLI 层对异常做友好兜底。
- **可插拔记忆**：抽象存储接口，默认支持文件与 SQLite，便于替换为 Redis 等后端。
- **多 Agent 能力**：`BaseAgent` 抽象与多 Agent 协作（规划/对话/工具等），由 `AgentCoordinator` 编排。

## 目录结构

```bash
.
├── agent.py                   # 顶层启动：python agent.py（转发至 src.interface.cli）
├── src/
│   ├── interface/             # 接口层：CLI 入口（cli.py -> main()）
│   ├── application/           # 应用编排层：AgentApp、AgentAppConfig（app.py）
│   ├── domain/                # 领域层
│   │   ├── agent/             # 业务域：config / models / planning / execution / memory / runtime
│   │   └── tools/             # 工具域：spec / runtime / registry / catalog / bootstrap
│   └── infrastructure/       # 基础设施层
│       ├── config.py          # 模型、Agent、记忆、工具与 LLM 配置
│       ├── llm/               # LLM 网关：base（LLMGateway）、types（LLMReply / LLMEngineProtocol）
│       ├── common/            # 公共错误类型（JarvisError / TransientError / TimeoutError 等）
│       └── observability/     # 可观测性：metrics、audit
├── docs/
│   ├── OVERVIEW.md            # 产品与框架总览
│   ├── ARCHITECTURE.md        # 架构说明（分层与数据流）
│   ├── DESIGN_AGENT.md        # Agent 层设计
│   ├── DESIGN_MULTI_AGENT.md  # 多 Agent 编排（Coordinator / Router / Factory / ConfigurableAgent）
│   ├── DESIGN_TOOLS.md        # Tool 层设计
│   ├── DESIGN_MEMORY.md       # Memory 层设计
│   ├── DESIGN_LLMGATEWAY.md   # LLMGateway 设计
│   └── OBSERVABILITY.md       # 日志与可观测性（含 metrics / audit）
└── README.md
```

## 快速开始

### 安装依赖

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 启动命令行交互

```bash
python agent.py
```

输入 `exit` / `quit` / `q` 退出。

### 配置与密钥

- API Key 等敏感配置应通过环境变量或本地配置文件提供，不要提交到版本库。
- 长期记忆目录（如 `.jarvis/`）建议加入 `.gitignore`，仅本地使用。

## 开发者示例

```python
from src.application.app import AgentApp, AgentAppConfig

app = AgentApp(
    AgentAppConfig(
        provider="deepseek",
        enable_planning=True,
        max_iterations=6,
    )
)

print(app.chat("我叫Hanxu，以后请用中文回答。"))
print(app.chat("现在几点？再帮我算一下 12.3 + 45.6"))

envelope = app.chat_structured("请帮我算 1+2，并告诉我是否调用了工具")
print(envelope.to_dict())
```

### 结构化输出

- `app.chat(user_input)`：兼容旧接口，返回 `str`。
- `app.chat_structured(user_input)`：返回 `ChatEnvelope`，包含：
  - `version`
  - `answer`
  - `steps`
  - `reason`
  - `tool_traces`
  - `tool_errors`
  - `request_id` / `trace_id` / `session_id`

### HTTP 工具安全配置

- `JARVIS_HTTP_ALLOW_HOSTS`：可选，逗号分隔主机白名单（支持 `*.example.com`）。
- `JARVIS_HTTP_DENY_HOSTS`：可选，逗号分隔主机黑名单。
- 即使未配置白黑名单，HTTP 工具默认仍会拦截 `localhost`、内网 IP、链路本地地址等高风险目标。

## 工具开发

仅支持**类实现**：继承 `BaseTool`，在子类中定义 `ToolSpec` 并实现 `execute()`，再 `registry.register(YourTool())`。

```python
from src.domain.tools import create_tooling
from src.domain.tools.spec import BaseTool, ToolResult, ToolSpec

registry, executor = create_tooling(register_defaults=False)

class AddNumbersTool(BaseTool):
    def __init__(self):
        super().__init__(
            ToolSpec(
                name="add_numbers",
                description="两个数求和",
                parameters={
                    "type": "object",
                    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                    "required": ["a", "b"],
                },
                idempotent=True,
            )
        )

    def execute(self, args, context=None):
        _ = context
        return ToolResult(ok=True, content=str(float(args["a"]) + float(args["b"])))

registry.register(AddNumbersTool())
```

## 文档索引

- 总览与数据流：`docs/OVERVIEW.md`
- 分层与扩展点：`docs/ARCHITECTURE.md`
- 各层设计：`docs/DESIGN_AGENT.md`、`docs/DESIGN_MULTI_AGENT.md`、`docs/DESIGN_TOOLS.md`、`docs/DESIGN_MEMORY.md`、`docs/DESIGN_LLMGATEWAY.md`
- 日志与可观测性（含 metrics / audit）：`docs/OBSERVABILITY.md`

## License

MIT
