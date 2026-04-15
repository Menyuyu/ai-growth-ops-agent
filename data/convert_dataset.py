"""
将 zengweida/e-commerce 数据集转换为 GrowthLoop 项目格式

输入: E_commerce.csv (795 客户, 51289 订单)
输出: data/kaggle_users.csv (与 mock_users_saas.csv 同格式)
"""

import os
import sys
import random
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

KAGGLE_PATH = os.path.expanduser("~/.cache/kagglehub/datasets/zengweida/e-commerce/versions/1/E_commerce.csv")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle_users.csv")

random.seed(42)

def main():
    print(f"加载数据: {KAGGLE_PATH}")
    df = pd.read_csv(KAGGLE_PATH, low_memory=False)

    # 清理金额字段 — 正则提取数字部分，处理 '$140.00 ' 和 '0.xf' 等异常值
    for col in ["Sales", "Profit", "Shipping Cost"]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace("$", "")
            .str.strip()
        )
        # 非数字值设为 0（如 '0.xf' 这种数据损坏行）
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # 解析日期
    df["Order Date"] = pd.to_datetime(df["Order Date"], format="%Y/%m/%d")

    # 参考日期 = 最新订单日期 + 1 天
    ref_date = df["Order Date"].max() + timedelta(days=1)
    print(f"参考日期: {ref_date.strftime('%Y-%m-%d')}")

    # 按客户聚合
    user_agg = df.groupby("Customer ID").agg(
        # Recency: 最近一次订单距参考日期的天数
        recency_days=("Order Date", lambda x: (ref_date - x.max()).days),
        # Frequency: 订单总数
        frequency_orders=("Order ID", "count"),
        # Monetary: 总销售额
        monetary_spent=("Sales", "sum"),
        # 首次下单日期
        first_order=("Order Date", "min"),
        # 浏览时长（平均）
        avg_browsing=("Browsing Time (min)", "mean"),
        # Like/Share/Cart 总次数
        like_count=("Like", "sum"),
        share_count=("Share", "sum"),
        cart_count=("Add to Cart", "sum"),
        # 国家/地区（取第一条）
        country=("Country", "first"),
        segment=("Segment", "first"),
        # Product Category 多样性
        category_diversity=("Product Category", "nunique"),
    ).reset_index()

    print(f"客户数: {len(user_agg)}")

    records = []
    for _, row in user_agg.iterrows():
        uid = str(row["Customer ID"])
        recency = int(row["recency_days"])
        frequency = int(row["frequency_orders"])
        monetary = round(float(row["monetary_spent"]), 2)

        days_since = int((ref_date - row["first_order"]).days)
        avg_duration = round(float(row["avg_browsing"]), 1)
        likes = int(row["like_count"])
        shares = int(row["share_count"])
        carts = int(row["cart_count"])
        categories = int(row["category_diversity"])

        # 漏斗阶段映射 — 基于订单频率的百分位数
        # 该数据集每行都是一个订单，所有客户都有购买记录
        # 用 frequency 的百分位数映射到标准漏斗：已注册→已浏览→首次使用→已活跃→已付费
        # frequency 范围: 29 ~ 108
        if frequency >= 85:
            funnel_level = 4  # 已付费
        elif frequency >= 65:
            funnel_level = 3  # 已活跃
        elif frequency >= 50:
            funnel_level = 2  # 首次使用
        elif frequency >= 35:
            funnel_level = 1  # 已浏览
        else:
            funnel_level = 0  # 已注册

        # churn_risk: 基于 RFM 综合评分（适配该数据集范围）
        churn_risk = min(100, max(1, int(
            30 +
            recency * 0.4 +
            max(0, 108 - frequency) * 0.3 +
            max(0, 17000 - monetary) * 0.002
        )))

        records.append({
            "user_id": f"K{uid}",
            "signup_date": row["first_order"].strftime("%Y-%m-%d"),
            "channel": random.choice(["自然搜索", "付费广告", "社交媒体", "推荐", "直接访问"]),
            "plan_type": random.choice(["免费版", "试用版", "专业版"]),
            "funnel_level": funnel_level,
            "recency_days": recency,
            "frequency_sessions": frequency,
            "monetary_spent": monetary,
            "design_count": likes,
            "export_count": frequency,
            "share_count": shares,
            "avg_session_duration": avg_duration,
            "features_used": categories,
            "trial_days_remaining": random.randint(0, 30),
            "days_since_signup": days_since,
            "has_completed_core_action": frequency > 0 or carts > 0,
            "email_opened_last_campaign": random.random() > 0.5,
            "churn_risk_score": churn_risk,
        })

    result = pd.DataFrame(records)

    # 将 funnel_level 映射为阶段名称
    funnel_names = ["已注册", "已浏览", "首次使用", "已活跃", "已付费"]
    result["funnel_stage"] = result["funnel_level"].map(lambda x: funnel_names[x])

    # 删除中间列，保持和 mock 数据一致
    result = result.drop(columns=["funnel_level"])
    result.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"\n输出完成:")
    print(f"  路径: {OUTPUT_FILE}")
    print(f"  用户数: {len(result)}")
    print(f"  漏斗分布:")
    for stage, count in result["funnel_stage"].value_counts().items():
        pct = count / len(result) * 100
        print(f"    {stage}: {count} ({pct:.1f}%)")
    print(f"\n  recency_days: {result['recency_days'].min()} ~ {result['recency_days'].max()}")
    print(f"  frequency_sessions: {result['frequency_sessions'].min()} ~ {result['frequency_sessions'].max()}")
    print(f"  monetary_spent: ${result['monetary_spent'].min():.2f} ~ ${result['monetary_spent'].max():.2f}")
    print(f"\n可直接在 Streamlit 界面上传此文件使用。")


if __name__ == "__main__":
    main()
