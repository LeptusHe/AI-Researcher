# AI-Researcher 移动端图形学版 — 使用指南

## 项目简介

本项目改造自 Stanford NLP 的 AI-Researcher，将研究领域从 NLP 切换为**移动端图形学 / 实时渲染 / 游戏引擎优化**。系统保留了原有六阶段流水线架构：

```
文献检索 → 创意生成 → 去重 → 提案展开 → 排序 → 过滤
```

系统自动检索相关学术论文，基于论文生成研究创意，去重后展开为完整的实验计划提案，最后通过排序和多维度过滤筛选出高质量提案。

---

## 一、环境配置

### 1.1 安装 Python 依赖

```bash
cd AI-Researcher
pip install -r requirements.txt
```

主要依赖：

| 包名 | 用途 |
|------|------|
| `anthropic` | Claude API 调用 |
| `openai` | GPT-4 API 调用 |
| `sentence_transformers` | 创意去重（语义相似度计算） |
| `retry` | API 调用自动重试 |
| `tqdm` | 进度条 |
| `requests` | Semantic Scholar API 调用 |

### 1.2 配置 API Keys

在项目**根目录**（`AI-Researcher/`，与 `ai_researcher/` 同级）创建 `keys.json`：

```json
{
    "api_key": "你的 OpenAI API Key",
    "organization_id": "你的 OpenAI Organization ID",
    "anthropic_key": "你的 Anthropic API Key",
    "s2_key": "你的 Semantic Scholar API Key"
}
```

各 Key 的获取方式：

- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/
- **Semantic Scholar**: https://www.semanticscholar.org/product/api#api-key （免费申请，文献检索必需）

> 如果只使用 Claude，OpenAI 相关字段可填空字符串 `""`，反之亦然。

### 1.3 使用第三方 OpenAI 兼容 API（可选）

如果你使用 OpenAI 格式的第三方 API 中间商（如代理服务、私有部署端点），在 `keys.json` 中添加以下可选字段：

```json
{
    "openai_base_url": "https://your-provider.com/v1",
    "openai_compatible_key": "your-api-key"
}
```

字段说明：

| 字段 | 说明 | 默认行为 |
|------|------|----------|
| `openai_base_url` | 第三方 API 的 base URL | 留空或不填则使用官方 OpenAI |
| `openai_compatible_key` | 第三方 API 的 Key | 留空则回退到 `api_key` |

配置后，所有非 Claude 模型的请求都会路由到该端点。支持任何实现了 OpenAI Chat Completions API 的服务（如 vLLM、Ollama、各类 API 代理等）。

> **注意**：Claude 模型始终通过 Anthropic 官方 API 调用，不受此配置影响。

### 1.4 支持的 LLM 引擎

所有脚本通过 `--engine` 参数选择模型：

| 引擎 | 说明 | 备注 |
|------|------|------|
| `claude-3-5-sonnet-20240620` | Anthropic Claude 3.5 Sonnet | **推荐**，性价比最优 |
| `gpt-4o` | OpenAI GPT-4o | 需 OpenAI key |
| `o1-preview` / `o1-mini` | OpenAI o1 系列 | 推理能力强，价格较高 |
| `meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo` | Llama 3.1 70B | 通过 Together API，需设环境变量 `TOGETHER_API_KEY` |

---

## 二、设置研究主题

### 2.1 主题格式

研究主题是一句**英文自然语言描述**，通过 `--topic_description` 参数传入。主题应简明概括研究方向和关键约束。

### 2.2 预设主题示例

| 方向 | topic_description |
|------|-------------------|
| 移动端渲染优化 | `"novel real-time rendering techniques for mobile GPUs with limited bandwidth and compute"` |
| 移动端抗锯齿/超分 | `"energy-efficient temporal antialiasing and upsampling algorithms for mobile devices with constrained power budgets"` |
| 移动端神经渲染 | `"neural rendering methods optimized for deployment on mobile devices"` |
| 游戏引擎帧率优化 | `"game engine optimization techniques for achieving stable 60fps on mobile platforms"` |

### 2.3 自定义主题

编写主题时的建议：

- 包含**具体技术方向**（如 "shadow mapping"、"texture compression"、"LOD management"）
- 包含**目标平台约束**（如 "mobile GPUs"、"limited bandwidth"、"power constrained"）
- 包含**目标效果**（如 "real-time"、"energy-efficient"、"high visual quality"）

示例：

```
"bandwidth-efficient shadow mapping techniques for tile-based mobile GPU architectures"
"real-time global illumination methods for mobile game engines with sub-2ms per-frame budget"
"neural mesh compression and streaming for mobile AR applications"
```

### 2.4 方法类型

创意生成和提案展开支持三种方法类型（`--method` 参数）：

| 方法类型 | 说明 | 适用方向 |
|----------|------|----------|
| `rendering_optimization` | 渲染管线优化 | Shader 优化、LOD、阴影、剔除等 |
| `neural_graphics` | 神经图形学 | 神经渲染、神经纹理压缩、神经 LOD 等 |
| `engine_architecture` | 引擎架构（通用） | 综合方法，不限定具体类别 |

---

## 三、运行方式

