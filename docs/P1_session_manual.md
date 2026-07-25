# P1 实验运行手册

本手册用于 P1 provenance 实验的彩排与正式 session。手册与代码在同一仓库、同一分支下版本控制；任何影响 session 行为、记录字段或分析裁定的代码变更，都必须同步更新本手册。

ERGO 115447：导师已批准，当前状态为 `Awaiting FEC Review`（截至 2026-07-18）。正式招募、录音与数据收集必须待 FEC 最终批准。

## 1. Session 前检查单

### 1.1 实验准入

- 已获得 FEC 最终批准。
- `COMP2300` 教学材料许可状态：导师已在 2026-07-10 例会中口头同意本项目使用；书面确认已收到（截至 2026-07-22）。该材料现可用于阶段 D 正式文档生成；源文件与派生 CSV 仍须保持本地、不得进入 Git。
- 已确定最终模型：本地 `llama3.2:3b` 与 `qwen2.5:3b`，云端 Azure `Mistral-Large-3`（deployment version `1`、`GlobalStandard`）。
- 确认 participant information sheet 已发送、consent form 已签署、录音设备已就绪。
- 确认 participant、task、batch 和 doc ID 已按分配表固定。
- 确认该 doc 的 `pipelineRuns` 记录包含 `finished_at`。
- 确认 `pipelineRuns.llm_backend`、`model_name`、`code_version` 与本次批准的实验配置一致。
- 确认该 doc 位于正式 doc ID whitelist，不是开发或测试文档。

#### 正式 doc ID whitelist 与盲测密钥（阶段 D 填写）

阶段 D 生成正式实验文档后，在下表填入全部 9 个 `doc_id`。模型列只允许 researcher 查看；参与者只见 Batch 标签。表格填满并核对前，不得运行正式分析。

| 正式 survey name | Batch | 真实模型 | doc_id |
| --- | --- | --- | --- |
| `P1_task1_batchA` | A | `llama3.2:3b` | |
| `P1_task2_batchB` | B | `Mistral-Large-3` | |
| `P1_task3_batchC` | C | `qwen2.5:3b` | |
| `P2_task1_batchB` | B | `qwen2.5:3b` | |
| `P2_task2_batchC` | C | `llama3.2:3b` | |
| `P2_task3_batchA` | A | `Mistral-Large-3` | |
| `P3_task1_batchC` | C | `Mistral-Large-3` | |
| `P3_task2_batchA` | A | `qwen2.5:3b` | |
| `P3_task3_batchB` | B | `llama3.2:3b` | |

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
- Azure 运行必须核对 `AZURE_OPENAI_BASE_URL` 以 `/openai/v1/` 结尾、`AZURE_OPENAI_API_KEY` 已配置、`AZURE_OPENAI_MODEL=Mistral-Large-3`、`AZURE_OPENAI_MODEL_VERSION=1`、`AZURE_OPENAI_DEPLOYMENT_TYPE=GlobalStandard`；密钥不得写入手册、日志或 Git。
- Ollama 运行必须核对 `OLLAMA_BASE_URL=http://localhost:11434` 与本场批准的 `OLLAMA_MODEL`，确认 `/api/tags` 可访问，并核对完整 digest：`llama3.2:3b` 为 `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`，`qwen2.5:3b` 为 `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`。
- 正式文档生成与正式 session 均必须设置 `LLM_STRICT_MODE=true` 和 `FREEZE_LABELS=true`；两个开关语义正交，可长期同时启用。
- 正式文档生成必须设置 `LLM_TIMEOUT_SECONDS=60`、`LLM_TEMPERATURE=0`、`LLM_SEED=42`、`LLM_MAX_TOKENS=1024`。Azure 的 seed 为 best-effort，不宣称逐位可复现；Ollama 将 `LLM_MAX_TOKENS` 映射为 `num_predict`。
- 两个开关均在 AI service 启动时读取；修改 `.env` 后必须完整重启 AI service，不能依赖热更新。
- 在每场生成与 session 记录中写明实际 backend、model、`FREEZE_LABELS` 与四项 sampling/timeout 值，并目视核对其与批准配置一致。
- 运行 `git status --short`；正式 session 要求无输出，即 clean worktree。
- 正式生成前建立 annotated tag `generation-frozen-G`；九条正式 `pipelineRuns.code_version` 必须全部等于该 tag 指向的完整 hash `G`。
- 九个 doc ID、smoke 排除 doc ID 与全部生成台账填满后，只允许提交一次 `docs/` 变更，得到 session 操作版本 `S`。在 `S` 上以 `S` full hash 为端点运行非 docs diff 与 prompt hash 复核。随后只允许恰好一个 message 为 `docs: audit record for S` 的 docs-only audit commit，记录 `S` full hash 和已得到的验证结果，不得改变任何操作性内容。正式 session 固定 checkout 到该 audit commit；`S` 与 audit commit 除 `docs/` 外都必须与 `G` 等价。

#### 版本凭据（阶段 D 填写）

