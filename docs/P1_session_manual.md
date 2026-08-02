# P1 实验运行手册

本手册用于 P1 provenance 实验的彩排与正式 session。手册与代码在同一仓库、同一分支下版本控制；任何影响 session 行为、记录字段或分析裁定的代码变更，都必须同步更新本手册。

ERGO 115447：导师已批准；researcher 于 2026-08-01 目视确认 ERGO/FEC 门户状态显示
`Approved`。门户未提供独立 PDF 批准函，因此不得虚构 PDF 凭据或把 2026-08-01
写成批准签发日期；该日期只表示状态的观察日期。正式 session 使用门户状态的
日期化截图/打印件（若门户允许）或日期化 researcher 核对记录作为批准状态凭据。

## 1. Session 前检查单

### 1.1 实验准入

- 已获得 FEC 最终批准；门户状态显示 `Approved`。记录核对日期与核对人；无独立
  PDF 批准函时写明“portal status evidence”，不得把申请表或指导文件冒充批准函。
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

`OLLAMA_MODEL=llama3.2:3b` 只用于防止配置缺省或漂移；正式 session **不调用
模型**。Session 期间 Ollama 必须停止且 `11434` 无监听。这个说明同时写入本地
`.env` 的注释，但 `.env` 本身不得提交、打印或进入证据包。

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

### 1.7 固定顺序、45 分钟上限与计时

- 三份正式文档的审查段总上限为 **45 分钟**。计时从第一份文档完成加载、
  researcher 宣布可以开始审查时开始；第三份文档结束或总计时达到 45 分钟时
  结束，以先发生者为准。Consent、录音设置和结束检查不计入这 45 分钟。
- 文档顺序使用第 1.1 节正式矩阵中 participant 的 task1 → task2 → task3
  顺序；该顺序是预先固定的 Latin-square 分配，**session 内不再随机化**，
  也不因前一份文档的粒度、完成度或参与者反应而调换。
- Researcher 记录审查段总开始/结束时间，并为每份文档分别记录
  `doc_id`、开始时间与结束时间；时间使用带时区的 ISO 8601。
- 使用外部可见的 `45:00` 倒计时器执行停止规则；计时器静音、只对 researcher
  可见，参与者不可见，以免诱发赶工。不得用墙钟估算或事后推算 45 分钟。
- 达到 45 分钟时立即停止，不要求完成当前卡片或当前文档，不补时、不加速
  提示，也不在 session 后补做。尚无有效 feedback 的 eligible fragments
  仍按第 5.1 节记为 `no recorded decision (reject-or-unreviewed)`。

### 1.8 固定 session 台本

以下结构与措辞在 P1、P2、P3 三场保持一致。模型名称、本地/云端身份和任何暗示
条件差异的说明均不得出现在 participant briefing 中；参与者只看到 Batch A/B/C。

1. **接待与知情同意（不计入 45 分钟）**：全部内容按获批 ERGO/PIS/consent
   文件执行。录音只能在 consent 完成后开始；拒绝录音时能否继续参加按获批文件
   执行，不临场决定。Consent 后先录制约 10 秒测试音频，停止并回放确认可听，
   再开始正式录音；每次正式文档切换时仅目视确认录音仍在运行，不中断任务。
2. **统一 briefing（不计入 45 分钟）**：三场逐字使用以下六点：
   - AI 已把访谈内容初步分成若干组；请逐条查看，判断 fragment 当前所在组是否合适。
   - 这是对 **first-pass clustering placement** 的检查，不是要求完成完整的定性
     coding、主题命名或主题分析。`Confirm` 只表示认可 fragment 当前所在位置，
     不表示该组是唯一正确解释。
   - 认可当前位置时点击 `Confirm`；认为应该换组时拖到已有的目标组。若没有合适
     的目标组，可以自然说出这一点。
   - 三份文档共用一个 45 分钟计时段；看不完是正常的，不必赶。
   - 请把心里自然想到的内容说出来。Researcher 不就 split、merge、navigation
     或判断理由追加追问。
   - 逐字界面提示：**“本研究关闭了界面的部分功能。你可能会看到一个提到
     AI suggestions 的进度提示，请忽略它，它不会启用。”**
