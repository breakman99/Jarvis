# LLMGateway 层设计

> 与底层 LLM 服务通信的唯一出入口；对上层提供统一的 `chat(messages, tools, context)` 接口并返回 `LLMReply` DTO；集中处理重试、超时与错误分类。

---

## 1. 设计目标与约束

- 将“调用具体 LLM 提供商”与 Agent 逻辑解耦；上层不关心 base_url、api_key、model 名。
- 单一入口：所有 LLM 调用经 LLMGateway，便于横切能力（重试、超时、日志、成本）集中实现。
- 错误分类：可重试错误（网络、超时、5xx）与不可重试错误（4xx、认证、参数）区分处理；重试采用指数退避与抖动。
- 便于测试：可注入 fake Gateway 返回预设 message/tool_calls，验证编排逻辑。

---

## 2. 组件与文件

| 组件 | 文件 | 职责 |
|------|------|------|
| LLMGateway | `src/infrastructure/llm/base.py` | 构造 OpenAI 兼容 client；chat() 带重试与超时 |
| 配置 | `src/infrastructure/config.py` | `.env` 动态 provider 配置（`JARVIS_PROVIDERS` + `<PROVIDER>_*`）与 LLM 重试/超时参数 |

---

## 3. LLMGateway 接口与行为

- **构造**：`LLMGateway(provider: str)`；从 `.env` 动态加载的 provider 配置中读取 base_url、api_key、model；构造 OpenAI(api_key=..., base_url=...) 的 client。provider 不在 `JARVIS_PROVIDERS` 中时抛出明确错误。
- **chat(messages, tools?, context?)**：
  - 使用配置的 timeout、max_retries、backoff 等。
  - 可重试：连接失败、超时、5xx、限流（429）等；退避采用指数+抖动。
  - 不可重试：4xx（除 429）、认证失败、参数错误；记录日志后直接抛出。
  - 成功：记录 provider、model、latency_ms、是否带 tools；并把 provider 原始响应适配为 `LLMReply(content, tool_calls, raw)`。
  - 失败：记录 llm_chat_error 后抛出或按策略重试后抛出。

---

## 4. 配置项（建议）

- LLM_MAX_RETRIES、LLM_BASE_BACKOFF_MS、LLM_MAX_BACKOFF_MS、LLM_TIMEOUT_SECONDS。
- API Key 等敏感项从环境变量或安全配置读取，不写死在仓库。
- provider 配置建议：
  - `JARVIS_PROVIDERS=deepseek,gemini`
  - `JARVIS_DEFAULT_PROVIDER=deepseek`
  - `DEEPSEEK_BASE_URL / DEEPSEEK_API_KEY / DEEPSEEK_MODEL`
  - `GEMINI_BASE_URL / GEMINI_API_KEY / GEMINI_MODEL`

---

## 5. 与 Agent 层关系

- AgentApp 根据 config.provider 构造 LLMGateway 并注入 Orchestrator（或 AgentCoordinator）。
- 编排层每轮调用 `engine.chat(session.messages, tool_registry.to_openai_tools(), context=...)`；不处理重试细节，仅处理 `LLMReply` 或异常。

---

## 6. 日志与可观测性

- 成功：llm_chat provider=... model=... latency_ms=... tools=...
- 失败/重试：llm_chat_error、attempt、backoff_ms 等，见 OBSERVABILITY.md。

---

## 7. 扩展与测试

- 新增 provider：修改 `.env` 的 `JARVIS_PROVIDERS` 并补齐 `<PROVIDER>_BASE_URL / _API_KEY / _MODEL` 即可。
- 测试：fake LLMGateway 实现 chat() 返回预设 Completion，用于 Orchestrator/Coordinator 单测。
