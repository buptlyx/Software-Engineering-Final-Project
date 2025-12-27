import requests
import pandas as pd
import time

# 配置
API_BASE = "http://localhost:5000/api"
OUTPUT_FILE = "test_report_for_hot.xlsx"

# 测试用例定义
# 格式: { 分钟数: [ (房间号, 动作类型, 值) ] }
# 动作类型: 'power' (True/False), 'temp' (float), 'speed' ('High'/'Mid'/'Low')
# 请根据您的图片内容填写以下字典
TEST_CASES = {
    0: [("106", "power", True)],
    1: [("106", "temp", 24),("106","power", True)],
    2: [("108", "power", True)],
    3: [("108", "temp", 28), ("109", "power", True), ("110", "power", True)],
    4: [("108", "temp", 28), ("110", "speed", "High")],
    5: [("106", "speed", "High")],
    7: [("110", "temp", 24)],
    9: [("106", "temp", 22), ("109", "temp", 21), ("109", "speed", "High")],
    11: [("110", "speed", "Mid")],

    12: [("107", "power", False)],
    14: [("106", "power", False), ("108", "speed", "Low")],
    16: [("110", "power", False)],

    17: [("108", "speed", "High")],
    18: [("106", "power", True), ("109", "temp", 25), ("109", "speed", "Mid")],

    20: [("107", "temp", 26), ("107", "speed", "Mid"), ("110", "power", True)],


    24: [("106", "power", False), ("108", "power", False), ("110", "power", False)],
    25: [("107", "power", False), ("109", "power", False)]
}

def run_test():
    print("Starting Simulation Mode...")
    requests.post(f"{API_BASE}/test/start")
    
    # 准备数据存储
    report_data = []
    
    # 模拟 25 分钟 (0-25)
    for minute in range(26):
        print(f"--- Minute {minute} ---")
        
        # 1. 执行当前分钟的操作
        if minute in TEST_CASES:
            actions = TEST_CASES[minute]
            for room_id, action_type, value in actions:
                payload = {}
                if action_type == 'power':
                    payload['power_on'] = value
                elif action_type == 'temp':
                    payload['target_temp'] = value
                elif action_type == 'speed':
                    payload['fan_speed'] = value
                
                print(f"  Action: Room {room_id} -> {action_type}={value}")
                requests.post(f"{API_BASE}/room/{room_id}/control", json=payload)
        
        # 2. 获取当前状态快照
        # 获取所有房间状态
        target_rooms = ["106", "107", "108", "109", "110"]
        row = {"Time (min)": minute}
        
        # 获取调度队列信息 (需要后端支持，或者通过遍历所有房间状态推断)
        # 目前后端 /api/room/<id>/status 返回 is_waiting
        service_queue = []
        waiting_queue = []
        
        for rid in target_rooms:
            try:
                resp = requests.get(f"{API_BASE}/room/{rid}/status")
                if resp.status_code == 200:
                    data = resp.json()
                    # 填充房间数据
                    prefix = f"Room {rid}"
                    row[f"{prefix} Current"] = round(data['current_temp'], 2)
                    row[f"{prefix} Target"] = data['target_temp']
                    row[f"{prefix} Speed"] = data['fan_speed'] if data['power_on'] else "OFF"
                    row[f"{prefix} Fee"] = round(data['total_fee'], 2)
                    
                    if data['is_active']:
                        service_queue.append(rid)
                    elif data.get('is_waiting', False): # is_waiting 是我们在 app.py 中添加的
                        waiting_queue.append(rid)
            except Exception as e:
                print(f"Error fetching room {rid}: {e}")

        row["Service Queue"] = ", ".join(service_queue)
        row["Waiting Queue"] = ", ".join(waiting_queue)
        report_data.append(row)
        
        # 3. 前进 1 分钟 (60秒)
        requests.post(f"{API_BASE}/test/tick", json={"seconds": 60})
        
    # 导出 Excel
    df = pd.DataFrame(report_data)
    
    # 调整列顺序 (可选)
    # cols = ["Time (min)"] + [c for c in df.columns if c != "Time (min)"]
    # df = df[cols]
    
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"Report saved to {OUTPUT_FILE}")
    
    print("Stopping Simulation Mode...")
    requests.post(f"{API_BASE}/test/stop")

if __name__ == "__main__":
    run_test()
