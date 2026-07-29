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

#### Session 仪器冻结裁定（2026-07-29）

正式 P1/P2/P3 三场 session 统一使用精确 commit：

```text
ddb5355972ca63df44edad184b11e30f420e4c62
```

裁定采用“不修改 session UI”的路径。候选分支
`codex/session-card-readability-v1` 及其 commits `c5b7354`、`2f49694`
不得用于正式 session。该候选不仅改变字号或对比度，还增加 full-text
hover/pin、note popover、键盘交互和 URL 文档持久化，因此属于未重新彩排和
冻结的参与者仪器变化。

第一场 session 前必须 detached checkout 到上述完整 hash，并核对 clean
worktree。P1、P2、P3 三场之间绝对不得切换 commit、分支或修改参与者界面。
若任何可读性问题被裁定为足以影响数据质量，必须在第一场前停止招募日程，
建立新 instrument、在 `nie_pilot` 重跑彩排、重新冻结并更新版本凭据；不得
在 participant 之间热修。

#### 正式 doc ID whitelist 与盲测密钥（阶段 D 填写）

阶段 D 的 9 个 G2 正式文档已经全部完成并通过矩阵级验收。只有下表中的
九个 `doc_id` 可以进入正式分析；`run_id` 是对应的唯一获批生成记录。模型列
只允许 researcher 查看；参与者只见 Batch 标签。任何名称相同但 ID 不同的
文档均不因名称匹配而获得资格。

| 正式 survey name | Batch | 真实模型 | doc_id | run_id |
| --- | --- | --- | --- | --- |
| `P1_task1_batchA` | A | `llama3.2:3b` | `6a6621355e9bd7a009d1b97f` | `6a66213a5e9bd7a009d1b991` |
| `P1_task2_batchB` | B | `Mistral-Large-3` | `6a6672adaaaa46976afdb5ba` | `6a6672b1aaaa46976afdb5d0` |
| `P1_task3_batchC` | C | `qwen2.5:3b` | `6a662813ed5bcd0c9d8a4439` | `6a662818ed5bcd0c9d8a444e` |
| `P2_task1_batchB` | B | `qwen2.5:3b` | `6a666d4f04fc296116b621af` | `6a666d5404fc296116b621c5` |
| `P2_task2_batchC` | C | `llama3.2:3b` | `6a662346b88c6db2d9915ac9` | `6a66234bb88c6db2d9915ade` |
| `P2_task3_batchA` | A | `Mistral-Large-3` | `6a667375aaaa46976afdb5dc` | `6a667376aaaa46976afdb5ee` |
| `P3_task1_batchC` | C | `Mistral-Large-3` | `6a6673f2aaaa46976afdb5f7` | `6a6673f3aaaa46976afdb60c` |
| `P3_task2_batchA` | A | `qwen2.5:3b` | `6a666f0d5f60ce182f69ff12` | `6a666f125f60ce182f69ff24` |
| `P3_task3_batchB` | B | `llama3.2:3b` | `6a6625e3460dababa39a9be4` | `6a6625e7460dababa39a9bfa` |

### 1.2 服务启动顺序

1. 生成/技术验证时确认 Ollama 可用；正式 session 不保持 Ollama 运行，按
   第 1.3.1 节执行双重物理隔离：

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
- 正式文档生成必须设置 `LLM_TIMEOUT_SECONDS=60`、`LLM_TEMPERATURE=0`、`LLM_SEED=42`、`LLM_MAX_TOKENS=1024`。固定 seed 不保证两次运行得到相同 assignment decision；Ollama 将 `LLM_MAX_TOKENS` 映射为 `num_predict`。
- 两个开关均在 AI service 启动时读取；修改 `.env` 后必须完整重启 AI service，不能依赖热更新。
- 在每场生成与 session 记录中写明实际 backend、model、`FREEZE_LABELS` 与四项 sampling/timeout 值，并目视核对其与批准配置一致。
- 运行 `git status --short`；正式 session 要求无输出，即 clean worktree。
- G-era tag `generation-frozen-G` 永久保留但已被 G2 仪器取代；G-era completed 候选均为 superseded，不得进入 whitelist。正式生成前必须建立获批的 annotated tag `generation-frozen-G2`；九条正式 `pipelineRuns.code_version` 必须全部等于该 tag 指向的完整 hash。
- 每条正式 run 的 `params` 还必须记录 `schema_enforced: true`、`schema_version: "stage_d_structured_output_v1"`、`schema_dynamic_cluster_id_enum: true` 与匹配 backend 的 `schema_transport`。
- 九个 doc ID、三个 G2 smoke 排除 doc ID 与全部生成台账填满后，只允许提交一次 `docs/` 变更，得到 session 操作版本 `S`。在 `S` 上以 `S` full hash 为端点运行 G2→S 非 docs diff 与 G2 prompt hash 复核。随后只允许恰好一个 message 为 `docs: audit record for S` 的 docs-only audit commit，记录 `S` full hash 和已得到的验证结果，不得改变任何操作性内容。正式 session 固定 checkout 到该 audit commit；`S` 与 audit commit 除 `docs/` 外都必须与 G2 等价。

