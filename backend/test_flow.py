"""
Test Complete Meeting Flow - 测试完整会议流程
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_full_flow():
    # 1. 创建会议
    print("=== 创建会议 ===")
    resp = requests.post(
        f"{API_BASE}/api/meeting/start",
        json={"topic": "贵州茅台值得投资吗"}
    )
    data = resp.json()
    meeting_id = data["meeting_id"]
    print(f"meeting_id: {meeting_id}")

    # 2. 连接SSE获取Phase 0-2
    print("\n=== Phase 0-2 SSE ===")
    url = f"{API_BASE}/api/meeting/{meeting_id}/stream"

    questions = []
    try:
        with requests.get(url, stream=True, timeout=180) as r:
            for line in r.iter_lines(decode_unicode=True):
                if line:
                    print(f"收到: {line[:100]}...")
                    if line.startswith("data: "):
                        try:
                            msg = json.loads(line[6:])
                            print(f"  type={msg.get('type')}, phase={msg.get('phase')}")
                            if msg.get('type') == 'phase_update':
                                phase = msg.get('phase')
                                if phase == 'PHASE_1':
                                    questions = msg.get('data', {}).get('questions', [])
                                    print(f"  问题数: {len(questions)}")
                                elif phase == 'PHASE_2':
                                    advisors = msg.get('data', {}).get('advisors', [])
                                    print(f"  顾问数: {len(advisors)}")
                                    for a in advisors:
                                        print(f"    - {a}")
                            elif msg.get('type') == 'waiting_input':
                                print("  等待用户输入...")
                        except json.JSONDecodeError as e:
                            print(f"  JSON解析失败: {e}")
    except requests.exceptions.Timeout:
        print("SSE超时")

    # 3. 检查会议状态
    print("\n=== 会议状态 ===")
    resp = requests.get(f"{API_BASE}/api/meeting/{meeting_id}")
    state = resp.json()
    print(f"phase: {state['phase']}")
    print(f"selected_advisors: {state['selected_advisors']}")

    # 4. 提交答案
    if questions:
        print("\n=== 提交答案 ===")
        answers = {}
        for i, q in enumerate(questions[:2]):  # 只回答前2个问题简化测试
            answers[f"question_{i}"] = "长期持有"

        resp = requests.post(
            f"{API_BASE}/api/meeting/{meeting_id}/answer",
            json={"answers": answers}
        )
        print(f"响应: {resp.json()}")

        # 5. 连接SSE获取Phase 3-5
        print("\n=== Phase 3-5 SSE ===")
        url = f"{API_BASE}/api/meeting/{meeting_id}/continue"
        try:
            with requests.get(url, stream=True, timeout=300) as r:
                for line in r.iter_lines(decode_unicode=True):
                    if line:
                        print(f"收到: {line[:100]}...")
        except requests.exceptions.Timeout:
            print("SSE超时")

        # 6. 最终状态
        print("\n=== 最终状态 ===")
        resp = requests.get(f"{API_BASE}/api/meeting/{meeting_id}")
        state = resp.json()
        print(f"phase: {state['phase']}")
        print(f"opinions数: {len(state['opinions'])}")
        print(f"resolution: {state['resolution'].get('overall_judgment', 'N/A')}")

if __name__ == "__main__":
    test_full_flow()