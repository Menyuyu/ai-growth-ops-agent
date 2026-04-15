"""
Harness Engineering 自动化评估流水线

流程：跑分 → 诊断失败 → 输出修复建议 → 等待复测
这是一个最小实现，演示完整的评估迭代循环。
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.benchmark import run_benchmark, print_report

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def run_harness_loop(iteration: int = None):
    """运行一次评估迭代"""
    print("=" * 70)
    print("  Harness Engineering - 评估迭代循环")
    print(f"  迭代 #{iteration} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    # Step 1: 跑分
    print("[1/3] 跑分：运行 Agent 质量评估...")
    result = run_benchmark()

    # Step 2: 输出报告
    print("[2/3] 诊断：分析评估结果...")
    print()
    print_report(result)

    # Step 3: 输出修复建议
    print("[3/3] 优化建议：")
    issues = result.get("issues", [])
    if issues:
        print(f"\n  发现 {len(issues)} 个待修复项：")
        for i, issue in enumerate(issues, 1):
            agent = issue.split("/")[0]
            test = issue.split("/")[1].split(":")[0]
            print(f"  {i}. [{agent}] {test}")
        print()
        print("  建议：针对以上 issue 修复对应 Agent 代码，然后重新运行本脚本复测。")
    else:
        print()
        print("  所有测试通过，无需修复。")

    print()

    # 保存报告
    report_file = os.path.join(REPORTS_DIR, f"harness_iteration_{iteration}.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "iteration": iteration,
            "timestamp": datetime.now().isoformat(),
            "overall_score": result["overall"],
            "agent_scores": result["scores"],
            "issues": result["issues"],
        }, f, ensure_ascii=False, indent=2)

    print(f"  报告已保存: {report_file}")

    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Harness Engineering 评估流水线")
    parser.add_argument("--iter", type=int, default=1, help="迭代轮次编号")
    args = parser.parse_args()

    run_harness_loop(args.iter)
