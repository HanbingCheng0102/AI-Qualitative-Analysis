# 阶段 D：9 个正式文档生成手册

本手册是阶段 D 的唯一操作清单。它只记录已裁定的实验条件。第 2 节
source manifest 已在建立 `G` 前定稿。`G` 运行暴露的重复 assignment
协议违规按预注册触发器升级为结构化输出仪器；当前正式生成只允许使用
第 4 节定义的 `G2`。第 8 节生成台账与第 9 节 `S` 凭据属于生成后
docs-only 回填项；它们不构成自指式的生成前门禁。正式源材料和派生 CSV
只保存在本机，不得加入 Git。

## 1. 当前裁定

### 1.1 三个正式模型

| 角色 | Backend | 精确模型标识 | 版本凭据 |
| --- | --- | --- | --- |
| Local 1 | `ollama` | `llama3.2:3b` | digest `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72` |
| Local 2 | `ollama` | `qwen2.5:3b` | digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b` |
| Cloud benchmark | `azure` | `Mistral-Large-3` | version `1`; deployment type `GlobalStandard` |

`qwen2.5:7b` 不进入正式矩阵。它在本机唯一一次 20 行门禁运行的首个
relevance 调用中触发 60 秒 `ReadTimeout`；未重试、未改变共同 timeout。
完整证据见 `docs/verification_records/local_model_selection.md`。

### 1.2 冻结参数

```text
LLM_STRICT_MODE=true
FREEZE_LABELS=true
LLM_TIMEOUT_SECONDS=60
LLM_TEMPERATURE=0
LLM_SEED=42
LLM_MAX_TOKENS=1024
SDK max_retries=0
```

G-era assignment prompt 以 commit `f7421cf` 为边界。G2 只把
existing-assignment 输出包装成固定 decision envelope，其 byte hash 为
`992487fd59b21235eea7cc96ea6d539b4ff06706e22fab3208afd6862093664f`；
relevance、initial-assignment 与 labelling prompt 的 G-era hash 保持不变。
G2 的 prompt/instrument 实现边界 commit 为
`697bece97573a3f3ee616cd8dce2f17e8f400eea`。三个模型必须使用同一 prompt、
research question、CSV 字节内容、sampling 参数及
`stage_d_structured_output_v1` schema 仪器。完整双时代 hash 表见
`docs/verification_records/g2_instrument_upgrade.md`。

## 2. 正式输入 Manifest（生成前必须填满）

受限材料建议放在已被 `.gitignore` 覆盖的
`test-data/private/formal/`。每个 Batch 只保留一个正式 CSV；三个模型
重复使用同一文件，不为不同模型另存内容副本。

| Batch | 本地 CSV 绝对路径 | 主题/来源范围 | 行数 | Research question（逐字一致） | SHA-256 |
| --- | --- | --- | --- | --- | --- |
| A | `D:\6003\thematic_clusters_git\test-data\private\formal\batch_A.csv` | COMP2300 sexual-health transcript P1；只含 participant answers，排除 interviewer prompts 与 demographics | 17 | `factors influencing access to and experience of sexual-health services` | `d631c56d573537057a8005ac26d94bd799b414fff30695b8decf85f0182972ea` |
| B | `D:\6003\thematic_clusters_git\test-data\private\formal\batch_B.csv` | COMP2300 sexual-health transcript P2；只含 participant answers，排除 interviewer prompts 与 demographics | 21 | `factors influencing access to and experience of sexual-health services` | `58d8b85f1c4f1442aa3800673ab89a3ef3998b3ecc51d295636eec96dfeb327c` |
| C | `D:\6003\thematic_clusters_git\test-data\private\formal\batch_C.csv` | COMP2300 sexual-health transcript P3；只含 participant answers，排除 interviewer prompts 与 demographics | 20 | `factors influencing access to and experience of sexual-health services` | `3d6d2032e244b1031ad32426a5880c059aa4312f9775225e766c77eab62f918e` |

三份 CSV 的列结构均为 `respondent_id,Experience`；已按 Survey Ingestion 的
列预览逻辑确认，均只显示非 metadata 列 `Experience`。后端 ingestion 解析得到的
fragment 数分别为 17、21、20，与 manifest 行数一致。

计算哈希：

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath "CSV_ABSOLUTE_PATH"
```

Manifest 验收条件：

- 三行所有字段均已填写。
- CSV 不被 `git status --short` 列出，且不在 `git ls-files` 中。
- 每个 Batch 的列结构已在 Survey Ingestion 预览中确认。
- 同一 Batch 的三个模型运行使用完全相同的 SHA-256。
- Research question 在第一次正式运行前固定；之后不得修改措辞、标点或大小写。
- 不在 Git、日志或验证记录中粘贴受限原文。

## 3. 正交拉丁方与盲测密钥

