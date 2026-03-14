# AI-Researcher 技术报告

## 1. 项目概述

**AI-Researcher** 是由 Stanford NLP 团队（Chenglei Si, Diyi Yang, Tatsunori Hashimoto）开发的 LLM 驱动的研究创意生成智能体（Research Ideation Agent）。该项目对应两篇学术论文：

1. **"Can LLMs Generate Novel Research Ideas? A Large-Scale Human Study with 100+ NLP Researchers"** (ICLR 2025) — 创意生成研究
2. **"The Ideation–Execution Gap: Execution Outcomes of LLM-Generated versus Human Research Ideas"** — 创意执行研究

**核心发现**：LLM 生成的研究创意在新颖性上被专家评审评为高于人类专家，但在实际执行后，LLM 创意的分数下降幅度显著大于人类创意，甚至在多数指标上被人类创意反超。

**许可证**：MIT License (Copyright 2024, Chenglei Si)

---

## 2. 项目结构

```
AI-Researcher/
├── ai_researcher/              # 核心代码
│   ├── src/                    # 主要模块实现（~30个Python文件）
│   ├── scripts/                # 运行各模块的Shell脚本
│   └── prompts/                # Prompt模板和Few-shot示例
├── reviews_ideation/           # 创意研究的评审数据与统计分析
│   ├── data_points_all_anonymized.json
│   ├── stats_overall.py        # 总体统计检验
│   ├── stats_per_idea.py       # 按创意统计
│   ├── stats_per_reviewer.py   # 按评审人统计
│   └── stats_per_topic.py      # 按主题统计
├── reviews_execution/          # 执行研究的评审数据与统计分析
│   ├── data_points_all_execution.json
│   ├── stats_overall.py
│   ├── stats_overall_controls.py
│   ├── stats_per_idea.py
│   └── compare_change.py       # 执行前后分数对比
├── data/backups/               # 数据备份目录
├── figures/                    # 论文配图
├── requirements.txt            # Python依赖
└── README.md
```

---

## 3. 技术架构与流水线

系统采用 **六阶段顺序流水线** 架构，输入为自然语言描述的研究主题，输出为排序后的详细项目提案。

### 3.1 Pipeline 总览

```
研究主题 → [1]文献检索 → [2]创意生成 → [3]创意去重 → [4]提案展开 → [5]提案排序 → [6]提案过滤 → 最终提案
```

### 3.2 各模块详解

#### 模块 1: Related Paper Search (`lit_review.py` + `lit_review_tools.py`)

**功能**：基于给定主题或创意，通过 Semantic Scholar API 迭代搜索和评分相关论文。

**技术细节**：
- 使用三种查询类型：`KeywordQuery`（关键词搜索）、`PaperQuery`（相似论文推荐）、`GetReferences`（引用追溯）
- LLM 负责生成搜索查询并对检索到的论文进行相关性评分（1-10分）
- 迭代扩展策略：以高分论文为锚点，不断生成新查询直到达到论文库上限（默认120篇）
- 论文去重基于 paperId、标题、摘要三重判断
- 过滤启发式规则：排除 survey、review、position paper

**外部API**：
- Semantic Scholar Graph API (`/graph/v1/paper/search/`)
- Semantic Scholar Recommendations API (`/recommendations/v1/papers/forpaper/`)

#### 模块 2: Grounded Idea Generation (`grounded_idea_gen.py`)

**功能**：基于主题和检索论文，批量生成研究创意。

**技术细节**：
- 支持 RAG 模式（将检索到的论文作为背景知识注入 prompt）和非 RAG 模式
- 每批生成 5 个创意（`ideas_n=5`），通过不同随机种子多次运行积累（论文中为每主题生成 4000 个种子创意）
- 创意结构化为五个维度：Problem、Existing Methods、Motivation、Proposed Method、Experiment Plan
- 增量生成：每次生成时将已有创意名称作为约束，避免重复
- Prompt 中包含 few-shot 示例（来自 `prompts/idea_examples_*.json`）
- 支持按方法类型区分（prompting / finetuning / general）