#### 版本凭据（阶段 D 填写）

| 凭据 | 值 |
| --- | --- |
| Historical instrument `G` full hash | `da47d0eda734fc4136b8303a03d09e2d5f78c95f` |
| Historical tag | `generation-frozen-G`（immutable；superseded formal candidates excluded） |
| Generation instrument `G2` full hash | `544540beedb707c2be5c08fa1647107f80587c84` |
| Generation tag | `generation-frozen-G2` |
| Generation date | 2026-07-26 |
| Session operation `S` full hash | `5a70fb9e785cffd5a19d9d1501fc598923d909b7` |
| `G2 → S` 非 docs diff | 2026-07-26；exit 0；无输出 |
| `S` prompt hash 复核 | 2026-07-26；Ran 1 test；OK |
| G→G2 upgrade record | `docs/verification_records/g2_instrument_upgrade.md` |
| G2 generation record | `docs/verification_records/stage_d_g2_generation.md` |
| Audit commit | `ddb5355972ca63df44edad184b11e30f420e4c62`；message `docs: audit record for S` |
| Session checkout endpoint | `ddb5355972ca63df44edad184b11e30f420e4c62`（三场固定，不跟随分支移动） |
| Session 前 `G2 → audit` 非 docs diff | 每次 session 前运行；必须无输出 |
| Session 前 `S → audit` 非 docs diff | 每次 session 前运行；必须无输出 |
| Session 前 prompt hash 复核 | 每次 session 前运行；必须通过 |

当前操作版本层固定为 `G2`（annotated tag）→ `S`（whitelist/台账
commit）→ 唯一 audit commit。历史 `G`、G-era runs 与升级过程保留在
provenance 链中，但不得混入正式 whitelist。Audit commit 不自指记录自己的
hash；其身份由正式操作分支的 `HEAD`、固定 commit message 及 parent=`S`
共同核对。

若建立 G2 后发现代码缺陷，不得在 `G2 → S` 间直接修补。必须二选一并留档：保持 G2 完成实验并把缺陷写入 limitation；或修复后废止当前正式候选文档、建立新 generation tag 并重新生成全部九个文档。不得混用两个仪器版本。

### 1.3.1 正式 session 的离线配置与物理隔离

正式 session 使用以下本地配置；这是手册中的操作凭据，本次 S 文档落地不
修改本机 `.env`：

```dotenv
LLM_BACKEND=ollama
OLLAMA_MODEL=llama3.2:3b
LLM_STRICT_MODE=true
FREEZE_LABELS=true
LLM_TIMEOUT_SECONDS=60
LLM_TEMPERATURE=0
LLM_SEED=42
LLM_MAX_TOKENS=1024
```

Session 前必须从本地 `.env` 移除 Azure key，并停止 Ollama，形成云端凭据与
本地模型服务的双重物理隔离。完成隔离后不得再触发生成、LLM clustering、
LLM labelling 或 suggestion 路径；`FREEZE_LABELS=true` 的正式 session
只使用已经生成并列入 whitelist 的固定文档。参与者 move 只走既有
`/feedback/recluster`，该路径在 labels frozen 时不调用 labeller。若 session
工具或隔离方式将来需要代码改动，必须另立 instrument 版本，不能混入 S。

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
- 若文档只有一个 cluster，界面没有可表达“拆分成多个 cluster”的 move
  目标。Researcher 不提示判断，但要特别留意并在 think-aloud/field note
  中记录参与者自发表达的拆分意愿；这类口头观察不能伪装成 move 记录。