以下矩阵已批准。它覆盖全部九个 `Batch × Model` 组合各一次；每位参与者
见到三个不同 Batch 和三个不同模型，且 Batch 与模型在 task1/2/3 的位置
各出现一次。

| 生成块 | 正式 survey name | Participant | Task | Batch | 真实模型 |
| --- | --- | --- | --- | --- | --- |
| Llama | `P1_task1_batchA` | P1 | 1 | A | `llama3.2:3b` |
| Llama | `P2_task2_batchC` | P2 | 2 | C | `llama3.2:3b` |
| Llama | `P3_task3_batchB` | P3 | 3 | B | `llama3.2:3b` |
| Qwen | `P1_task3_batchC` | P1 | 3 | C | `qwen2.5:3b` |
| Qwen | `P2_task1_batchB` | P2 | 1 | B | `qwen2.5:3b` |
| Qwen | `P3_task2_batchA` | P3 | 2 | A | `qwen2.5:3b` |
| Azure | `P1_task2_batchB` | P1 | 2 | B | `Mistral-Large-3` |
| Azure | `P2_task3_batchA` | P2 | 3 | A | `Mistral-Large-3` |
| Azure | `P3_task1_batchC` | P3 | 1 | C | `Mistral-Large-3` |

矩阵只允许 researcher 知晓。参与者只看到 Batch 标签，不看到模型名称、
backend、digest、deployment 或矩阵；三场 session 之间不透露任何模型信息。
这是本研究 single-blind 的操作定义。

## 4. G 与 G2：生成仪器版本冻结

### 4.1 G 历史凭据与升级触发

`generation-frozen-G` 永久指向
`da47d0eda734fc4136b8303a03d09e2d5f78c95f`，不得移动、覆盖或重建。
G-era 完成了一个 Llama smoke 和两个 Llama 正式候选，但在两个不同正式
Batch 上出现修复后 prompt 仍返回列表外 cluster ID 的 assignment
协议违规。第二个不同数据集上的同类违规击发 prompt 修复销案时保留的
常备触发器；它不是 Batch A `_attempt2` 决策树的分支二。

G-era 两个 completed 正式候选已裁定为 superseded，全部 G-era 文档与 run
保留在数据库中但不得进入正式 whitelist。G 与 G2 不得混用。完整触发链、
G-era 台账及方法论边界见
`docs/verification_records/g2_instrument_upgrade.md`。

### 4.2 G2 仪器与候选门禁

G2 为 relevance、initial assignment 与 existing assignment 共用同一
schema 构造模块；schema version 固定为
`stage_d_structured_output_v1`。Existing assignment 的合法 cluster ID
enum 随每次请求动态生成。Ollama 通过 native `/api/generate` 的 `format`
传输，Azure 通过 OpenAI-compatible `response_format=json_schema` strict
传输。原有本地 strict parser、分支形状与合法 ID 校验继续作为第二道闸；
labelling 不施加 schema。Strict 路径直接解析 provider 原始 JSON，不剥离
Markdown fence；relevance、initial assignment、existing assignment 的 fenced
JSON 一律失败。`cluster_id` 不接受字符串或数组；只接受非负 JSON integer，
或按 JSON Schema integer 语义接受数值上为整数的有限非负 JSON number。
非 strict 历史路径保留原有宽松解析。

三个正式 backend 的生产路径 capability probe 已全部通过；证据、脚本哈希、
payload 哈希及静默忽略限界见
`docs/verification_records/g2_probe.md`。

最终 annotated tag `generation-frozen-G2` 于 2026-07-26 建立，永久指向
`544540beedb707c2be5c08fa1647107f80587c84`。九个正式 run 的
`pipelineRuns.code_version` 已全部核对为该完整 hash。

G2 候选只允许在 `codex/g2-structured-output` 上、工作树干净后执行：

```powershell
git status --short
git rev-parse HEAD
cd D:\6003\thematic_clusters_git\ai-service
.\venv\Scripts\python.exe -m unittest discover -s tests -v
.\venv\Scripts\python.exe -m unittest tests.test_llm_provider.PromptFreezeTests.test_current_prompts_match_g2_byte_hashes -v
```

完整测试与独立 prompt hash 门禁必须全绿。候选 full hash 报告并获得明确
“创建 G2”批准后，才允许建立并 push 不可移动的 annotated tag：

```powershell
git tag -a generation-frozen-G2 -m "Freeze Stage D G2 generation instrument"
git push origin generation-frozen-G2
git rev-parse 'generation-frozen-G2^{commit}'
git ls-remote origin refs/tags/generation-frozen-G2
```

后两项必须共同证明本地 tag 与 origin tag 指向已批准的候选 full hash。
从 tag 建立起，九个正式文档唯一允许的 `pipelineRuns.code_version` 是该
G2 tag target。`generation-frozen-G2` 不得移动、覆盖或重建；任何后续代码
或 prompt 改动都必须停止生成并重新裁定。

