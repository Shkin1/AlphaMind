"""
Test SSE Stream - 测试SSE流是否正常工作
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_sse():
    # 1. 创建会议
    print("1. 创建会议...")
    resp = requests.post(
        f"{API_BASE}/api/meeting/start",
        json={"topic": "格力电器值得买入吗？"}
    )
    data = resp.json()
    meeting_id = data["meeting_id"]
    print(f"   meeting_id: {meeting_id}")

    # 2. 连接SSE
    print("2. 连接SSE流...")
    url = f"{API_BASE}/api/meeting/{meeting_id}/stream"

    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            print(f"   状态码: {r.status_code}")
            print(f"   Content-Type: {r.headers.get('content-type')}")

            print("3. 接收SSE数据...")
            for line in r.iter_lines(decode_unicode=True):
                if line:
                    print(f"   收到: {line}")
                    # 解析数据
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            print(f"   解析: type={data.get('type')}, phase={data.get('phase')}")
                        except json.JSONDecodeError as e:
                            print(f"   JSON解析失败: {e}")
                    elif line.startswith(":"):
                        print(f"   Ping: {line}")

    except requests.exceptions.Timeout:
        print("   超时！SSE流未返回数据")
    except Exception as e:
        print(f"   错误: {e}")

if __name__ == "__main__":
    test_sse()