- 两个已知单簇正式文档为
  `P2_task1_batchB / 6a666d4f04fc296116b621af` 与
  `P3_task2_batchA / 6a666f0d5f60ce182f69ff12`。两者没有可用的 move
  目标；其 confirm 指标必须连同单簇背景解释，不能简称为完整“接受率”。
- 对细粒度、多簇文档，界面同样没有“把两个 cluster 合并”的独立动作。
  Researcher 只记录参与者自然说出的 merge 意愿或 navigation 负担，不主动
  追问、不把口头观察编码为 confirm/move。

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

### 2.4 Think-aloud 与观察笔记隔离

- 采用自然观察方案：固定记录参与者自发说出的 split、merge 与 navigation
  意愿；researcher 不主动追问这些判断。
- 观察笔记与 `clusterFeedback` 定量数据物理隔离，存放在独立的 session
  field-note 记录中，不写入 MongoDB，不伪装成 confirm、move 或 no-op。
- 定量分析只使用 whitelist 文档的 `clusterFeedback`；观察笔记只作质性
  上下文。二者在原始存储、导出文件和分析步骤中均保持分离。
- 本裁定不授权修改 session 工具。将来若要加入 split/merge 控件或结构化
  观察字段，必须建立新的 instrument 版本，不能作为 S 的补丁。

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
S 建立时已逐项核对上述名单；没有从 private generation ledger 发现新的
participant 身份。正式分析仍须先运行 `distinct("participant_id")`，不能把
本快照当作未来数据的自动许可。

### 4.4 开发与 smoke 文档排除名单

以下文档真实存在于 `documents` 与 `pipelineRuns`，但绝不进入正式 doc ID
whitelist，也绝不进入分析。生成冻结期先把每个 smoke/attempt 写入 ignored
private ledger；九个正式文档完成后在 S 中一次性回填本表，避免生成期间
产生 tracked docs 变更。正式分析开始前本表必须完成对账。

| Survey name | 用途 | doc_id（阶段 D 登记） |
| --- | --- | --- |
| `D_SMOKE_LLAMA_batchA` | Llama smoke attempt 1；编排失败，provider 未调用 | `6a64c2e83e0dbddf5447c741` |
| `D_SMOKE_LLAMA_batchA_attempt2` | G-era Llama 20 行 smoke；completed；G2 后排除 | `6a64c6bb3e0dbddf5447c757` |
| `P1_task1_batchA` | G-era formal attempt；assignment 失败 | `6a64c87f3e0dbddf5447c76f` |
| `P1_task1_batchA_attempt2` | G-era completed formal candidate；G2 后 superseded | `6a64e3a53e0dbddf5447c782` |
| `P2_task2_batchC` | G-era completed formal candidate；G2 后 superseded | `6a651c263e0dbddf5447c796` |
| `P3_task3_batchB` | G-era formal attempt；assignment 失败并触发 G2 | `6a651df93e0dbddf5447c7ad` |
| `D_SMOKE_G2_LLAMA_batchA` | G2 Llama smoke attempt 1；旧 Azure 监听进程造成 backend mismatch；run completed 但验收拒绝 | `6a660bdef041b5fef471e029` |
| `D_SMOKE_G2_LLAMA_batchA_attempt2` | 获批的环境恢复重试；G2 Llama smoke；completed | `6a66119a59652a872b0639b2` |
| `D_SMOKE_G2_QWEN_batchA` | G2 Qwen 20 行配置/provider/schema smoke；completed | `6a661d1ec2a3cea7e6de6028` |
| `D_SMOKE_G2_AZURE_batchA` | G2 Azure deployment/schema 20 行 smoke；completed | `6a661f814b63e7a3c45dd144` |
| `P1_task2_batchB` | 2026-07-16 历史开发文档；与未来 Azure 正式文档同名 | `6a58d2cd1d6d1e80c35ba564` |

所有分析脚本必须同时实施两道 document 门禁：

1. `doc_id` 必须位于第 1.1 节正式 whitelist；
2. `doc_id` 不得位于本节开发/smoke 排除名单。

两份名单未填满或发生交集时必须 fail closed，禁止运行正式分析。只依赖
survey name、participant 排除名单或其中任一 document 名单都不合格。