## 5. 每个模型块的共同前置

生成顺序固定为 Llama → Qwen → Azure，只切换三次配置。每次切换后必须
完整重启 AI service，不能依赖热更新。

每个模型块开始前：

1. 确认 `git status --short` 无输出。
2. 确认 `git rev-parse HEAD` 等于 `generation-frozen-G2` 的 tag target。
3. 核对共同冻结参数。
4. 核对 backend、精确 model name 及本地 digest/云端 deployment metadata。
5. 执行一个非正式 20 行 smoke：
   - CSV：`test-data/p1_pipeline_run_20.csv`
   - 内容范围：非性健康的 synthetic hospital-ward 小数据，不是任何正式
     Batch，也不得替换为正式 Batch CSV。
   - 行数：20。
   - SHA-256：
     `9270f9dad53d00777e822b5c26356f5eab28a3a1cae9e64ee6c6f50d8fadcd7a`。
   - Survey name：`D_SMOKE_G2_LLAMA_batchA`、
     `D_SMOKE_G2_QWEN_batchA` 或 `D_SMOKE_G2_AZURE_batchA`
   - Pipeline：`LLM Semantic`
6. 只接受 smoke 的 `status: "completed"`、`strict_mode: true`、
   `code_version` 精确等于 G2 tag target、backend/model/params 全部匹配。
7. Smoke doc 不进入正式 whitelist。生成冻结期间，每发 smoke 后立即把
   document/run/验收结果写入 ignored
   `test-data/private/g2_smoke_ledger.txt` 并制作仓库外备份；不得在九个正式
   文档完成前修改 tracked docs。9/9 后在 operational S 中一次性回填下表与
   `docs/P1_session_manual.md` 第 4.4 节的排除名单。

20 行 smoke 只验证当前配置可启动、provider 可调用、多片段 assignment
分支可完成及 metadata 可追溯，不是正式比较数据。名称中的 `batchA` 只是
开发文档命名与 `batch_label` 解析需要；输入并非正式 Batch A。

| G2 smoke survey name | Expected backend/model | doc_id | run_id | outcome |
| --- | --- | --- | --- | --- |
| `D_SMOKE_G2_LLAMA_batchA` | expected `ollama` / `llama3.2:3b`; actual `azure` / `Mistral-Large-3` | `6a660bdef041b5fef471e029` | `6a660be2f041b5fef471e03e` | run completed；backend mismatch；验收拒绝；环境事故 |
| `D_SMOKE_G2_LLAMA_batchA_attempt2` | `ollama` / `llama3.2:3b` | `6a66119a59652a872b0639b2` | `6a66123e59652a872b0639c7` | 获批环境恢复重试；completed；accepted |
| `D_SMOKE_G2_QWEN_batchA` | `ollama` / `qwen2.5:3b` | `6a661d1ec2a3cea7e6de6028` | `6a661dc2c2a3cea7e6de603d` | completed；accepted |
| `D_SMOKE_G2_AZURE_batchA` | `azure` / `Mistral-Large-3` | `6a661f814b63e7a3c45dd144` | `6a661f844b63e7a3c45dd159` | completed；accepted |

G-era smoke `D_SMOKE_LLAMA_batchA` 与
`D_SMOKE_LLAMA_batchA_attempt2` 已永久进入开发/smoke 排除名单；G2 不复用
这些文档或名称。G2 三个 smoke 都必须重新 ingest、embed 20/20，并在 G2
仪器上完成一次新的 LLM run。

任一 smoke 失败：停止该模型块，不生成其正式文档，不立即重试。

## 6. 三个模型块的配置与生成顺序

### 6.1 Llama 块

`.env` 的相关值：

```dotenv
LLM_BACKEND=ollama
OLLAMA_MODEL=llama3.2:3b
OLLAMA_BASE_URL=http://localhost:11434
```

先执行 `ollama list`，再通过 Ollama `/api/tags` 核对完整 digest 必须为
`a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`。
核对通过后才运行本块 smoke，并按顺序生成：

1. `P1_task1_batchA`，使用 Batch A manifest。
2. `P2_task2_batchC`，使用 Batch C manifest。
3. `P3_task3_batchB`，使用 Batch B manifest。

### 6.2 Qwen 块

`.env` 的相关值：

```dotenv
LLM_BACKEND=ollama
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_BASE_URL=http://localhost:11434
```

先执行 `ollama list`，再通过 Ollama `/api/tags` 核对完整 digest 必须为
`357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`。
核对通过后才运行本块 smoke，并按顺序生成：

1. `P1_task3_batchC`，使用 Batch C manifest。
2. `P2_task1_batchB`，使用 Batch B manifest。
3. `P3_task2_batchA`，使用 Batch A manifest。

### 6.3 Azure 块

从安全位置恢复本地 Azure 配置；密钥不得写入本手册、终端历史或 Git。

