"""
端到端测试脚本
模拟完整增长周期，验证数据在 Agent 间正确流转
通过 HTTP API 调用（与 n8n 工作流相同的方式）
"""

import sys
import os
import json
import re
import urllib.request
import urllib.error
import urllib.parse

BASE_URL = os.getenv("API_URL", "http://localhost:8000")
PASS = "[OK]"
FAIL = "[FAIL]"
ARROW = "  ->"

passed = 0
failed = 0


def sanitize(text):
    """Remove emojis and non-ASCII characters for Windows console"""
    return re.sub(r'[^\x00-\x7F\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', '', str(text))


def post(path, params=None):
    """Send POST request"""
    url = f"{BASE_URL}{path}"
    if params:
        qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url = f"{url}?{qs}"
    req = urllib.request.Request(url, method="POST", data=b"")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"  {FAIL} Connection failed: {e}")
        print(f"  Tip: uvicorn api.server:app --host 0.0.0.0 --port 8000")
        sys.exit(1)


def get(path):
    """Send GET request"""
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"  {FAIL} Connection failed: {e}")
        sys.exit(1)


def check(name, condition, detail=""):
    """Check condition"""
    global passed, failed
    if condition:
        passed += 1
        print(f"  {PASS} {name}")
    else:
        failed += 1
        print(f"  {FAIL} {name} -- {sanitize(detail)}")


def main():
    global passed, failed

    print("=" * 60)
    print("GrowthLoop AI - End-to-End Test")
    print(f"API URL: {BASE_URL}")
    print("=" * 60)

    # ========== Phase 1: Funnel Diagnosis ==========
    print(f"\n{'='*60}")
    print("Phase 1: Funnel Diagnosis")
    print(f"{'='*60}")

    diagnose = post("/api/diagnose")
    check("has problem_stage", "problem_stage" in diagnose, diagnose.keys())
    check("has leak_rate", "leak_rate" in diagnose, diagnose.keys())
    check("has actual_conversion", "actual_conversion" in diagnose, diagnose.keys())
    check("has benchmark_gap", "benchmark_gap" in diagnose, diagnose.keys())

    if "problem_stage" in diagnose:
        print(f"  {ARROW} Problem stage: {sanitize(diagnose['problem_stage'])}")
        print(f"  {ARROW} Leak rate: {diagnose.get('leak_rate', 'N/A')}%")
        print(f"  {ARROW} Actual conversion: {diagnose.get('actual_conversion', 'N/A')}%")
        print(f"  {ARROW} Benchmark gap: {diagnose.get('benchmark_gap', 'N/A')}%")

    # ========== Phase 2: User Segmentation ==========
    print(f"\n{'='*60}")
    print("Phase 2: User Segmentation")
    print(f"{'='*60}")

    segment = post("/api/segment")
    check("has priority_segment", "priority_segment" in segment, segment.keys())
    check("has segment_count", "segment_count" in segment, segment.keys())
    check("has segment_profile", "segment_profile" in segment, segment.keys())
    check("has recommended_intervention", "recommended_intervention" in segment, segment.keys())

    if "priority_segment" in segment:
        print(f"  {ARROW} Priority segment: {sanitize(segment['priority_segment'])}")
        print(f"  {ARROW} User count: {segment.get('segment_count', 'N/A')}")
        print(f"  {ARROW} Profile: {sanitize(segment.get('segment_profile', 'N/A'))}")

    # ========== Phase 3a: Strategy Recommendation ==========
    print(f"\n{'='*60}")
    print("Phase 3a: Strategy Recommendation")
    print(f"{'='*60}")

    strategy = post("/api/strategy")
    check("has campaign_type", "campaign_type" in strategy, strategy.keys())
    check("has message_framework", "message_framework" in strategy, strategy.keys())
    check("has tone_guidance", "tone_guidance" in strategy, strategy.keys())
    check("has channel_priority", "channel_priority" in strategy, strategy.keys())
    check("channel_priority is list", isinstance(strategy.get("channel_priority"), list), type(strategy.get("channel_priority")))

    if "campaign_type" in strategy:
        print(f"  {ARROW} Campaign: {sanitize(strategy['campaign_type'])}")
        print(f"  {ARROW} Framework: {sanitize(strategy.get('message_framework', 'N/A'))}")

    # ========== Phase 3b: Content Generation ==========
    print(f"\n{'='*60}")
    print("Phase 3b: Content Generation")
    print(f"{'='*60}")

    content = post("/api/generate", {"variant_count": 3})
    check("has variants", "variants" in content, content.keys())
    variants = content.get("variants", [])
    check("generates 3 variants", len(variants) >= 3, f"actual: {len(variants)}")

    for i, v in enumerate(variants[:3]):
        check(f"variant {i+1} has content", "content" in v, v.keys())
        check(f"variant {i+1} has hypothesis", "hypothesis" in v, v.keys())

    if variants:
        print(f"  {ARROW} Variants generated: {len(variants)}")

    # ========== Phase 4: A/B Test Analysis ==========
    print(f"\n{'='*60}")
    print("Phase 4: A/B Test Analysis")
    print(f"{'='*60}")

    abtest = post("/api/abtest", {
        "conversions_a": 30,
        "n_a": 100,
        "conversions_b": 45,
        "n_b": 100,
        "test_name": "email_test",
    })
    check("has winning_variant", "winning_variant" in abtest, abtest.keys())
    check("has p_value", "p_value" in abtest, abtest.keys())
    check("has actual_uplift", "actual_uplift" in abtest, abtest.keys())
    check("has recommendation", "recommendation" in abtest, abtest.keys())

    p_value = abtest.get("p_value", 1)
    check("p_value is numeric", isinstance(p_value, (int, float)), type(p_value))

    if "winning_variant" in abtest:
        print(f"  {ARROW} Winner: {sanitize(abtest['winning_variant'])}")
        print(f"  {ARROW} p-value: {abtest.get('p_value', 0):.4f}")
        print(f"  {ARROW} Uplift: {sanitize(abtest.get('actual_uplift', 'N/A'))}")

    # ========== Phase 5: Knowledge Persistence ==========
    print(f"\n{'='*60}")
    print("Phase 5: Knowledge Persistence")
    print(f"{'='*60}")

    record = post("/api/memory/record", {
        "segment": "high_priority",
        "strategy": strategy.get("campaign_type", "test"),
        "significant": "true" if p_value < 0.05 else "false",
        "winning_variant": abtest.get("winning_variant", "A"),
        "lift_percent": 15.5,
    })
    check("record success", record.get("status") == "recorded", record)

    memory = get("/api/memory")
    check("has knowledge_report", "knowledge_report" in memory, memory.keys())
    check("report not empty", len(memory.get("knowledge_report", "")) > 0, "empty")

    if "knowledge_report" in memory:
        print(f"  {ARROW} Report length: {len(memory['knowledge_report'])} chars")

    # ========== Summary ==========
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")

    if failed == 0:
        print("\nALL PASSED: Full growth cycle data flow verified!")
    else:
        print(f"\nWARNING: {failed} checks failed.")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