#### 模块 3: Idea Deduplication (`dedup_ideas.py` + `analyze_ideas_semantic_similarity.py`)

**功能**：去除语义重复的创意。

**技术细节**：
- 使用 `sentence-transformers` 库（`all-MiniLM-L6-v2` 模型）计算创意的语义嵌入
- 预计算余弦相似度矩阵并缓存为 `.npy` 文件
- 贪心去重：按顺序遍历，将与已保留创意相似度 > 0.8 的标记为重复
- 不消耗 API 额度（纯本地计算）

#### 模块 4: Project Proposal Generation (`experiment_plan_gen.py`)

**功能**：将简短创意扩展为包含完整实验设计的详细项目提案。

**提案结构**（7个部分）：
1. Title — 论文标题
2. Problem Statement — 问题定义与重要性
3. Motivation — 现有方法不足与新方法灵感
4. Proposed Method — 详细方法步骤
5. Step-by-Step Experiment Plan — 数据集、模型、指标、Prompt 示例
6. Test Case Examples — 基线失败 + 新方法成功的具体案例
7. Fallback Plan — 备选方案

**约束设计**：
- 面向 black-box LLM API 场景（GPT/Claude/Gemini），避免大规模预训练
- 方法论一致性检查（如使用 black-box API 则不应包含 white-box 操作）

#### 模块 5: Project Proposal Ranking (`tournament_ranking.py`)

**功能**：对所有提案进行排序。

**技术细节**：
- 采用 **锦标赛排序**（Swiss-system tournament）
- LLM 作为评委，两两比较判断哪个提案更好
- 默认进行 5 轮比赛，基于累计得分排序
- 第一轮随机配对，后续轮次按当前得分就近配对
- 评判方式支持 zero-shot 和 few-shot-cot 两种模式
- 保存每轮分数和 Top-10 提案详细内容

#### 模块 6: Project Proposal Filtering (`filter_ideas.py`)

**功能**：对排序后的提案进行多维度质量过滤。

**包含 6 项检查**（串行执行，任一不通过即淘汰）：
| 检查项 | 功能 |
|--------|------|
| Consistency Check | 方法论一致性（black-box vs white-box） |
| Feasibility Check | 实验可行性（数据集是否可获取） |
| Significance Check | 问题重要性 |
| Relevance Check | 与主题相关性 |
| Self-Novelty Check | LLM 自评新颖性 |
| Retrieval-Novelty Check | 基于检索的新颖性验证（最严格，逐一比对 Top-10 相似论文） |

---

## 4. 技术栈与依赖

### 4.1 LLM 后端（多模型支持）

| 提供商 | 模型 | 用途 |
|--------|------|------|
| Anthropic | Claude 3.5 Sonnet, Claude 3 Opus | 主力模型（创意生成、排序、评审） |
| OpenAI | GPT-4o, o1-preview, o1-mini | 备选模型 |
| Together AI | Llama 3.1 (8B/70B/405B), Qwen 2.5-72B, QwQ-32B | 开源模型支持 |

### 4.2 核心依赖

```
anthropic==0.34.1          # Anthropic Claude API
openai==1.42.0             # OpenAI API
sentence_transformers==3.0.1  # 语义嵌入（去重）
requests==2.32.3           # Semantic Scholar API 调用
numpy==1.22.4              # 数值计算
pandas==2.0.3              # 数据分析
matplotlib==3.7.4          # 可视化
nltk==3.8.1                # 文本处理
datasets==2.18.0           # HuggingFace Datasets
retry==0.9.2               # API 重试机制
tqdm==4.66.1               # 进度条
```

### 4.3 外部服务

- **Semantic Scholar API**：论文搜索、推荐、引用关系
- **OpenAI API**：LLM 推理
- **Anthropic API**：LLM 推理
- **Together API**：开源模型推理

---

## 5. Prompt 工程策略

项目大量使用精心设计的 prompt，体现了以下策略：

