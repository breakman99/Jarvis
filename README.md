# Jarvis

personal intelligent assistant  
一个面向真实工程演进的 Python Agent 项目：支持结构化 Agent 编排、可扩展工具层、命令行多轮交互，以及文件型长期记忆。

## 当前能力（V2）

- **结构化 Agent 架构**
  - `AgentApp` 负责应用装配
  - `AgentOrchestrator` 负责主循环编排
  - `AgentSession` / `Planner` / `AgentResponse` 分别管理会话、规划提示与输出
- **可扩展 Tool 框架（重构后）**
  - `ToolRegistry`：统一注册与查询工具
  - `ToolExecutor`：统一执行、异常归一化
  - 同时支持：
    - 装饰器注册（`@tool(...)`）
    - 显式注册（`register_function(...)`）
- **LLM 网关抽象**
  - `LLMGateway`（兼容 `AgentEngine` 旧命名）统一封装模型调用
- **长期记忆（文件版）**
  - `MemoryService` + `FileMemoryStore`
  - 可持久化用户名字、语言偏好等信息（重启后仍保留）

## 目录结构

```bash
.
├── agent.py                   # 顶层启动脚本：python agent.py
├── src/
│   ├── main.py                # CLI 入口（REPL）
│   ├── config.py              # 模型配置 + Agent 运行配置
│   ├── engine/
│   │   └── base.py            # LLMGateway / AgentEngine
│   ├── tools/
│   │   ├── base.py            # ToolSpec / BaseTool / FunctionTool
│   │   ├── registry.py        # ToolRegistry（注册中心）
│   │   ├── executor.py        # ToolExecutor（执行与错误处理）
│   │   ├── context.py         # ToolContext
│   │   ├── bootstrap.py       # 全局 registry/executor 与 decorator 入口
│   │   └── builtin/
│   │       └── basic.py       # 内置工具示例（时间、加法）
│   └── agent/
│       ├── app.py             # AgentApp / AgentAppConfig
│       ├── orchestrator.py    # Agent 主循环
│       ├── session.py         # 会话消息管理
│       ├── planner.py         # 规划层（可开关）
│       ├── memory.py          # 长期记忆抽象与文件实现
│       ├── response.py        # 响应模型
│       └── simple.py          # 兼容层（旧接口转发）
├── docs/
│   ├── ARCHITECTURE.md
│   └── TEACHING_PLAN.md
└── README.md
```

## 快速开始

### 1) 安装依赖

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2) 启动命令行交互

```bash
python agent.py
```

输入 `exit` / `quit` / `q` 可退出。

## 开发者示例

```python
from src.agent import AgentApp, AgentAppConfig

app = AgentApp(
    AgentAppConfig(
        provider="deepseek",
        enable_planner=True,
        max_iterations=6,
    )
)

print(app.chat("我叫Hanxu，以后请用中文回答。"))
print(app.chat("现在几点？再帮我算一下 12.3 + 45.6"))
```

## 工具开发方式（V2）

### 方式 A：装饰器注册

```python
from src.tools.bootstrap import tool

@tool(
    description="返回当前时间",
    parameters={"type": "object", "properties": {}},
)
def get_now():
    ...
```

### 方式 B：显式注册

```python
from src.tools.bootstrap import tool_registry

tool_registry.register_function(
    name="add_numbers",
    description="两个数求和",
    parameters={...},
    func=add_numbers,
)
```

## 说明

- 架构细节见 `docs/ARCHITECTURE.md`
- 学习路线见 `docs/TEACHING_PLAN.md`

## License

MIT