```dotenv
LLM_BACKEND=azure
AZURE_OPENAI_BASE_URL=https://msc-foundry.services.ai.azure.com/openai/v1/
AZURE_OPENAI_MODEL=Mistral-Large-3
AZURE_OPENAI_MODEL_VERSION=1
AZURE_OPENAI_DEPLOYMENT_TYPE=GlobalStandard
AZURE_OPENAI_API_KEY=<LOCAL_SECRET_ONLY>
```

完整重启后，以 `D_SMOKE_G2_AZURE_batchA` 作为 deployment 存活、endpoint
可达、key 有效及当前配额可用的真实 provider 门禁，不另发会绕过
`pipelineRuns` 的临时请求。若 smoke 因 authentication、deployment not
found、quota/rate limit、network 或其他基础设施原因失败，应归类为
deployment-side preflight failure：停止本块、保留记录并先报告，不得把它
误判为代码或正式数据失败，也不得立即重试。Smoke completed 且 metadata
核对通过后，按顺序生成：

1. `P1_task2_batchB`，使用 Batch B manifest。数据库已有同名历史开发文档
   `6a58d2cd1d6d1e80c35ba564`；新 ingest 返回的 `doc_id` 必须与它不同，
   后续所有调用只使用新返回的 `doc_id`，正式 whitelist 也只收新 `doc_id`。
2. `P2_task3_batchA`，使用 Batch A manifest。
3. `P3_task1_batchC`，使用 Batch C manifest。

## 7. 单个正式文档操作与验收

### 7.1 固定 API 编排

阶段 D 使用本地 API 批量生成，不依赖 UI 点击。UI 会隐式执行
`ingest → embed → LLM Semantic`；底层 API 不会自动补齐下一步，因此每个
smoke 和正式文档必须显式、按顺序执行以下完整调用链，不得跳步：

1. 重新计算即将上传的 CSV SHA-256：
   - smoke 必须匹配第 5 节的 20 行 hash；
   - 正式文档必须匹配第 2 节对应 Batch hash。
2. 生成前确认 `git status --short` 无输出、`git rev-parse HEAD` 等于
   `generation-frozen-G2` 的 tag target，并核对本模型块的有效配置。
3. `POST /ingest/survey`：
   - file 为本次已核对 hash 的 CSV；
   - `survey_name` 必须逐字等于矩阵值或已批准的 `_attemptN` 值；
   - 保存响应直接返回的 `doc_id`，此后不得按 survey name 反查或选择文档；
   - `fragment_count` 必须等于 smoke 20 或 manifest 的 A=17、B=21、C=20；
     不等则停止，不调用 embed。
4. `POST /embed/fragments`，请求体只使用上一步返回的 `doc_id`：
   - 响应 `embedded_count` 必须等于该文档完整 fragment 数；
   - MongoDB 中该 `doc_id` 的非空 embedding 数也必须等于完整 fragment 数；
   - smoke 必须为 20/20；正式文档必须为 A=17/17、B=21/21、C=20/20；
   - 任一计数不全立即停止，不调用 LLM，不在同一文档上补跑。
5. `POST /llm-cluster/run`，仍只使用同一 `doc_id`：
   - `research_question` 必须从 manifest 逐字复制；
   - `column_filters` 固定为空对象；
   - 流式终局必须为 `done`；`error` 立即按失败协议停止。
6. 成功或失败都先登记 document、run、各阶段计数与终局，不删除任何记录；
   在开始下一文档前完成第 7.2 节验收。

任何按名查询仅可用于碰撞审计，不能决定后续 API 的 `doc_id`。已知具体案例：
历史开发文档 `P1_task2_batchB / 6a58d2cd1d6d1e80c35ba564` 与未来 Azure
正式文档同名；两者只能靠 `doc_id` 区分。G2 还保留原矩阵 survey name，
所以三个 Llama 名称都可能与 G-era attempt/candidate 同名。每次 G2 ingest
必须保存新返回的 `doc_id`，验证它不等于排除台账中的旧 ID，并只沿该新 ID
调用 embed、LLM 与验收；禁止按名称选“最新一条”。

### 7.2 单个 run 验收

在 mongosh 中核对该文档最新 run：

```javascript
use nie
var DOC = ObjectId("DOC_ID")
var RUN = db.pipelineRuns.find({doc_id: DOC})
  .sort({started_at: -1, _id: -1})
  .limit(1)
  .next()
RUN
db.fragments.countDocuments({docid: DOC})
db.clusters.countDocuments({survey_doc_id: DOC})
```

接受条件：

- `status: "completed"` 且存在 `finished_at`。
- `pipeline: "llm_semantic"`、`strict_mode: true`。
- `code_version` 精确等于 `generation-frozen-G2` 的 tag target。
- `llm_backend`、`model_name`、Azure version/deployment 与矩阵一致。
- `params` 包含 60 / 0 / 42 / 1024、`max_retries: 0` 和正确
  `seed_semantics`。
