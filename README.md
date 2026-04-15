# GrowthLoop AI - AIGC 产品增长运营 Agent 系统

> AI 驱动的增长实验平台 — 从行业调研到知识沉淀的完整自动化闭环

---

## 一句话介绍

围绕 AIGC 产品用户全生命周期（注册→浏览→首次使用→活跃→付费），搭建 6 个专业 Agent 组成的增长引擎，将传统需要数周的增长实验流程压缩到分钟级。

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      GrowthLoop 编排器                       │
│  熔断器 │ 可观测性 │ 分级自治 │ 上下文裁剪                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
     ┌─────────────────┼─────────────────┐
     ▼                 ▼                 ▼
┌─────────┐     ┌─────────────┐   ┌─────────────┐
│诊断 Agent │ →  │识别 Agent   │ → │行动 Agent   │
│漏斗分析  │     │用户分层(RFM)│   │策略+内容生成 │
└─────────┘     └─────────────┘   └────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
              ┌──────────┐         ┌──────────┐          ┌──────────┐
              │验证 Agent │   →    │学习 Agent │   →    │下一轮循环 │
              │A/B测试   │         │知识沉淀  │          │越用越聪明 │
              └──────────┘         └──────────┘          └──────────┘
```

---

## 6 个核心 Agent

| Agent | 职责 | 关键技术 |
|-------|------|---------|
| **漏斗诊断** | 自动分析转化率，对比行业基准，定位最严重流失环节 | 累计计数 + 行业基准比对 |
| **用户分层** | 综合评分模型（RFM + 流失风险 + 使用深度）精准定位高优群体 | RFM 模型 + 优先级评分 |
| **策略推荐** | 基于知识库 + AIGC 行业洞察，推荐增长策略和信息框架 | LLM + 策略知识库 |
| **内容生成** | 生成 3 版个性化触达内容，各附可验证假设 | Prompt 模板 + LLM |
| **A/B 测试** | 统计检验与商业影响分析（实验执行层对接外部渠道系统） | Z-test / 卡方检验 + 效应量计算 |
| **增长记忆** | 沉淀实验结果，供下一轮参考，系统越用越聪明 | JSON 持久化 + 策略评分 |

---

## Harness Engineering — 系统可靠性保障

| 能力 | 说明 |
|------|------|
| **熔断器** | Agent 连续 3 次失败自动降级，防止无限重试，300 秒冷却后重试 |
| **可观测性** | 结构化事件日志（JSONL 持久化）、Token 消耗追踪、Agent 决策回溯 |
| **分级自治** | 4 级权限控制：manual → review → auto_safe → auto |
| **上下文裁剪** | 每个 Agent 只继承它需要的上下文，避免数据泄露和冗余 |

---

## Agent 质量评估 — 30 项自动化测试

每个 Agent 经过多维度评估，产出 0-100 分量化报告：

| 评估维度 | 覆盖 Agent | 说明 |
|----------|-----------|------|
| 正常数据 | 全部 6 个 | 标准输入下的正确性 |
| 边界条件 | 漏斗/分层/策略/内容 | 零转化、空数据、单用户、缺失字段 |
| LLM 输出质量 | 策略/内容 | 输出完整性、JSON 解析鲁棒性 |
| 统计准确性 | A/B 测试 | 显著/非显著结果判断、统计检验准确性 |
| 持久化 | 增长记忆 | 数据持久化与恢复 |

**评估流程**：`跑分 → 诊断失败 → 修复代码 → 复测`

```bash
# 运行质量评估
python tests/benchmark.py

# 自动化评估流水线
python scripts/harness_loop.py
```

---

## 快速开始

### 1. 安装依赖

```bash
git clone <repo-url>
cd ai-growth-ops-agent
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

### 2. 配置 API Key（可选）

```bash
cp .env.example .env
# 编辑 .env，填入阿里云百炼 / OpenAI API Key
```

> **无需 API Key 也能体验**：内置实验室模式（预计算模型输出），可直接查看完整工作流结果。

### 3. 运行 Streamlit 演示

```bash
streamlit run app.py
```

### 4. 体验方式

| 模式 | 操作 | 说明 |
|------|------|------|
| **一键演示** | 侧边栏点击「一键演示」 | 5 秒加载完整工作流结果，适合面试快速展示 |
| **逐步演示** | 一键演示后切换「逐步演示」 | 分 6 步浏览，每步展示对应 Agent 输出 |
| **实验室模式** | 侧边栏「加载模拟数据」 | 加载数据 + 预计算结果，逐步点击「查看结果」 |
| **实时调用** | 配置 API Key + 上传数据 | 每一步真实调用 LLM，用于深度验证 |

---

## 项目结构