同名碰撞的具体审计案例为 `P1_task2_batchB`：历史开发 doc ID
`6a58d2cd1d6d1e80c35ba564` 必须始终被排除；未来 Azure 正式生成返回的新
doc ID 必须与它不同，且只有新 doc ID 可以进入正式 whitelist。任何按
survey name join、取第一条或取最新一条的做法都不合格。G2 的三个 Llama
survey name 也会与保留的 G-era attempt/candidate 名称碰撞；同样只能使用
G2 ingest 直接返回且 `code_version` 等于 G2 tag target 的新 doc/run。

## 5. 分析约定

### 5.1 Participant action 与分母

- 正式分析前必须先在 mongosh 运行：

  ```javascript
  db.clusterFeedback.distinct("participant_id")
  ```

  将结果与第 4.3 节排除名单及正式身份 `P1`、`P2`、`P3` 逐项对账。出现名单外身份即为漏登记：立即暂停分析、查明来源并完成登记或排除，不得静默忽略后继续分析。
- `clusterFeedback` 按 `participant_id` 精确匹配，不使用“排除 TEST 后全部保留”的宽松规则。
- 分析单位固定为 participant + doc + fragment。同一分析单位的有效记录按
  `{timestamp: -1, _id: -1}` 排序，取第一条作为 latest effective action。
- `confirm` 表示明确认可当前 placement；`move` 表示显式纠正。若先 confirm
  后 move，最终状态归入 move，但两条 provenance 均保留，不覆盖历史记录。
- 没有任何有效 feedback 的 eligible fragment 记为
  `no recorded decision (reject-or-unreviewed)`；不得自动推断为接受、拒绝或
  已审查。
- `eligible fragments` 定义为该正式 whitelist 文档在生成时通过 relevance
  并进入 Cluster Graph 的 kept fragments。分母按 participant + doc 固定，
  不是“至少留过一条 feedback 的片段数”。
- `confirm / eligible` 报告为确认覆盖率或认可率下界；`move / eligible`
  报告为显式纠正率；`no recorded decision / eligible` 作为剩余比例同时报告。
  禁止把 `confirm / eligible` 简称为完整“接受率”。
- 两个单簇文档 `6a666d4f04fc296116b621af` 与
  `6a666f0d5f60ce182f69ff12` 必须显式标注粒度背景：其 move 在结构上不可用，
  split 意愿只存在于物理隔离的 think-aloud/field note 中。

### 5.2 Document、run 与粒度门禁

- `pipelineRuns.doc_id` 与 `clusterFeedback.doc_id` 必须同为 BSON `ObjectId` 后再 join。
- 只有满足 `{status: "completed", finished_at: {$exists: true}}`、backend/model 与正式条件一致、`params.temperature=0`、`params.seed=42`、`params.max_tokens=1024`、`params.timeout_seconds=60`、`params.max_retries=0`、`params.schema_enforced=true`、`params.schema_version="stage_d_structured_output_v1"`、`params.schema_dynamic_cluster_id_enum=true`、schema transport 匹配 backend，且 `code_version` 精确等于 `generation-frozen-G2` tag target 的 run 才能进入实验。
- 遗留 `status: "running"` 的非当前 run 视为进程中断并作废；没有 `status` 字段的旧 P1 run 属开发数据，一律排除。
- 正式分析同时使用 participant 排除名单、正式 doc ID whitelist 与第 4.4 节开发/smoke doc ID 排除名单；必须执行“在 whitelist 且不在 smoke 排除名单”的 document 双门禁，不能只依赖 survey name。`P1_task2_batchB` 的历史/正式同名碰撞必须按两个不同 BSON `ObjectId` 处理，禁止按名称 join。
- 模型间 cluster 粒度、过滤数量和实际审查数量的差异保留为结果，不通过删除记录强行等量化。
- Smoke 只属于开发/配置证据，不进入 Results，也不用于估计正式文档的
  relevance 产出率。G2 正式粒度画像为 Qwen `1/1/2`、Azure `8/11/10`、
  Llama `6/7/15`；原始矩阵顺序与逐文档计数见生成记录。该差异只在参与者
  数据产生后结合任务背景解释，不据此重生成。

### 5.3 Retention coverage