- `params.schema_enforced: true`、
  `params.schema_version: "stage_d_structured_output_v1"`、
  `params.schema_dynamic_cluster_id_enum: true`，且
  `params.schema_transport` 对 Ollama 为
  `ollama_api_generate_format`、对 Azure 为
  `openai_chat_completions_response_format_json_schema`。
- `batch_label` 与矩阵一致，不得为 `UNKNOWN`。
- 不存在任何 `failure_*` 字段。
- fragment 数等于 manifest 行数。
- cluster 数及 filtered fragment 数如实记录，不以结果好坏决定重生成。

若 run 失败或 completed 但无法供参与者审查：立即停止该模型块。不得删除、
覆盖、放宽参数或私自重跑；先记录 failure stage/code/type 和累计失败次数，
但不记录受限原文，再报告并等待人工裁定。只有明确获批后才能重新 ingest；
新文档名依次使用 `_attempt2`、`_attempt3` 等后缀。所有 document、run 和
attempt 必须保留并进入第 8 节全尝试台账；正式 whitelist 只纳入最终获批的
completed doc ID。

## 8. G2 九文档生成台账

| Survey name | Model | Batch | doc_id | run_id | status | fragments/embedded | kept/filtered | clusters | finished_at | code_version |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `P1_task1_batchA` | `llama3.2:3b` | A | `6a6621355e9bd7a009d1b97f` | `6a66213a5e9bd7a009d1b991` | completed | 17/17 | 15/2 | 7 | `2026-07-26T15:04:07.601000Z` | `544540beedb707c2be5c08fa1647107f80587c84` |
| `P2_task2_batchC` | `llama3.2:3b` | C | `6a662346b88c6db2d9915ac9` | `6a66234bb88c6db2d9915ade` | completed | 20/20 | 20/0 | 15 | `2026-07-26T15:13:32.846000Z` | `544540beedb707c2be5c08fa1647107f80587c84` |
| `P3_task3_batchB` | `llama3.2:3b` | B | `6a6625e3460dababa39a9be4` | `6a6625e7460dababa39a9bfa` | completed | 21/21 | 19/2 | 6 | `2026-07-26T15:24:25.873000Z` | `544540beedb707c2be5c08fa1647107f80587c84` |
| `P1_task3_batchC` | `qwen2.5:3b` | C | `6a662813ed5bcd0c9d8a4439` | `6a662818ed5bcd0c9d8a444e` | completed | 20/20 | 17/3 | 2 | `2026-07-26T15:33:23.828000Z` | `544540beedb707c2be5c08fa1647107f80587c84` |
| `P2_task1_batchB` | `qwen2.5:3b` | B | `6a666d4f04fc296116b621af` | `6a666d5404fc296116b621c5` | completed | 21/21 | 16/5 | 1 | `2026-07-26T20:28:42.553000Z` | `544540beedb707c2be5c08fa1647107f80587c84` |
| `P3_task2_batchA` | `qwen2.5:3b` | A | `6a666f0d5f60ce182f69ff12` | `6a666f125f60ce182f69ff24` | completed | 17/17 | 16/1 | 1 | `2026-07-26T20:35:58.113000Z` | `544540beedb707c2be5c08fa1647107f80587c84` |
| `P1_task2_batchB` | `Mistral-Large-3` | B | `6a6672adaaaa46976afdb5ba` | `6a6672b1aaaa46976afdb5d0` | completed | 21/21 | 20/1 | 11 | `2026-07-26T20:49:54.237000Z` | `544540beedb707c2be5c08fa1647107f80587c84` |
| `P2_task3_batchA` | `Mistral-Large-3` | A | `6a667375aaaa46976afdb5dc` | `6a667376aaaa46976afdb5ee` | completed | 17/17 | 16/1 | 8 | `2026-07-26T20:52:46.838000Z` | `544540beedb707c2be5c08fa1647107f80587c84` |
| `P3_task1_batchC` | `Mistral-Large-3` | C | `6a6673f2aaaa46976afdb5f7` | `6a6673f3aaaa46976afdb60c` | completed | 20/20 | 19/1 | 10 | `2026-07-26T20:55:01.170000Z` | `544540beedb707c2be5c08fa1647107f80587c84` |

九行已全部通过矩阵级只读复核；九个正式 `doc_id` 与对应 `run_id` 已抄入
`docs/P1_session_manual.md` 的 whitelist。

### 8.1 全尝试与失败台账

初始尝试及每个获批 retry 均须逐行添加；不得只登记最终成功项。G-era
记录是仪器升级证据，不计入 G2 九文档，但必须永久保留并排除。

