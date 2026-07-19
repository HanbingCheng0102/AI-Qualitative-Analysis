# P1 实验运行手册

本手册用于 P1 provenance 实验的彩排与正式 session。手册与代码在同一仓库、同一分支下版本控制；任何影响 session 行为、记录字段或分析裁定的代码变更，都必须同步更新本手册。

ERGO 115447：导师已批准，当前状态为 `Awaiting FEC Review`（截至 2026-07-18）。正式招募、录音与数据收集必须待 FEC 最终批准。

## 1. Session 前检查单

### 1.1 实验准入

- 已获得 FEC 最终批准。
- 已获得 COMP2300 教学材料的数据使用许可。
- 已确定本实验使用的最终模型。
- 确认 participant information sheet 已发送、consent form 已签署、录音设备已就绪。
- 确认 participant、task、batch 和 doc ID 已按分配表固定。
- 确认该 doc 的 `pipelineRuns` 记录包含 `finished_at`。
- 确认 `pipelineRuns.llm_backend`、`model_name`、`code_version` 与本次批准的实验配置一致。
- 确认该 doc 位于正式 doc ID whitelist，不是开发或测试文档。

#### 正式 doc ID whitelist（阶段 D 填写）

阶段 D 生成正式实验文档后，在下表填入全部 9 个 `doc_id`。表格填满并核对前，不得运行正式分析。

| 序号 | doc_id |
| --- | --- |
| 1 | |
| 2 | |
| 3 | |
| 4 | |
| 5 | |
| 6 | |
| 7 | |
| 8 | |
| 9 | |

### 1.2 服务启动顺序

1. 确认 Ollama 可用：

   ```powershell
   ollama list
   ```

2. 启动 MongoDB，并保持终端窗口开启：

   ```powershell
   D:\mongodb\bin\mongod.exe --dbpath D:\mongodb\data
   ```

3. 在项目目录启动 React、API server 和 AI service：

   ```powershell
   cd D:\6003\thematic_clusters_git\react-client
   npm run dev:all
   ```

4. 确认以下页面可访问：

   ```text
   http://localhost:5173
   http://localhost:8000/docs
   ```

### 1.3 配置与代码版本

- 查看仓库根目录 `.env`，目视核对 `LLM_BACKEND` 与对应 model name。
- 正式文档生成与正式 session 均必须设置 `LLM_STRICT_MODE=true` 和 `FREEZE_LABELS=true`；两个开关语义正交，可长期同时启用。
- 两个开关均在 AI service 启动时读取；修改 `.env` 后必须完整重启 AI service，不能依赖热更新。
- 在每场 session 记录中写明实际 `FREEZE_LABELS` 值，并目视核对其为 `true`。
- 运行 `git status --short`；正式 session 要求无输出，即 clean worktree。
- 运行 `git rev-parse HEAD`，记录当前 commit，并与正式文档的 `pipelineRuns.code_version` 核对。

### 1.4 Participant 与浏览器

- 正式 participant 只使用 `P1`、`P2`、`P3`。
- 使用带身份参数的链接，例如：

  ```text
  http://localhost:5173/cluster-graph?participant=P1
  ```

- 目视核对页面 badge 必须显示预期身份，例如 `Participant: P1`。
- 输入分配表中的 doc ID，并确认页面只显示盲测 batch 信息，不显示 model identity。
- Session 全程停留在 Cluster Graph；避免刷新或离开页面。若发生刷新，记录事件并重新输入同一 doc ID。

### 1.5 本地错误日志

Session 开始前在浏览器 Console 查看：

```javascript
JSON.parse(localStorage.getItem("nieFeedbackProvenanceErrors"))
```

- 若存在上一场 session 的日志，先导出并归入上一场 session 记录。
- 确认导出后清空：

  ```javascript
  localStorage.removeItem("nieFeedbackProvenanceErrors")
  ```

- `localStorage` 按同一 browser origin 跨 session 保留，不能依赖它自动按 participant 隔离。

## 2. Session 中现场处理

开始参与者任务前，researcher 开始录音，并口头确认 participant 已阅读 information sheet、已签署 consent form 且同意本次录音。