九份正式文档全部满足 `input = kept + filtered`，第三桶为零。三个模型各处理
58 条输入；按模型的 observed retention 为 Llama `54/58 (93.1%)`、Qwen
`49/58 (84.5%)`、Azure Mistral `55/58 (94.8%)`。逐文档结果必须与汇总同时
呈现，因为 Qwen 的 9 条 filtered 中有 5 条来自单一文档
`P2_task1_batchB`。

同 batch 的输入内容和顺序均配平：

| Batch | Input | Multiset SHA-256 | Sequence SHA-256 |
| --- | ---: | --- | --- |
| A | 17 | `c415ea08c3871b1ff5b937c196797c04405cbed0f1fe4691a5142732d489e7b6` | `22a0547afaf9517d1be40b77d5d430309a07c09081742c8fcf2069c2faa37dee` |
| B | 21 | `eff5d47ad974aac74acf7dec839aba4dd4a3c78b66114e40761d9f39c4d151b3` | `127f865640dd78405638e3bd8dd79f566e4f37c22a20646a9081a3b02a92a3d1` |
| C | 20 | `a88a44acf6ea4f3c81c7670610451b50ec8ef5032b2f4910ff158714de807b6f` | `99183b4b35e28059ff4e0d31a043f8ebe6f4986a9c09bee44d5094cdfdda1d83` |

Multiset/sequence identity 使用规范化内容 hash，不比较独立 ingest 产生的
ObjectId。九份文档当前 Mongo natural traversal、ObjectId 插入顺序代理和
`row_num=1..N` 顺序一致。正式 run 未保存逐 fragment 调用顺序事件日志，
因此顺序结论属于强重建证据，而非独立历史日志证明。

Retention 不是质量或 accuracy 指标。Relevance filtering 是预期功能；没有
relevance ground truth 时，不得把较高或较低 retention 解释为更好、更差、
更激进或更保守。固定表述为：

> Observed retention differed across models; without relevance ground truth,
> retention cannot be interpreted as accuracy.

Qwen 的较低 observed retention 与 `1/1/2` 粒度可表述为
*consistent with* 同一 loss-of-discrimination 假设，但不得写成 effect、
因果关系或已验证机制。

### 5.4 资源画像

正式 generation wall-clock 只从九条冻结 `pipelineRuns` 的起止时间提取。
正文按秒取整并报告 mean + range：

| Model | 三次正式观察（秒） | Mean | Range |
| --- | --- | ---: | --- |
| Llama | 174, 210, 194 | 193 | 174–210 |
| Qwen | 172, 166, 156 | 165 | 156–172 |
| Azure Mistral | 65, 40, 49 | 52 | 40–65 |

这些是 observations，不是 benchmarks。毫秒精度只保留在证据 JSON。独立
instrumentation 中，同一 Batch C 的 Llama 运行约 132 秒，与正式观察相差
数十秒，证明环境负载/运行状态会产生实质波动。

Peak memory 不是九次冻结生成时同步采样，而是在相同配置与代码状态
`ddb5355972ca63df44edad184b11e30f420e4c62` 下、独立 `nie_pilot` 副本中的
separate instrumentation runs。RAM 是 AI + Ollama + `llama-server` 的
observed working-set；GPU 是 Windows WDDM 下 whole-system used memory，
不是 per-process VRAM。采样间隔约 0.9–1.0 秒，正文按 0.1 GiB 报告。

| Model | Separate run | Local-stack WS pre/peak | Whole-system GPU pre/peak |
| --- | ---: | ---: | ---: |
| Llama | 132 s | 0.6 / 3.1 GiB | 494 / 2781 MiB |
| Qwen | 93 s | 0.6 / 1.6 GiB | 489 / 2614 MiB |

Llama 在 4096 MiB GPU 上的 whole-system peak 约为 68%，且本地栈峰值约
3.1 GiB；允许的解释是“消费级硬件可运行，但余量有限”。该 Llama 测量已
排除活跃 `llama-server`/allocator 残留，但未通过重启清除 OS page cache，
因此其 RAM 数字在 post-reboot repeat 前标为 provisional。

跨后端时间必须附带限定：本地 wall-clock 包含本地 client/model-loading
行为；Azure wall-clock 包含网络往返和 GlobalStandard 服务端排队。两者不是
like-for-like，只能在各自 backend 内比较。