| Survey name | Attempt | doc_id | run_id | status | failure count | failure stage/code/type | decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `D_SMOKE_LLAMA_batchA` | 1 | `6a64c2e83e0dbddf5447c741` | `6a64c2e93e0dbddf5447c756` | `failed` | 1 | `load_fragments` / `NO_EMBEDDED_FRAGMENTS` / `PipelineRunAbort` | G-era；编排遗漏；provider 未调用；保留并排除 |
| `D_SMOKE_LLAMA_batchA_attempt2` | 2 | `6a64c6bb3e0dbddf5447c757` | `6a64c6be3e0dbddf5447c76c` | `completed` | 1 cumulative | none | G-era smoke；保留并排除 |
| `P1_task1_batchA` | 1 | `6a64c87f3e0dbddf5447c76f` | `6a64c8813e0dbddf5447c781` | `failed` | 1 | `cluster_assignment` / `INVALID_LLM_RESPONSE` / out-of-list ID | G-era；记录保留；`_attempt2` 获批 |
| `P1_task1_batchA_attempt2` | 2 | `6a64e3a53e0dbddf5447c782` | `6a64e3a63e0dbddf5447c794` | `completed` | 1 cumulative | none | G-era completed；G2 升级后 superseded；永不 whitelist |
| `P2_task2_batchC` | 1 | `6a651c263e0dbddf5447c796` | `6a651c283e0dbddf5447c7ab` | `completed` | 0 | none | G-era completed；G2 升级后 superseded；永不 whitelist |
| `P3_task3_batchB` | 1 | `6a651df93e0dbddf5447c7ad` | `6a651dfa3e0dbddf5447c7c3` | `failed` | 1 | `cluster_assignment` / `INVALID_LLM_RESPONSE` / out-of-list ID | 常备触发器击发；停止 G；不做 retry |
| `D_SMOKE_G2_LLAMA_batchA` | 1 | `6a660bdef041b5fef471e029` | `6a660be2f041b5fef471e03e` | `completed / rejected` | 1 acceptance incident | environment / backend mismatch；旧 Azure listener 接收请求；无 `failure_*` | 停止 smoke 阶段；保留并排除；获批环境恢复 `_attempt2` |
| `D_SMOKE_G2_LLAMA_batchA_attempt2` | 2 | `6a66119a59652a872b0639b2` | `6a66123e59652a872b0639c7` | `completed` | 1 acceptance incident cumulative | none | accepted G2 Llama smoke；不入 whitelist |
| `D_SMOKE_G2_QWEN_batchA` | 1 | `6a661d1ec2a3cea7e6de6028` | `6a661dc2c2a3cea7e6de603d` | `completed` | 0 | none | accepted G2 Qwen smoke；不入 whitelist |
| `D_SMOKE_G2_AZURE_batchA` | 1 | `6a661f814b63e7a3c45dd144` | `6a661f844b63e7a3c45dd159` | `completed` | 0 | none | accepted G2 Azure smoke；不入 whitelist |
| `P1_task1_batchA` | 1 | `6a6621355e9bd7a009d1b97f` | `6a66213a5e9bd7a009d1b991` | `completed` | 0 | none | accepted G2 formal；whitelist |
| `P2_task2_batchC` | 1 | `6a662346b88c6db2d9915ac9` | `6a66234bb88c6db2d9915ade` | `completed` | 0 | none | accepted G2 formal；whitelist |
| `P3_task3_batchB` | 1 | `6a6625e3460dababa39a9be4` | `6a6625e7460dababa39a9bfa` | `completed` | 0 | none | accepted G2 formal；G-era 触发数据上的升级闭环；whitelist |
| `P1_task3_batchC` | 1 | `6a662813ed5bcd0c9d8a4439` | `6a662818ed5bcd0c9d8a444e` | `completed` | 0 | none | accepted G2 formal；whitelist |
| `P2_task1_batchB` | 1 | `6a666d4f04fc296116b621af` | `6a666d5404fc296116b621c5` | `completed` | 0 | none | accepted G2 formal；单簇；whitelist |
| `P3_task2_batchA` | 1 | `6a666f0d5f60ce182f69ff12` | `6a666f125f60ce182f69ff24` | `completed` | 0 | none | accepted G2 formal；单簇；whitelist |
| `P1_task2_batchB` | 1 | `6a6672adaaaa46976afdb5ba` | `6a6672b1aaaa46976afdb5d0` | `completed` | 0 | none | accepted G2 formal；与历史同名开发 doc ID 不同；whitelist |
| `P2_task3_batchA` | 1 | `6a667375aaaa46976afdb5dc` | `6a667376aaaa46976afdb5ee` | `completed` | 0 | none | accepted G2 formal；whitelist |
| `P3_task1_batchC` | 1 | `6a6673f2aaaa46976afdb5f7` | `6a6673f3aaaa46976afdb60c` | `completed` | 0 | none | accepted G2 formal；whitelist |