3. **熟悉界面（不计入 45 分钟）**：仅使用下表中该 participant 专属的 demo
   文档各演示一次 confirm 与拖动；三份 demo 均为 20 fragments、2 clusters、
   零初始 feedback 的等价副本，不得交叉使用、复用 smoke 文档或打开九份正式
   whitelist 文档。

   | Formal session | Demo participant 参数与 badge | Demo doc ID | 初始簇数 |
   | --- | --- | --- | ---: |
   | P1 | `DEMO_P1` / `Participant: DEMO_P1` | `6a6f8bd596018eb206d7ead2` | 2 |
   | P2 | `DEMO_P2` / `Participant: DEMO_P2` | `6a6f8bd696018eb206d7eae7` | 2 |
   | P3 | `DEMO_P3` / `Participant: DEMO_P3` | `6a6f8bd696018eb206d7eafc` | 2 |

   Demo 完成后必须把 URL participant 改回正式 `P1`/`P2`/`P3`，重新核对 badge，
   再用精确 doc ID 加载第一份正式文档。Demo feedback 只属于对应 `DEMO_Px`
   身份和 demo doc，永不进入正式分析。三份 ingest、等价性和正式九文档零变化
   证据见 `docs/verification_records/formal_session_demo_freeze.md`。
4. **计时任务（45 分钟）**：第一份正式文档加载完成且 researcher 宣布开始时
   计时。逐文档记录起止时间；参与者自行决定何时进入下一份。45 分钟到立即停止。
5. **统一结束问题（不计入 45 分钟）**：三场均逐字只问一次：
   **“整体感受如何？”** Researcher 只记录、不追问；不得询问哪份最好、要求
   逐文档比较或透露模型身份。

## 2. Session 中现场处理

开始参与者任务前，researcher 开始录音，并口头确认 participant 已阅读 information sheet、已签署 consent form 且同意本次录音。

### 2.1 参与者操作

- 认可当前 placement：点击单卡 `Confirm`。
- 不认可当前 placement：将卡拖到参与者认为正确的 cluster。
- confirm 与后续 move 都保留为独立 provenance 记录，不修改或删除旧记录。
- 当前裁定以该 participant 对该 fragment 的最后动作为准。
- 卡片在当前所属 cluster 内拿起并放回属于 no-op，不产生 move 记录。
- 若文档只有一个 cluster，界面没有可表达“拆分成多个 cluster”的 move
  目标。Researcher 不提示判断，但要特别留意参与者自发表达的拆分意愿，现场
  仅记录音时间点与定位关键词，准确原话取自录音转录；这类口头观察不能伪装成
  move 记录。
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
- 只要发言涉及当前分组结构、簇间关系、卡片移动、阅读或界面操作，无论表达
  是否明确，现场都必须记录录音时间点与三至五个定位关键词；不得因 researcher
  当场认为“还不算 observed”而省略，也不得在现场写近似原话。明确性只在三场
  结束后的回听编码阶段判断，含糊内容可编码为 `unclear`。
- 观察笔记与 `clusterFeedback` 定量数据物理隔离，存放在独立的 session
  field-note 记录中，不写入 MongoDB，不伪装成 confirm、move 或 no-op。
- 观察笔记只作为录音回听的定位工具，不是独立分析材料，不在论文中引用。
  质性编码与汇总使用已批准录音的转录和录音时间点；定量分析只使用 whitelist
  文档的 `clusterFeedback`。三者在原始存储、导出文件和分析步骤中均保持分离。
- 正式 session 观察笔记只使用 `P1`/`P2`/`P3` 身份，不记录姓名、邮箱、签名或
  其他可识别信息；其存储与销毁遵循 DPA Plan，与其他研究数据同等处理。
- 本裁定不授权修改 session 工具。将来若要加入 split/merge 控件或结构化
  观察字段，必须建立新的 instrument 版本，不能作为 S 的补丁。

#### 2.4.1 质性观察记录规格

记录单位是 `participant × document`，不是 participant 总体，也不只记录第一份
文档。Split/merge 属于 RQ2 粒度背景；navigation 属于 workload/界面背景，三者
不得合成同一量表或并列解释为同一构念。

编码值固定为：

- `observed`：参与者以言语表达对当前分组粒度的不满、明确的结构改动意愿，或
  明确的导航/界面负担。
