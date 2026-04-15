"""
统计检验工具函数
用于A/B测试分析
基于 scipy.stats 实现 (https://scipy.org/)
"""

import numpy as np
from scipy import stats


def z_test_proportions(
    conversions_a: int,
    n_a: int,
    conversions_b: int,
    n_b: int,
    alpha: float = 0.05,
) -> dict:
    """
    双样本比例Z检验（用于A/B测试转化率比较）

    Args:
        conversions_a: A组转化数
        n_a: A组样本量
        conversions_b: B组转化数
        n_b: B组样本量
        alpha: 显著性水平

    Returns:
        包含检验结果的字典
    """
    # Handle edge case: both groups have zero conversions
    if conversions_a == 0 and conversions_b == 0:
        return {
            "conversion_a": 0.0, "conversion_b": 0.0, "lift_percent": 0.0,
            "z_statistic": 0.0, "p_value": 1.0, "significant": False,
            "confidence_level": (1 - alpha) * 100,
            "ci_lower": 0.0, "ci_upper": 0.0, "effect_size": 0.0,
            "sample_size_a": n_a, "sample_size_b": n_b,
        }

    p_a = conversions_a / n_a
    p_b = conversions_b / n_b

    # 合并比例
    p_pool = (conversions_a + conversions_b) / (n_a + n_b)

    # 标准误
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))

    # Z统计量
    z_stat = (p_a - p_b) / se if se > 0 else 0.0

    # p值（双尾检验）
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

    # 效应量 (Cohen's h)
    effect_size = 2 * np.arcsin(np.sqrt(p_a)) - 2 * np.arcsin(np.sqrt(p_b))

    # 置信区间
    se_diff = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    z_crit = stats.norm.ppf(1 - alpha / 2)
    ci_lower = (p_a - p_b) - z_crit * se_diff
    ci_upper = (p_a - p_b) + z_crit * se_diff

    # 提升百分比
    lift = (p_b - p_a) / p_a * 100 if p_a > 0 else 0

    significant = p_value < alpha

    return {
        "conversion_a": round(p_a * 100, 2),
        "conversion_b": round(p_b * 100, 2),
        "lift_percent": round(lift, 2),
        "z_statistic": round(z_stat, 4),
        "p_value": round(p_value, 6),
        "significant": significant,
        "confidence_level": (1 - alpha) * 100,
        "ci_lower": round(ci_lower * 100, 2),
        "ci_upper": round(ci_upper * 100, 2),
        "effect_size": round(effect_size, 4),
        "sample_size_a": n_a,
        "sample_size_b": n_b,
    }


def chi_square_test(
    conversions_a: int, n_a: int, conversions_b: int, n_b: int
) -> dict:
    """
    卡方检验（用于A/B测试）

    Args:
        conversions_a: A组转化数
        n_a: A组样本量
        conversions_b: B组转化数
        n_b: B组样本量

    Returns:
        包含检验结果的字典
    """
    # Handle edge cases: zero conversions or zero samples
    if n_a == 0 or n_b == 0:
        return {
            "chi2_statistic": 0.0, "p_value": 1.0, "degrees_of_freedom": 1,
            "cramers_v": 0.0, "significant_05": False, "significant_01": False,
        }

    # Check for zero expected frequencies (all conversions = 0 or all non-conversions = 0)
    if conversions_a == 0 and conversions_b == 0:
        return {
            "chi2_statistic": 0.0, "p_value": 1.0, "degrees_of_freedom": 1,
            "cramers_v": 0.0, "significant_05": False, "significant_01": False,
        }

    observed = np.array([
        [conversions_a, n_a - conversions_a],
        [conversions_b, n_b - conversions_b],
    ])

    # Check if any expected frequency would be zero
    row_sums = observed.sum(axis=1)
    col_sums = observed.sum(axis=0)
    total = observed.sum()
    if total > 0:
        expected = np.outer(row_sums, col_sums) / total
        if (expected == 0).any():
            return {
                "chi2_statistic": 0.0, "p_value": 1.0, "degrees_of_freedom": 1,
                "cramers_v": 0.0, "significant_05": False, "significant_01": False,
            }

    chi2_stat, p_value, dof, expected = stats.chi2_contingency(observed)

    # Cramer's V 效应量
    n = n_a + n_b
    cramers_v = np.sqrt(chi2_stat / (n * (min(2, 2) - 1)))

    return {
        "chi2_statistic": round(chi2_stat, 4),
        "p_value": round(p_value, 6),
        "degrees_of_freedom": dof,
        "cramers_v": round(cramers_v, 4),
        "significant_05": p_value < 0.05,
        "significant_01": p_value < 0.01,
    }


def calculate_sample_size(
    baseline_rate: float,
    mde: float = 0.1,
    alpha: float = 0.05,
    power: float = 0.8,
) -> int:
    """
    计算A/B测试所需样本量

    Args:
        baseline_rate: 基准转化率
        mde: 最小可检测效应（相对提升，如0.1表示10%提升）
        alpha: 显著性水平
        power: 统计功效

    Returns:
        每组所需样本量
    """
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    p1 = baseline_rate
    p2 = baseline_rate * (1 + mde)

    p_bar = (p1 + p2) / 2

    n = (
        (z_alpha * np.sqrt(2 * p_bar * (1 - p_bar))
         + z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2)))
        ** 2
        / (p2 - p1) ** 2
    )

    return int(np.ceil(n))