Azure 服务端 RAM/VRAM 对客户端不可见；这属于资源可观测性不对称，而不是
用本地 client memory 补值。Azure 实际成本仍待 portal usage/token 证据；
`< $10` 仅为预算上限，不得写成实测。如果本研究规模下实际成本很低，RQ1
不得主张本研究已证明本地方案更省钱；论证应区分隐私、外部依赖、per-call
计费和规模化/长期重复使用。

完整逐文档 retention、顺序证据、资源尝试台账、full SHA-256 与失败处置见
`docs/verification_records/retention_resource_order_audit.md`。

## 6. PILOT 隔离与正式文档只读规则

- 九个正式 whitelist 文档从 S 建立起到正式 session 结束均视为只读生成
  资产。PILOT 禁止直接打开或操作正式 `nie` 数据库中的九个 doc ID。
- `participant=PILOT` 只能隔离 `clusterFeedback.participant_id`，不能隔离
  recluster 的全局副作用。Recluster 会修改正式 fragment 的 `cluster_id`、
  cluster membership 与 centroid，因此不能靠 participant 标签保护正式文档。
- P2 的完整彩排必须使用独立 `nie_pilot` 数据库，或使用经过逐字段验证的
  专用副本文档。必须对 `documents`、`fragments` 与 `clusters` 的全部
  非易失字段逐字段比较；若复制需要重映射 ObjectId，还必须验证完整映射、
  fragment identity、cluster membership、label、centroid 及来源正式 doc ID。
  任何未验证字段或不一致都必须 fail closed。
- PILOT 的文档、feedback、观察笔记与导出永不进入正式 whitelist 或正式
  分析。正式 participant 排除与 document 双门禁仍同时生效。
- 本次 S 只冻结隔离规则，不制作副本、不启动 PILOT、不写入 MongoDB。
  `nie_pilot`/专用副本方案必须在 S 后另行审查批准。
- P2 是优先完整彩排顺序：Qwen 单簇
  `6a666d4f04fc296116b621af` → Llama 15 簇
  `6a662346b88c6db2d9915ac9` → Azure 8 簇
  `6a667375aaaa46976afdb5dc`。彩排副本用于演练从 split 意愿观察切换到
  merge/navigation 观察的 researcher 负担，不得触碰这三个正式 ID。

## 7. 已知边界与历史包装

- `react-client/src/api/dataFacade.ts::cluster_recordFeedback` 调用 `storage.recordClusterFeedback`，属于 api-server 历史路径。当前实验 UI 没有调用它；P1 中勿用勿删，避免误认成第二条正式 feedback 写入路径。
- P1 将 cosine suggestion 的 `SUGGEST_AT` 设为 `9999`，正式 session 不展示 suggestion cards。相关 accept/reject 代码保留但不属于当前参与者流程。
- Cluster Graph 刷新后不会自动恢复 doc ID，需重新输入；刷新属于需记录的 session 异常。
- `FREEZE_LABELS` 已实现并验证（commit `fd49542`，2026-07-19）。启用时，`/feedback/recluster` 仍记录 provenance、移动 fragment、更新簇成员与 centroid，但跳过运行时 `labeller`，并返回 `labels_frozen: true`。
- 启用 `FREEZE_LABELS` 时，`/cluster/run`、`/label/clusters`、`/suggest/save` 在任何数据库写入前返回 `423 Locked` 和 `labels_frozen`；`/llm-cluster/run` 不受 freeze 阻塞，其生成结果进入正式实验仍由 strict mode 与正式 doc ID whitelist 共同门禁。
- Strict experiment mode 已实现并验证（commit `f7421cf`，2026-07-18）；正式文档生成必须使用该模式，使 LLM 请求失败或无效响应显式终止 run，不写入 heuristic fallback 聚类结果。
- G-era assignment prompt 已于 commit `f7421cf` 修订，明确列出合法整数 cluster ID。两个不同正式数据集上仍出现列表外 ID，按预注册常备触发器升级 G2。G2 为三个模型统一施加 `stage_d_structured_output_v1`：relevance、initial 与 assignment 走共享 schema；assignment 合法 ID enum 按调用动态生成；本地 strict 校验不撤。Strict 本地闸直接解析原始 JSON、拒绝 Markdown fence，并拒绝字符串/数组形式的 `cluster_id`。G-era completed 文档均为 superseded。完整边界与台账见 `docs/verification_records/g2_instrument_upgrade.md`。
- G→G2 只作为生成仪器可靠性与 provenance 流程证据，不是模型质量结果。
  G 的三个 Llama 首次正式尝试为 `1/3 completed`，两个失败均为非法
  cluster ID；G2 Llama 为 `3/3 completed`，G2 全矩阵为 `9/9 completed`。
  未 embed 的 G smoke 是 API 编排事故，provider 未调用，不计作 schema
  失败。G/G2 之间的粒度差异属于仪器边界诊断，不与正式 participant
  Results 混合。