历史开发文档 `P1_task2_batchB / 6a58d2cd1d6d1e80c35ba564` 与正式 Azure
文档同名，但始终排除。正式新 doc ID
`6a6672adaaaa46976afdb5ba` 已验证与其不同；禁止按 survey name 选择记录。

### 8.2 生成完成后的方法论边界

- G→G2 是生成仪器可靠性与 provenance 流程证据，不是模型质量结果。
- G 的三个 Llama 首次正式尝试为 `1/3 completed`；两个失败均为修复后
  prompt 下的列表外 cluster ID。G2 Llama 为 `3/3 completed`，G2 全矩阵为
  `9/9 completed`，全部是首次正式尝试且无 `failure_*`。
- 未 embed 的 G smoke 是底层 API 编排事故，provider 未调用，不计作 schema
  失败。G2 Llama 的 backend-mismatch attempt 是旧监听进程造成的运行环境
  事故；run 虽 completed 但验收拒绝，获批 attempt2 后通过。
- G2 正式粒度画像按模型汇总为：Qwen `1/1/2`（稳定但极粗）；
  Azure `8/11/10`（中等且较稳定）；Llama `6/7/15`（粒度显著上升且
  批次间波动大）。这些是仪器边界与 session 负担背景，不在生成阶段判定
  哪个输出更好。
- Smoke 仅为开发、配置与 provenance 证据，不进入 Results；其 relevance
  过滤率不用于预测正式批次材料量。
- 本研究三次正式 Azure run 未观察到 `CONTENT_FILTERED`。该陈述不得外推到
  其他 Azure/Mistral deployment、其他输入或未来运行。
- 完整 S 生成记录、九文档矩阵、ledger hash 与分析边界见
  `docs/verification_records/stage_d_g2_generation.md`。

## 9. S：Session 操作版本与等价性证明

G2 tag 建立后到九文档完成前不得修改代码、prompt、schema、参数、模型、
正式输入或矩阵。该冻结期内每发 smoke/run 先写 ignored private ledger 并
制作仓库外备份；“每发立即登记”指 private ledger，不指 tracked docs。三个
G2 smoke 与九个正式文档全部验收后，只允许一次性修改 `docs/`：回填 G2 tag
凭据、第 5 节 smoke doc ID、第 8 节正式与全尝试台账，以及
`docs/P1_session_manual.md` 的正式 whitelist、superseded、smoke 排除名单、
session 指标与 PILOT 隔离裁定。该 docs-only commit 定义为 `S`。

在 `S` 上执行并记录：

```powershell
git status --short
git diff --exit-code generation-frozen-G2..S_FULL_HASH -- . ':(exclude)docs'
cd D:\6003\thematic_clusters_git\ai-service
.\venv\Scripts\python.exe -m unittest tests.test_llm_provider.PromptFreezeTests.test_current_prompts_match_g2_byte_hashes -v
```

要求：工作树干净；排除 `docs/` 后的 diff 无输出；prompt hash 测试通过。
这证明 `S` 的运行代码与 G2 的生成仪器等价。

`S` 无法在自身内容中记录自己的 full hash。`S` 及上述等价性结果产生后，
允许恰好一个后续 docs-only commit，commit message 固定为
`docs: audit record for S`。该 audit commit 只允许把 `S` full hash 和已经
得到的等价性/prompt-hash 结果写入版本凭据，不得修改任何操作性内容。

正式 session 的固定 checkout 端点是该唯一 audit commit，即
承载 audit commit 的正式操作分支 `HEAD`，不是裸 `S`。Session 前固定运行：

```powershell
git status --short
git diff --exit-code generation-frozen-G2..HEAD -- . ':(exclude)docs'
git diff --exit-code S_FULL_HASH..HEAD -- . ':(exclude)docs'
cd D:\6003\thematic_clusters_git\ai-service
.\venv\Scripts\python.exe -m unittest tests.test_llm_provider.PromptFreezeTests.test_current_prompts_match_g2_byte_hashes -v
```

两条 diff 都必须无输出；audit commit 的 parent 必须是 `S`，且 commit
message 必须逐字等于上述固定值。三层版本关系固定为：
`G2`（annotated tag）→ `S`（whitelist/台账 commit）→ 唯一 audit commit。
历史 `G` 与 G-era runs 留在 provenance 链中，但不构成最终 session 的
运行版本层。

若 G2 后发现任何代码缺陷，禁止在 `G2 → S` 间直接修补。必须单独裁定：

- 保留 G2 的代码完成实验，并将缺陷写入 limitation；或
- 修复代码、废止当前正式候选文档、建立新 generation tag，并重新生成
  全部九个文档。

不得混用两个仪器版本生成同一正式矩阵。

## 10. 新任务交接入口

新任务开始时必须先读取：