```
ai-growth-ops-agent/
├── app.py                        # Streamlit 主应用（仪表盘 + 逐步演示）
├── requirements.txt
│
├── core/                         # 核心引擎
│   ├── orchestrator.py           # 增长周期编排器（串联所有 Agent）
│   ├── llm_client.py             # LLM API 封装（百炼/OpenAI/硅基流动）
│   ├── data_models.py            # 统一数据模型（Pydantic dataclass）
│   ├── circuit_breaker.py        # 熔断器（连续失败自动降级）
│   ├── observability.py          # 可观测性（事件日志 + Token 追踪）
│   ├── logger.py                 # 日志
│   └── prompt_templates.py       # 营销场景 Prompt 模板
│
├── agents/                       # 6 个专业 Agent
│   ├── funnel_agent.py           # 漏斗诊断
│   ├── segmentation_agent.py     # 用户分层（RFM）
│   ├── strategy_agent.py         # 策略推荐
│   ├── content_agent.py          # 内容生成
│   ├── ab_test_agent.py          # A/B 测试
│   └── growth_memory.py          # 增长记忆
│
├── utils/                        # 工具模块
│   ├── stats.py                  # 统计检验（Z-test / 卡方 / 样本量）
│   └── rfm.py                    # RFM 分层模型
│
├── tests/                        # 质量评估
│   └── benchmark.py              # 30 项自动化测试
│
├── scripts/                      # 脚本
│   └── harness_loop.py           # 自动化评估流水线
│
├── data/
│   ├── mock_users_saas.csv       # 模拟用户数据（500 条，19 个字段）
│   ├── demo_cycle_results.json   # 实验室模式预计算结果
│   └── insight_engine.py         # AIGC 行业洞察引擎
│
└── api/                          # FastAPI REST 服务（可选）
    └── server.py
```

---

## 技术栈

| 类别 | 技术 |
|------|------|
| **核心语言** | Python 3.11+ |
| **数据处理** | Pandas, NumPy, Scipy |
| **可视化** | Matplotlib, Streamlit |
| **AI/LLM** | openai SDK（兼容阿里云百炼、硅基流动） |
| **测试评估** | 自研 30 项自动化测试框架 |
| **Web 服务** | FastAPI, Uvicorn（可选） |

---

## 关键数据指标

| 指标 | 数值 |
|------|------|
| 用户评价分析 | 1000+ 条评价，TF-IDF + 情感分析 |
| 竞品覆盖 | 467 款 AIGC 工具，7 大品类 |
| Prompt 场景分析 | 25 万条 Midjourney Prompt 聚类 |
| Agent 质量评分 | 30 项测试，0-100 分量分 |
| A/B 测试方法 | Z-test 比例检验 + 卡方检验 |
| 转化优化预估 | 8-25% 提升 |

---

## 面试演示路径

### 快速路径（3 分钟）
1. 打开应用，点击侧边栏「一键演示」
2. 查看仪表盘总览（6 行：指标 → 漏斗 → AIGC → 策略 → A/B → 工程）
3. 切换到「逐步演示」，逐步浏览 6 步工作流

### 完整路径（5 分钟）
1. 侧边栏「加载模拟数据」
2. Step 0: 查看行业调研结果（AIGC 洞察）
3. Step 1-3: 查看诊断 → 识别 → 策略生成
4. Step 4-5: 查看 A/B 测试 → 知识沉淀
5. 面试官可现场查看源代码和测试用例

---

## 实时演示工具

侧边栏内置了 5 个实时演示工具，**不需要 API Key**，面试官可现场验证系统完整性：

| 工具 | 说明 | 耗时 |
|------|------|------|
| Agent 质量评估 | 31 项测试逐条跳出，0-100 分评分 | ~10 秒 |
| 熔断器状态机 | 模拟失败，观察 CLOSED → OPEN → HALF_OPEN | ~5 秒 |
| 漏斗实时诊断 | 上传 CSV 或模拟数据，实时计算转化率 | ~2 秒 |
| A/B 检验计算器 | 输入两组数据，实时出 Z-test p 值 + 效应量 | ~1 秒 |
| RFM 用户分层 | 上传用户数据，实时算出 6 层分类 | ~3 秒 |

---

## A/B 测试模块说明

ABTestAgent 是 A/B 实验的**设计和分析引擎**，负责：
- 统计检验（Z-test 比例检验 + 卡方检验）
- 效应量计算（Cohen's h + Cramer's V）
- 商业影响估算
- 结构化分析报告生成

**实验执行层**（实际触达用户、收集转化数据）对接外部渠道系统（邮件服务商、CRM 平台），不在本系统范围内。本模块从外部系统接收实验数据后进行分析。

---

## 致谢与引用

本项目参考了以下开源项目和技术概念，完整引用说明见 [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md)：

| 引用内容 | 来源 | 使用方式 |
|---------|------|---------|
| Circuit Breaker 3 状态模式 | Netflix Hystrix | 参考概念，代码从零实现 |
| 可观测性 span/event 模型 | OpenTelemetry | 参考概念，代码从零实现 |
| 分级自治模式 | Anthropic escalation pattern | 参考概念，代码从零实现 |
| Harness Engineering 评估思路 | Harbor benchmark | 参考概念，代码从零实现 |
| Z-test / 卡方检验 | scipy.stats | 直接使用 API |
| RFM 分位数评分 | pandas pd.qcut | 直接使用 API |
| AIGC 工具数据集 | Kaggle | 用于 Insight Engine 分析 |