- Sampling 参数已实现并验证（commit `2567fc3`，2026-07-19；验证记录 `docs/verification_records/sampling_freeze.md`）。三个模型统一请求 `temperature=0`、`seed=42`、`max_tokens=1024` 与 60 秒 timeout，SDK 隐藏重试保持为零。G-era 相同输入、模型和请求参数的两个运行产生了不同 assignment decision behavior；固定 seed 未保证决策结果一致。原始输出未保存并逐位比较，因此不得上升为“输出不具备逐位复现性”。Prompt、schema 与 sampling 参数共同构成冻结的 G2 实验仪器；正式生成开始后若必须修改任一项，旧仪器下的全部正式候选 run 均作废并重新生成，且所有尝试记录保留。
- 本地模型选择已验证并留档于 `docs/verification_records/local_model_selection.md`。候选 `qwen2.5:7b` 在唯一一次 20 行门禁运行的首个 relevance 调用中触发 `ReadTimeout`，strict run 失败且零簇落库；未重试、未放宽 60 秒共同 timeout。预定义回退 `qwen2.5:3b` 在相同配置下唯一一次完成，因此最终本地模型固定为 `llama3.2:3b + qwen2.5:3b`。
- 阶段 D 按模型分组生成：Llama 三个 → Qwen 三个 → Azure 三个。每次只切换一次 `.env` 并完整重启，先做非正式 smoke 并核对 `pipelineRuns`，再生成该模型的三个正式文档。完整顺序、输入 manifest、失败处理和九文档台账见 `docs/stage_d_generation_runbook.md`。
- Azure/Mistral backend 已通过共享 provider 接入并完成技术验证（共享层 commit `936fdda`，Azure 实现 commit `434efe1`，验证记录 `docs/verification_records/azure_mistral.md`）。已验证 `Mistral-Large-3` deployment version `1`、`GlobalStandard`、60 秒 timeout、零隐藏重试、active-backend-only 配置校验、Ollama 离线隔离、缺 key fail-loud 及 content-filter 失败语义。
- 本研究三次正式 Azure run 未观察到 `CONTENT_FILTERED`。该陈述只覆盖这
  三次已记录运行，不得外推为 Azure、Mistral、该 deployment 或未来请求
  不会触发内容过滤。
- 性健康 smoke test 仅运行一次并以 `status: "completed"` 终局结束（结果 commit `da5a49a`），未触发 content filter。该单行测试只覆盖 relevance 与首簇创建分支，不能视为多片段 assignment 或正式批次验证；正式生成仍受最终模型选择、clean worktree 与正式 doc ID whitelist 门禁。

## 8. 变更记录

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
| 2026-07-25 | 记录首次 Llama smoke 的 `NO_EMBEDDED_FRAGMENTS` 编排失败；固定底层 API 的 `ingest → embed → LLM` 全量计数门禁，并登记历史 `P1_task2_batchB` 同名开发 doc ID 与分析排除规则。 |
| 2026-07-26 | 记录 G-era 重复 assignment 协议违规、G2 structured-output 仪器、G-era superseded/排除文档、G2 provenance 验收字段及 `G2 → S → audit` 版本结构。 |
| 2026-07-26 | 回填 G2 9/9 whitelist、全部 generation/smoke 排除记录、eligible-fragment 指标、单簇解释、think-aloud 物理隔离及 PILOT 数据库隔离铁律；建立 operational S 文档。 |
| 2026-07-29 | 冻结正式 session checkout 为 `ddb5355972ca63df44edad184b11e30f420e4c62`，排除未重新彩排的 readability 候选；补充 fragment-level retention、输入内容/顺序配平、资源画像、精度限制、Azure 可观测性与待办。 |