所有脚本需在 `ai_researcher/src/` 目录下执行：

```bash
cd ai_researcher/src
```

### 3.1 端到端运行（推荐）

```bash
bash ../scripts/end_to_end.sh
```

默认执行前 4 步（文献检索 → 创意生成 → 去重 → 提案展开）。排序和过滤步骤默认注释掉以节省费用，取消注释即可启用。

要修改主题，编辑 `scripts/end_to_end.sh` 中的：

1. **第 6 行** `--topic_description` — 修改为你的主题描述
2. **第 8 行** `--cache_name` — 修改缓存文件路径中的名称
3. **第 13 行** `topic_names=(...)` — 修改为对应的缓存名称

### 3.2 分步运行

#### Step 1：文献检索

检索 Semantic Scholar 上的相关论文，由 LLM 评分排序。

```bash
python3 src/lit_review.py \
  --engine "claude-3-5-sonnet-20240620" \
  --mode "topic" \
  --topic_description "novel real-time rendering techniques for mobile GPUs with limited bandwidth and compute" \
  --cache_name "../cache_results_test/lit_review/mobile_rendering_optimization.json" \
  --max_paper_bank_size 50 \
  --print_all
```

参数说明：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--mode` | `topic`（按主题检索）或 `idea`（按创意检索） | `topic` |
| `--max_paper_bank_size` | 最大论文收集数量 | 60 |
| `--grounding_k` | 每轮用于生成下一查询的 top-k 论文数 | 10 |
| `--cache_name` | 输出文件路径 | — |

输出：JSON 文件，包含 `topic_description`、`paper_bank`（按相关性排序的论文列表）。

#### Step 2：创意生成

基于检索到的论文（RAG），生成研究创意。

```bash
python3 src/grounded_idea_gen.py \
  --engine "claude-3-5-sonnet-20240620" \
  --paper_cache "../cache_results_test/lit_review/mobile_rendering_optimization.json" \
  --idea_cache "../cache_results_test/seed_ideas/mobile_rendering_optimization.json" \
  --method "rendering_optimization" \
  --ideas_n 5 \
  --grounding_k 10 \
  --seed 1 \
  --RAG True
```

参数说明：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--method` | 方法类型：`rendering_optimization`、`neural_graphics`、`engine_architecture` | `rendering_optimization` |
| `--ideas_n` | 每次生成的创意数量 | 5 |
| `--grounding_k` | 用于 RAG 的论文数量 | 10 |
| `--RAG` | 是否启用 RAG（`True`/`False`） | `True` |
| `--seed` | 随机种子 | 2024 |
| `--append_existing_ideas` | 是否在已有创意上追加 | `True` |
| `--debug` | 启用调试模式（不捕获异常） | 关闭 |

多次运行会**追加**创意到同一文件。可通过变化 `--seed` 和 `--RAG` 生成更多样的创意。

#### Step 3：创意去重

使用 sentence-transformers 计算语义相似度，去除重复创意。

```bash
# 计算相似度矩阵
python3 src/analyze_ideas_semantic_similarity.py \
  --cache_dir "../cache_results_test/seed_ideas/" \
  --cache_name "mobile_rendering_optimization" \
  --save_similarity_matrix

# 去重
python3 src/dedup_ideas.py \
  --cache_dir "../cache_results_test/seed_ideas/" \
  --cache_name "mobile_rendering_optimization" \
  --dedup_cache_dir "../cache_results_test/ideas_dedup" \
  --similarity_threshold 0.8
```

`--similarity_threshold`：相似度阈值（0-1），超过此值的创意被视为重复。默认 0.8。

#### Step 4：提案展开

将简短创意展开为包含完整实验计划的详细提案。

```bash
python3 src/experiment_plan_gen.py \
  --engine "claude-3-5-sonnet-20240620" \
  --idea_cache_dir "../cache_results_test/ideas_dedup/" \
  --cache_name "mobile_rendering_optimization" \
  --experiment_plan_cache_dir "../cache_results_test/project_proposals/" \
  --idea_name "all" \
  --method "rendering_optimization" \
  --seed 2024
```

`--idea_name`：指定单个创意名称，或 `"all"` 展开所有创意。

输出的提案 JSON 包含 7 个部分：Title、Problem Statement、Motivation、Proposed Method、Step-by-Step Experiment Plan、Test Case Examples、Fallback Plan。

#### Step 5：提案排序（可选）

通过锦标赛制（tournament）两两比较对提案排序。

```bash
python3 src/tournament_ranking.py \
  --engine "claude-3-5-sonnet-20240620" \
  --experiment_plan_cache_dir "../cache_results_test/project_proposals/" \
  --cache_name "mobile_rendering_optimization" \
  --ranking_score_dir "../cache_results_test/ranking/" \
  --max_round 5
```

`--max_round`：锦标赛轮数，越多越准确但成本越高。

#### Step 6：提案过滤（可选）

按排名顺序对提案进行多维度检查，过滤不合格提案。

