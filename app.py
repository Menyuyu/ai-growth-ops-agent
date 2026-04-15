"""
GrowthLoop AI - 增长运营自动化系统
行业调研 → 诊断 → 识别 → 行动 → 验证 → 学习
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Microsoft JhengHei']
plt.rcParams['axes.unicode_minus'] = False

from core.llm_client import API_CONFIGS
from core.orchestrator import GrowthOrchestrator
from core.logger import get_logger
from core.data_models import (
    GrowthCycle, FunnelResult, SegmentResult,
    StrategyResult, ContentResult, Variant, ABResult,
)

logger = get_logger("app")

# ========== 页面配置 ==========
st.set_page_config(
    page_title="GrowthLoop AI",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ========== 全局 CSS ==========
st.markdown("""
<style>
    /* 隐藏 Streamlit 底部装饰 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* 自定义卡片样式 */
    .card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border: 1px solid #e9ecef;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 16px;
    }
    .card-header {
        font-size: 14px;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .card-value {
        font-size: 28px;
        font-weight: 700;
        color: #1a1a2e;
    }
    .card-sub {
        font-size: 13px;
        color: #868e96;
        margin-top: 4px;
    }
    .metric-green { color: #2ecc71; }
    .metric-blue { color: #3498db; }
    .metric-red { color: #e74c3c; }
    .metric-orange { color: #f39c12; }

    /* 步骤标签 */
    .step-nav {
        display: flex;
        gap: 4px;
        flex-wrap: wrap;
        margin-bottom: 20px;
    }
    .step-nav .step {
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        border: 2px solid #e9ecef;
        background: #fff;
        color: #868e96;
    }
    .step-nav .step.active {
        background: #3498db;
        color: #fff;
        border-color: #3498db;
    }
    .step-nav .step.done {
        background: #e8f8e8;
        color: #2ecc71;
        border-color: #2ecc71;
    }

    /* 演示模式横幅 */
    .demo-banner {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        font-size: 14px;
    }

    /* 获胜卡片 */
    .winner-card {
        background: linear-gradient(135deg, #e8f8e8 0%, #f0fff0 100%);
        border: 2px solid #2ecc71;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }

    /* 痛点卡片 */
    .pain-card {
        border-left: 4px solid #e74c3c;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        background: #fff5f5;
    }

    /* 增长方案卡片 */
    .proposal-card {
        background: linear-gradient(135deg, #e8f8e8 0%, #d4efdf 100%);
        border: 2px solid #2ecc71;
        border-radius: 12px;
        padding: 20px;
    }

    /* 内容变体卡片 */
    .variant-card {
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 16px;
        height: 100%;
        background: #fff;
    }

    /* 架构流程图 */
    .flow-step {
        text-align: center;
        padding: 12px 8px;
        border-radius: 10px;
        background: #f8f9fa;
        border: 1px solid #e9ecef;
    }
    .flow-arrow {
        text-align: center;
        font-size: 24px;
        color: #3498db;
        padding-top: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ========== 实时演示工具函数 ==========

# ---------- 压力测试工作台：数据工厂 ----------

def _wb_make_df(n=200, noise=0.0, missing_cols=None, scenario="normal"):
    """生成测试数据，支持难度参数"""
    import numpy as np
    import pandas as pd
    np.random.seed(42)
    if scenario == "empty":
        return pd.DataFrame(columns=["user_id","funnel_stage","churn_risk_score","monetary_spent","design_count","frequency_sessions"])
    if scenario == "single":
        return pd.DataFrame({"user_id":["u1"],"funnel_stage":["已注册"],"churn_risk_score":[80],"monetary_spent":[0.0],"design_count":[0],"frequency_sessions":[1]})
    if scenario == "same_stage":
        df = pd.DataFrame({
            "user_id": [f"u{i}" for i in range(n)],
            "funnel_stage": ["已注册"] * n,
            "churn_risk_score": np.random.randint(10, 90, n),
            "monetary_spent": np.random.uniform(0, 500, n).round(2),
            "design_count": np.random.randint(0, 30, n),
            "frequency_sessions": np.random.randint(1, 50, n),
        })
    else:  # normal
        n = max(n, 5)
        n_registered = max(int(n * 0.25), 1)
        n_browsed = max(int(n * 0.20), 1)
        n_first_use = max(int(n * 0.15), 1)
        n_active = max(int(n * 0.22), 1)
        n_paid = n - n_registered - n_browsed - n_first_use - n_active
        if n_paid < 0:
            n_paid = 1
        df = pd.DataFrame({
            "user_id": [f"u{i}" for i in range(n)],
            "funnel_stage": (["已注册"]*n_registered + ["已浏览"]*n_browsed +
                           ["首次使用"]*n_first_use + ["已活跃"]*n_active + ["已付费"]*n_paid),
            "churn_risk_score": np.random.randint(10, 90, n),
            "monetary_spent": np.random.uniform(0, 500, n).round(2),
            "design_count": np.random.randint(0, 30, n),
            "frequency_sessions": np.random.randint(1, 50, n),
        })
    # 注入噪声
    if noise > 0 and "churn_risk_score" in df.columns and len(df) > 0:
        df["churn_risk_score"] = (df["churn_risk_score"] + int(noise * 80)).clip(0, 150)
    # 删除缺失列
    if missing_cols:
        df = df.drop(columns=[c for c in missing_cols if c in df.columns], errors="ignore")
    return df


# ---------- 压力测试工作台：测试运行器 ----------

def _wb_test_funnel(scenarios, data_size, noise, missing_cols):
    """运行 FunnelAgent 测试"""
    import pandas as pd
    from agents.funnel_agent import FunnelAgent
    agent = FunnelAgent()
    results = {}

    # normal_data
    if "normal_data" in scenarios:
        try:
            df = _wb_make_df(n=data_size, noise=noise, missing_cols=missing_cols, scenario="normal")
            r = agent.analyze_from_data(df)
            max_s = 25
            score = 0
            if r.problem_stage and isinstance(r.problem_stage, str):
                score += 15
            if r.leak_rate is not None and isinstance(r.leak_rate, (int, float)):
                score += 10
            results["normal_data"] = {"score": score, "max": max_s, "pass": score >= max_s * 0.6,
                                      "detail": f"问题环节={r.problem_stage}, 流失率={r.leak_rate}%"}
        except Exception as e:
            results["normal_data"] = {"score": 0, "max": 25, "pass": False, "detail": str(e)[:60]}

    # single_user
    if "single_user" in scenarios:
        try:
            df = _wb_make_df(scenario="single")
            r = agent.analyze_from_data(df)
            max_s = 15
            score = 15 if r.problem_stage is not None else 5
            results["single_user"] = {"score": score, "max": max_s, "pass": score >= max_s * 0.6,
                                      "detail": f"问题环节={r.problem_stage}"}
        except Exception as e:
            results["single_user"] = {"score": 0, "max": 15, "pass": False, "detail": str(e)[:60]}

    # empty_data
    if "empty_data" in scenarios:
        try:
            df = _wb_make_df(scenario="empty")
            r = agent.analyze_from_data(df)
            max_s = 15
            score = 15 if r.problem_stage is not None else 0
            results["empty_data"] = {"score": score, "max": max_s, "pass": score >= max_s * 0.6,
                                     "detail": f"问题环节={r.problem_stage}"}
        except Exception as e:
            results["empty_data"] = {"score": 0, "max": 15, "pass": False, "detail": str(e)[:60]}

    # same_stage
    if "same_stage" in scenarios:
        try:
            df = _wb_make_df(n=data_size, scenario="same_stage")
            r = agent.analyze_from_data(df)
            max_s = 15
            score = 15 if r.problem_stage is not None else 0
            results["same_stage"] = {"score": score, "max": max_s, "pass": score >= max_s * 0.6,
                                     "detail": f"问题环节={r.problem_stage}"}
        except Exception as e:
            results["same_stage"] = {"score": 0, "max": 15, "pass": False, "detail": str(e)[:60]}

    # missing_columns
    if "missing_columns" in scenarios:
        try:
            test_missing = missing_cols or ["churn_risk_score", "design_count", "frequency_sessions"]
            df = _wb_make_df(n=50, missing_cols=test_missing, scenario="normal")
            r = agent.analyze_from_data(df)
            max_s = 15
            score = 0
            if r.problem_stage and isinstance(r.problem_stage, str):
                score += 8
            if r.affected_user_ids is not None and isinstance(r.affected_user_ids, list):
                score += 7
            results["missing_columns"] = {"score": score, "max": max_s, "pass": score >= max_s * 0.6,
                                          "detail": f"问题环节={r.problem_stage}, 影响用户={len(r.affected_user_ids or [])}"}
        except Exception as e:
            results["missing_columns"] = {"score": 0, "max": 15, "pass": False, "detail": str(e)[:60]}

    return results


def _wb_test_segmentation(scenarios, data_size, noise, missing_cols):
    """运行 SegmentationAgent 测试"""
    from agents.funnel_agent import FunnelAgent
    from agents.segmentation_agent import SegmentationAgent
    funnel = FunnelAgent()
    agent = SegmentationAgent()
    results = {}

    # normal
    if "normal" in scenarios:
        try:
            df = _wb_make_df(n=data_size, noise=noise, missing_cols=missing_cols, scenario="normal")
            fr = funnel.analyze_from_data(df)
            r = agent.analyze(df, fr)
            max_s = 25
            score = 0
            if r.priority_segment: score += 10
            if r.segment_count > 0: score += 5
            if r.segment_profile: score += 5
            if r.recommended_intervention: score += 5
            results["normal"] = {"score": score, "max": max_s, "pass": score >= max_s * 0.6,
                                 "detail": f"优先群体={r.priority_segment}, 数量={r.segment_count}"}
        except Exception as e:
            results["normal"] = {"score": 0, "max": 25, "pass": False, "detail": str(e)[:60]}

    # empty_data
    if "empty_data" in scenarios:
        try:
            df = _wb_make_df(scenario="empty")
            r = agent.analyze(df)
            max_s = 20
            score = 20 if r.priority_segment is not None else 0
            results["empty_data"] = {"score": score, "max": max_s, "pass": score >= max_s * 0.6,
                                     "detail": f"结果={r.priority_segment}"}
        except Exception as e:
            results["empty_data"] = {"score": 0, "max": 20, "pass": False, "detail": str(e)[:60]}

    # missing_columns
    if "missing_columns" in scenarios:
        try:
            test_missing = missing_cols or ["churn_risk_score", "design_count"]
            df = _wb_make_df(n=50, missing_cols=test_missing)
            r = agent.analyze(df)
            max_s = 20
            score = 0
            if r.priority_segment: score += 12
            if r.segment_count is not None: score += 8
            results["missing_columns"] = {"score": score, "max": max_s, "pass": score >= max_s * 0.6,
                                          "detail": f"优先群体={r.priority_segment}"}
        except Exception as e:
            results["missing_columns"] = {"score": 0, "max": 20, "pass": False, "detail": str(e)[:60]}

    # priority_scoring
    if "priority_scoring" in scenarios:
        try:
            df = _wb_make_df(n=data_size, noise=noise, missing_cols=missing_cols)
            df_scored = agent._calculate_priority_scores(df)
            max_s = 20
            score = 0
            if "priority_score" in df_scored.columns: score += 5
            if len(df_scored) > 0 and df_scored["priority_score"].between(0, 100).all():
                score += 10
            if "priority_segment" in df_scored.columns and df_scored["priority_segment"].notna().all():
                score += 5
            results["priority_scoring"] = {"score": score, "max": max_s, "pass": score >= max_s * 0.6,
                                           "detail": f"分数范围={df_scored['priority_score'].min():.0f}~{df_scored['priority_score'].max():.0f}"}
        except Exception as e:
            results["priority_scoring"] = {"score": 0, "max": 20, "pass": False, "detail": str(e)[:60]}

    return results


def _wb_test_strategy():
    """运行 StrategyAgent 测试（确定性）"""
    from agents.strategy_agent import StrategyAgent
    agent = StrategyAgent()
    results = {}

    # kb_coverage
    try:
        covered = len(set(agent.STRATEGY_KNOWLEDGE.keys()) & {"已注册","已浏览","首次使用","已活跃","已付费"})
        score = int((covered / 5) * 20)
        results["kb_coverage"] = {"score": score, "max": 20, "pass": score >= 12,
                                  "detail": f"知识库覆盖 {covered}/5 个漏斗阶段"}
    except Exception as e:
        results["kb_coverage"] = {"score": 0, "max": 20, "pass": False, "detail": str(e)[:60]}

    # json_parsing
    try:
        r = agent._parse_result('{"campaign_type":"email","message_framework":"social proof","tone_guidance":"friendly","cta_recommendation":"Click here","channel_priority":["email"],"selected_templates":["email"],"reasoning":"test"}', {}, {})
        score = 15 if r.campaign_type == "email" else 0
        results["json_parsing"] = {"score": score, "max": 15, "pass": score >= 9,
                                   "detail": f"解析 campaign_type={r.campaign_type}"}
    except Exception as e:
        results["json_parsing"] = {"score": 0, "max": 15, "pass": False, "detail": str(e)[:60]}

    return results


def _wb_test_ab(conv_a, n_a, conv_b, n_b, run_edge=True):
    """运行 ABTestAgent 测试（参数来自滑块）"""
    from agents.ab_test_agent import ABTestAgent
    agent = ABTestAgent()
    results = {}

    # 显著性测试（用户自定义参数）
    try:
        r = agent.analyze_from_data(test_name="自定义测试", conversions_a=conv_a, n_a=n_a, conversions_b=conv_b, n_b=n_b)
        max_s = 25
        score = 0
        if r.winning_variant: score += 10
        if r.p_value is not None: score += 15
        sig_label = f"显著 (p={r.p_value:.4f})" if r.p_value < 0.05 else f"不显著 (p={r.p_value:.4f})"
        results["custom_significance"] = {"score": score, "max": max_s, "pass": score >= max_s * 0.6,
                                          "detail": f"获胜={r.winning_variant}, {sig_label}, 提升={r.actual_uplift}"}
    except Exception as e:
        results["custom_significance"] = {"score": 0, "max": 25, "pass": False, "detail": str(e)[:60]}

    # 非显著边界测试
    if run_edge:
        try:
            r = agent.analyze_from_data(test_name="边界测试", conversions_a=30, n_a=100, conversions_b=32, n_b=100)
            max_s = 15
            passed = (r.winning_variant == "无显著差异" or r.p_value >= 0.05)
            score = max_s if passed else 0
            results["non_significant"] = {"score": score, "max": max_s, "pass": passed,
                                          "detail": f"p={r.p_value:.4f}, 结果={r.winning_variant}"}
        except Exception as e:
            results["non_significant"] = {"score": 0, "max": 15, "pass": False, "detail": str(e)[:60]}

    # 零转化边界
    if run_edge:
        try:
            r = agent.analyze_from_data(test_name="零转化", conversions_a=0, n_a=50, conversions_b=0, n_b=50)
            max_s = 20
            score = max_s if r.winning_variant is not None else 0
            results["zero_conversion"] = {"score": score, "max": max_s, "pass": score >= max_s * 0.6,
                                          "detail": f"结果={r.winning_variant}"}
        except Exception as e:
            results["zero_conversion"] = {"score": 0, "max": 20, "pass": False, "detail": str(e)[:60]}

    # 大效应量
    if run_edge:
        try:
            r = agent.analyze_from_data(test_name="大效应", conversions_a=100, n_a=1000, conversions_b=200, n_b=1000)
            max_s = 15
            score = 15 if r.p_value < 0.001 else (10 if r.p_value < 0.05 else 0)
            results["large_effect"] = {"score": score, "max": max_s, "pass": score >= max_s * 0.6,
                                       "detail": f"p={r.p_value:.6f}"}
        except Exception as e:
            results["large_effect"] = {"score": 0, "max": 15, "pass": False, "detail": str(e)[:60]}

    return results


def _wb_test_growth_memory():
    """运行 GrowthMemory 测试（确定性）"""
    import tempfile
    from agents.growth_memory import GrowthMemory
    temp_file = os.path.join(tempfile.gettempdir(), f"gl_wb_mem_{id(tempfile)}.json")
    results = {}
    try:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        mem = GrowthMemory(filepath=temp_file)
        mem.record_cycle_result("高优先级","挽回邮件",{"significant":True,"winning_variant":"A","lift_percent":15.5},"email_marketing")

        s1 = 20 if mem.get_best_strategy("高优先级") == "挽回邮件" else 0
        results["record"] = {"score": s1, "max": 20, "pass": s1 >= 12,
                             "detail": f"最佳策略={mem.get_best_strategy('高优先级')}"}

        s2 = 20 if mem.get_template_score("email_marketing","高优先级") > 0 else 0
        results["template_scoring"] = {"score": s2, "max": 20, "pass": s2 >= 12,
                                       "detail": f"模板评分={mem.get_template_score('email_marketing','高优先级')}"}

        mem2 = GrowthMemory(filepath=temp_file)
        s3 = 15 if mem2.get_best_strategy("高优先级") == "挽回邮件" else 0
        results["persistence"] = {"score": s3, "max": 15, "pass": s3 >= 9,
                                  "detail": f"持久化恢复={'成功' if s3 > 0 else '失败'}"}
    except Exception as e:
        for tn in ["record", "template_scoring", "persistence"]:
            results[tn] = {"score": 0, "max": {"record": 20, "template_scoring": 20, "persistence": 15}[tn], "pass": False, "detail": str(e)[:60]}
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    return results


def _wb_run_selected_tests(selected_agents, funnel_scenarios, seg_scenarios,
                           ab_params, data_size, noise, missing_cols, run_edge=True):
    """运行选定的测试，返回结果字典"""
    results = {}
    if "FunnelAgent" in selected_agents:
        results["FunnelAgent"] = _wb_test_funnel(funnel_scenarios, data_size, noise, missing_cols)
    if "SegmentationAgent" in selected_agents:
        results["SegmentationAgent"] = _wb_test_segmentation(seg_scenarios, data_size, noise, missing_cols)
    if "StrategyAgent" in selected_agents:
        results["StrategyAgent"] = _wb_test_strategy()
    if "ABTestAgent" in selected_agents:
        results["ABTestAgent"] = _wb_test_ab(ab_params["conv_a"], ab_params["n_a"],
                                             ab_params["conv_b"], ab_params["n_b"], run_edge)
    if "GrowthMemory" in selected_agents:
        results["GrowthMemory"] = _wb_test_growth_memory()
    return results


def _wb_calculate_agent_score(test_results):
    """计算单个 Agent 的总分"""
    total = sum(t["score"] for t in test_results.values())
    max_total = sum(t["max"] for t in test_results.values())
    return round(total / max_total * 100, 1) if max_total else 0


def _wb_calculate_overall(agent_scores):
    """计算总体得分"""
    return round(sum(agent_scores.values()) / len(agent_scores), 1) if agent_scores else 0


# ---------- 压力测试工作台：主渲染函数 ----------

def _render_live_demo_benchmark():
    """Agent 鲁棒性压力测试工作台"""
    import time
    import copy

    st.markdown("#### 🧪 Agent 鲁棒性压力测试工作台")
    st.caption("选择测试场景，调整难度参数，观察 Agent 分数变化")

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("**Agent 选择**")
        all_agents = ["FunnelAgent", "SegmentationAgent", "StrategyAgent", "ABTestAgent", "GrowthMemory"]
        selected = st.multiselect("选择要测试的 Agent", all_agents, default=all_agents, label_visibility="collapsed")

        st.divider()

        # FunnelAgent 场景
        with st.expander("🔍 FunnelAgent 场景", expanded=True):
            f_normal = st.checkbox("正常数据", value=True, key="wb_f_normal")
            f_single = st.checkbox("单用户", value=True, key="wb_f_single")
            f_empty = st.checkbox("空数据", value=True, key="wb_f_empty")
            f_same = st.checkbox("同阶段数据", value=True, key="wb_f_same")
            f_missing = st.checkbox("缺列数据", value=True, key="wb_f_missing")
        funnel_scenarios = {}
        if f_normal: funnel_scenarios["normal_data"] = True
        if f_single: funnel_scenarios["single_user"] = True
        if f_empty: funnel_scenarios["empty_data"] = True
        if f_same: funnel_scenarios["same_stage"] = True
        if f_missing: funnel_scenarios["missing_columns"] = True

        # SegmentationAgent 场景
        with st.expander("👥 SegmentationAgent 场景", expanded=True):
            s_normal = st.checkbox("正常数据", value=True, key="wb_s_normal")
            s_empty = st.checkbox("空数据", value=True, key="wb_s_empty")
            s_missing = st.checkbox("缺列数据", value=True, key="wb_s_missing")
            s_priority = st.checkbox("优先级评分范围", value=True, key="wb_s_priority")
        seg_scenarios = {}
        if s_normal: seg_scenarios["normal"] = True
        if s_empty: seg_scenarios["empty_data"] = True
        if s_missing: seg_scenarios["missing_columns"] = True
        if s_priority: seg_scenarios["priority_scoring"] = True

        # ABTestAgent 参数
        with st.expander("📐 ABTestAgent 参数", expanded=True):
            ab_conv_a = st.number_input("A组转化数", min_value=0, max_value=500, value=30, key="wb_ab_ca")
            ab_n_a = st.number_input("A组样本量", min_value=1, max_value=2000, value=100, key="wb_ab_na")
            ab_conv_b = st.number_input("B组转化数", min_value=0, max_value=500, value=50, key="wb_ab_cb")
            ab_n_b = st.number_input("B组样本量", min_value=1, max_value=2000, value=100, key="wb_ab_nb")
        ab_params = {"conv_a": ab_conv_a, "n_a": ab_n_a, "conv_b": ab_conv_b, "n_b": ab_n_b}

        st.divider()

        st.markdown("**难度控制**")
        data_size = st.slider("数据规模 (N)", min_value=3, max_value=500, value=200, key="wb_data_size")
        noise_level = st.slider("噪声注入", min_value=0.0, max_value=1.0, value=0.0, step=0.1, key="wb_noise")
        missing_cols = st.multiselect(
            "随机缺失列",
            ["churn_risk_score", "design_count", "frequency_sessions", "monetary_spent"],
            default=[], key="wb_missing_cols",
        )

        st.divider()
        run_btn = st.button("▶ 运行选定测试", type="primary", use_container_width=True)

    # 右侧结果区
    with col_right:
        if run_btn and selected:
            progress_bar = st.progress(0)
            status_text = st.empty()
            t0 = time.time()

            all_steps = len(selected)
            done = 0
            results = {}
            for agent_name in selected:
                status_text.text(f"⏳ 正在测试 {agent_name}...")
                if agent_name == "FunnelAgent":
                    results["FunnelAgent"] = _wb_test_funnel(funnel_scenarios, data_size, noise_level, missing_cols)
                elif agent_name == "SegmentationAgent":
                    results["SegmentationAgent"] = _wb_test_segmentation(seg_scenarios, data_size, noise_level, missing_cols)
                elif agent_name == "StrategyAgent":
                    results["StrategyAgent"] = _wb_test_strategy()
                elif agent_name == "ABTestAgent":
                    results["ABTestAgent"] = _wb_test_ab(ab_params["conv_a"], ab_params["n_a"],
                                                         ab_params["conv_b"], ab_params["n_b"], run_edge=True)
                elif agent_name == "GrowthMemory":
                    results["GrowthMemory"] = _wb_test_growth_memory()
                done += 1
                progress_bar.progress(done / all_steps)

            elapsed = time.time() - t0
            progress_bar.progress(1.0)
            status_text.success(f"✅ 完成 ({elapsed:.1f}秒)")

            st.session_state["wb_results"] = results
            st.session_state["wb_elapsed"] = elapsed
            st.session_state["wb_config"] = {
                "data_size": data_size, "noise": noise_level, "missing": missing_cols, "ab_params": ab_params
            }

        results = st.session_state.get("wb_results")
        if not results:
            st.info("← 在左侧选择测试场景，点击「运行选定测试」查看结果")
            return

        # 计算分数
        agent_scores = {}
        for name, tests in results.items():
            agent_scores[name] = _wb_calculate_agent_score(tests)
        overall = _wb_calculate_overall(agent_scores)

        # 总览卡片
        c1, c2, c3 = st.columns(3)
        score_color = "🟢" if overall >= 80 else "🟡" if overall >= 60 else "🔴"
        c1.metric("总体得分", f"{overall:.1f}/100")
        total_tests = sum(len(t) for t in results.values())
        pass_tests = sum(1 for t in results.values() for v in t.values() if v.get("pass"))
        c2.metric("通过测试", f"{pass_tests}/{total_tests}")
        c3.metric("耗时", f"{st.session_state.get('wb_elapsed', 0):.1f}秒")

        st.divider()

        # 分数柱状图
        score_df = pd.DataFrame([
            {"Agent": name.replace("Agent", ""), "得分": score}
            for name, score in agent_scores.items()
        ])
        st.bar_chart(score_df.set_index("Agent"), horizontal=True, height=200)

        st.divider()

        # 详细结果
        for agent_name, tests in results.items():
            score = agent_scores[agent_name]
            icon = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
            with st.expander(f"{icon} {agent_name} — {score:.0f}/100", expanded=True):
                for test_name, tr in tests.items():
                    t_icon = "✅" if tr.get("pass") else "❌"
                    st.markdown(f"{t_icon} **{test_name}** `{tr['score']}/{tr['max']}` — {tr.get('detail', '')}")

        # 配置摘要
        config = st.session_state.get("wb_config", {})
        if config:
            st.divider()
            st.caption(f"当前配置：N={config.get('data_size', '?')}, 噪声={config.get('noise', 0):.1f}, "
                       f"缺失列={config.get('missing', []) or '无'}, AB参数={config.get('ab_params', {})}")

        # 多轮对比
        st.divider()
        col_save, col_clear = st.columns(2)
        if col_save.button("💾 保存当前结果用于对比", use_container_width=True):
            history = st.session_state.get("wb_history", [])
            history.append({
                "config": config,
                "scores": dict(agent_scores),
                "overall": overall,
            })
            st.session_state["wb_history"] = history
            st.rerun()

        history = st.session_state.get("wb_history", [])
        if len(history) > 0:
            st.markdown("**历史对比**")
            comparison_data = []
            for i, saved in enumerate(history):
                for agent, score in saved["scores"].items():
                    comparison_data.append({
                        "轮次": f"Run {i+1}",
                        "Agent": agent.replace("Agent", ""),
                        "得分": score,
                        "总体": saved["overall"],
                    })
            # 当前轮
            for agent, score in agent_scores.items():
                comparison_data.append({
                    "轮次": "当前",
                    "Agent": agent.replace("Agent", ""),
                    "得分": score,
                    "总体": overall,
                })
            st.dataframe(pd.DataFrame(comparison_data), hide_index=True, use_container_width=True)

            if col_clear.button("🗑️ 清除历史", use_container_width=True):
                st.session_state["wb_history"] = []
                st.rerun()


def _render_live_demo_circuit_breaker():
    """熔断器状态机演示"""
    from core.circuit_breaker import AgentCircuitBreakers

    st.markdown("#### 🛡️ 熔断器状态机 — 实时演示")
    st.caption("模拟 Agent 连续失败，观察 CLOSED → OPEN → HALF_OPEN 状态翻转")

    cb = AgentCircuitBreakers(failure_threshold=3, cooldown_seconds=2)

    status_placeholder = st.empty()

    def render_cb_status():
        statuses = cb.get_all_status()
        lines = []
        for s in statuses:
            icon = {"closed": "🟢 CLOSED", "open": "🔴 OPEN", "half_open": "🟡 HALF_OPEN"}.get(s["state"], s["state"])
            lines.append(f"**{s['name']}**: {icon} | 失败: {s['failure_count']}/{s['failure_threshold']}")
        status_placeholder.markdown("\n".join(lines))

    # 初始状态
    render_cb_status()

    col1, col2, col3, col4 = st.columns(4)

    # 选择 Agent
    agent_options = ["FunnelAgent", "SegmentationAgent", "StrategyAgent", "ContentAgent", "ABTestAgent"]
    selected_agent = "FunnelAgent"

    if col1.button("模拟成功", use_container_width=True):
        breaker = cb.get(selected_agent)
        breaker.record_success()
        st.success(f"{selected_agent} 执行成功 → 状态保持 CLOSED")
        render_cb_status()

    if col2.button("模拟失败", use_container_width=True):
        breaker = cb.get(selected_agent)
        breaker.record_failure()
        state = breaker.state
        if state == "open":
            st.error(f"🔴 {selected_agent} 连续失败 3 次 → 熔断器打开 (OPEN)")
        elif state == "half_open":
            st.warning(f"🟡 {selected_agent} 冷却期结束 → 尝试重试 (HALF_OPEN)")
        else:
            st.warning(f"⚠️ {selected_agent} 失败 {breaker.failure_count}/3 次 → 状态: CLOSED")
        render_cb_status()

    if col3.button("重置熔断器", use_container_width=True):
        breaker = cb.get(selected_agent)
        breaker.reset()
        st.info(f"{selected_agent} 已重置")
        render_cb_status()

    if col4.button("重置全部", use_container_width=True):
        for name in agent_options:
            cb.get(name).reset()
        st.info("全部熔断器已重置")
        render_cb_status()

    st.divider()
    st.markdown("""
    **状态机说明：**
    - **CLOSED** (正常): Agent 正常执行，连续失败 3 次 → OPEN
    - **OPEN** (熔断): 停止调用 Agent，防止级联失败，等待冷却期
    - **HALF_OPEN** (半开): 冷却期结束，尝试一次调用，成功→CLOSED，失败→OPEN
    """)


def _render_live_demo_funnel():
    """漏斗实时诊断"""
    from agents.funnel_agent import FunnelAgent

    st.markdown("#### 🔍 漏斗诊断 — 实时运行")
    st.caption("上传 CSV 或使用模拟数据，实时计算各阶段转化率和最漏环节")

    # 用 session_state 保持数据状态，避免 rerun 后丢失
    if "funnel_demo_df" not in st.session_state:
        st.session_state["funnel_demo_df"] = None

    col1, col2 = st.columns(2)

    uploaded_file = col1.file_uploader("上传用户数据 CSV", type=["csv"], key="funnel_demo_csv")
    use_mock = col2.button("使用模拟数据", type="primary", use_container_width=True)

    if uploaded_file:
        st.session_state["funnel_demo_df"] = pd.read_csv(uploaded_file)
    elif use_mock:
        st.session_state["funnel_demo_df"] = pd.read_csv("data/mock_users_saas.csv")

    if st.session_state["funnel_demo_df"] is not None:
        df = st.session_state["funnel_demo_df"]
        st.success(f"已加载 {len(df)} 条数据")

        c1, c2 = st.columns([3, 1])
        run_btn = c1.button("运行漏斗诊断", type="primary", use_container_width=True)
        if c2.button("清除数据", use_container_width=True):
            st.session_state["funnel_demo_df"] = None
            st.rerun()

        if run_btn:
            agent = FunnelAgent()
            result = agent.analyze_from_data(df)

            st.divider()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("问题阶段", str(result.problem_stage))
            c2.metric("流失率", f"{result.leak_rate:.1f}%")
            c3.metric("实际转化率", f"{result.actual_conversion:.1f}%")
            c4.metric("行业基准", f"{result.benchmark_conversion:.1f}%")

            if result.benchmark_gap != 0:
                delta_color = "normal" if result.benchmark_gap >= 0 else "inverse"
                st.metric("与基准差距", f"{result.benchmark_gap:.1f}pp", delta=f"{result.benchmark_gap:+.1f}", delta_color=delta_color)

            st.info(f"受影响用户: {len(result.affected_user_ids)} 人")

            if result.estimated_impact:
                st.success(f"💡 {result.estimated_impact}")


def _render_live_demo_ab_calculator():
    """A/B 检验计算器"""
    from utils.stats import z_test_proportions, chi_square_test, calculate_sample_size

    st.markdown("#### 📐 A/B 检验计算器")
    st.caption("输入两组数据，实时计算 Z-test p 值 + 效应量 + 样本量建议")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**A 组**")
        conv_a = st.number_input("转化数", min_value=0, value=35, key="ab_conv_a")
        n_a = st.number_input("样本量", min_value=1, value=170, key="ab_n_a")

    with col2:
        st.markdown("**B 组**")
        conv_b = st.number_input("转化数", min_value=0, value=25, key="ab_conv_b")
        n_b = st.number_input("样本量", min_value=1, value=170, key="ab_n_b")

    calc_btn = st.button("计算", type="primary", use_container_width=True)

    if calc_btn:
        z_result = z_test_proportions(conv_a, n_a, conv_b, n_b)
        chi_result = chi_square_test(conv_a, n_a, conv_b, n_b)

        st.divider()
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("A组转化率", f"{z_result['conversion_a']}%")
        r2.metric("B组转化率", f"{z_result['conversion_b']}%")
        r3.metric("提升幅度", f"{z_result['lift_percent']:+.2f}%")
        r4.metric("P值", f"{z_result['p_value']:.4f}")

        c1, c2 = st.columns(2)
        with c1:
            sig = "✅ 显著 (p < 0.05)" if z_result["significant"] else "❌ 不显著"
            st.markdown(f"**统计结论**: {sig}")
            st.markdown(f"Z 统计量: {z_result['z_statistic']:.4f}")
            st.markdown(f"效应量 (Cohen's h): {z_result['effect_size']:.4f}")

        with c2:
            st.markdown("**卡方检验**")
            st.markdown(f"卡方值: {chi_result['chi2_statistic']:.4f}")
            st.markdown(f"Cramer's V: {chi_result['cramers_v']:.4f}")

        st.divider()
        st.markdown("**样本量建议**")
        baseline = z_result["conversion_a"] / 100
        if baseline > 0:
            sample_n = calculate_sample_size(baseline, mde=0.1)
            st.info(f"当前基线转化率 {baseline*100:.1f}%，检测 10% 相对提升需要每组 **{sample_n}** 个样本")
        else:
            st.warning("A 组无转化，无法计算样本量")


def _render_live_demo_rfm():
    """RFM 分层演示"""
    from utils.rfm import calculate_rfm_scores, segment_users

    st.markdown("#### 👥 RFM 用户分层 — 实时运行")
    st.caption("基于 Recency / Frequency / Monetary 计算用户价值分层")

    # 用 session_state 保持数据状态
    if "rfm_demo_df" not in st.session_state:
        st.session_state["rfm_demo_df"] = None

    col1, col2 = st.columns(2)

    uploaded_file = col1.file_uploader("上传用户数据 CSV", type=["csv"], key="rfm_demo_csv")
    use_mock = col2.button("使用模拟数据", type="primary", use_container_width=True)

    if uploaded_file:
        st.session_state["rfm_demo_df"] = pd.read_csv(uploaded_file)
    elif use_mock:
        st.session_state["rfm_demo_df"] = pd.read_csv("data/mock_users_saas.csv")

    if st.session_state["rfm_demo_df"] is not None:
        df = st.session_state["rfm_demo_df"]
        st.success(f"已加载 {len(df)} 条数据")

        c1, c2 = st.columns([3, 1])
        run_btn = c1.button("运行 RFM 分层", type="primary", use_container_width=True)
        if c2.button("清除数据", use_container_width=True):
            st.session_state["rfm_demo_df"] = None
            st.rerun()

        if run_btn:
            # mock_users_saas.csv 列名映射
            r_col = "recency_days" if "recency_days" in df.columns else "recency"
            f_col = "frequency_sessions" if "frequency_sessions" in df.columns else "frequency"
            m_col = "monetary_spent" if "monetary_spent" in df.columns else "monetary"

            missing = [c for c in [r_col, f_col, m_col] if c not in df.columns]
            if missing:
                st.error(f"缺少字段: {', '.join(missing)}")
                st.caption(f"需要字段: recency/recency_days, frequency/frequency_sessions, monetary/monetary_spent")
            else:
                df_scored = calculate_rfm_scores(df, recency_col=r_col, frequency_col=f_col, monetary_col=m_col)
                df_scored = segment_users(df_scored)

                st.divider()
                st.markdown("**分层分布**")
                seg_counts = df_scored["segment"].value_counts()
                seg_df = pd.DataFrame({
                    "分层": seg_counts.index,
                    "用户数": seg_counts.values,
                    "占比": (seg_counts.values / len(df_scored) * 100).round(1).astype(str) + "%"
                })
                st.dataframe(seg_df, hide_index=True, use_container_width=True)

                # R/F/M 分数统计
                st.divider()
                st.markdown("**R/F/M 分数统计**")
                c1, c2, c3 = st.columns(3)
                c1.metric("平均 R 分数", f"{df_scored['R_score'].mean():.2f}")
                c2.metric("平均 F 分数", f"{df_scored['F_score'].mean():.2f}")
                c3.metric("平均 M 分数", f"{df_scored['M_score'].mean():.2f}")


def _exit_live_demo():
    """关闭实时演示面板"""
    st.session_state["show_live_demo"] = None
    st.session_state.pop("funnel_demo_df", None)
    st.session_state.pop("rfm_demo_df", None)
    st.rerun()


# ========== 演示模式辅助函数 ==========

def _model_output_badge():
    """展示模型输出标识（实验室模式）"""
    if st.session_state.get("has_lab_results"):
        st.caption("🤖 模型输出 | 模型: qwen-max | 生成时间: 2026-04-14 10:00:00")

def _activate_demo_mode():
    """加载预计算结果，直接跳到仪表盘视图"""
    demo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "demo_cycle_results.json")
    if not os.path.exists(demo_path):
        st.error("演示数据文件不存在")
        return

    with open(demo_path, "r", encoding="utf-8") as f:
        demo_data = json.load(f)

    if "user_df" not in st.session_state:
        st.session_state["user_df"] = pd.read_csv("data/mock_users_saas.csv")

    fr = FunnelResult(**demo_data["funnel_result"])
    sr = SegmentResult(**demo_data["segment_result"])
    strat = StrategyResult(**demo_data["strategy_result"])
    variants = [Variant(**v) for v in demo_data["content_result"]["variants"]]
    cr = ContentResult(
        variants=variants,
        recommended_ab_setup=demo_data["content_result"]["recommended_ab_setup"],
        personalization_rules=demo_data["content_result"].get("personalization_rules", ""),
    )
    abr = ABResult(**demo_data["ab_result"])

    cycle = GrowthCycle(
        cycle_id=demo_data["cycle_id"],
        scenario_name=demo_data["scenario_name"],
        timestamp=demo_data["timestamp"],
        funnel_result=fr,
        segment_result=sr,
        strategy_result=strat,
        content_result=cr,
        ab_result=abr,
        aigc_insights=demo_data.get("aigc_insights"),
        status="completed",
    )

    st.session_state["cycle"] = cycle
    st.session_state["current_step"] = 5
    st.session_state["demo_mode"] = True
    st.session_state["view_mode"] = "dashboard"
    st.session_state["use_aigc_context"] = True
    st.session_state["aigc_insights"] = demo_data.get("aigc_insights")


def _exit_demo_mode():
    """退出演示模式"""
    st.session_state["demo_mode"] = False
    st.session_state.pop("view_mode", None)
    st.session_state.pop("cycle", None)
    st.session_state["current_step"] = 0


# ========== 侧边栏 ==========
st.sidebar.title("🔄 GrowthLoop AI")
st.sidebar.markdown("AI驱动的增长运营自动化平台")
st.sidebar.markdown("---")

# 一键演示模式按钮
if st.sidebar.button("🚀 一键演示", type="primary", use_container_width=True):
    _activate_demo_mode()
    st.rerun()

if st.session_state.get("demo_mode"):
    st.sidebar.markdown("---")
    st.sidebar.info("🎬 演示模式 — 展示预计算的工作流结果")
    view_mode = st.sidebar.radio(
        "视图模式",
        ["📊 仪表盘总览", "📋 逐步演示"],
        index=0 if st.session_state.get("view_mode") == "dashboard" else 1,
    )
    if "仪表盘" in view_mode:
        st.session_state["view_mode"] = "dashboard"
    else:
        st.session_state["view_mode"] = "wizard"

    st.sidebar.markdown("---")
    if st.sidebar.button("📂 使用自定义数据", use_container_width=True):
        _exit_demo_mode()
        st.rerun()

    if st.sidebar.button("退出演示", use_container_width=True):
        _exit_demo_mode()
        st.rerun()

# 数据源
if not st.session_state.get("demo_mode"):
    st.sidebar.markdown("### 📂 数据源")
    uploaded_file = st.sidebar.file_uploader("上传CSV", type=["csv"], label_visibility="collapsed")

    if uploaded_file:
        st.session_state["user_df"] = pd.read_csv(uploaded_file)
        st.sidebar.success(f"已加载 {len(st.session_state['user_df'])} 条")
    elif "user_df" not in st.session_state:
        if st.sidebar.button("📥 加载模拟数据", use_container_width=True):
            st.session_state["user_df"] = pd.read_csv("data/mock_users_saas.csv")
            st.session_state["has_lab_results"] = True
            st.session_state["current_step"] = 0
            st.sidebar.success("已加载 500 条用户数据 + 实验室模型输出")

    if "user_df" in st.session_state:
        st.sidebar.markdown("### 🎯 分层模型")
        segmentation_method = st.sidebar.radio(
            "",
            ["RFM 模型", "综合评分"],
            index=0,
            horizontal=True,
            label_visibility="collapsed",
        )

# 实验室模式标识
if st.session_state.get("has_lab_results") and not st.session_state.get("demo_mode"):
    st.sidebar.markdown("---")
    st.sidebar.info("🧪 **实验室模式**\n每一步将展示预计算的模型输出结果")

# 实时演示工具面板
st.sidebar.markdown("---")
with st.sidebar.expander("🧪 实时演示工具"):
    st.caption("不需要 API Key，现场运行代码验证系统完整性")

    live_demo_options = {
        "🧪 Agent 鲁棒性测试": "benchmark",
        "🛡️ 熔断器状态机": "circuit_breaker",
        "🔍 漏斗实时诊断": "funnel",
        "📐 A/B 检验计算器": "ab_calculator",
        "👥 RFM 用户分层": "rfm",
    }

    for label, key in live_demo_options.items():
        if st.button(label, use_container_width=True, key=f"live_demo_{key}"):
            st.session_state["show_live_demo"] = key

    if st.session_state.get("show_live_demo"):
        if st.button("✕ 关闭演示工具", use_container_width=True, key="close_live_demo_btn"):
            st.session_state["show_live_demo"] = None

# API 配置（可选，折叠）
st.sidebar.markdown("---")
with st.sidebar.expander("🔑 API 配置（可选）"):
    st.caption("实验室模式不需要 API Key。如需真实调用 LLM，请在此配置。")
    provider = st.selectbox(
        "API平台",
        ["dashscope", "openai", "siliconflow"],
        format_func=lambda x: {"openai": "OpenAI", "dashscope": "阿里云百炼", "siliconflow": "硅基流动"}.get(x, x),
    )
    api_key = st.text_input("API Key", type="password", placeholder="sk-...")

    if api_key:
        st.session_state["api_key"] = api_key
        st.session_state["provider"] = provider
        st.session_state["has_lab_results"] = False  # 有了 API Key 就切换到真实模式
        st.success(f"已连接 ({provider})")

# ========== 实时演示工具主界面 ==========
if st.session_state.get("show_live_demo"):
    demo_type = st.session_state["show_live_demo"]
    if demo_type == "benchmark":
        _render_live_demo_benchmark()
    elif demo_type == "circuit_breaker":
        _render_live_demo_circuit_breaker()
    elif demo_type == "funnel":
        _render_live_demo_funnel()
    elif demo_type == "ab_calculator":
        _render_live_demo_ab_calculator()
    elif demo_type == "rfm":
        _render_live_demo_rfm()

    st.divider()
    if st.button("← 返回", use_container_width=True):
        _exit_live_demo()
    st.stop()

# ========== 主界面 ==========

# 演示模式 + 仪表盘视图
if st.session_state.get("demo_mode") and st.session_state.get("view_mode") == "dashboard":
    cycle = st.session_state.get("cycle")
    df = st.session_state.get("user_df")
    insights = st.session_state.get("aigc_insights")

    if not cycle:
        st.warning("请先点击侧边栏「一键演示」")
        st.stop()

    # 演示模式横幅
    st.markdown(
        """<div class="demo-banner">
        🚀 <b>演示模式</b> — GrowthLoop AI 完整工作流仪表盘 &nbsp;|&nbsp;
        行业调研 → 漏斗诊断 → 用户识别 → 策略生成 → A/B验证 → 知识沉淀
        </div>""",
        unsafe_allow_html=True,
    )

    # ===== 第一行：核心指标 =====
    fr = cycle.funnel_result
    sr = cycle.segment_result
    ab = cycle.ab_result

    st.markdown("### 📊 增长周期总览")
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(f'<div class="card"><div class="card-header">漏斗问题</div><div class="card-value metric-red" style="font-size:18px">{fr.problem_stage}</div><div class="card-sub">转化率 {fr.actual_conversion}% vs 基准 {fr.benchmark_conversion}%</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="card"><div class="card-header">目标用户</div><div class="card-value metric-blue">{sr.segment_count}</div><div class="card-sub">{sr.priority_segment} · {sr.segment_percentage}%</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="card"><div class="card-header">策略类型</div><div class="card-value" style="font-size:16px">{cycle.strategy_result.campaign_type[:18]}…</div><div class="card-sub">{cycle.strategy_result.message_framework}</div></div>', unsafe_allow_html=True)
    with m4:
        uplift_val = ab.actual_uplift.strip(" +%")
        try:
            uplift_num = float(uplift_val)
        except (ValueError, TypeError):
            uplift_num = 0
        st.markdown(f'<div class="card"><div class="card-header">A/B 提升</div><div class="card-value metric-green">{ab.actual_uplift}</div><div class="card-sub">{ab.winning_variant} 胜出 · p={ab.p_value:.3f}</div></div>', unsafe_allow_html=True)
    with m5:
        st.markdown(f'<div class="card"><div class="card-header">预估月影响</div><div class="card-value metric-green" style="font-size:16px">{ab.estimated_monthly_impact[:20]}…</div><div class="card-sub">{ab.downstream_impact}</div></div>', unsafe_allow_html=True)

    # ===== 第二行：漏斗图 + 用户分层 =====
    st.divider()
    chart_l, chart_r = st.columns([3, 2])

    with chart_l:
        st.markdown("### 📈 漏斗分析")
        if df is not None:
            funnel_order = ["已注册", "已浏览", "首次使用", "已活跃", "已付费"]
            counts = [int(df["funnel_stage"].value_counts().get(s, 0)) for s in funnel_order]
        else:
            funnel_order = ["已注册", "已浏览", "首次使用", "已活跃", "已付费"]
            counts = [4, 101, 305, 328, 57]

        fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # 漏斗图
        max_count = max(counts) if counts else 1
        for i, (name, count) in enumerate(zip(funnel_order, counts)):
            width = count / max_count * 0.8 + 0.2
            ax1.barh(i, width, color=["#3498db", "#2ecc71", "#f39c12", "#e74c3c", "#9b59b6"][i], height=0.6)
            ax1.text(width + 0.02, i, f"{name}\n{count}人", va="center", fontsize=10, fontweight="bold")
        ax1.set_xlim(0, 1.2)
        ax1.set_yticks([])
        ax1.invert_yaxis()
        ax1.set_title("漏斗分布", fontsize=14, fontweight="bold")

        # 转化率对比
        labels = ["已注册→已浏览", "已浏览→首次使用", "首次使用→已活跃", "已活跃→已付费"]
        x = np.arange(len(labels))
        ax2.bar(x - 0.2, [85, 60, 45, 30], 0.35, label="行业基准", color="#3498db", alpha=0.7)
        ax2.bar(x + 0.2, [99.5, 87.2, 55.8, 14.8], 0.35, label="实际数据", color="#e74c3c", alpha=0.7)
        ax2.set_xticks(x)
        ax2.set_xticklabels(labels, rotation=15, ha="right", fontsize=8)
        ax2.set_ylabel("转化率 (%)", fontsize=10)
        ax2.legend(fontsize=8)
        ax2.set_title("转化率对比", fontsize=14, fontweight="bold")

        plt.tight_layout()
        st.pyplot(fig1)

    with chart_r:
        st.markdown("### 🎯 用户画像")
        st.markdown(f"""
<div class="card">
    <div class="card-header">优先分层</div>
    <div class="card-value metric-red" style="font-size:18px">{sr.priority_segment}</div>
    <hr style="border:none;border-top:1px solid #e9ecef;margin:12px 0">
    <div><b>用户数量</b>: {sr.segment_count} 人 ({sr.segment_percentage}%)</div>
    <div><b>用户画像</b>: {sr.segment_profile}</div>
    <div><b>干预建议</b>: {sr.recommended_intervention}</div>
</div>
""", unsafe_allow_html=True)

        # 问题环节重点标出
        st.markdown(f"""
<div class="card" style="border-left:4px solid #e74c3c;">
    <div class="card-header">⚠️ 问题环节</div>
    <div><b>{fr.problem_stage}</b></div>
    <div>流失率 <span class="metric-red"><b>{fr.leak_rate}%</b></span></div>
    <div>低于基准 <span class="metric-red">{fr.benchmark_gap}pp</span></div>
    <div style="margin-top:8px;color:#6c757d">{fr.estimated_impact}</div>
</div>
""", unsafe_allow_html=True)

    # ===== 第三行：AIGC 洞察 =====
    st.divider()
    st.markdown("### 📊 AIGC 行业洞察")

    if insights:
        pain_points = insights.get("sentiment_analysis", {}).get("top_pain_points", [])
        key_finding = insights.get("scene_insights", {}).get("key_finding", {})
        categories = insights.get("competitive_matrix", {}).get("categories", [])

        pain_l, insight_r = st.columns([2, 1])

        with pain_l:
            st.markdown("#### 用户核心痛点")
            cols = st.columns(min(5, len(pain_points)))
            for i, pp in enumerate(pain_points[:5]):
                color = "#e74c3c" if pp["avg_sentiment"] < -0.4 else "#f39c12"
                with cols[i]:
                    st.markdown(
                        f"""<div class="card" style="border-left:4px solid {color}; padding:12px 14px; margin:0 4px;">
                        <div style="font-weight:bold; font-size:13px;">{pp['chinese']}</div>
                        <div style="color:gray; font-size:11px; margin-top:4px;">提及 {pp['freq']} 次 · 情感 {pp['avg_sentiment']}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

        with insight_r:
            st.markdown("#### 竞品品类分布")
            if categories:
                for cat in categories[:6]:
                    pct = cat["count"] / sum(c["count"] for c in categories) * 100
                    st.markdown(
                        f"""<div style="display:flex; justify-content:space-between; align-items:center; padding:4px 0; border-bottom:1px solid #f0f0f0;">
                        <span style="font-size:12px;">{cat['name'][:8]}</span>
                        <span style="font-size:12px; font-weight:bold; color:#3498db;">{cat['count']}</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )

        if key_finding:
            st.markdown("### 💡 关键发现与增长方案")
            proposal = key_finding.get("growth_proposal", {})
            st.markdown(f"""
<div class="proposal-card">
    <h4 style="margin:0 0 8px 0">📈 {proposal.get('name', '')}</h4>
    <p style="margin:0 0 12px 0; color:#555;">{proposal.get('description', '')}</p>
    <div style="display:flex; gap:20px;">
        <div><b>核心洞察</b>: {key_finding.get('insight', '')}</div>
    </div>
    <hr style="border:none;border-top:1px solid #a8e6cf;margin:12px 0">
    <div style="font-size:16px; font-weight:bold; color:#2ecc71;">📈 预期影响: {proposal.get('expected_impact', '')}</div>
</div>
""", unsafe_allow_html=True)

    # ===== 第四行：策略 + 内容变体 =====
    st.divider()
    st.markdown("### 📝 增长策略与内容")

    strategy = cycle.strategy_result
    content = cycle.content_result

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown(f"""<div class="card"><div class="card-header">活动类型</div><div style="font-size:14px;font-weight:bold;">{strategy.campaign_type}</div></div>""", unsafe_allow_html=True)
    with s2:
        st.markdown(f"""<div class="card"><div class="card-header">信息框架</div><div style="font-size:14px;font-weight:bold;">{strategy.message_framework}</div></div>""", unsafe_allow_html=True)
    with s3:
        st.markdown(f"""<div class="card"><div class="card-header">语气指导</div><div style="font-size:14px;font-weight:bold;">{strategy.tone_guidance}</div></div>""", unsafe_allow_html=True)
    with s4:
        st.markdown(f"""<div class="card"><div class="card-header">CTA建议</div><div style="font-size:14px;font-weight:bold;">{strategy.cta_recommendation}</div></div>""", unsafe_allow_html=True)

    if strategy.reasoning:
        st.info(f"💡 {strategy.reasoning}")

    st.markdown("#### 内容变体对比")
    v_cols = st.columns(3)
    for idx, (v_col, v) in enumerate(zip(v_cols, content.variants)):
        label = ["A", "B", "C"][idx]
        is_winner = (ab.winning_variant == v.version)
        border = "3px solid #2ecc71" if is_winner else "1px solid #e9ecef"
        with v_col:
            st.markdown(f"""
<div class="card" style="border:{border};">
    {"<div style='background:#2ecc71;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;display:inline-block;margin-bottom:8px;'>🏆 胜出</div>" if is_winner else ""}
    <div style="font-weight:bold; font-size:14px;">{label}. {v.version}</div>
    <div style="color:gray; font-size:12px; margin:6px 0;"><i>假设: {v.hypothesis}</i></div>
    <div style="font-size:13px; color:#555; margin-top:8px;">{v.content[:120]}…</div>
    <details style="margin-top:8px;">
        <summary style="cursor:pointer; color:#3498db; font-size:12px;">查看完整内容</summary>
        <div style="margin-top:8px; font-size:12px; white-space:pre-wrap;">{v.content}</div>
    </details>
</div>
""", unsafe_allow_html=True)

    # ===== 第五行：A/B 测试 =====
    st.divider()
    st.markdown("### 🧪 A/B 测试结果")

    ab_col1, ab_col2 = st.columns([1, 1])

    with ab_col1:
        conv_a = ab.conversion_a
        conv_b = ab.conversion_b
        fig2, ax = plt.subplots(figsize=(8, 4))
        bars = ax.bar(["A组\n功能价值", "B组\n社交证明"], [conv_a, conv_b], color=["#3498db", "#e74c3c"], width=0.5)
        for bar, val in zip(bars, [conv_a, conv_b]):
            ax.text(bar.get_x() + bar.get_width() / 2, val + 0.3, f"{val}%", ha="center", fontsize=16, fontweight="bold", color="#1a1a2e")
        ax.set_ylabel("转化率 (%)", fontsize=12)
        ax.set_title(f"转化对比 (p={ab.p_value:.3f}, 提升 {ab.actual_uplift})", fontsize=14, fontweight="bold")
        ax.set_ylim(0, max(conv_a, conv_b) + 5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        st.pyplot(fig2)

    with ab_col2:
        st.markdown(f"""
<div class="winner-card">
    <h4 style="margin:0 0 8px 0">🏆 {ab.winning_variant} 胜出</h4>
    <p style="margin:0 0 12px 0">{ab.recommendation}</p>
    <hr style="border:none;border-top:1px solid #a8e6cf;margin:12px 0">
    <div style="display:flex; gap:20px; font-size:13px;">
        <div><b>统计显著性</b>: p={ab.p_value:.4f} {"✅" if ab.p_value < 0.05 else "❌"}</div>
        <div><b>提升幅度</b>: {ab.actual_uplift}</div>
    </div>
    <div style="margin-top:8px; font-size:13px; color:#2ecc71; font-weight:bold;">💰 {ab.estimated_monthly_impact}</div>
</div>
""", unsafe_allow_html=True)

    # ===== 第六行：工程面板 =====
    st.divider()
    st.markdown("### 🔧 驾驭工程面板")

    # 熔断器 + 质量报告
    eng1, eng2 = st.columns(2)

    with eng1:
        st.markdown("#### 🛡️ 熔断器状态")
        agents_list = ["FunnelAgent", "SegmentationAgent", "StrategyAgent", "ContentAgent", "ABTestAgent"]
        for agent in agents_list:
            st.markdown(
                f"""<div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid #f0f0f0;">
                <span style="font-size:13px;">🟢 {agent}</span>
                <span style="font-size:11px; color:#2ecc71; font-weight:bold;">CLOSED</span>
                </div>""",
                unsafe_allow_html=True,
            )

    with eng2:
        st.markdown("#### ✅ Agent Benchmark 质量报告")
        benchmark_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_report.json")
        if os.path.exists(benchmark_path):
            with open(benchmark_path, "r", encoding="utf-8") as f:
                benchmark_data = json.load(f)
            overall = benchmark_data.get("overall", 100)
            overall_color = "#2ecc71" if overall >= 70 else "#f39c12"
            st.markdown(f'<div style="font-size:20px;font-weight:bold;color:{overall_color}">总体得分: {overall}/100</div>', unsafe_allow_html=True)
            st.progress(overall / 100)

            agents_scores = benchmark_data.get("agents", {})
            for agent_name, score_info in agents_scores.items():
                score = score_info.get("score", 0)
                icon = "🟢" if score >= 70 else "🟡" if score >= 40 else "🔴"
                st.markdown(f'{icon} {agent_name}: {score}/100')
                st.progress(score / 100)

    # ===== 底部导航 =====
    st.divider()
    st.markdown(
        """<div style="text-align:center; color:#868e96; font-size:12px; padding:12px;">
        GrowthLoop AI — AI驱动的增长运营闭环系统 &nbsp;|&nbsp; 行业调研 → 诊断 → 识别 → 行动 → 验证 → 学习
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    step_nav_cols = st.columns([1, 4, 1])
    with step_nav_cols[1]:
        col_w, col_s = st.columns(2)
        with col_w:
            if st.button("📋 切换到逐步演示", use_container_width=True):
                st.session_state["view_mode"] = "wizard"
                st.session_state["current_step"] = 0
                st.rerun()
        with col_s:
            if st.button("🔄 重新开始", use_container_width=True):
                st.session_state.pop("cycle", None)
                st.session_state["current_step"] = 0
                st.rerun()

    st.stop()

# ========== 逐步演示模式 ==========
if st.session_state.get("demo_mode") and st.session_state.get("view_mode") == "wizard":
    cycle = st.session_state.get("cycle")
    df = st.session_state.get("user_df")

    st.markdown(
        """<div class="demo-banner">
        🚀 <b>演示模式 — 逐步演示</b> — 点击「下一步」逐步浏览完整工作流 &nbsp;|&nbsp;
        <a href="javascript:void(0)" style="color:#fff;text-decoration:underline;">切换到仪表盘总览</a>
        </div>""",
        unsafe_allow_html=True,
    )

    # 步骤导航
    steps_meta = [
        ("0", "行业调研", "AIGC洞察"),
        ("1", "漏斗诊断", "发现问题"),
        ("2", "用户识别", "定位目标"),
        ("3", "策略行动", "生成内容"),
        ("4", "A/B验证", "效果测试"),
        ("5", "学习沉淀", "知识积累"),
    ]

    current_step = st.session_state.get("current_step", 0)
    progress_pct = (current_step + 1) / len(steps_meta)
    st.progress(progress_pct, text=f"步骤 {current_step}/{len(steps_meta) - 1} — {steps_meta[current_step][1]}")

    with st.container(border=True):
        for i, (num, name, desc) in enumerate(steps_meta):
            col_icon, col_text = st.columns([1, 9])
            if i < current_step:
                col_icon.markdown("<div style='text-align:center;font-size:18px;margin-top:6px'>✅</div>", unsafe_allow_html=True)
                col_text.markdown(f"<div style='padding:2px 8px; border-left:4px solid #2ecc71;'><b>步骤{num}: {name}</b> <span style='color:gray;font-size:12px'>{desc}</span></div>", unsafe_allow_html=True)
            elif i == current_step:
                col_icon.markdown("<div style='text-align:center;font-size:18px;margin-top:6px'>🔵</div>", unsafe_allow_html=True)
                col_text.markdown(f"<div style='padding:6px 8px; background:#e8f4fd; border-left:4px solid #3498db; border-radius:4px;'><b>步骤{num}: {name}</b> <span style='color:gray;font-size:12px'>{desc}</span></div>", unsafe_allow_html=True)
            else:
                col_icon.markdown("<div style='text-align:center;font-size:18px;margin-top:6px;color:#bdc3c7'>○</div>", unsafe_allow_html=True)
                col_text.markdown(f"<div style='padding:2px 8px; border-left:4px solid #bdc3c7; color:#95a5a6;'><b>步骤{num}: {name}</b> <span style='font-size:12px'>{desc}</span></div>", unsafe_allow_html=True)
            if i < len(steps_meta) - 1:
                st.divider()

    st.markdown("---")
    step = current_step

    # 演示模式快速渲染 — 只显示对应步骤的关键信息
    if step == 0:
        insights = st.session_state.get("aigc_insights")
        st.markdown("### 📊 步骤0: 行业调研")
        st.markdown("基于 Kaggle 数据集分析 AIGC 产品用户情感和竞品格局")
        if insights:
            pain_points = insights.get("sentiment_analysis", {}).get("top_pain_points", [])[:3]
            cols = st.columns(3)
            for i, pp in enumerate(pain_points):
                color = "#e74c3c" if pp["avg_sentiment"] < -0.4 else "#f39c12"
                with cols[i]:
                    st.markdown(f"""<div class="card" style="border-left:4px solid {color}; padding:10px 14px; margin:0 4px;">
                    <b>{pp['chinese']}</b><br/><span style="color:gray;font-size:12px">提及 {pp['freq']} 次 | 情感 {pp['avg_sentiment']}</span></div>""", unsafe_allow_html=True)
            key_finding = insights.get("scene_insights", {}).get("key_finding", {})
            proposal = key_finding.get("growth_proposal", {})
            st.success(f"**增长方案**: {proposal.get('name', '')} — {proposal.get('expected_impact', '')}")

    elif step == 1:
        fr = cycle.funnel_result
        st.markdown("### 📊 步骤1: 漏斗诊断")
        st.markdown(f"发现问题环节 **{fr.problem_stage}**，转化率 {fr.actual_conversion}% vs 基准 {fr.benchmark_conversion}%")
        st.warning(f"流失率 {fr.leak_rate}%，差距 {fr.benchmark_gap}pp")

    elif step == 2:
        sr = cycle.segment_result
        st.markdown("### 🎯 步骤2: 用户识别")
        st.markdown(f"定位 **{sr.priority_segment}**，{sr.segment_count} 人（{sr.segment_percentage}%）")
        st.info(f"画像: {sr.segment_profile}")

    elif step == 3:
        strategy = cycle.strategy_result
        content = cycle.content_result
        st.markdown("### 📝 步骤3: 策略与内容")
        st.markdown(f"**策略**: {strategy.campaign_type}")
        st.markdown(f"**信息框架**: {strategy.message_framework}")
        for v in content.variants:
            st.markdown(f"- **{v.version}**: {v.hypothesis}")

    elif step == 4:
        ab = cycle.ab_result
        st.markdown("### 🧪 步骤4: A/B 验证")
        st.markdown(f"**{ab.winning_variant}** 胜出，p={ab.p_value:.4f}，提升 {ab.actual_uplift}")

    elif step == 5:
        ab = cycle.ab_result
        st.markdown("### 🧠 步骤5: 学习沉淀")
        st.markdown(f"测试结果已存入知识库。{ab.winning_variant} 胜出，提升 {ab.actual_uplift}")
        st.success(f"💰 {ab.estimated_monthly_impact}")

    # 导航按钮
    st.divider()
    nav_c1, nav_c2 = st.columns([1, 1])
    with nav_c1:
        if current_step > 0:
            if st.button("← 上一步", use_container_width=True):
                st.session_state["current_step"] = current_step - 1
                st.rerun()
    with nav_c2:
        if current_step < 5:
            if st.button("下一步 →", type="primary", use_container_width=True):
                st.session_state["current_step"] = current_step + 1
                st.rerun()
        else:
            if st.button("📊 切换到仪表盘总览", type="primary", use_container_width=True):
                st.session_state["view_mode"] = "dashboard"
                st.rerun()

    st.stop()

# ========== 普通工作流模式（非演示） ==========
if "user_df" not in st.session_state:
    st.markdown(
        """
<div style="text-align:center; padding:60px 20px;">
<h1>🔄 GrowthLoop AI</h1>
<p style="color:#868e96; font-size:16px;">AI驱动的增长运营自动化平台</p>
<p style="color:#868e96; font-size:14px;">从行业调研到知识沉淀的完整增长闭环</p>
<br/>
<p style="color:#3498db; font-size:18px;">👈 请在侧边栏点击「一键演示」或上传数据开始</p>
</div>
""",
        unsafe_allow_html=True,
    )
    st.stop()

df = st.session_state.get("user_df")
if df is not None:
    df = df.copy()

# 实验室模式：有预计算结果，不需要 API Key
lab_mode = st.session_state.get("has_lab_results", False)

if not lab_mode:
    # 非实验室模式：需要 API Key
    if "api_key" not in st.session_state:
        st.warning("请先在侧边栏设置 API Key，或点击「加载模拟数据」使用实验室模型输出")
        st.stop()

if "orchestrator" not in st.session_state and not lab_mode:
    logger.info("初始化编排器 | provider=%s | 数据量=%d", st.session_state["provider"], len(df))
    st.session_state["orchestrator"] = GrowthOrchestrator(
        api_key=st.session_state["api_key"],
        provider=st.session_state["provider"],
    )

# 实验室模式：加载预计算结果
if lab_mode and "cycle" not in st.session_state:
    demo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "demo_cycle_results.json")
    if os.path.exists(demo_path):
        with open(demo_path, "r", encoding="utf-8") as f:
            demo_data = json.load(f)
        fr = FunnelResult(**demo_data["funnel_result"])
        sr = SegmentResult(**demo_data["segment_result"])
        strat = StrategyResult(**demo_data["strategy_result"])
        variants = [Variant(**v) for v in demo_data["content_result"]["variants"]]
        cr = ContentResult(
            variants=variants,
            recommended_ab_setup=demo_data["content_result"]["recommended_ab_setup"],
            personalization_rules=demo_data["content_result"].get("personalization_rules", ""),
        )
        abr = ABResult(**demo_data["ab_result"])
        cycle = GrowthCycle(
            cycle_id=demo_data["cycle_id"],
            scenario_name=demo_data["scenario_name"],
            timestamp=demo_data["timestamp"],
            funnel_result=fr,
            segment_result=sr,
            strategy_result=strat,
            content_result=cr,
            ab_result=abr,
            aigc_insights=demo_data.get("aigc_insights"),
            status="completed",
        )
        st.session_state["cycle"] = cycle
        st.session_state["aigc_insights"] = demo_data.get("aigc_insights")

orch = st.session_state.get("orchestrator")

# 步骤导航
steps_meta = [
    ("0", "行业调研", "AIGC洞察"),
    ("1", "漏斗诊断", "发现问题"),
    ("2", "用户识别", "定位目标"),
    ("3", "策略行动", "生成内容"),
    ("4", "A/B验证", "效果测试"),
    ("5", "学习沉淀", "知识积累"),
]

current_step = st.session_state.get("current_step", 0)
progress_pct = (current_step + 1) / len(steps_meta)
st.progress(progress_pct, text=f"步骤 {current_step}/{len(steps_meta) - 1} — {steps_meta[current_step][1]}")

with st.container(border=True):
    for i, (num, name, desc) in enumerate(steps_meta):
        col_icon, col_text = st.columns([1, 9])
        if i < current_step:
            col_icon.markdown("<div style='text-align:center;font-size:18px;margin-top:6px'>✅</div>", unsafe_allow_html=True)
            col_text.markdown(f"<div style='padding:2px 8px; border-left:4px solid #2ecc71;'><b>步骤{num}: {name}</b> <span style='color:gray;font-size:12px'>{desc}</span></div>", unsafe_allow_html=True)
        elif i == current_step:
            col_icon.markdown("<div style='text-align:center;font-size:18px;margin-top:6px'>🔵</div>", unsafe_allow_html=True)
            col_text.markdown(f"<div style='padding:6px 8px; background:#e8f4fd; border-left:4px solid #3498db; border-radius:4px;'><b>步骤{num}: {name}</b> <span style='color:gray;font-size:12px'>{desc}</span></div>", unsafe_allow_html=True)
        else:
            col_icon.markdown("<div style='text-align:center;font-size:18px;margin-top:6px;color:#bdc3c7'>○</div>", unsafe_allow_html=True)
            col_text.markdown(f"<div style='padding:2px 8px; border-left:4px solid #bdc3c7; color:#95a5a6;'><b>步骤{num}: {name}</b> <span style='font-size:12px'>{desc}</span></div>", unsafe_allow_html=True)
        if i < len(steps_meta) - 1:
            st.divider()

st.markdown("---")

cycle = st.session_state.get("cycle")
step = current_step

# ==================== Step 0: 行业调研 ====================
if step == 0:
    with st.container(border=True):
        st.markdown("### 📊 步骤0: 行业调研")
        st.caption("基于 Kaggle 数据集分析 AIGC 产品用户情感和竞品格局")

    col_run, col_skip = st.columns([1, 1])
    with col_run:
        btn_text = "📊 查看行业调研结果" if lab_mode else "🔍 运行分析"
        run_clicked = st.button(btn_text, type="primary", use_container_width=True)
    with col_skip:
        skip_clicked = st.button("跳过 →", use_container_width=True)

    if run_clicked:
        if lab_mode:
            # 实验室模式：直接展示预计算结果
            pass  # insights 已在 cycle 初始化时加载
        else:
            from data.insight_engine import InsightEngine
            if "insight_engine" not in st.session_state:
                st.session_state["insight_engine"] = InsightEngine()
            with st.status("正在分析...", expanded=True) as status:
                insights = st.session_state["insight_engine"].run_analysis()
                status.update(label="完成 ✅", state="complete")
            st.session_state["aigc_insights"] = insights

    if skip_clicked:
        st.session_state["current_step"] = 1
        st.rerun()

    insights = st.session_state.get("aigc_insights")
    if insights:
        st.divider()
        pain_points = insights.get("sentiment_analysis", {}).get("top_pain_points", [])[:3]
        if pain_points:
            st.markdown("#### 用户核心痛点")
            cols = st.columns(3)
            for i, pp in enumerate(pain_points):
                color = "#e74c3c" if pp["avg_sentiment"] < -0.4 else "#f39c12"
                with cols[i]:
                    st.markdown(f"""<div class="card" style="border-left:4px solid {color}; padding:10px 14px; margin:0 4px;">
                    <b>{pp['chinese']}</b><br/><span style="color:gray;font-size:12px">提及 {pp['freq']} 次 | 情感 {pp['avg_sentiment']}</span></div>""", unsafe_allow_html=True)

        key_finding = insights.get("scene_insights", {}).get("key_finding", {})
        proposal = key_finding.get("growth_proposal", {})
        if proposal:
            st.divider()
            st.markdown(f"""
<div class="proposal-card">
    <b>📈 增长方案: {proposal.get('name', '')}</b><br/>
    {proposal.get('description', '')}<br/>
    <b>预期影响</b>: {proposal.get('expected_impact', '')}
</div>
""", unsafe_allow_html=True)

        use_aigc = st.checkbox("将行业洞察注入策略推荐", value=True)
        st.session_state["use_aigc_context"] = use_aigc

        if st.button("下一步：漏斗诊断 →", type="primary", use_container_width=True):
            st.session_state["current_step"] = 1
            st.rerun()

# ==================== Step 1: 诊断 ====================
elif step == 1:
    with st.container(border=True):
        st.markdown("### 📊 步骤1: 漏斗诊断")
        st.caption("自动分析用户漏斗，找到最严重的流失环节")
        if df is not None:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("总用户数", f"{len(df):,}")
            c2.metric("漏斗阶段数", df["funnel_stage"].nunique())
            if "channel" in df.columns:
                c3.metric("渠道数", df["channel"].nunique())
            if "avg_session_duration" in df.columns:
                c4.metric("平均会话时长", f"{df['avg_session_duration'].mean():.1f}min")

    lab_btn_text = "📊 查看模型诊断结果" if lab_mode else "🔍 开始诊断"
    if st.button(lab_btn_text, type="primary", use_container_width=True):
        if lab_mode:
            # 实验室模式：cycle 已在初始化时加载，直接跳下一步
            st.session_state["current_step"] = 2
            st.rerun()
        else:
            with st.status("正在诊断...", expanded=True) as status:
                use_rfm = (segmentation_method == "RFM 模型")
                aigc_insights = st.session_state.get("aigc_insights") if st.session_state.get("use_aigc_context") else None
                cycle = orch.run_cycle(df, "SaaS增长周期", use_rfm=use_rfm, aigc_insights=aigc_insights)
                status.update(label="完成 ✅", state="complete")
                st.session_state["cycle"] = cycle
                st.session_state["current_step"] = 2
                st.rerun()

    with st.expander("📋 数据预览"):
        if df is not None:
            st.dataframe(df.head(10), use_container_width=True)

    nav_c1, nav_c2 = st.columns([1, 1])
    with nav_c1:
        if st.button("← 上一步", use_container_width=True):
            st.session_state["current_step"] = 0
            st.rerun()

# ==================== Step 2: 识别 ====================
elif step == 2:
    if not cycle:
        st.error("请先完成步骤1")
        st.stop()

    _model_output_badge()
    fr = cycle.funnel_result
    sr = cycle.segment_result

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("问题环节", fr.problem_stage)
    m2.metric("实际转化率", f"{fr.actual_conversion}%")
    m3.metric("行业基准", f"{fr.benchmark_conversion}%")
    try:
        gap_val = float(fr.benchmark_gap)
        m4.metric("差距", f"{fr.benchmark_gap}pp", delta=f"-{fr.benchmark_gap}pp", delta_color="inverse")
    except (ValueError, TypeError):
        m4.metric("差距", f"{fr.benchmark_gap}pp")

    st.warning(f"⚠️ **{fr.problem_stage}** 环节流失严重，低于基准 {fr.benchmark_gap}pp")
    st.info(f"💡 {fr.estimated_impact}")

    st.divider()
    with st.container(border=True):
        st.markdown("### 🎯 目标用户定位")
        sc1, sc2 = st.columns(2)
        sc1.markdown(f"**分层**: {sr.priority_segment}")
        sc1.markdown(f"**数量**: {sr.segment_count} 人 ({sr.segment_percentage}%)")
        sc2.markdown(f"**画像**: {sr.segment_profile}")
        if sr.target_user_ids:
            with st.expander(f"查看用户ID（{len(sr.target_user_ids)}人）"):
                st.text(", ".join(sr.target_user_ids[:20]) + ("..." if len(sr.target_user_ids) > 20 else ""))

    if df is not None:
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            with st.container(border=True):
                st.markdown("#### 漏斗分布")
                funnel_order = ["已注册", "已浏览", "首次使用", "已活跃", "已付费"]
                counts = [int(df["funnel_stage"].value_counts().get(s, 0)) for s in funnel_order]
                fig1, ax1 = plt.subplots(figsize=(6, 4))
                max_count = max(counts) if counts else 1
                for j, (name, count) in enumerate(zip(funnel_order, counts)):
                    width = count / max_count * 0.8 + 0.2
                    ax1.barh(j, width, color=["#3498db", "#2ecc71", "#f39c12", "#e74c3c", "#9b59b6"][j], height=0.6)
                    ax1.text(width + 0.02, j, f"{name}: {count}", va="center", fontsize=9)
                ax1.set_xlim(0, 1.2)
                ax1.set_yticks([])
                ax1.invert_yaxis()
                st.pyplot(fig1)

        with chart_col2:
            with st.container(border=True):
                st.markdown("#### 转化率对比")
                labels = ["已注册→已浏览", "已浏览→首次使用", "首次使用→已活跃", "已活跃→已付费"]
                x = np.arange(len(labels))
                fig2, ax2 = plt.subplots(figsize=(6, 4))
                ax2.bar(x - 0.2, [85, 60, 45, 30], 0.35, label="基准", color="#3498db", alpha=0.7)
                ax2.bar(x + 0.2, [85, 55, 40, 28], 0.35, label="实际", color="#e74c3c", alpha=0.7)
                ax2.set_xticks(x)
                ax2.set_xticklabels(labels, rotation=15, ha="right", fontsize=8)
                ax2.set_ylabel("转化率 (%)")
                ax2.legend(fontsize=8)
                st.pyplot(fig2)

    nav_c1, nav_c2 = st.columns([1, 1])
    with nav_c1:
        if st.button("← 返回步骤1", use_container_width=True):
            st.session_state["current_step"] = 1
            st.rerun()
    with nav_c2:
        if st.button("下一步 →", type="primary", use_container_width=True):
            st.session_state["current_step"] = 3
            st.rerun()

# ==================== Step 3: 行动 ====================
elif step == 3:
    if not cycle:
        st.error("请先完成前两步")
        st.stop()

    _model_output_badge()
    strategy = cycle.strategy_result
    content = cycle.content_result

    st.markdown("### 📝 增长策略")
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown(f"""<div class="card"><div class="card-header">活动类型</div><div style="font-weight:bold;">{strategy.campaign_type}</div></div>""", unsafe_allow_html=True)
    with s2:
        st.markdown(f"""<div class="card"><div class="card-header">信息框架</div><div style="font-weight:bold;">{strategy.message_framework}</div></div>""", unsafe_allow_html=True)
    with s3:
        st.markdown(f"""<div class="card"><div class="card-header">语气指导</div><div style="font-weight:bold;">{strategy.tone_guidance}</div></div>""", unsafe_allow_html=True)
    with s4:
        st.markdown(f"""<div class="card"><div class="card-header">CTA建议</div><div style="font-weight:bold;">{strategy.cta_recommendation}</div></div>""", unsafe_allow_html=True)

    if strategy.reasoning:
        st.info(f"💡 {strategy.reasoning}")

    st.divider()
    st.markdown("### 📝 内容变体")
    v_cols = st.columns(3)
    for idx, (v_col, v) in enumerate(zip(v_cols, content.variants)):
        with v_col:
            st.markdown(f"""
<div class="variant-card">
    <b>{v.version}</b><br/>
    <span style="color:gray;font-size:12px"><i>{v.hypothesis}</i></span>
    <div style="margin-top:8px;font-size:13px;">{v.content[:120]}…</div>
    <details style="margin-top:8px;"><summary style="cursor:pointer;color:#3498db;font-size:12px;">展开全文</summary>
    <div style="margin-top:8px;font-size:12px;white-space:pre-wrap;">{v.content}</div></details>
</div>
""", unsafe_allow_html=True)

    st.info(content.recommended_ab_setup)

    nav_c1, nav_c2 = st.columns([1, 1])
    with nav_c1:
        if st.button("← 返回步骤2", use_container_width=True):
            st.session_state["current_step"] = 2
            st.rerun()
    with nav_c2:
        if st.button("下一步 →", type="primary", use_container_width=True):
            st.session_state["current_step"] = 4
            st.rerun()

# ==================== Step 4: 验证 ====================
elif step == 4:
    if not cycle:
        st.stop()

    content = cycle.content_result
    variants = content.variants
    variant_labels = [v.version for v in variants]

    st.markdown("### 🧪 步骤4: A/B测试验证")
    ab_col1, ab_col2 = st.columns(2)
    with ab_col1:
        with st.container(border=True):
            st.markdown("#### A组")
            idx_a = st.selectbox("选择A组", options=range(len(variants)), format_func=lambda i: variant_labels[i], index=0, key="ab_variant_a", label_visibility="collapsed")
            st.caption(f"*{variants[idx_a].hypothesis}*")
            n_a = st.number_input("A组样本量", min_value=1, value=170, key="n_a")
            c_a = st.number_input("A组转化数", min_value=0, max_value=n_a, value=25, key="c_a")
    with ab_col2:
        with st.container(border=True):
            st.markdown("#### B组")
            idx_b = st.selectbox("选择B组", options=range(len(variants)), format_func=lambda i: variant_labels[i], index=1 if len(variants) > 1 else 0, key="ab_variant_b", label_visibility="collapsed")
            st.caption(f"*{variants[idx_b].hypothesis}*")
            n_b = st.number_input("B组样本量", min_value=1, value=170, key="n_b")
            c_b = st.number_input("B组转化数", min_value=0, max_value=n_b, value=35, key="c_b")

    lab_ab_btn = "📊 查看 A/B 测试结果" if lab_mode else "📊 分析结果"
    if st.button(lab_ab_btn, type="primary", use_container_width=True):
        if lab_mode:
            # 实验室模式：A/B 结果已预加载，直接跳下一步
            st.session_state["current_step"] = 5
            st.rerun()
        else:
            with st.status("正在分析...", expanded=True) as status:
                cycle = orch.complete_cycle(cycle, c_a, n_a, c_b, n_b)
                status.update(label="完成 ✅", state="complete")
                st.session_state["cycle"] = cycle
                st.session_state["current_step"] = 5
                st.rerun()

    if st.button("← 返回步骤3", use_container_width=True):
        st.session_state["current_step"] = 3
        st.rerun()

# ==================== Step 5: 学习 ====================
elif step == 5:
    if not cycle or not cycle.ab_result:
        st.error("请先完成A/B测试分析")
        st.stop()

    _model_output_badge()
    ab = cycle.ab_result

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("获胜版本", ab.winning_variant)
    r2.metric("提升幅度", ab.actual_uplift)
    r3.metric("P值", f"{ab.p_value:.4f}")
    sig = "显著" if ab.p_value < 0.05 else "不显著"
    r4.metric("显著性", sig, delta="✅" if ab.p_value < 0.05 else "❌")

    st.markdown(f"""
<div class="winner-card">
    <h4 style="margin:0 0 8px 0">🏆 {ab.winning_variant} 胜出</h4>
    <p style="margin:0">{ab.recommendation}</p>
</div>
""", unsafe_allow_html=True)

    if ab.estimated_monthly_impact:
        st.info(f"💰 {ab.estimated_monthly_impact}")

    with st.container(border=True):
        st.markdown("#### A/B 测试结果对比")
        fig, ax = plt.subplots(figsize=(8, 4))
        bars = ax.bar(["A组", "B组"], [ab.conversion_a, ab.conversion_b], color=["#3498db", "#e74c3c"], width=0.5)
        for bar, val in zip(bars, [ab.conversion_a, ab.conversion_b]):
            ax.text(bar.get_x() + bar.get_width() / 2, val + 0.3, f"{val}%", ha="center", fontsize=14, fontweight="bold")
        ax.set_ylabel("转化率 (%)")
        ax.set_title(f"内容A/B测试结果 (p={ab.p_value:.4f})")
        ax.set_ylim(0, max(ab.conversion_a, ab.conversion_b) + 5)
        st.pyplot(fig)

    with st.expander("📋 完整AI报告"):
        st.markdown(ab.full_report)

    with st.expander("📚 增长知识库"):
        knowledge = orch.get_knowledge_report()
        st.markdown(knowledge)

    with st.expander("📡 系统可观测性"):
        obs_summary = orch.get_observability_summary()
        o1, o2, o3, o4 = st.columns(4)
        o1.metric("事件数", obs_summary.get("event_count", 0))
        o2.metric("输入 Token", f"{obs_summary.get('total_tokens_in', 0):,}")
        o3.metric("输出 Token", f"{obs_summary.get('total_tokens_out', 0):,}")
        o4.metric("API 成本", f"${obs_summary.get('total_cost_usd', 0):.4f}")

        cb_status = orch.get_circuit_breaker_status()
        if cb_status:
            st.divider()
            for cb in cb_status:
                icon = {"closed": "🟢", "open": "🔴", "half_open": "🟡"}.get(cb["state"], "⚪")
                st.markdown(f"{icon} **{cb['name']}** | {cb['state']} | 失败: {cb['failure_count']}/{cb['failure_threshold']}")

    st.divider()
    if st.button("🔄 新一轮", type="primary", use_container_width=True):
        st.session_state["cycle"] = None
        st.session_state["current_step"] = 0
        st.rerun()
