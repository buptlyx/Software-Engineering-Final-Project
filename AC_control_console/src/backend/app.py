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
        # 根据楼层确定房间费用 (元/晚)
        # 1楼：100元/晚，2楼：150元/晚，3楼：200元/晚，4楼：250元/晚
        room_price = {1: 100.0, 2: 150.0, 3: 200.0, 4: 250.0}[floor]
        
        room_state[room_id] = {
            "power_on": False,
            "is_active": False, # 是否正在送风/计费
            "fan_speed": "Mid",  # Low, Mid, High
            "initial_temp": 28.0,
            "current_temp": 28.0, # 初始温度稍微有点差异
            "target_temp": 25.0,
            "total_fee": 0.0,
            "duration": 0,
            "room_price": room_price  # 房间费用 (元/晚)
        }
#以下是制冷测试用例
room_state["101"]["initial_temp"] = 32.0
room_state["101"]["current_temp"] = 32.0
room_state["101"]["room_price"] = 100.0

room_state["102"]["initial_temp"] = 28.0
room_state["102"]["current_temp"] = 28.0
room_state["102"]["room_price"] = 125.0

room_state["103"]["initial_temp"] = 30.0
room_state["103"]["current_temp"] = 30.0
room_state["103"]["room_price"] = 150

room_state["104"]["initial_temp"] = 29.0
room_state["104"]["current_temp"] = 29.0
room_state["104"]["room_price"] = 200

room_state["105"]["initial_temp"] = 35.0
room_state["105"]["current_temp"] = 35.0
room_state["105"]["room_price"] = 100.0
#以下是制热测试用例
room_state["106"]["initial_temp"] = 10.0
room_state["106"]["current_temp"] = 10.0
room_state["106"]["room_price"] = 100.0

room_state["107"]["initial_temp"] = 15.0
room_state["107"]["current_temp"] = 15.0
room_state["107"]["room_price"] = 125.0

room_state["108"]["initial_temp"] = 18.0
room_state["108"]["current_temp"] = 18.0
room_state["108"]["room_price"] = 150

room_state["109"]["initial_temp"] = 12.0
room_state["109"]["current_temp"] = 12.0
room_state["109"]["room_price"] = 200

room_state["110"]["initial_temp"] = 14.0
room_state["110"]["current_temp"] = 14.0
room_state["110"]["room_price"] = 100.0
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
    "High": 0.6 / 6.0,
    "Mid":  0.5 / 60.0,
    "Low":  0.4 / 60.0
}
# 回温速率: 0.5度/分钟
RETURN_RATE = 0.5 / 60.0

def background_task():
    """后台线程：负责计费和温度模拟"""
    while True:
        for room_id, state in room_state.items():
            # --- 开机状态逻辑 ---
            if state["power_on"]:
                # 1. 计费逻辑
                # High: 1.0元/60秒, Mid: 1.0元/120秒, Low: 1.0元/180秒
                fee_rates = {"High": 1.0/60, "Mid": 1.0/120, "Low": 1.0/180}
                current_rate = fee_rates.get(state["fan_speed"], 0)
                
                # 2. 温度模拟逻辑
                temp_change = TEMP_RATES.get(state["fan_speed"], 0)
                
                # 逼近目标温度
                diff = state["current_temp"] - state["target_temp"]
                
                # 如果 is_active=False (待机状态)，检查温差是否超过 1 度
                if not state["is_active"]:
                    # 待机中，检查温差是否超过 1 度来决定是否重新启动
                    if abs(diff) > 1.0:
                        state["is_active"] = True
                        print(f"[Auto Reactivate] Room {room_id} temp diff > 1.0. Resuming cooling/heating.")
                    else:
                        # 继续待机，只做回温
                        diff_init = state["current_temp"] - state["initial_temp"]
                        if abs(diff_init) > 0.01:
                            if diff_init > 0:
                                state["current_temp"] -= RETURN_RATE
                            else:
                                state["current_temp"] += RETURN_RATE
                        continue
                
                # 如果温差非常小（例如小于 0.01），认为已达到目标
                if abs(diff) < 0.01:
                    # 达到目标温度，停止送风和计费，进入待机模式
                    state["is_active"] = False
                    print(f"[Reached Target] Room {room_id} reached target temp. Entering idle mode.")
                    
                    # 回温逻辑：向 initial_temp 靠近
                    diff_init = state["current_temp"] - state["initial_temp"]
                    if abs(diff_init) > 0.01:
                        if diff_init > 0:
                            state["current_temp"] -= RETURN_RATE
                        else:
                            state["current_temp"] += RETURN_RATE
                            
                    # 注意：这里不执行 state["total_fee"] += current_rate
                    # 也不执行 state["power_on"] = False
                    
                else:
                    # 未达到目标温度，正常送风和计费
                    state["total_fee"] += current_rate
                    state["duration"] += 1 # 增加运行时长(秒)
                    
                    if diff > 0:
                        state["current_temp"] -= temp_change
                    else:
                        state["current_temp"] += temp_change

            # --- 关机状态逻辑 (仅回温，不自动重启) ---
            else:
                # 1. 回温逻辑：向 initial_temp 靠近
                diff_init = state["current_temp"] - state["initial_temp"]
                
                if abs(diff_init) > 0.01: # 如果还没回到初始温度
                    if diff_init > 0:
                        state["current_temp"] -= RETURN_RATE
                    else:
                        state["current_temp"] += RETURN_RATE
                
                # 2. 自动重启逻辑：已移除
                # 关闭空调后，空调不会自动开机

        time.sleep(1) # 每秒执行一次

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
