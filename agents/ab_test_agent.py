"""
A/B测试分析Agent — 实验设计与分析引擎

本 Agent 是 A/B 实验的分析引擎，使用 scipy 实现统计检验。
实验数据来源于外部渠道系统（邮件/短信/CRM 等），本模块不负责数据采集。

关联内容变体，自动计算显著性和商业影响
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm_client import LLMClient
from core.data_models import ABResult
from utils.stats import z_test_proportions, chi_square_test, calculate_sample_size


class ABTestAgent:
    """A/B测试分析Agent"""

    def __init__(self, client: LLMClient = None):
        self.client = client or LLMClient()

    def analyze_from_data(
        self,
        conversions_a: int, n_a: int,
        conversions_b: int, n_b: int,
        test_name: str = "A/B测试",
        variant_a_hypothesis: str = "",
        variant_b_hypothesis: str = "",
        baseline_conversion: float = 0,
        total_target_users: int = 0,
    ) -> ABResult:
        """
        从实际数据分析A/B测试结果

        Args:
            conversions_a/b: A/B组转化数
            n_a/b: A/B组样本量
            test_name: 测试名称
            variant_a/b_hypothesis: 各版本假设
            baseline_conversion: 基线转化率
            total_target_users: 目标用户总数

        Returns:
            ABResult: 分析结果
        """
        # Handle edge cases: zero conversions or zero sample
        if n_a == 0 or n_b == 0:
            return ABResult(
                test_name=test_name,
                winning_variant="无显著差异",
                statistical_significance=0.0,
                p_value=1.0,
                actual_uplift="0.00%",
                downstream_impact="样本量为0，无法计算",
                estimated_monthly_impact="样本量为0，无法计算",
                recommendation="样本量为0，请确保两组都有有效数据后再进行分析",
                full_report="样本量为0，无法进行A/B测试分析。",
                conversion_a=0.0,
                conversion_b=0.0,
            )

        # If both groups have zero conversions, handle gracefully
        if conversions_a == 0 and conversions_b == 0:
            z_result = {"conversion_a": 0.0, "conversion_b": 0.0, "p_value": 1.0, "lift_percent": 0.0}
            chi_result = {"chi2": 0.0, "p_value": 1.0, "significant": False}
            winning = "无显著差异"
            monthly_impact = f"两组均无转化，建议检查漏斗或扩大样本量" if total_target_users > 0 else ""
        else:
            z_result = z_test_proportions(conversions_a, n_a, conversions_b, n_b)
            chi_result = chi_square_test(conversions_a, n_a, conversions_b, n_b)

            # 判定获胜版本
            if z_result["p_value"] < 0.05:
                if z_result["conversion_b"] > z_result["conversion_a"]:
                    winning = "B"
                else:
                    winning = "A"
            else:
                winning = "无显著差异"

            # 计算商业影响
            monthly_impact = ""
            if total_target_users > 0 and baseline_conversion > 0:
                lift = z_result["lift_percent"] / 100
                recovered = int(total_target_users * baseline_conversion / 100 * lift)
                monthly_impact = f"预计每月可多转化约{recovered}名用户"

        # LLM生成报告
        report = self._generate_report(
            test_name, z_result, chi_result,
            winning, variant_a_hypothesis, variant_b_hypothesis, monthly_impact
        )

        return ABResult(
            test_name=test_name,
            winning_variant=winning,
            statistical_significance=1 - z_result["p_value"],
            p_value=z_result["p_value"],
            actual_uplift=f"{z_result['lift_percent']:+.2f}%",
            downstream_impact=monthly_impact,
            estimated_monthly_impact=monthly_impact,
            recommendation=f"{'✅ 建议全量推送' + winning + '版本' if winning != '无显著差异' else '⚠️ 结果不显著，建议扩大样本量继续测试'}",
            full_report=report,
            conversion_a=z_result["conversion_a"],
            conversion_b=z_result["conversion_b"],
        )

    def analyze_from_stages(
        self,
        conversions_a: int, n_a: int,
        conversions_b: int, n_b: int,
        test_name: str = "A/B测试",
    ) -> ABResult:
        """兼容旧接口"""
        z_result = z_test_proportions(conversions_a, n_a, conversions_b, n_b)
        chi_result = chi_square_test(conversions_a, n_a, conversions_b, n_b)

        winning = "B" if z_result["conversion_b"] > z_result["conversion_a"] else "A"
        if z_result["p_value"] >= 0.05:
            winning = "无显著差异"

        report = self._generate_report(
            test_name, z_result, chi_result, winning, "", "", ""
        )

        return ABResult(
            test_name=test_name,
            winning_variant=winning,
            statistical_significance=1 - z_result["p_value"],
            p_value=z_result["p_value"],
            actual_uplift=f"{z_result['lift_percent']:+.2f}%",
            downstream_impact="",
            estimated_monthly_impact="",
            recommendation=f"{'✅ 建议推送' + winning + '版本' if winning != '无显著差异' else '⚠️ 不显著'}",
            full_report=report,
            conversion_a=z_result["conversion_a"],
            conversion_b=z_result["conversion_b"],
        )

    def _generate_report(
        self, test_name, z_result, chi_result,
        winning, hypothesis_a, hypothesis_b, monthly_impact
    ) -> str:
        """生成分析报告"""
        conv_a = z_result["conversion_a"]
        conv_b = z_result["conversion_b"]
        lift = z_result["lift_percent"]
        p_val = z_result["p_value"]
        sample_a = z_result.get("sample_size_a", "N/A")

        commercial_line = f"商业影响：{monthly_impact}" if monthly_impact else ""

        prompt = (
            f"请根据以下A/B测试数据生成分析报告：\n\n"
            f"测试：{test_name}\n"
            f"A组转化率：{conv_a}%（样本{sample_a}）\n"
            f"B组转化率：{conv_b}%\n"
            f"提升：{lift:+.2f}%\n"
            f"P值：{p_val}\n"
            f"获胜版本：{winning}\n"
            f"A版假设：{hypothesis_a}\n"
            f"B版假设：{hypothesis_b}\n"
            f"{commercial_line}\n\n"
            f"请输出：\n"
            f"1. 核心结论（一句话）\n"
            f"2. 数据解读\n"
            f"3. 假设验证结果\n"
            f"4. 业务建议"
        )

        system = "你是一个数据分析师，擅长A/B测试结果解读。"
        return self.client.generate(prompt, system_prompt=system, max_tokens=800)
