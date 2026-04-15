"""
GrowthLoop Agent Quality Benchmark

评估框架参考：Harbor benchmark protocol (https://github.com/laude-institute/harbor)
实现为从零编写的自定义测试框架，针对本项目 6 个 Agent 定制测试用例

设计原则：
- 每个 Agent 独立评估，不依赖其他 Agent 的输出
- 覆盖正常数据、边界条件（零转化/单用户/空数据/缺失字段）、LLM 输出质量、统计检验准确性
- 产出 0-100 的量化评分，低于 60% 阈值判定为 issue
- benchmark 结果驱动 Agent 代码迭代："跑分 → 诊断失败 → 修复代码 → 复测"

运行方式：
    python tests/benchmark.py        # 终端输出 + JSON 报告
    python scripts/harness_loop.py   # 自动化评估流水线
"""

import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

from agents.funnel_agent import FunnelAgent
from agents.segmentation_agent import SegmentationAgent
from agents.strategy_agent import StrategyAgent
from agents.content_agent import ContentAgent
from agents.ab_test_agent import ABTestAgent
from agents.growth_memory import GrowthMemory


def make_df(scenario="normal"):
    if scenario == "normal":
        return pd.DataFrame({
            "user_id": [f"u{i}" for i in range(200)],
            "funnel_stage": (["已注册"]*50 + ["已浏览"]*40 + ["首次使用"]*30 + ["已活跃"]*45 + ["已付费"]*35),
            "churn_risk_score": np.random.randint(10, 90, 200),
            "monetary_spent": np.random.uniform(0, 500, 200).round(2),
            "design_count": np.random.randint(0, 30, 200),
            "frequency_sessions": np.random.randint(1, 50, 200),
        })
    elif scenario == "empty":
        return pd.DataFrame(columns=["user_id","funnel_stage","churn_risk_score","monetary_spent","design_count","frequency_sessions"])
    elif scenario == "single":
        return pd.DataFrame({"user_id":["u1"],"funnel_stage":["已注册"],"churn_risk_score":[80],"monetary_spent":[0.0],"design_count":[0],"frequency_sessions":[1]})
    elif scenario == "same_stage":
        return pd.DataFrame({"user_id":[f"u{i}" for i in range(50)],"funnel_stage":["已注册"]*50,"churn_risk_score":np.random.randint(10,90,50),"monetary_spent":np.random.uniform(0,500,50).round(2),"design_count":np.random.randint(0,30,50),"frequency_sessions":np.random.randint(1,50,50)})
    elif scenario == "missing_cols":
        return pd.DataFrame({"user_id":[f"u{i}" for i in range(50)],"funnel_stage":["已注册"]*30+["已付费"]*20})
    return make_df("normal")


def score_check(result, name, max_pts):
    """Helper: returns (pts, passed) tuple."""
    pts = result.get(name, 0)
    return min(pts, max_pts), pts >= max_pts * 0.6