- `no spontaneous expression recorded`：录音转录中没有符合标准的自发表达；
  它**不表示**参与者没有这种感受。
- `unclear`：评论含糊、语境不足、录音不清或无法可靠归类；必须保留录音时间点
  和转录中的原话。
- `n/a (structurally unavailable)`：只允许用于 `cluster_count = 1` 文档的 merge
  字段，由预填表自动给出，不由 researcher 临场选择。Split 不设簇数阈值，
  split 与 navigation 均不得记 `n/a`。

`observed` 的边界固定如下：

- “这两个应该分开”等明确拆分意愿记 split `observed`。
- 在当前分组语境下询问能否新建一组，且表达了把内容分开的意愿，记 split
  `observed`；教程中的一般功能询问不计。
- “应该把这两组并在一起”等明确合并意愿记 merge `observed`。
- “这个组有点杂”等未明确表达拆分或结构改动的评论记 `unclear`，不得追问澄清。
- 纯 move、停顿、反复浏览或其他无言语行为不构成质性 `observed`；行为数据只由
  `clusterFeedback` 记录。
- 明确说出“簇太多、找不到目标、移动/阅读困难”等界面导航负担时，才记
  navigation `observed`；仅耗时较长不得据此推断。

每条 `observed` 或 `unclear` 须附：participant、document/task、cluster count、
录音时间点、转录中的原话、必要的最小语境。原话一律取自录音转录，不取自现场
手记。现场手记只记录时间点与定位关键词，其作用是让回听阶段能够定位。

采用两阶段编码：

1. **现场捕获阶段**：仅标“有相关发言”、录音时间点与三至五个定位关键词；
   不记近似原话、不做三值判定。凡涉及分组结构或界面操作的发言，无论是否明确，
   一律记时间点；宁可多记，不得在现场筛掉可能成为 `unclear` 的内容。技术故障与
   reflexivity 可另栏记录，但不作为参与者原话或独立质性分析材料。
2. **延迟编码阶段**：三场全部结束后一次性回听，才依据上述冻结规则为每个
   document 填入 split、merge、navigation 三值（或结构性 `n/a`）；原话取自
   转录，并同时保留录音时间点与 cluster count。不回写 MongoDB，不改变原始
   录音或观察笔记。

质性汇总只陈述具体观察，例如：

> Navigation difficulty was spontaneously mentioned during two document
> reviews (P1/task2, 11 clusters; P3/task1, 10 clusters).

必须列出具体 participant/task 和簇数；不报告百分比、模型间比较、显著性检验或
“navigation rate”。`no spontaneous expression recorded` 与结构性 `n/a` 不进入
同一个分母。

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
- 记录本场原始失败条目数 `N`；`N` 的作用和非零处置按第 5.2 节执行。
- 将审查段总开始/结束时间及三份文档各自的开始/结束时间归入本场记录。
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
- 固定界面演示身份：`DEMO_P1`、`DEMO_P2`、`DEMO_P3`；各自只允许操作第 1.8 节
  指定的专属 demo doc，不得用于正式 whitelist 文档。
- Participant ID 按 `trim + uppercase` 规范化，并进行精确匹配。
- 缺失或空身份进入 `TEST` 隔离桶。

### 4.3 开发与测试身份排除名单

正式分析一律排除：