```bash
python3 src/filter_ideas.py \
  --engine "claude-3-5-sonnet-20240620" \
  --cache_dir "../cache_results_test/project_proposals/" \
  --cache_name "mobile_rendering_optimization" \
  --passed_cache_dir "../cache_results_test/project_proposals_passed/" \
  --score_file "../cache_results_test/ranking/mobile_rendering_optimization/round_5.json"
```

过滤维度（自动执行）：

| 检查项 | 说明 |
|--------|------|
| 一致性检查 | 方法和实验设计是否一致（如声称移动端但使用桌面 GPU） |
| 可行性检查 | 硬件、场景资产是否可获取 |
| 显著性检查 | 问题是否有足够的研究意义 |
| 检索新颖性检查 | 通过 Semantic Scholar 检索确认创意未被已有论文覆盖 |

---

## 四、输出文件结构

所有中间结果和最终输出保存在 `cache_results_test/` 目录下：

```
cache_results_test/
├── lit_review/                          # 文献检索结果
│   └── mobile_rendering_optimization.json
├── seed_ideas/                          # 原始创意
│   └── mobile_rendering_optimization.json
├── ideas_dedup/                         # 去重后的创意
│   └── mobile_rendering_optimization.json
├── project_proposals/                   # 展开后的完整提案
│   └── mobile_rendering_optimization/
│       ├── adaptive_tile-based_shading.json
│       ├── neural_texture_compression.json
│       └── ...
├── ranking/                             # 排序结果
│   └── mobile_rendering_optimization/
│       ├── round_1.json ... round_5.json
│       └── top_ideas.json
└── project_proposals_passed/            # 通过过滤的提案
    └── mobile_rendering_optimization/
        └── ...
```

---

## 五、费用估算

使用 Claude 3.5 Sonnet 的参考费用：

| 阶段 | 预估费用 (USD) | 说明 |
|------|----------------|------|
| 文献检索 (50 篇) | $0.5 - $1 | 多轮查询 + 论文评分 |
| 创意生成 (20 个) | $1 - $3 | 4 轮生成，每轮 5 个 |
| 去重 | 免费 | 本地 sentence-transformers |
| 提案展开 (15 个) | $2 - $4 | 每个提案一次 LLM 调用 |
| 排序 (5 轮) | $3 - $8 | O(n) 次两两比较 × 5 轮 |
| 过滤 | $3 - $8 | 每个提案 4-5 次检查 + 检索 |
| **总计** | **$3 - $8**（前4步）<br>**$10 - $24**（全6步） | |

---

## 六、快速上手示例

以"移动端阴影优化"为例，完整运行：

```bash
cd ai_researcher/src

# 1. 文献检索
python3 src/lit_review.py \
  --engine "claude-3-5-sonnet-20240620" \
  --mode "topic" \
  --topic_description "bandwidth-efficient shadow mapping for tile-based mobile GPU architectures" \
  --cache_name "../cache_results_test/lit_review/mobile_shadow_mapping.json" \
  --max_paper_bank_size 50 \
  --print_all

# 2. 创意生成（运行两轮以获得更多创意）
for seed in 1 2; do
  for rag in True False; do
    python3 src/grounded_idea_gen.py \
      --engine "claude-3-5-sonnet-20240620" \
      --paper_cache "../cache_results_test/lit_review/mobile_shadow_mapping.json" \
      --idea_cache "../cache_results_test/seed_ideas/mobile_shadow_mapping.json" \
      --method "rendering_optimization" \
      --ideas_n 5 --seed $seed --RAG $rag
  done
done

# 3. 去重
python3 src/analyze_ideas_semantic_similarity.py \
  --cache_dir "../cache_results_test/seed_ideas/" \
  --cache_name "mobile_shadow_mapping" \
  --save_similarity_matrix

python3 src/dedup_ideas.py \
  --cache_dir "../cache_results_test/seed_ideas/" \
  --cache_name "mobile_shadow_mapping" \
  --dedup_cache_dir "../cache_results_test/ideas_dedup" \
  --similarity_threshold 0.8

# 4. 提案展开
python3 src/experiment_plan_gen.py \
  --engine "claude-3-5-sonnet-20240620" \
  --idea_cache_dir "../cache_results_test/ideas_dedup/" \
  --cache_name "mobile_shadow_mapping" \
  --experiment_plan_cache_dir "../cache_results_test/project_proposals/" \
  --idea_name "all" \
  --method "rendering_optimization"
```

完成后在 `cache_results_test/project_proposals/mobile_shadow_mapping/` 下查看生成的提案 JSON 文件。

---

## 七、领域配置参考

领域常量定义在 `ai_researcher/domain_config.py` 中，包括：

- **目标会议**: SIGGRAPH, SIGGRAPH Asia, Eurographics, I3D, HPG, MobiSys, MobiCom
- **研究子方向**: 移动端实时渲染、Shader 优化、LOD/场景管理、纹理压缩、神经渲染移动部署、帧率优化、Vulkan/Metal 优化等
- **质量指标**: PSNR, SSIM, LPIPS, FPS, 帧时间, 功耗, GPU 显存占用, Draw Call 数, 三角形吞吐量
- **硬件约束**: 移动端 GPU (Adreno/Mali/Apple GPU), 有限 VRAM 和带宽, 功耗与温控预算