| 凭据 | 值 |
| --- | --- |
| Generation instrument `G` full hash | `TBD` |
| Generation tag | `generation-frozen-G` |
| Generation date | `TBD` |
| Session operation `S` full hash | `TBD` |
| `G → S` 非 docs diff | `TBD` |
| `S` prompt hash 复核 | `TBD` |
| Audit commit | `S` 后恰好一个；message `docs: audit record for S` |
| Session checkout endpoint | 上述唯一 audit commit |
| Session 前 `G → audit` 非 docs diff | `TBD` |
| Session 前 `S → audit` 非 docs diff | `TBD` |
| Session 前 prompt hash 复核 | `TBD` |

三层关系固定为 `G`（annotated tag）→ `S`（whitelist/台账 commit）→
唯一 audit commit。Audit commit 不自指记录自己的 hash；其身份由
`provenance-extension` 的 `HEAD`、固定 commit message 及 parent=`S` 共同
核对。

若建立 `G` 后发现代码缺陷，不得在 `G → S` 间直接修补。必须二选一并留档：保持 `G` 完成实验并把缺陷写入 limitation；或修复后废止当前正式候选文档、建立新 generation tag 并重新生成全部九个文档。不得混用两个仪器版本。

### 1.4 盲测纪律

- 本研究为 single-blind：researcher 知道上表矩阵，参与者不知道模型身份。
- 参与者界面、任务说明与口头交流只使用 Batch A/B/C，不显示或透露 model、backend、digest 或 deployment。
- 三场 session 之间不得透露任何模型信息或其他参与者看到的模型顺序。
- Researcher 按矩阵中的 doc ID 打开任务，不根据参与者反应临场调换文档。

### 1.5 Participant 与浏览器

- 正式 participant 只使用 `P1`、`P2`、`P3`。
- 使用带身份参数的链接，例如：

  ```text
  http://localhost:5173/cluster-graph?participant=P1
  ```

- 目视核对页面 badge 必须显示预期身份，例如 `Participant: P1`。
- 输入分配表中的 doc ID，并确认页面只显示盲测 batch 信息，不显示 model identity。
- Session 全程停留在 Cluster Graph；避免刷新或离开页面。若发生刷新，记录事件并重新输入同一 doc ID。

### 1.6 本地错误日志

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

### 4.4 开发与 smoke 文档排除名单

以下文档真实存在于 `documents` 与 `pipelineRuns`，但绝不进入正式 doc ID
whitelist，也绝不进入分析。阶段 D 每个 smoke 完成或失败后立即登记其
`doc_id`；正式分析开始前任一空缺都必须先对账。

| Survey name | 用途 | doc_id（阶段 D 登记） |
| --- | --- | --- |
| `D_SMOKE_LLAMA_batchA` | Llama 20 行配置/provider smoke | |
| `D_SMOKE_QWEN_batchA` | Qwen 20 行配置/provider smoke | |
| `D_SMOKE_AZURE_batchA` | Azure deployment 存活及 20 行 provider smoke | |

所有分析脚本必须同时实施两道 document 门禁：

1. `doc_id` 必须位于第 1.1 节正式 whitelist；
2. `doc_id` 不得位于本节开发/smoke 排除名单。

两份名单未填满或发生交集时必须 fail closed，禁止运行正式分析。只依赖
survey name、participant 排除名单或其中任一 document 名单都不合格。

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
- 只有满足 `{status: "completed", finished_at: {$exists: true}}`、backend/model 与正式条件一致、`params.temperature=0`、`params.seed=42`、`params.max_tokens=1024`、`params.timeout_seconds=60`，且 `code_version` 属批准 commit 的 run 才能进入实验。
- 遗留 `status: "running"` 的非当前 run 视为进程中断并作废；没有 `status` 字段的旧 P1 run 属开发数据，一律排除。
- 正式分析同时使用 participant 排除名单、正式 doc ID whitelist 与第 4.4 节开发/smoke doc ID 排除名单；必须执行“在 whitelist 且不在 smoke 排除名单”的 document 双门禁，不能只依赖 survey name。
- 模型间 cluster 粒度、过滤数量和实际审查数量的差异保留为结果，不通过删除记录强行等量化。

## 6. 已知边界与历史包装