```text
TEST
P_TEST
P_OTHER
PILOT
DEMO_P1
DEMO_P2
DEMO_P3
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

### 4.4 开发、smoke 与 demo 文档排除名单

以下条目真实存在于 `documents`；生成/smoke 条目还具有 `pipelineRuns`，而专用
demo 文档按设计没有 generation run。它们绝不进入正式 doc ID whitelist，也
绝不进入分析。生成冻结期先把每个 smoke/attempt 写入 ignored
private ledger；九个正式文档完成后在 S 中一次性回填本表，避免生成期间
产生 tracked docs 变更。正式分析开始前本表必须完成对账。

| Survey name | 用途 | doc_id（登记） |
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
| `R5_OLLAMA_SAMPLING_batchA` | 历史 sampling 诊断文档；只作为 demo 初始投影来源，不向正式 participant 打开 | `6a5cfca621fc0a91ba66e692` |
| `D_SESSION_DEMO_P1` | P1 专属界面演示副本；20 fragments、2 clusters；永不分析 | `6a6f8bd596018eb206d7ead2` |
| `D_SESSION_DEMO_P2` | P2 专属界面演示副本；20 fragments、2 clusters；永不分析 | `6a6f8bd696018eb206d7eae7` |
| `D_SESSION_DEMO_P3` | P3 专属界面演示副本；20 fragments、2 clusters；永不分析 | `6a6f8bd696018eb206d7eafc` |

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
  split 意愿只从物理隔离的 think-aloud 录音转录中编码；观察笔记只用于定位。

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

#### 5.2.1 失败日志与 integrity figure

- `nieFeedbackProvenanceErrors` 原始导出是“浏览器已观察到 feedback 请求
  失败”的权威记录；MongoDB 是“已成功持久化 action”的权威记录。两者职责
  不互相替代，不能仅因数据库中没有 action 就把失败日志解释为没有发生失败。
- `N` 固定定义为本场 session 原始错误日志中，participant 与正式身份一致、
  `doc_id` 属于该 participant 三份 whitelist 文档、且 action 为
  `confirm` 或 `move` 的条目数。`N` 是 integrity figure，不去重、不根据
  HTTP status 或后续数据库状态删减；按 participant 报告，并汇总报告总数。
- `N=0` 只允许表述为“没有浏览器观察到的 feedback 提交失败”，不能证明
  系统不存在未观测故障。`N>0` 时不得静默重试、删除或把失败 action 改记为
  成功；保留原始日志，逐条与 MongoDB、现场笔记和时间戳对账。
- 对账后，只有 MongoDB 中有效持久化的 action 进入 confirm/move 计算。
  未成功持久化的失败 action 不进入分子；若该 fragment 没有其他有效 action，
  它保留为 `no recorded decision`。报告 `N`、失败类型、受影响文档/fragment
  数及处置。若下列一致性检查任一失败，暂停该 participant-document 的定量
  分析并单独裁定；不得事后修库来制造通过。

现场推进只按以下四类事件裁定；`N` 与工具/执行故障不得混为一类：

| 事件 | 第一场前冻结的处理 |
| --- | --- |
| `integrity_N > 0`，但脚本正常、数据库/participant/doc 身份正确 | 保存原始日志并逐条对账；按上述预注册规则报告和调整指标，**不因 N 非零单独停掉后续 participant**。 |
| 完整性脚本自身异常、未生成可信输出或退出码非零 | 停线，不开始下一名 participant；保留输出并核查工具或适用检查的 FAIL。 |
| 数据库、正式 participant、whitelist doc/run 身份不匹配 | 立即停线；隔离受影响 participant-document，等待单独裁定，不删除或自动宣布整场有效/无效。 |
| 本应适用的检查返回 `NA` | 停线核查作用域；但某文档没有任何 move 时，检查 5/6 返回 `NA` 是预注册的正常结果，不触发停线。 |

`overall_status` 只汇总六项检查的 PASS/FAIL，不含 `integrity_N`；因此不得把
“`overall_status=PASS` 且 `N=0`”写成继续下一场的联合门槛。

#### 5.2.2 六项一致性检查

正式分析前按 participant-document 运行并保存以下六项 PASS/FAIL/NA：

1. **Whitelist/run 身份：**doc 精确位于九文档 whitelist，且唯一批准的
   `pipelineRuns` 为 completed G2 run；model、batch、params 与 run ID
   均匹配。
2. **Participant 与 eligible 范围：**feedback participant 精确为该场
   `P1`/`P2`/`P3`，doc 属于其固定矩阵；每个 feedback fragment 属于该 doc
   的 eligible fragment 集，不混入 filtered、PILOT、TEST 或开发记录。
3. **Action 与引用完整性：**正式定量 action 只含 `confirm`/`move`；所有
   doc、fragment、from/to cluster 引用存在且属于同一正式文档；move 的
   from/to 不相同。
4. **Latest-state 与算术闭合：**按 `{timestamp:-1,_id:-1}` 取最后有效
   action 后，`confirm + move + no recorded decision = eligible`，三个桶
   互斥；事件总数不得小于有记录的 distinct fragment 数。
5. **Move 事件链连续性：**仅对至少有一条有效 move 的 fragment 检查。按
   `{timestamp:1,_id:1}` 排序后，首条 move 的 `from_cluster_id` 是该
   participant 操作前的 assignment；后续每条 move 的 from 必须等于前一条
   move 的 to。没有 move 的 confirm-only 或未审查 fragment 记为 `NA`，
   不能因不适用而判 FAIL。
6. **Move 后数据库投影：**仅对发生过 move 的 fragment 及其受影响 clusters
   检查。fragment 当前 `cluster_id`/`feedback_cluster_id`、最后一条 move
   的 `to_cluster_id` 与 cluster `fragment_ids` membership 必须一致，且
   该 fragment 只属于一个当前 cluster。未受 move 影响的 fragment/clusters
   不属于本项覆盖范围；本项不声称验证整个数据库或模型输出质量。

检查 5/6 是针对 recluster 副作用与事件链的完整性门禁，不是参与者判断或
cluster 质量指标。任一适用检查为 FAIL 时，保存原始证据并暂停分析；不得把
FAIL 改记为 `NA`，也不得用清理数据的方式使检查通过。

版本化只读实现位于
`docs/verification_tools/formal_session_integrity.py`。脚本把 browser 原始失败
日志的 integrity `N` 与六项检查、final confirm/move/no-recorded-decision 在
同一次运行中生成；分析表不得手工填写，也不得先看指标后补算 `N`。脚本只输出
ID、计数与 PASS/FAIL/NA，不读取或输出 fragment 文本、HTML、embedding、
research question 或密钥。正式运行必须提供未经编辑的浏览器日志文件；PILOT
门禁可用其已保存的原始 `null` 证据。

第一场前的 `nie_pilot` 实跑已于 2026-08-01 完成：三份 P2 彩排文档的检查
1–4 均为 PASS；无 move 的单簇 task1 在检查 5/6 为预期 `NA`，其余两份文档的
检查 5/6 均为 PASS；integrity `N=0`。脚本、完整 hash、逐项结果和环境尝试台账见
`docs/verification_records/formal_session_integrity_pilot_gate.md`。

分析表中的 `final confirm` / `final move` 是每个 fragment 依
`{timestamp:-1,_id:-1}` 得到的裁定终态，不是原始事件数。若同一 fragment
先 confirm 后 move，终态归 move，但两条原始 provenance 记录均保留。

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
instrumentation 中，同一 Batch C 的两次有效 Llama 运行约为 132 与 123 秒，
与正式观察相差数十秒，证明环境负载/运行状态会产生实质波动。

Peak memory 不是九次冻结生成时同步采样，而是在相同配置与代码状态
`ddb5355972ca63df44edad184b11e30f420e4c62` 下、独立 `nie_pilot` 副本中的
separate instrumentation runs。RAM 是 AI + Ollama + `llama-server` 的
observed working-set；GPU 是 Windows WDDM 下 whole-system used memory，
不是 per-process VRAM。采样间隔约 0.9–1.0 秒，正文按 0.1 GiB 报告。

| Model | Separate runs | Local-stack WS peaks | Whole-system GPU allocation deltas |
| --- | --- | --- | --- |
| Llama | 132, 123 s | 3.1, 3.1 GiB | 2287, 2302 MiB |
| Qwen | 93, 90 s | 1.6, 1.6 GiB | 2125, 2142 MiB |

2026-07-30 资源更新：post-reboot Llama repeat 与先前 process-clean run 的
local-stack working-set peak 只相差 0.0225%，GPU allocation delta 只相差
15 MiB。因此 3.1 GiB 已由 provisional 升为 confirmed separate-instrumentation
observation；采用的 post-reboot wall-clock 为 123 秒，whole-system GPU peak
为 2730 MiB，约占 4096 MiB 的 67%。允许的解释是“消费级硬件可运行，但余量
有限”；它仍不是九次冻结生成期间的同步测量，也不是 benchmark。

同日 Qwen post-reboot repeat 与先前 process-clean run 的 local-stack
working-set peak 相差 0.0507%，GPU allocation delta 相差 17 MiB，
wall-clock 为 90 与 93 秒。两模型现均有两次有效独立观测；Llama/Qwen
host WS peak 均值比为 1.931，但**差异原因没有被分离**，不得归因于模型文件
大小、量化格式、卸载切分或 buffer 分配。Ollama runtime 细节只作描述，
不能写成因果解释；硬件可运行性的主证据使用 GPU 占用/余量，host WS 只说明
本机系统 RAM 下的实际 fit。

Azure 实际成本仍不可用：当前 researcher account 无权查看或导出 Portal
usage、token 或 billing 证据。这不表示成本为零，也不得用估算值代替缺失的
Portal 证据。

跨后端时间必须附带限定：本地 wall-clock 包含本地 client/model-loading
行为；Azure wall-clock 包含网络往返和 GlobalStandard 服务端排队。两者不是
like-for-like，只能在各自 backend 内比较。

Azure 服务端 RAM/VRAM 对客户端不可见；这属于资源可观测性不对称，而不是
用本地 client memory 补值。当前 researcher account 无权查看或导出 portal
usage/token/billing，因此 Azure 实际成本记为 unavailable，而不是零；
`< $10` 仅为预算上限，不得写成实测，也不得以 fragment 数估算替代。如果
未来取得证据且本研究规模下实际成本很低，RQ1 不得主张本研究已证明本地方案
更省钱；论证应区分隐私、外部依赖、per-call 计费和规模化/长期重复使用。

完整逐文档 retention、顺序证据、资源尝试台账、full SHA-256 与失败处置见
`docs/verification_records/retention_resource_order_audit.md`。

### 5.5 Coding 与 clustering 构念边界

本研究评估的是 **first-pass clustering assistance**：模型先为 fragments
提供候选分组与 placement，参与者再审查这些 placement。它不是完整 qualitative
coding、主题命名/解释或 reflexive thematic analysis 的替代。

`confirm` 只表示参与者在该时刻明确认可“该 fragment 当前位于这个 cluster”
这一 placement。它不表示参与者认可整个模型、cluster label、主题解释、
relevance 判定或完整 coding accuracy。`move` 只表示参与者把 fragment
显式纠正到另一个现有 cluster；界面没有独立 split、merge 或创建新 code/theme
的动作。无记录仍是 `no recorded decision (reject-or-unreviewed)`。

因此 Results 只能把 confirm/move 指标解释为候选 clustering placement 的
确认覆盖率下界与显式纠正率；不得把它们表述为完整接受率、编码质量、主题
有效性或模型 accuracy。稳定编号的预注册表述见
`docs/verification_records/formal_session_preregistration.md` 第 §12 节。

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
| 2026-07-30 | 在任何正式 session 开始前预注册：浏览器失败日志与 `N` integrity figure 的非零处置、六项一致性检查及第 5/6 项的 move-only 作用域、first-pass clustering assistance 构念边界、固定顺序与 45 分钟停止/逐文档计时规则。 |
| 2026-07-30 | 在同一固定代码、20-input Batch C、零预加载模型与冻结参数下完成 Qwen post-reboot repeat；Llama/Qwen 各保留两次有效资源观测，并冻结“只报观察值、差异原因未分离”的解释边界。 |
| 2026-08-01 | 在第一场正式 session 前记录 ERGO/FEC 门户 `Approved` 状态及无独立 PDF 批准函的证据边界；固定六点 briefing、统一结束问题、participant×document 两阶段质性观察编码、结构性 merge `n/a`、三张空白现场记录表和只读六项一致性检查工具。参与者仪器仍固定为 `ddb5355972ca63df44edad184b11e30f420e4c62`。 |
| 2026-08-02 | 在第一场正式 session 前完成最后一次 docs-only 协议冻结：澄清 `N>0` 不单独停线及四类事件处置；固定外部 45 分钟计时、录音回放/存活检查、含糊发言全量现场捕获，以及 P1/P2/P3 三份等价双簇 demo 文档、`DEMO_Px` 身份和双重分析排除。参与者代码端点仍未改变。 |
| 2026-08-02 | 在第一场正式 session 前依据 ERGO 115447 覆盖核实另立修订：观察笔记收紧为录音定位工具，只记录音时间点与 3–5 个关键词；准确原话和质性编码依据改为已批准录音的转录。三值、判定、汇总及分析口径不变；父提交 `0044d24ba8575e9e3216c177f50110d2a422d149` 未 amend。 |
