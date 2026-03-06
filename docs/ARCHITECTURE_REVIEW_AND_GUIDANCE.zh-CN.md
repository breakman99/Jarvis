# Jarvis 架构审视与指导建议（2026-03-07）

基于当前仓库代码与测试（`33 passed`）的审视结论。目标是帮助你把项目从“结构良好的工程样板”推进到“可持续演进的生产级 Agent 平台”。

## 1. 审视范围

- 应用主链路：`interface -> application -> domain -> infrastructure`
- Agent 编排：`Coordinator / Factory / Planner / LoopExecutor`
- Tool 子系统：注册、执行、参数校验、HTTP 安全
- Memory 子系统：observer、store、prompt 注入
- 配置、日志、指标、审计、测试与 CI

## 2. 总体结论

项目当前状态可以概括为：

- 架构分层清晰，扩展点设计优于多数同体量项目
- 测试覆盖核心行为，回归反馈快
- 可靠性和安全基础机制已具备，但生产化闭环未完全打通

建议按「安全 -> 可靠性 -> 演进能力」三阶段推进，而不是一次性重写。

## 3. 优先级改进清单

### 3.1 P0（尽快落地）

#### P0-1 HTTP 工具补齐重定向安全控制

- 现状：`http_get/http_post_json` 只校验初始 URL，`requests` 默认可跟随重定向
- 风险：可能被外部站点重定向到内网地址，绕过 SSRF 防护意图
- 建议：
  - 默认 `allow_redirects=False`，或
  - 对每次重定向目标重新执行 `validate_http_url_safety`

相关文件：

- `src/domain/tools/catalog/builtin/http_get_tool.py`
- `src/domain/tools/catalog/builtin/http_post_json_tool.py`

#### P0-2 增加外呼网络最小权限策略

- 现状：HTTP allow/deny 是可选项，未配置时策略偏宽
- 风险：Agent 可访问任意公网目标，生产环境边界不够明确
- 建议：
  - 生产 profile 强制 `JARVIS_HTTP_ALLOW_HOSTS`
  - 启动时若检测到生产模式且白名单为空，直接 fail fast

相关文件：

- `src/infrastructure/config.py`
- `src/domain/tools/catalog/builtin/common.py`

### 3.2 P1（近期迭代）

#### P1-1 补齐 metadata 链路一致性

- 现状：`LoopExecutor` 的部分返回分支未统一携带 `request_id/trace_id`
- 风险：故障排查时链路断裂，日志和结构化返回难关联
- 建议：所有 `ExecutionResult(metadata)` 出口统一附带链路字段

相关文件：

- `src/domain/agent/execution/loop_executor.py`

#### P1-2 API Key 校验策略从“警告”升级为“环境可配置的强校验”

- 现状：LLM key 缺失仅 warning，并使用 placeholder 初始化 client
- 风险：部署后运行时才失败，错误发现滞后
- 建议：
  - 新增 `JARVIS_STRICT_STARTUP=true` 时强制校验 `<PROVIDER>_API_KEY`
  - 在 `validate_settings()` 阶段返回明确错误

相关文件：

- `src/infrastructure/config.py`
- `src/infrastructure/llm/base.py`

#### P1-3 指标存储内存上限控制

- 现状：`MetricsCollector` 直方图样本无限累积
- 风险：长时运行可能导致内存增长
- 建议：为 histograms 增加 ring buffer 或聚合桶

相关文件：

- `src/infrastructure/observability/metrics.py`

#### P1-4 会话长度治理升级为 token 维度

- 现状：`session.trim` 仅按 message 条数裁剪
- 风险：消息短长差异大，无法稳定控制 token 成本与上下文窗口
- 建议：引入 token 估算器，按 token budget 裁剪并保留关键摘要

相关文件：

- `src/domain/agent/models/session.py`
- `src/domain/agent/execution/loop_executor.py`

### 3.3 P2（中期演进）

#### P2-1 Router 升级为策略化路由

- 现状：默认 `DefaultRouter` 固定路由到单 Agent
- 价值：引入意图分类路由后可自然支持专家 Agent（检索/代码/工具重型任务）
- 建议：增加 `RuleRouter`（关键词+规则）与 `LLMRouter`（可选）

相关文件：

- `src/domain/agent/runtime/router.py`
- `src/domain/agent/runtime/coordinator.py`

#### P2-2 Memory Observer 升级为规则 + 模型混合抽取

- 现状：Regex 规则简单稳定，但覆盖有限
- 建议：保留 regex 为低成本高精度层，增加轻量模型抽取器并做字段置信度控制

相关文件：

- `src/domain/agent/memory/service.py`

#### P2-3 引入 API 层（FastAPI）并标准化结构化响应

- 现状：CLI 友好，服务化接口缺位
- 建议：复用 `chat_structured()` 输出，新增 `/chat` endpoint 与健康检查/指标导出

## 4. 30 天落地路线（建议）

### 第 1 周：安全封边

1. HTTP 重定向安全校验
2. 生产白名单策略与配置校验
3. 增加 SSRF 回归测试（重定向场景）

### 第 2 周：可靠性与可观测性

1. metadata 全分支链路字段统一
2. MetricsCollector 内存上限
3. 增加链路一致性测试

### 第 3 周：成本治理与上下文管理

1. token 预算裁剪
2. 会话摘要机制（可选）
3. 压测对比（延迟/成本/成功率）

### 第 4 周：演进能力

1. RuleRouter 多 Agent 路由
2. Memory 抽取器分层
3. 评估 API 层落地（可先只做内部接口）

## 5. 测试策略加强建议

现有测试质量不错，建议补充以下类型：

- 安全回归：HTTP 302/307 重定向到内网地址
- 稳定性：LLM 与 Tool 重试边界（极值、随机故障）
- 性能：100+ 连续对话下会话裁剪与内存占用
- 合约：`ChatEnvelope` 字段向后兼容测试

## 6. 你可以优先做的三件事

1. 先做 P0（HTTP 重定向安全 + 白名单策略）
2. 再做 P1-1（链路 metadata 一致性）
3. 最后做 P1-3（metrics 内存上限），确保长跑稳定

这三项改造成本低、收益高、回归范围可控。