- `react-client/src/api/dataFacade.ts::cluster_recordFeedback` 调用 `storage.recordClusterFeedback`，属于 api-server 历史路径。当前实验 UI 没有调用它；P1 中勿用勿删，避免误认成第二条正式 feedback 写入路径。
- P1 将 cosine suggestion 的 `SUGGEST_AT` 设为 `9999`，正式 session 不展示 suggestion cards。相关 accept/reject 代码保留但不属于当前参与者流程。
- Cluster Graph 刷新后不会自动恢复 doc ID，需重新输入；刷新属于需记录的 session 异常。
- `FREEZE_LABELS` 已实现并验证（commit `fd49542`，2026-07-19）。启用时，`/feedback/recluster` 仍记录 provenance、移动 fragment、更新簇成员与 centroid，但跳过运行时 `labeller`，并返回 `labels_frozen: true`。
- 启用 `FREEZE_LABELS` 时，`/cluster/run`、`/label/clusters`、`/suggest/save` 在任何数据库写入前返回 `423 Locked` 和 `labels_frozen`；`/llm-cluster/run` 不受 freeze 阻塞，其生成结果进入正式实验仍由 strict mode 与正式 doc ID whitelist 共同门禁。
- Strict experiment mode 已实现并验证（commit `f7421cf`，2026-07-18）；正式文档生成必须使用该模式，使 LLM 请求失败或无效响应显式终止 run，不写入 heuristic fallback 聚类结果。
- Assignment prompt 已于 commit `f7421cf` 修订，明确列出合法整数 cluster ID 并约束 `assign` 只能从中选择；三个模型统一使用该版本。正式 9 个 doc 生成前不得再修改 prompt；若必须修改，改动前生成的所有正式候选 run 均作废并重新生成。
- Sampling 参数已实现并验证（commit `2567fc3`，2026-07-19；验证记录 `docs/verification_records/sampling_freeze.md`）。三个模型统一请求 `temperature=0`、`seed=42`、`max_tokens=1024` 与 60 秒 timeout，SDK 隐藏重试保持为零；Azure seed 的 best-effort 语义单独记入 `pipelineRuns.params.seed_semantics`。Prompt 与 sampling 参数共同构成冻结的实验仪器；正式生成开始后若必须修改任一项，旧仪器下的全部正式候选 run 均作废并重新生成，且所有尝试记录保留。
- 本地模型选择已验证并留档于 `docs/verification_records/local_model_selection.md`。候选 `qwen2.5:7b` 在唯一一次 20 行门禁运行的首个 relevance 调用中触发 `ReadTimeout`，strict run 失败且零簇落库；未重试、未放宽 60 秒共同 timeout。预定义回退 `qwen2.5:3b` 在相同配置下唯一一次完成，因此最终本地模型固定为 `llama3.2:3b + qwen2.5:3b`。
- 阶段 D 按模型分组生成：Llama 三个 → Qwen 三个 → Azure 三个。每次只切换一次 `.env` 并完整重启，先做非正式 smoke 并核对 `pipelineRuns`，再生成该模型的三个正式文档。完整顺序、输入 manifest、失败处理和九文档台账见 `docs/stage_d_generation_runbook.md`。
- Azure/Mistral backend 已通过共享 provider 接入并完成技术验证（共享层 commit `936fdda`，Azure 实现 commit `434efe1`，验证记录 `docs/verification_records/azure_mistral.md`）。已验证 `Mistral-Large-3` deployment version `1`、`GlobalStandard`、60 秒 timeout、零隐藏重试、active-backend-only 配置校验、Ollama 离线隔离、缺 key fail-loud 及 content-filter 失败语义。
- 性健康 smoke test 仅运行一次并以 `status: "completed"` 终局结束（结果 commit `da5a49a`），未触发 content filter。该单行测试只覆盖 relevance 与首簇创建分支，不能视为多片段 assignment 或正式批次验证；正式生成仍受最终模型选择、clean worktree 与正式 doc ID whitelist 门禁。

## 7. 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-07-18 | 建立正式 P1 实验运行手册；记录 participant、启动检查、失败恢复、分析裁定、测试身份排除和历史 feedback 包装边界。 |
| 2026-07-18 | 更正 ERGO 状态；补充伦理程序、participant 排除名单审计及正式 doc ID whitelist。 |
| 2026-07-18 | 记录 strict mode 验证结果、completed run 分析规则、中断 run 排除规则及 assignment prompt 冻结政策。 |
| 2026-07-19 | 记录 `FREEZE_LABELS` 全局改写守卫、recluster 冻结行为、423 拒绝边界及与 strict mode 的正交关系。 |
| 2026-07-19 | 记录 COMP2300 口头许可与待回书面确认状态；记录 Azure/Mistral 技术验证、性健康单行 smoke test 结果及其覆盖边界。 |
| 2026-07-19 | 冻结 `temperature=0`、`seed=42`、`max_tokens=1024` 与 60 秒 timeout；记录 Azure/Ollama 真实 20 行验证、provider seed 语义和 prompt+sampling 联合冻结政策。 |
| 2026-07-22 | 记录 COMP2300 书面许可已收到；解除阶段 D 正式文档生成的数据许可阻塞，保留源文件与派生 CSV 不进入 Git 的约束。 |
| 2026-07-22 | 根据预注册门禁结果固定本地模型为 `llama3.2:3b + qwen2.5:3b`；记录 `qwen2.5:7b` 的 60 秒超时淘汰、3B 回退通过及完整 Ollama digest。 |
| 2026-07-22 | 固定九文档正交拉丁方、single-blind 操作定义、按模型分组生成顺序，以及 generation `G` / session `S` 双版本凭据与非 docs 等价性证明。 |
| 2026-07-25 | 在 `G` 前固定 20 行 smoke 输入、smoke 文档排除双门禁、Ollama digest 与 Azure deployment 存活检查、人工批准的 `_attemptN` 失败协议，以及 `G → S → audit commit` 三层版本结构。 |
