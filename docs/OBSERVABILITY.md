# 可观测性：日志分层与打点

> 使用 Python 标准库 `logging`，在关键路径打点，便于调试与后续接入结构化日志或外部监控。

---

## 1. 日志配置

- **配置位置**：在 `src/main.py` 顶部通过 `logging.basicConfig` 统一配置（REPL 启动时生效）。
- **格式**：`[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s`
- **默认级别**：`INFO`；需要更细粒度时可将某 logger 设为 `DEBUG`（如 Orchestrator 的迭代详情）。

各模块使用 `logger = logging.getLogger(__name__)`，日志名与包路径一致（如 `src.agent.orchestrator`）。

---

## 2. 分层打点策略

### 2.1 CLI / AgentApp 层

| 位置 | 级别 | 关键字段 / 内容 |
|------|------|-----------------|
| `main.py` | INFO | `session=cli`、`user_input_len`、`input_summary`（截断）、`reply_len`、`reply_summary`（截断） |
| `app.py` | INFO | `chat finished`、`content_len`、`phase_log` |

不记录完整用户输入或回复，仅摘要与长度，避免敏感信息写入日志。

### 2.2 Orchestrator 层

| 位置 | 级别 | 关键字段 / 内容 |
|------|------|-----------------|
| 每轮迭代开始 | DEBUG | `iteration`、`messages_count` |
| 无 tool_calls（最终答案） | INFO | `iteration`、`decision=final_answer` |
| 有 tool_calls | INFO | `iteration`、`decision=use_tools`、`tools=[...]` |
| 正常结束 | INFO | `finished_with=success` |
| 达到迭代上限 | INFO | `finished_with=max_iterations` |

### 2.3 Tool 层（ToolExecutor）

| 位置 | 级别 | 关键字段 / 内容 |
|------|------|-----------------|
| 每次工具执行 | INFO | `tool_name`、`ok`、`args_summary`（截断） |
| 工具执行失败（ToolResult.ok=False） | ERROR | `tool_exec_failed`、`tool_name`、`error` |
| 工具不存在 | ERROR | `tool_not_found`、`tool_name` |
| 执行过程异常 | ERROR | `tool_exec_exception`、`tool_name`、`exception` |

### 2.4 LLM 网关层（LLMGateway）

| 位置 | 级别 | 关键字段 / 内容 |
|------|------|-----------------|
| 每次 chat 调用成功 | INFO | `provider`、`model`、`latency_ms`、`tools`（是否传了 tools） |
| 调用异常 | ERROR | `llm_chat_error`、`provider`、`model`、`error` |

不记录 API Key 或完整 message 内容。

### 2.5 Memory 层

| 位置 | 级别 | 关键字段 / 内容 |
|------|------|-----------------|
| 记忆被更新时 | INFO | `memory_updated`、`fields`（如 `user_name`、`preferred_language`） |

---

## 3. 使用与扩展

- **本地调试**：将 `src.agent.orchestrator` 的 level 设为 `DEBUG` 可看到每轮迭代的 message 数量。
- **结构化日志**：后续可将 `logging` 的 Formatter 替换为输出 JSON 的 handler，便于接入 ELK、Datadog 等。
- **敏感信息**：所有打点均避免打印 API Key、完整用户输入或完整回复内容。