1. `docs/stage_d_generation_runbook.md`
2. `docs/P1_session_manual.md`
3. `docs/verification_records/sampling_freeze.md`
4. `docs/verification_records/local_model_selection.md`
5. `docs/verification_records/azure_mistral.md`
6. `docs/verification_records/g2_probe.md`
7. `docs/verification_records/g2_instrument_upgrade.md`

新任务首先核对 G2 tag 状态、clean worktree 与当前已批准步骤。第 2 节
manifest 已冻结，不得改动。不得重新使用 G-era 候选、跳过 smoke、直接上传
其他 CSV 或生成正式文档。

## 11. Session 仪器冻结与分析证据交接

2026-07-29 的 session-instrument 裁定采用“不修改 UI”的路径。正式
P1/P2/P3 三场固定运行精确 commit：

```text
ddb5355972ca63df44edad184b11e30f420e4c62
```

`codex/session-card-readability-v1`、`c5b7354` 与 `2f49694` 是保留但未批准
的候选，不得进入正式 session。它们包含 full-text inspection、note popover、
键盘行为与 URL document persistence，不属于可在既有 PILOT 后静默接受的
纯视觉修改。三场之间任何代码、界面或行为变化都会破坏 participant 间仪器
一致性；若必须修改，必须在第一场前重新彩排、冻结和审核。

上述 2026-07-29 裁定作为历史记录保留。2026-08-02、第一场 participant action
发生前，researcher 明确选择使用该 readability UI；因此停止旧端点开场，按本节
预注册分支完成新鲜 `nie_pilot` 复制、简化交互验证、正式库零变化复核和重新
冻结。两个 UI commits 与最新 session 协议链在
`68c93006d408b6cf9d01c459d86757563f65b052` 汇合；当前正式 session checkout
改为 `0e37f187d95db5f10cb6892cc2a97b543a5bd4eb`，完整证据见
`docs/verification_records/session_card_readability_v1.md`。G2、九份正式文档、
API/AI、Confirm/Move 记录行为及分析规则均未改变。

正式 retention 与资源审计已确认：

- A/B/C input 分别为 17/21/20，同 batch 三模型的 fragment multiset 与当前
  重建处理顺序一致；
- 三模型各接收 58 条平衡输入；
- 九份文档均满足 `input = kept + filtered`，第三桶为零；
- retention 只描述 relevance 产出，不是 accuracy/quality；
- 正式 wall-clock 从冻结 `pipelineRuns` 提取，正文只报整数秒；
- local peak memory 来自 separate instrumentation，而非九次正式生成；
- Azure 服务端 RAM/VRAM 不可观测；当前 researcher account 无权查看或导出
  portal usage/token/billing，实际货币成本记为 unavailable，而不是零；以及
- Llama post-reboot repeat 已确认 3.1 GiB separate-instrumentation
  observation，不再标为 provisional。

完整数字、全长 SHA-256、顺序重建限制和资源失败尝试见：

```text
docs/verification_records/retention_resource_order_audit.md
```

当前关键路径：

1. session readability 分支已在第一场前完成 `nie_pilot` 验证和重新冻结；正式
   endpoint 为 audit child 记录的 session UI operational full hash；
2. ERGO/FEC 门户状态已目视核对为 `Approved`；无独立 PDF 批准函时只使用
   portal status evidence，不虚构 PDF 凭据；
3. Llama post-reboot repeat 已关闭；Azure portal cost 因当前账号无查看/
   导出权限而不可获得。该证据缺口不授权修改 session 仪器、估算成本或延伸
   成新的正式 generation；
4. 本次 UI 变更已经用新鲜 `nie_pilot` 关闭该阻塞；任何后续 UI/code 变更仍会
   立即重新阻塞，直到另立仪器并重新完成 PILOT、冻结和审核；以及
5. 第一场开始后直至 P3 结束，仪器不可变。

后续任务除第 10 节七个文件外，还必须读取：

```text
docs/verification_records/stage_d_g2_generation.md
docs/verification_records/retention_resource_order_audit.md
```

### 11.1 资源交接更新（2026-07-30）

Post-reboot Llama repeat 在同一固定代码状态下完成；它与先前测量的
local-stack peak 只相差 0.0225%（3,370,754,048 对 3,371,511,808 bytes），
GPU allocation delta 相差 15 MiB。因此 Llama 的 3.1 GiB
separate-instrumentation observation 已由 provisional 升为 confirmed。
accepted attempt 之前的所有 setup-only 失败均保留在验证台账中，且均未发送
模型请求。

Azure 实际成本仍不可用：当前 researcher account 无权查看或导出 Portal
usage/token/billing 证据。`< $10` 仍只表示预算上限，不得写成 observed cost。
本节更新取代前文把 Azure cost 与 Llama post-reboot repeat 同时列为待办的
表述：Llama 复测已经关闭；仅 Azure 成本证据仍不可获得，且不得用模型估算值
替代。