### 2.1 参与者操作

- 认可当前 placement：点击单卡 `Confirm`。
- 不认可当前 placement：将卡拖到参与者认为正确的 cluster。
- confirm 与后续 move 都保留为独立 provenance 记录，不修改或删除旧记录。
- 当前裁定以该 participant 对该 fragment 的最后动作为准。
- 卡片在当前所属 cluster 内拿起并放回属于 no-op，不产生 move 记录。

### 2.2 卡片弹回

卡片移动后自动弹回原 cluster，表示 recluster 请求被拒绝或失败，前端已重新读取数据库投影。这不是参与者操作错误。

现场处理规则：

- Researcher 记录发生时间、participant、task、doc ID 和卡片标识。
- 不向参与者解释技术细节，不引导其改变判断；让 think-aloud 自然记录其反应。
- 不弹出参与者可见的错误横幅是预期设计。
- 不要求参与者立即重复操作；researcher 先确认服务状态和错误日志。
- 若恢复读取也失败，屏幕可能暂时保留乐观位置。恢复服务后重新载入同一 doc，以 MongoDB 状态为准，并记录该异常。

### 2.3 409 与其他异常

- 单人、单标签页、每 fragment 串行写入的 session 中，`409` 理论上不应发生。
- 出现 `409` 时将其记为实验异常事件，不把失败动作计为成功 move。
- `404` 或 `422` 表示请求引用关系不合法，同样记录并停止该卡的继续操作，直至数据库投影恢复。

## 3. Session 后检查单

- 停止录音。
- 将音频文件命名为 `P{n}_YYYYMMDD`。
- 按已批准的数据管理计划存放音频文件。

在 mongosh 中切换到 `nie`：

```javascript
use nie
```

设置本场 doc 与 participant：

```javascript
var DOC = ObjectId("本场_DOC_ID")
var PARTICIPANT = "P1"
```

核对 provenance 事件总数：

```javascript
db.clusterFeedback.countDocuments({
  doc_id: DOC,
  participant_id: PARTICIPANT
})
```

核对实际审查 fragment 数：

```javascript
db.clusterFeedback.distinct("fragment_id", {
  doc_id: DOC,
  participant_id: PARTICIPANT
}).length
```

查看本场记录的时间顺序：

```javascript
db.clusterFeedback.find(
  { doc_id: DOC, participant_id: PARTICIPANT },
  { fragment_id: 1, action: 1, from_cluster_id: 1, to_cluster_id: 1, timestamp: 1 }
).sort({ timestamp: 1, _id: 1 }).pretty()
```

Session 结束后再次读取浏览器错误日志：

```javascript
JSON.parse(localStorage.getItem("nieFeedbackProvenanceErrors"))
```

每条错误应包含：

```text
ts, participant, action, doc_id, fragment_id, http_status, message
```

- 将日志内容归入本场 session 记录，即使结果为 `null` 或空数组也要记载。
- 核对现场记录中的卡片弹回、409 或服务中断是否均有对应日志。
- 在下一场 session 前，完成导出后再清空 localStorage。

## 4. 命名与身份规范

### 4.1 Doc 命名

正式 survey name 使用：

```text
P{n}_task{m}_batch{A|B|C}
```

示例：

```text
P1_task2_batchB
```

`pipelineRuns.batch_label` 从该命名解析。无法唯一解析时写入 `UNKNOWN` 并产生 warning；`UNKNOWN` run 不得直接进入正式分析。

### 4.2 Participant 身份

- 正式身份：`P1`、`P2`、`P3`。
- 彩排身份：`PILOT`；只用于端到端彩排，不进入正式模型比较。
- Participant ID 按 `trim + uppercase` 规范化，并进行精确匹配。
- 缺失或空身份进入 `TEST` 隔离桶。

### 4.3 开发与测试身份排除名单

正式分析一律排除：

```text
TEST
P_TEST
P_OTHER
PILOT
RACE_TEST
RACE_TEST_1
RACE_TEST_2
REL_TEST
SWAGGER_REL
VERIFY_REL
VERIFY_REL_2
```

后续新增任何开发、Swagger 或恢复测试身份，必须先登记在此名单，再产生测试数据。