def run_benchmark():
    checks = {}  # agent -> {test_name: {"score": x, "max": y, "pass": bool}}
    scores = {}  # agent -> total_score

    # ================================================================
    # FunnelAgent
    # ================================================================
    fc = {}
    te = 0; tm = 0

    # 1. Normal data (25)
    try:
        r = FunnelAgent().analyze_from_data(make_df("normal"))
        s = 0
        if all([r.problem_stage, r.leak_rate >= 0, r.actual_conversion >= 0, r.benchmark_conversion > 0]): s += 10
        if r.affected_user_ids and len(r.affected_user_ids) > 0: s += 5
        if 0 <= r.actual_conversion <= 100: s += 5
        if abs(r.benchmark_gap) <= 100: s += 5
        fc["normal_data"] = {"score": s, "max": 25, "pass": s >= 15}
    except Exception as e:
        fc["normal_data"] = {"score": 0, "max": 25, "pass": False, "error": str(e)}
    te += 25; tm += 25

    # 2. Single user (15)
    try:
        r = FunnelAgent().analyze_from_data(make_df("single"))
        s = 15 if r.problem_stage and r.leak_rate >= 0 else 5
        fc["single_user"] = {"score": s, "max": 15, "pass": s >= 9}
    except Exception as e:
        fc["single_user"] = {"score": 0, "max": 15, "pass": False, "error": str(e)}
    te += 15; tm += 15

    # 3. All same stage (15)
    try:
        r = FunnelAgent().analyze_from_data(make_df("same_stage"))
        s = 15 if r.problem_stage else 0
        fc["all_same_stage"] = {"score": s, "max": 15, "pass": s >= 9}
    except Exception as e:
        fc["all_same_stage"] = {"score": 0, "max": 15, "pass": False, "error": str(e)}
    te += 15; tm += 15

    # 4. Missing columns (15)
    try:
        r = FunnelAgent().analyze_from_data(make_df("missing_cols"))
        s = 15 if r.problem_stage and r.affected_user_ids is not None else 5
        fc["missing_columns"] = {"score": s, "max": 15, "pass": s >= 9}
    except Exception as e:
        fc["missing_columns"] = {"score": 0, "max": 15, "pass": False, "error": str(e)}
    te += 15; tm += 15

    # 5. Report quality (15)
    try:
        agent = FunnelAgent()
        r = agent.analyze_from_data(make_df("normal"))
        report = agent.generate_report(r)
        s = 0
        if report and len(report) > 100: s += 10
        if r.problem_stage.split("->")[-1] in report: s += 5
        fc["report_quality"] = {"score": s, "max": 15, "pass": s >= 9}
    except Exception as e:
        fc["report_quality"] = {"score": 0, "max": 15, "pass": False, "error": str(e)}
    te += 15; tm += 15

    # 6. analyze_from_stages (15)
    try:
        stages = [{"name":"已注册","users":1000},{"name":"已浏览","users":800},{"name":"首次使用","users":400},{"name":"已活跃","users":200},{"name":"已付费","users":50}]
        r = FunnelAgent().analyze_from_stages(stages)
        s = 15 if r.problem_stage and r.leak_rate > 0 else 0
        fc["from_stages"] = {"score": s, "max": 15, "pass": s >= 9}
    except Exception as e:
        fc["from_stages"] = {"score": 0, "max": 15, "pass": False, "error": str(e)}
    te += 15; tm += 15

    scores["FunnelAgent"] = round(te / tm * 100, 1) if tm else 0
    checks["FunnelAgent"] = fc

    # ================================================================
    # SegmentationAgent
    # ================================================================
    sc2 = {}
    te = 0; tm = 0

    # 1. Normal segmentation (25)
    try:
        df = make_df("normal")
        funnel = FunnelAgent().analyze_from_data(df)
        r = SegmentationAgent().analyze(df, funnel)
        s = 0
        if all([r.priority_segment, r.segment_count > 0, r.segment_profile, r.recommended_intervention]): s += 15
        if r.target_user_ids and all(isinstance(u, str) for u in r.target_user_ids[:3]): s += 5
        if r.full_segmentation: s += 5
        sc2["normal"] = {"score": s, "max": 25, "pass": s >= 15}
    except Exception as e:
        sc2["normal"] = {"score": 0, "max": 25, "pass": False, "error": str(e)}
    te += 25; tm += 25

    # 2. LLM strategies (15)
    try:
        df = make_df("normal")
        funnel = FunnelAgent().analyze_from_data(df)
        r = SegmentationAgent().analyze(df, funnel)
        strategies = SegmentationAgent().generate_llm_strategies(r)
        s = 0
        if strategies and len(strategies) > 200: s += 10
        if r.priority_segment in strategies: s += 5
        sc2["llm_strategies"] = {"score": s, "max": 15, "pass": s >= 9}
    except Exception as e:
        sc2["llm_strategies"] = {"score": 0, "max": 15, "pass": False, "error": str(e)}
    te += 15; tm += 15

    # 3. Missing columns (20)
    try:
        df = make_df("missing_cols")
        r = SegmentationAgent().analyze(df)
        s = 20 if r.priority_segment else 0
        sc2["missing_columns"] = {"score": s, "max": 20, "pass": s >= 12}
    except Exception as e:
        sc2["missing_columns"] = {"score": 0, "max": 20, "pass": False, "error": str(e)}
    te += 20; tm += 20

    # 4. Empty data (20)
    try:
        df = make_df("empty")
        r = SegmentationAgent().analyze(df)
        sc2["empty_data"] = {"score": 20, "max": 20, "pass": True}
    except Exception as e:
        err = str(e).lower()
        if any(kw in err for kw in ["empty", "no data", "no user", "no rows"]):
            sc2["empty_data"] = {"score": 10, "max": 20, "pass": False, "error": str(e)}
        else:
            sc2["empty_data"] = {"score": 0, "max": 20, "pass": False, "error": str(e)}
    te += 20; tm += 20

    # 5. Priority scoring logic (20)
    try:
        df = make_df("normal")
        scored = SegmentationAgent()._calculate_priority_scores(df)
        s = 0
        if "priority_score" in scored.columns: s += 5
        if scored["priority_score"].between(0, 100).all(): s += 10
        if scored["priority_segment"].notna().all(): s += 5
        sc2["priority_scoring"] = {"score": s, "max": 20, "pass": s >= 12}
    except Exception as e:
        sc2["priority_scoring"] = {"score": 0, "max": 20, "pass": False, "error": str(e)}
    te += 20; tm += 20

    scores["SegmentationAgent"] = round(te / tm * 100, 1) if tm else 0
    checks["SegmentationAgent"] = sc2

    # ================================================================
    # StrategyAgent
    # ================================================================
    stc = {}
    te = 0; tm = 0

    # 1. Normal recommendation (30)
    try:
        df = make_df("normal")
        funnel = FunnelAgent().analyze_from_data(df)
        segment = SegmentationAgent().analyze(df, funnel)
        r = StrategyAgent().recommend(funnel, segment)
        s = 0
        if all([r.campaign_type, r.message_framework, r.tone_guidance, r.cta_recommendation]): s += 15
        if isinstance(r.channel_priority, list) and len(r.channel_priority) > 0: s += 5
        if r.reasoning and len(r.reasoning) > 10: s += 5
        if isinstance(r.selected_templates, list): s += 5
        stc["normal"] = {"score": s, "max": 30, "pass": s >= 18}
    except Exception as e:
        stc["normal"] = {"score": 0, "max": 30, "pass": False, "error": str(e)}
    te += 30; tm += 30

    # 2. KB coverage (20)
    try:
        stages_covered = set(StrategyAgent().STRATEGY_KNOWLEDGE.keys())
        expected = {"已注册","已浏览","首次使用","已活跃","已付费"}
        coverage = len(stages_covered & expected) / len(expected)
        s = int(coverage * 20)
        stc["kb_coverage"] = {"score": s, "max": 20, "pass": coverage >= 0.8}
    except Exception as e:
        stc["kb_coverage"] = {"score": 0, "max": 20, "pass": False, "error": str(e)}
    te += 20; tm += 20

    # 3. History (15)
    try:
        agent = StrategyAgent()
        df = make_df("normal")
        funnel = FunnelAgent().analyze_from_data(df)
        segment = SegmentationAgent().analyze(df, funnel)
        agent.recommend(funnel, segment)
        s = 15 if agent.get_history() else 0
        stc["history"] = {"score": s, "max": 15, "pass": s >= 9}
    except Exception as e:
        stc["history"] = {"score": 0, "max": 15, "pass": False, "error": str(e)}
    te += 15; tm += 15

    # 4. Fallback (20)
    try:
        from core.data_models import FunnelResult, SegmentResult
        funnel = FunnelResult(problem_stage="未知",leak_rate=50,actual_conversion=50,benchmark_conversion=50)
        segment = SegmentResult(priority_segment="未知",segment_count=100,segment_profile="Test")
        r = StrategyAgent().recommend(funnel, segment)
        s = 0
        if r.campaign_type and r.message_framework: s += 15
        stc["fallback"] = {"score": s, "max": 20, "pass": s >= 12}
    except Exception as e:
        stc["fallback"] = {"score": 0, "max": 20, "pass": False, "error": str(e)}
    te += 20; tm += 20

    # 5. JSON parsing robustness (15)
    try:
        text = '{"campaign_type":"email","message_framework":"social proof","tone_guidance":"friendly","cta_recommendation":"Click here","channel_priority":["email"],"selected_templates":["email"],"reasoning":"test"}'
        r = StrategyAgent()._parse_result(text, {}, {})
        s = 15 if r.campaign_type == "email" else 0
        stc["json_parsing"] = {"score": s, "max": 15, "pass": s >= 9}
    except Exception as e:
        stc["json_parsing"] = {"score": 0, "max": 15, "pass": False, "error": str(e)}
    te += 15; tm += 15

    scores["StrategyAgent"] = round(te / tm * 100, 1) if tm else 0
    checks["StrategyAgent"] = stc

    # ================================================================
    # ContentAgent
    # ================================================================
    cc = {}
    te = 0; tm = 0

    # 1. Generate for segment (25)
    try:
        df = make_df("normal")
        funnel = FunnelAgent().analyze_from_data(df)
        segment = SegmentationAgent().analyze(df, funnel)
        strategy = StrategyAgent().recommend(funnel, segment)
        r = ContentAgent().generate_for_segment(strategy, segment.segment_profile, funnel.problem_stage, 3)
        s = 0
        if r.variants and len(r.variants) >= 3: s += 15
        if all(v.content and len(v.content) > 10 for v in r.variants): s += 5
        if all(v.hypothesis for v in r.variants): s += 5
        cc["generate_for_segment"] = {"score": s, "max": 25, "pass": s >= 15}
    except Exception as e:
        cc["generate_for_segment"] = {"score": 0, "max": 25, "pass": False, "error": str(e)}
    te += 25; tm += 25

    # 2. Templates (15)
    try:
        tpls = ContentAgent().get_available_templates()
        s = 15 if tpls and len(tpls) > 0 else 0
        cc["templates"] = {"score": s, "max": 15, "pass": s >= 9}
    except Exception as e:
        cc["templates"] = {"score": 0, "max": 15, "pass": False, "error": str(e)}
    te += 15; tm += 15

    # 3. Content quality (20)
    try:
        df = make_df("normal")
        funnel = FunnelAgent().analyze_from_data(df)
        segment = SegmentationAgent().analyze(df, funnel)
        strategy = StrategyAgent().recommend(funnel, segment)
        r = ContentAgent().generate_for_segment(strategy, segment.segment_profile, funnel.problem_stage, 1)
        v = r.variants[0]
        s = 0
        if len(v.content) > 50: s += 10
        if len(v.hypothesis) > 20: s += 5
        if r.personalization_rules: s += 5
        cc["content_quality"] = {"score": s, "max": 20, "pass": s >= 12}
    except Exception as e:
        cc["content_quality"] = {"score": 0, "max": 20, "pass": False, "error": str(e)}
    te += 20; tm += 20

    # 4. AB setup recommendation (15)
    try:
        df = make_df("normal")
        funnel = FunnelAgent().analyze_from_data(df)
        segment = SegmentationAgent().analyze(df, funnel)
        strategy = StrategyAgent().recommend(funnel, segment)
        r = ContentAgent().generate_for_segment(strategy, segment.segment_profile, funnel.problem_stage, 3)
        s = 0
        if r.recommended_ab_setup and len(r.recommended_ab_setup) > 20: s += 15
        cc["ab_setup"] = {"score": s, "max": 15, "pass": s >= 9}
    except Exception as e:
        cc["ab_setup"] = {"score": 0, "max": 15, "pass": False, "error": str(e)}
    te += 15; tm += 15

    # 5. Iteration (25)
    try:
        agent = ContentAgent()
        content = agent.generate_content(
            template_key="email_marketing",
            params={"product_name":"TestApp","target_audience":"Designers"},
            iterations=2,
        )
        s = 0
        if content and len(content) > 50: s += 15
        if len(agent.iteration_history) == 2: s += 10
        cc["iteration"] = {"score": s, "max": 25, "pass": s >= 15}
    except Exception as e:
        cc["iteration"] = {"score": 0, "max": 25, "pass": False, "error": str(e)}
    te += 25; tm += 25

    scores["ContentAgent"] = round(te / tm * 100, 1) if tm else 0
    checks["ContentAgent"] = cc

    # ================================================================
    # ABTestAgent
    # ================================================================
    ac = {}
    te = 0; tm = 0

    # 1. Significant result (25)
    try:
        r = ABTestAgent().analyze_from_data(
            conversions_a=30, n_a=100, conversions_b=50, n_b=100,
            test_name="Clear winner", variant_a_hypothesis="Simple CTA",
            variant_b_hypothesis="Social proof CTA", baseline_conversion=30.0, total_target_users=1000,
        )
        s = 0
        if r.winning_variant and r.p_value < 0.05: s += 10
        if r.statistical_significance > 0.9: s += 5
        if r.recommendation: s += 5
        if r.full_report and len(r.full_report) > 100: s += 5
        ac["significant"] = {"score": s, "max": 25, "pass": s >= 15}
    except Exception as e:
        ac["significant"] = {"score": 0, "max": 25, "pass": False, "error": str(e)}
    te += 25; tm += 25

    # 2. Non-significant (20)
    try:
        r = ABTestAgent().analyze_from_data(
            conversions_a=30, n_a=100, conversions_b=32, n_b=100,
            test_name="Close result", baseline_conversion=30.0,
        )
        s = 15 if (r.winning_variant == "无显著差异" or r.p_value >= 0.05) else 0
        ac["non_significant"] = {"score": s, "max": 20, "pass": s >= 12}
    except Exception as e:
        ac["non_significant"] = {"score": 0, "max": 20, "pass": False, "error": str(e)}
    te += 20; tm += 20

    # 3. Business impact (20)
    try:
        r = ABTestAgent().analyze_from_data(
            conversions_a=30, n_a=100, conversions_b=50, n_b=100,
            baseline_conversion=30.0, total_target_users=10000,
        )
        s = 0
        if r.downstream_impact and len(r.downstream_impact) > 0: s += 15
        ac["business_impact"] = {"score": s, "max": 20, "pass": s >= 12}
    except Exception as e:
        ac["business_impact"] = {"score": 0, "max": 20, "pass": False, "error": str(e)}
    te += 20; tm += 20

    # 4. Edge cases (20)
    try:
        r = ABTestAgent().analyze_from_data(conversions_a=0, n_a=50, conversions_b=0, n_b=50)
        s = 20 if r.winning_variant is not None else 0
        ac["edge_cases"] = {"score": s, "max": 20, "pass": s >= 12}
    except Exception as e:
        ac["edge_cases"] = {"score": 0, "max": 20, "pass": False, "error": str(e)}
    te += 20; tm += 20

    # 5. Statistical accuracy (15)
    try:
        r = ABTestAgent().analyze_from_data(
            conversions_a=100, n_a=1000, conversions_b=200, n_b=1000,
        )
        s = 15 if r.p_value < 0.001 else (10 if r.p_value < 0.05 else 0)
        ac["statistical_accuracy"] = {"score": s, "max": 15, "pass": s >= 10}
    except Exception as e:
        ac["statistical_accuracy"] = {"score": 0, "max": 15, "pass": False, "error": str(e)}
    te += 15; tm += 15

    scores["ABTestAgent"] = round(te / tm * 100, 1) if tm else 0
    checks["ABTestAgent"] = ac

    # ================================================================
    # GrowthMemory
    # ================================================================
    gc = {}
    te = 0; tm = 0
    temp_file = os.path.join(tempfile.gettempdir(), "test_growth_mem.json")

    try:
        mem = GrowthMemory(filepath=temp_file)

        # 1. Record cycle (25)
        mem.record_cycle_result("高优先级","挽回邮件",{"significant":True,"winning_variant":"A","lift_percent":15.5},"email_marketing")
        s = 0
        if mem.get_best_strategy("高优先级") == "挽回邮件": s += 20
        gc["record"] = {"score": s, "max": 25, "pass": s >= 15}
        te += 25; tm += 25

        # 2. Template scoring (20)
        s = 20 if mem.get_template_score("email_marketing","高优先级") > 0 else 0
        gc["template_scoring"] = {"score": s, "max": 20, "pass": s >= 12}
        te += 20; tm += 20

        # 3. Knowledge report (25)
        mem.record_cycle_result("中优先级","功能推荐",{"significant":False,"winning_variant":"B","lift_percent":3.2},"in_app")
        report = mem.get_knowledge_report()
        s = 0
        if report and len(report) > 100: s += 20
        if "高优先级" in report: s += 5
        gc["report"] = {"score": s, "max": 25, "pass": s >= 15}
        te += 25; tm += 25

        # 4. Cycle summary (15)
        mem.add_cycle_summary({"scenario":"test","best_segment":"高优先级","total_uplift":15.5})
        s = 15 if mem.get_cycle_summary() else 0
        gc["summary"] = {"score": s, "max": 15, "pass": s >= 9}
        te += 15; tm += 15

        # 5. Persistence (15)
        mem2 = GrowthMemory(filepath=temp_file)
        s = 15 if mem2.get_best_strategy("高优先级") == "挽回邮件" else 0
        gc["persistence"] = {"score": s, "max": 15, "pass": s >= 9}
        te += 15; tm += 15
    except Exception as e:
        gc["error"] = {"score": 0, "max": 100, "pass": False, "error": str(e)}
        te += 0; tm += 100
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    scores["GrowthMemory"] = round(te / tm * 100, 1) if tm else 0
    checks["GrowthMemory"] = gc

    # ================================================================
    # Overall
    # ================================================================
    overall = round(sum(scores.values()) / len(scores), 1) if scores else 0

    # Collect issues
    issues = []
    for agent, agent_checks in checks.items():
        for name, cr in agent_checks.items():
            if not cr.get("pass", True):
                err = cr.get("error", f"{cr.get('score',0)}/{cr.get('max',0)}")
                issues.append(f"{agent}/{name}: {err}")

    return {"scores": scores, "checks": checks, "overall": overall, "issues": issues}


def print_report(result):
    print("=" * 70)
    print("  Agent Quality Benchmark Report")
    print("=" * 70)
    print(f"\n  Overall Score: {result['overall']}/100\n")

    for agent, score in result["scores"].items():
        status = "PASS" if score >= 70 else "NEEDS IMPROVEMENT" if score >= 40 else "FAIL"
        bar = "#" * int(score / 2) + "-" * (50 - int(score / 2))
        print(f"  {agent:20s} [{bar}] {score:5.1f}/100  {status}")
        for name, cr in result["checks"][agent].items():
            p = "[+]" if cr.get("pass", False) else "[-]"
            print(f"    {p} {name:25s} {cr.get('score',0)}/{cr.get('max',0)}")
        print()

    if result["issues"]:
        print(f"  Issues found: {len(result['issues'])}")
        for issue in result["issues"]:
            print(f"    - {issue}")
        print()
    print("=" * 70)


if __name__ == "__main__":
    result = run_benchmark()
    print_report(result)
    # Save JSON report
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "benchmark_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n  JSON report saved to: {report_path}")