1. **角色设定**：根据任务设定不同角色（"expert researcher"、"professor"、"reviewer"）
2. **结构化输出**：要求 JSON 格式输出，便于程序解析
3. **Few-shot 示例**：提供丰富的示例（`prompts/` 目录下超过 400KB 的示例文件）
4. **约束注入**：明确告知 LLM 避免的行为（如避免大规模预训练、避免人工标注）
5. **创意激发**："we love unhinged ideas that sound crazy" 的措辞鼓励创新
6. **去重约束**：将已生成创意列表注入 prompt，要求新创意必须不同

---

## 6. 统计分析框架

`reviews_ideation/` 和 `reviews_execution/` 目录包含了完整的统计分析代码：

### 6.1 创意研究（Ideation Study）

- **评审指标**：overall_score, novelty_score, feasibility_score, effectiveness_score, excitement_score
- **实验条件**：AI（纯LLM生成）、Human（人类专家）、AI_Rerank（AI生成+人类重排）
- **统计方法**：
  - Welch's t-test（不等方差 t 检验）
  - Bonferroni 校正（多重比较）
  - 混合效应模型（statsmodels）
  - 按评审人/主题的分层分析

### 6.2 执行研究（Execution Study）

- **评审指标**：novelty_score, excitement_score, soundness_score, effectiveness_score, overall_score
- **分析内容**：
  - AI vs Human 执行后分数比较（单尾 t 检验）
  - FDR-BH 校正
  - 执行前后分数变化对比（`compare_change.py`）
  - 相关性分析（`correlation_pre_and_post_execution.py`）

---

## 7. 代码执行支持

项目还包含将 LLM 生成的提案自动转化为可执行代码并运行的功能：

- `execution_code_gen.py`：生成实验代码
- `execution_result_check.py`：检查执行结果
- `execute.py`：批量运行生成的 Python 脚本，记录日志，统计成功率

---

## 8. 成本分析

根据 README 和代码中的记录，运行 demo pipeline 的典型成本：

| 阶段 | 成本（美元） |
|------|-------------|
| 文献检索（50篇） | ~$0.51 |
| 创意生成（20个种子） | ~$0.85 |
| 去重 | $0（本地计算） |
| 提案展开（10个） | ~$2.9 |
| 排序（10个，5轮） | ~$0.74 |
| 过滤（每个提案） | ~$1.9 |
| **Demo 总计** | **~$7** |

完整实验（每主题 4000 创意）的成本会显著更高。

---

## 9. 设计亮点与局限

### 亮点

1. **端到端自动化**：从主题到可执行提案的完整流水线
2. **多层质量把控**：去重 → 排序 → 六维过滤，层层筛选
3. **检索增强生成（RAG）**：通过 Semantic Scholar 实时检索论文，确保创意的接地性
4. **多模型兼容**：统一接口支持 OpenAI / Anthropic / Together AI，便于模型对比实验
5. **统计严谨性**：配套完整的统计检验代码，支持论文中的定量结论

### 局限

1. **错误处理粗糙**：大量 bare `except` 语句，可能掩盖重要错误
2. **硬编码路径**：部分文件包含开发者本地路径（如 `/Users/clsi/Desktop/`）
3. **模块耦合**：`lit_review_tools.py` 在模块级直接读取 `keys.json`，不利于测试和复用
4. **缺乏类型注解**：所有函数均无 type hints
5. **成本优化空间**：部分操作（如逐一论文新颖性检查）成本较高，可考虑批处理优化
6. **`calc_price` 中的 bug**：`if "qwen2.5-72b" or "qwq-32b" in model.lower()` 条件永远为 True（Python 运算符优先级问题）

---

## 10. 总结

AI-Researcher 是一个完整的 **LLM-for-Science** 系统原型，展示了如何利用大语言模型自动化科研创意生成的全流程。其核心价值在于：

- 提供了一个可复现的、端到端的研究创意生成基准系统
- 配套了大规模人类评估数据（100+ NLP 研究者参与）
- 揭示了 LLM 创意生成的"创意-执行鸿沟"——LLM 擅长产生新颖创意，但这些创意在实际执行中的表现可能不如人类创意稳健

该项目对于理解 LLM 在科研辅助中的能力边界具有重要参考价值。
