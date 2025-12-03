from flask import Flask, jsonify, request
from flask_cors import CORS
import time
from threading import Thread

app = Flask(__name__)
CORS(app)  # 允许跨域请求，方便前端调用

# 模拟数据库：存储房间状态
# 初始化 40 个房间 (101-110, 201-210, 301-310, 401-410)
room_state = {}
for floor in range(1, 5):  # 1到4层
    for r in range(1, 11): # 每层10个房间
        room_id = f"{floor}{r:02d}"
        room_state[room_id] = {
            "power_on": False,
            "fan_speed": "Mid",  # Low, Mid, High
            "current_temp": 25.0, 
            "target_temp": 25.0,
            "total_fee": 0.0,
            "duration": 0
        }

# 计费费率 (元/秒)
# High: 1度/1分钟 = 1.0元/60秒
# Mid:  1度/2分钟 = 1.0元/120秒
# Low:  1度/3分钟 = 1.0元/180秒
FEE_RATES = {
    "High": 1.0 / 60.0,
    "Mid":  1.0 / 120.0,
    "Low":  1.0 / 180.0
}

# 温度变化速率 (°C/秒)
# High: 0.6度/分钟
# Mid:  0.5度/分钟
# Low:  0.4度/分钟
TEMP_RATES = {
    "High": 0.6 / 60.0,
    "Mid":  0.5 / 60.0,
    "Low":  0.4 / 60.0
}

def background_task():
    """后台线程：负责计费和温度模拟"""
    while True:
        for room_id, state in room_state.items():
            if state["power_on"]:
                # 1. 计费逻辑
                rate = FEE_RATES.get(state["fan_speed"], 0)
                state["total_fee"] += rate
                state["duration"] += 1

                # 2. 温度模拟逻辑
                temp_change = TEMP_RATES.get(state["fan_speed"], 0)
                
                # 逼近目标温度
                diff = state["current_temp"] - state["target_temp"]
                if abs(diff) < temp_change:
                    state["current_temp"] = state["target_temp"]
                elif diff > 0:
                    state["current_temp"] -= temp_change
                else:
                    state["current_temp"] += temp_change
                
                # [调试日志] 打印当前状态，方便观察变化
                print(f"[Room {room_id}] 风速:{state['fan_speed']} | 温度:{state['current_temp']:.4f} (变化:{temp_change:.4f}/s) | 费用:{state['total_fee']:.4f}")
        
        time.sleep(1)  # 每秒执行一次

# 启动后台线程
thread = Thread(target=background_task)
thread.daemon = True
thread.start()

@app.route('/api/room/<room_id>/status', methods=['GET'])
def get_room_status(room_id):
    """获取房间状态接口"""
    if room_id in room_state:
        return jsonify(room_state[room_id])
    else:
        return jsonify({"error": "Room not found"}), 404

@app.route('/api/room/<room_id>/control', methods=['POST'])
def control_room(room_id):
    """控制房间接口 (开关、调温、调风速)"""
    if room_id not in room_state:
        return jsonify({"error": "Room not found"}), 404
    
    data = request.json
    state = room_state[room_id]
    
    # 更新状态
    if 'power_on' in data:
        state['power_on'] = data['power_on']
        print(f"[Control] Room {room_id} Power -> {state['power_on']}")
    if 'target_temp' in data:
        state['target_temp'] = data['target_temp']
        print(f"[Control] Room {room_id} Target Temp -> {state['target_temp']}")
    if 'fan_speed' in data:
        state['fan_speed'] = data['fan_speed']
        print(f"[Control] Room {room_id} Fan Speed -> {state['fan_speed']}")
        
    return jsonify({"status": "success", "current_state": state})

if __name__ == '__main__':
    print("启动 Python 后端计费服务...")
    app.run(port=5000)