## 5. 分析约定

- 正式分析前必须先在 mongosh 运行：

  ```javascript
  db.clusterFeedback.distinct("participant_id")
  ```

  将结果与第 4.3 节排除名单及正式身份 `P1`、`P2`、`P3` 逐项对账。出现名单外身份即为漏登记：立即暂停分析、查明来源并完成登记或排除，不得静默忽略后继续分析。
- `clusterFeedback` 按 `participant_id` 精确匹配，不使用“排除 TEST 后全部保留”的宽松规则。
- 同一 participant、doc、fragment 的当前裁定顺序为 `{timestamp: -1, _id: -1}`，取第一条为 latest action。
- confirm 与 move 记录共存；latest action 只决定当前状态，不覆盖历史记录。
- “实际审查片段数”定义为该 participant 在该 doc 上至少留有一条 feedback 的不同 `fragment_id` 数。
- confirm rate、move rate 按实际审查片段数归一化。
- `pipelineRuns.doc_id` 与 `clusterFeedback.doc_id` 必须同为 BSON `ObjectId` 后再 join。
- 只有满足 `{status: "completed", finished_at: {$exists: true}}`、backend/model 与正式条件一致、`code_version` 属批准 commit 的 run 才能进入实验。
- 遗留 `status: "running"` 的非当前 run 视为进程中断并作废；没有 `status` 字段的旧 P1 run 属开发数据，一律排除。
- 正式分析同时使用 participant 排除名单与正式 doc ID whitelist；不能只依赖 survey name。
- 模型间 cluster 粒度、过滤数量和实际审查数量的差异保留为结果，不通过删除记录强行等量化。

## 6. 已知边界与历史包装

- `react-client/src/api/dataFacade.ts::cluster_recordFeedback` 调用 `storage.recordClusterFeedback`，属于 api-server 历史路径。当前实验 UI 没有调用它；P1 中勿用勿删，避免误认成第二条正式 feedback 写入路径。
- P1 将 cosine suggestion 的 `SUGGEST_AT` 设为 `9999`，正式 session 不展示 suggestion cards。相关 accept/reject 代码保留但不属于当前参与者流程。
- Cluster Graph 刷新后不会自动恢复 doc ID，需重新输入；刷新属于需记录的 session 异常。
- `FREEZE_LABELS` 已实现并验证（commit `fd49542`，2026-07-19）。启用时，`/feedback/recluster` 仍记录 provenance、移动 fragment、更新簇成员与 centroid，但跳过运行时 `labeller`，并返回 `labels_frozen: true`。
- 启用 `FREEZE_LABELS` 时，`/cluster/run`、`/label/clusters`、`/suggest/save` 在任何数据库写入前返回 `423 Locked` 和 `labels_frozen`；`/llm-cluster/run` 不受 freeze 阻塞，其生成结果进入正式实验仍由 strict mode 与正式 doc ID whitelist 共同门禁。
- Strict experiment mode 已实现并验证（commit `f7421cf`，2026-07-18）；正式文档生成必须使用该模式，使 LLM 请求失败或无效响应显式终止 run，不写入 heuristic fallback 聚类结果。
- Assignment prompt 已于 commit `f7421cf` 修订，明确列出合法整数 cluster ID 并约束 `assign` 只能从中选择；三个模型统一使用该版本。正式 9 个 doc 生成前不得再修改 prompt；若必须修改，改动前生成的所有正式候选 run 均作废并重新生成。

## 7. 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-07-18 | 建立正式 P1 实验运行手册；记录 participant、启动检查、失败恢复、分析裁定、测试身份排除和历史 feedback 包装边界。 |
| 2026-07-18 | 更正 ERGO 状态；补充伦理程序、participant 排除名单审计及正式 doc ID whitelist。 |
| 2026-07-18 | 记录 strict mode 验证结果、completed run 分析规则、中断 run 排除规则及 assignment prompt 冻结政策。 |
| 2026-07-19 | 记录 `FREEZE_LABELS` 全局改写守卫、recluster 冻结行为、423 拒绝边界及与 strict mode 的正交关系。 |
