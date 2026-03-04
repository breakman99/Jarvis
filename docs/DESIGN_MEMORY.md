# Memory 层设计

> 长期记忆的存储抽象、多后端实现与面向 Agent 的高层 API（构建 system 上下文、从用户输入中抽取并持久化记忆）。

---

## 1. 设计目标与约束

- 存储与使用解耦：存取由 Memory 层负责；何时读/写由 Agent 编排层控制。
- 可插拔后端：抽象 BaseMemoryStore；默认支持文件（FileMemoryStore）与 SQLite（SQLiteMemoryStore）；接口可扩展 Redis 等。
- 结构化、可扩展的抽取逻辑：避免在单一大函数中堆叠 if-else；采用 Observer/规则链从 user_input 提取并更新记忆。
- 默认后端为 SQLite；文件后端用于无外部依赖或轻量单机场景。

---

## 2. 组件与文件

| 组件 | 文件 | 职责 |
|------|------|------|
| BaseMemoryStore | `src/agent/memory.py` | 存储抽象：get/set/query（或 load/save 兼容） |
| FileMemoryStore | 同上 | 基于 JSON 文件的实现（namespace+key 或兼容结构） |
| SQLiteMemoryStore | 同上 | 基于 SQLite 的实现（默认）；表结构 memory_items 等 |
| MemoryService | 同上 | 高层 API：build_system_context、observe_user_input、get_user_profile 等 |
| Observer / 规则 | 同上 | 从 user_input 提取名字、语言、时区等；可扩展 |

---

## 3. 存储抽象 BaseMemoryStore

- **接口**（演进后）：get(namespace, key) -> Any；set(namespace, key, value)；query(namespace, filters?) -> List[Dict]（可选）。
- **兼容**：现有 load() -> Dict、save(data) -> None 可与 namespace/key 结构并存或迁移为基于 namespace 的平面存储。
- 实现体负责序列化（如 JSON）、并发与持久化策略。

---

## 4. FileMemoryStore

- 路径由配置提供（如 memory_file_path）；单文件 JSON。
- load()：文件不存在返回 {}；存在则 json.load。
- save(data)：确保父目录存在；json.dump(..., ensure_ascii=False, indent=2)。
- 适用于无 DB 依赖、单进程场景。

---

## 5. SQLiteMemoryStore（默认）

- 单文件 SQLite（路径如 memory_db_path）；表至少包含：id、namespace、key、value_json、updated_at。
- 实现 get/set/query（或与现有 load/save 的适配层），供 MemoryService 统一调用。
- 支持多进程时需注意连接与锁策略（如 WAL）。

---

## 6. MemoryService 高层 API

- **build_system_context() -> str**：从当前存储加载快照，拼出可读的“已知用户记忆”文案（如用户名、偏好语言），供 Orchestrator 注入 system prompt。
- **observe_user_input(user_input) -> Dict**：依次执行各 Observer/规则，合并变更到内存快照并写回存储；返回当前快照或变更集。
- **get_user_profile() / update_user_profile(...)**（可选）：对上层暴露结构化画像（user_name、preferred_language、timezone 等），内部仍通过 store get/set 实现。

---

## 7. 记忆抽取：Observer / 规则

- 现状：observe_user_input 内用少量正则与关键词提取 user_name、preferred_language。
- 目标：拆为独立 Observer（如 NameObserver、LanguageObserver、TimezoneObserver），每个实现 apply(snapshot, user_input) -> changed_fields 或直接修改 snapshot；MemoryService 仅负责调用顺序与写回。
- 新增记忆类型时新增 Observer，避免单函数膨胀。

---

## 8. 与 Agent 的协作点

- **Orchestrator 初始化**：调用 build_system_context()，将返回值拼入 AgentSession 的 system_prompt。
- **每次 run() 开始**：调用 observe_user_input(user_input)，再执行后续会话与 LLM 逻辑。
- 多 Agent 场景下，MemoryService 由 Coordinator 持有，保证各 Agent 共享同一用户画像。

---

## 9. 配置

- memory_backend：`"file"` | `"sqlite"` 等；默认 `"sqlite"`。
- memory_file_path：文件后端路径。
- memory_db_path：SQLite 后端路径。

---

## 10. 测试与演进

- 测试：临时文件或内存 SQLite；覆盖空存储、多次 observe 与 build_system_context 一致性。
- 演进：更多字段与 Observer；LLM 辅助抽取；与向量检索结合做长文档/知识库记忆。
