"""
下载 Kaggle 公开数据集用于 AIGC 行业洞察演示
依赖: pip install kaggle
需要先配置 Kaggle API Token (kaggle.json)
"""

import os
import sys
import zipfile
import shutil

KAGGLE_DIR = os.path.join(os.path.dirname(__file__), "kaggle")
os.makedirs(KAGGLE_DIR, exist_ok=True)

DATASETS = {
    "gen-ai-apps-reviews": {
        "slug": "rehamalabduljabbar/gen-ai-tools-appstore-googleplay",
        "desc": "Gen AI 应用商店评论 (ChatGPT/Bing/Gemini/Co-Pilot)",
        "target_file": "gen_ai_app_reviews.csv",
    },
    "ai-tools-ecosystem": {
        "slug": "zulqarnain11/ai-tools-ecosystem-dataset-2024-2025",
        "desc": "AI 工具生态 (467+ 工具)",
        "target_file": "ai_tools_ecosystem.csv",
    },
    "midjourney-prompts": {
        "slug": "succinctlyai/midjourney-texttoimage",
        "desc": "Midjourney 生成提示词 (250k+)",
        "target_file": "midjourney_prompts.csv",
    },
}


def download_dataset(slug, target_path):
    """使用 kaggle CLI 下载数据集"""
    import subprocess

    print(f"  下载: {slug}")
    try:
        result = subprocess.run(
            ["kaggle", "datasets", "download", "-d", slug, "-p", KAGGLE_DIR],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            print(f"  下载失败: {result.stderr.strip()}")
            return False

        # 解压 zip 文件
        for f in os.listdir(KAGGLE_DIR):
            if f.endswith(".zip"):
                zip_path = os.path.join(KAGGLE_DIR, f)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(KAGGLE_DIR)
                os.remove(zip_path)
                print(f"  解压完成: {f}")
                return True

        print("  警告: 未找到 zip 文件")
        return False

    except subprocess.TimeoutExpired:
        print("  下载超时")
        return False
    except FileNotFoundError:
        print("  错误: kaggle CLI 未安装。请运行: pip install kaggle")
        print("  并配置 API token: kaggle datasets init")
        return False
    except Exception as e:
        print(f"  错误: {e}")
        return False


def main():
    print("=" * 60)
    print("GrowthLoop AI - Kaggle 数据集下载")
    print("=" * 60)
    print()

    # 检查是否已有数据
    existing = [f for f in os.listdir(KAGGLE_DIR) if f.endswith(".csv")]
    if existing:
        print(f"发现已有 {len(existing)} 个 CSV 文件:")
        for f in existing:
            size = os.path.getsize(os.path.join(KAGGLE_DIR, f)) / 1024
            print(f"  {f} ({size:.0f} KB)")
        print()

    all_ok = True
    for key, info in DATASETS.items():
        target = os.path.join(KAGGLE_DIR, info["target_file"])
        if os.path.exists(target):
            print(f"[+] {info['desc']} — 已存在")
        else:
            ok = download_dataset(info["slug"], target)
            if ok:
                print(f"[+] {info['desc']} — 下载完成")
            else:
                print(f"[-] {info['desc']} — 下载失败")
                all_ok = False

    print()
    if all_ok:
        print("所有数据集准备就绪！")
    else:
        print("部分数据集下载失败。")
        print()
        print("备选方案：如果无法使用 Kaggle CLI，可以手动下载：")
        for key, info in DATASETS.items():
            url = f"https://www.kaggle.com/datasets/{info['slug']}"
            print(f"  {info['desc']}: {url}")
        print()
        print("下载后将 CSV 文件放入 data/kaggle/ 目录即可。")


if __name__ == "__main__":
    main()
