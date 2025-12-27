import requests
import pandas as pd
import time

# 配置
API_BASE = "http://localhost:5000/api"
OUTPUT_FILE = "test_report_for_cold.xlsx"

# 测试用例定义
# 格式: { 分钟数: [ (房间号, 动作类型, 值) ] }
# 动作类型: 'power' (True/False), 'temp' (float), 'speed' ('High'/'Mid'/'Low')
# 请根据您的图片内容填写以下字典
TEST_CASES = {
    0: [("101", "power", True)],
    1: [("101", "temp", 18),("102","power", True),("105","power", True)],
    2: [("103", "power", True)],
    3: [("102", "temp", 19), ("104", "power", True)],
    4: [("105", "temp", 22)],
    5: [("101", "speed", "High")],
    6: [("102", "power", False)],
    7: [("102", "power", True), ("105", "speed", "High")],
    9: [("101", "temp", 22), ("104", "temp", 18), ("104", "speed", "High")],
    11: [("102", "temp", 22)],
    12: [("105", "speed", "Low")],
    14: [("101", "power", False), ("103", "temp", 24), ("103", "speed", "Low")],
    15: [("105", "temp", 20), ("105", "speed", "High")],
    16: [("102", "power", False)],
    17: [("103", "speed", "High")],
    18: [("101", "power", True), ("103", "temp", 20), ("103", "speed", "Mid")],
    19: [("102", "power", True)],
    20: [("104", "temp", 25)],
    22: [("103", "power", False)],
    23: [("105", "power", False)],
    24: [("101", "power", False)],
    25: [("102", "power", False), ("104", "power", False)]
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
        # 这里我们假设只关心 101-105 (根据图片推测)
        target_rooms = ["101", "102", "103", "104", "105"]
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
