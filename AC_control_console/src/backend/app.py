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
    "High": 0.6 / 60.0,
    "Mid":  0.5 / 60.0,
    "Low":  0.4 / 60.0
}
# 回温速率: 0.5度/分钟
RETURN_RATE = 0.5 / 60.0

# --- 调度系统 ---
MAX_SERVICE_SLOTS = 3  # 服务对象上限
WAIT_DURATION_ALLOC = 120  # 等待服务时长 (秒)

class Scheduler:
    def __init__(self):
        self.service_queue = []  # [{'room_id': '101', 'fan_speed': 'High', 'start_time': 123}]
        self.waiting_queue = []  # [{'room_id': '102', 'fan_speed': 'Mid', 'wait_duration': 120}]

    def get_speed_val(self, speed_str):
        return {'High': 3, 'Mid': 2, 'Low': 1}.get(speed_str, 0)

    def request_service(self, room_id, fan_speed):
        """处理服务请求"""
        # 1. 更新现有请求的风速
        in_queue = False
        for item in self.service_queue:
            if item['room_id'] == room_id:
                item['fan_speed'] = fan_speed
                in_queue = True
                break

        if not in_queue:
            for item in self.waiting_queue:
                if item['room_id'] == room_id:
                    item['fan_speed'] = fan_speed
                    in_queue = True
                    break

        # 2. 如果是新请求，先加入等待队列
        if not in_queue:
            self.add_to_waiting(room_id, fan_speed)

        # 3. 执行全局调度平衡
        self.rebalance()

    def rebalance(self):
        """重新平衡服务队列和等待队列 (核心调度逻辑)"""
        # 1. 填充空闲槽位
        while len(self.service_queue) < MAX_SERVICE_SLOTS and self.waiting_queue:
            # 找出等待队列中优先级最高的
            # 优先级: High > Mid > Low
            # 同优先级: 先来后到 (waiting_queue 是按时间顺序 append 的)
            best_waiter = None
            max_prio = -1
            
            for w in self.waiting_queue:
                p = self.get_speed_val(w['fan_speed'])
                if p > max_prio:
                    max_prio = p
                    best_waiter = w
            
            if best_waiter:
                self.waiting_queue.remove(best_waiter)
                self.add_to_service(best_waiter['room_id'], best_waiter['fan_speed'])

        # 2. 抢占逻辑 (当服务满时)
        # 只要存在 等待队列优先级 > 服务队列最低优先级，就进行抢占
        while len(self.service_queue) >= MAX_SERVICE_SLOTS and self.waiting_queue:
            # 找出服务队列中优先级最低的
            min_service_val = 100
            min_service_items = []
            for item in self.service_queue:
                val = self.get_speed_val(item['fan_speed'])
                if val < min_service_val:
                    min_service_val = val
                    min_service_items = [item]
                elif val == min_service_val:
                    min_service_items.append(item)
            
            # 找出等待队列中优先级最高的
            max_wait_val = -1
            max_wait_items = []
            for item in self.waiting_queue:
                val = self.get_speed_val(item['fan_speed'])
                if val > max_wait_val:
                    max_wait_val = val
                    max_wait_items = [item]
                elif val == max_wait_val:
                    max_wait_items.append(item)
            
            # 如果 等待的最大优先级 > 服务的最小优先级 -> 抢占
            if max_wait_val > min_service_val:
                # 牺牲者：最低优先级中服务时间最长的 (start_time 最小)
                victim = min(min_service_items, key=lambda x: x['start_time'])
                # 受益者：最高优先级中等待最久的 (这里取列表第一个，即最早进入的)
                beneficiary = max_wait_items[0]
                
                # 从等待队列移除受益者，防止重复抢占
                self.waiting_queue.remove(beneficiary)
                
                self.preempt_service(victim, beneficiary['room_id'], beneficiary['fan_speed'])
            else:
                # 无法抢占，停止检查
                break

    def release_service(self, room_id):
        """释放服务对象 (关机或达到目标温度)"""
        # 从服务队列移除
        self.service_queue = [i for i in self.service_queue if i['room_id'] != room_id]
        # 从等待队列移除 (如果存在)
        self.waiting_queue = [i for i in self.waiting_queue if i['room_id'] != room_id]
        
        # 触发重平衡以填充空位
        self.rebalance()

    def check_time_slices(self):
        """检查时间片 (每秒调用)"""
        # 更新等待队列的倒计时
        for item in self.waiting_queue:
            item['wait_duration'] -= 1
        
        # 检查是否有等待时长归零的
        expired_items = [i for i in self.waiting_queue if i['wait_duration'] <= 0]
        
        for waiter in expired_items:
            # 时间片轮转策略：
            # 如果等待时间到了，且优先级 >= 服务队列中的最低优先级 (通常是相等，因为如果大于早就抢占了)
            # 尝试替换服务队列中服务时间最长的
            
            if self.service_queue:
                # 找出服务队列中服务时间最长的
                victim = min(self.service_queue, key=lambda x: x['start_time'])
                
                # 只有当 victim 的优先级 <= waiter 的优先级时才抢占
                # (防止低优先级利用时间片抢占高优先级)
                if self.get_speed_val(victim['fan_speed']) <= self.get_speed_val(waiter['fan_speed']):
                    self.waiting_queue.remove(waiter)
                    self.preempt_service(victim, waiter['room_id'], waiter['fan_speed'])
                else:
                    # 无法抢占，重置等待时间
                    waiter['wait_duration'] = WAIT_DURATION_ALLOC

    def add_to_service(self, room_id, fan_speed):
        self.service_queue.append({
            'room_id': room_id,
            'fan_speed': fan_speed,
            'start_time': time.time()
        })
        room_state[room_id]['is_active'] = True
        print(f"[Scheduler] Room {room_id} START service.")

    def add_to_waiting(self, room_id, fan_speed):
        # 检查是否已在等待队列
        for item in self.waiting_queue:
            if item['room_id'] == room_id:
                return
        self.waiting_queue.append({
            'room_id': room_id,
            'fan_speed': fan_speed,
            'wait_duration': WAIT_DURATION_ALLOC
        })
        room_state[room_id]['is_active'] = False # 等待中不送风
        print(f"[Scheduler] Room {room_id} ENTER waiting queue.")

    def preempt_service(self, victim, new_room_id, new_fan_speed):
        """抢占服务"""
        print(f"[Scheduler] Preempting Room {victim['room_id']} for Room {new_room_id}")
        # 移除受害者
        self.service_queue.remove(victim)
        # 受害者进入等待队列
        self.add_to_waiting(victim['room_id'], victim['fan_speed'])
        # 新房间进入服务队列
        self.add_to_service(new_room_id, new_fan_speed)

scheduler = Scheduler()

def background_task():
    """后台线程：负责计费和温度模拟"""
    while True:
        # 调度器时间片检查
        scheduler.check_time_slices()

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
                
                # 如果 is_active=False (待机状态/等待调度)，检查温差是否超过 1 度
                if not state["is_active"]:
                    # 检查是否在等待队列中 (如果是等待调度，则不做自动重启判断，由调度器控制)
                    in_waiting = any(i['room_id'] == room_id for i in scheduler.waiting_queue)
                    
                    if not in_waiting:
                        # 纯待机 (达到目标温度后的Idle)，检查温差是否超过 1 度来决定是否重新请求服务
                        if abs(diff) > 1.0:
                            print(f"[Auto Reactivate] Room {room_id} temp diff > 1.0. Requesting service.")
                            scheduler.request_service(room_id, state["fan_speed"])
                        else:
                            # 继续待机，只做回温
                            diff_init = state["current_temp"] - state["initial_temp"]
                            if abs(diff_init) > 0.01:
                                if diff_init > 0:
                                    state["current_temp"] -= RETURN_RATE
                                else:
                                    state["current_temp"] += RETURN_RATE
                    else:
                        # 在等待队列中，也只做回温
                        diff_init = state["current_temp"] - state["initial_temp"]
                        if abs(diff_init) > 0.01:
                            if diff_init > 0:
                                state["current_temp"] -= RETURN_RATE
                            else:
                                state["current_temp"] += RETURN_RATE
                    
                    continue
                
                # 如果温差非常小（例如小于 0.01），认为已达到目标
                if abs(diff) < 0.01:
                    # 达到目标温度，停止送风和计费，释放服务资源
                    print(f"[Reached Target] Room {room_id} reached target temp. Releasing service.")
                    scheduler.release_service(room_id)
                    state["is_active"] = False
                    
                    # 回温逻辑：向 initial_temp 靠近
                    diff_init = state["current_temp"] - state["initial_temp"]
                    if abs(diff_init) > 0.01:
                        if diff_init > 0:
                            state["current_temp"] -= RETURN_RATE
                        else:
                            state["current_temp"] += RETURN_RATE
                            
                else:
                    # 正常送风和计费 (只有 is_active=True 才会到这里)
                    state["total_fee"] += current_rate
                    state["duration"] += 1 # 增加运行时长(秒)
                    
                    if diff > 0:
                        state["current_temp"] -= temp_change
                    else:
                        state["current_temp"] += temp_change

            # --- 关机状态逻辑 (仅回温，不自动重启) ---
            else:
                # 确保释放资源
                if state["is_active"] or any(i['room_id'] == room_id for i in scheduler.waiting_queue):
                     scheduler.release_service(room_id)
                     state["is_active"] = False

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
        # 返回状态副本，并添加是否在等待队列的信息
        state = room_state[room_id].copy()
        state['is_waiting'] = any(i['room_id'] == room_id for i in scheduler.waiting_queue)
        return jsonify(state)
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
        
        if state['power_on']:
            # 开机，请求服务
            scheduler.request_service(room_id, state['fan_speed'])
        else:
            # 关机，释放服务
            scheduler.release_service(room_id)
            state['is_active'] = False

    if 'target_temp' in data:
        state['target_temp'] = data['target_temp']
        print(f"[Control] Room {room_id} Target Temp -> {state['target_temp']}")
        # 调温可能触发重新调度 (如果之前是Idle状态)
        if state['power_on'] and not state['is_active']:
             # 检查温差，如果需要则请求服务
             diff = state["current_temp"] - state["target_temp"]
             if abs(diff) > 1.0:
                 scheduler.request_service(room_id, state['fan_speed'])

    if 'fan_speed' in data:
        state['fan_speed'] = data['fan_speed']
        print(f"[Control] Room {room_id} Fan Speed -> {state['fan_speed']}")
        # 调速，更新调度请求
        if state['power_on']:
            scheduler.request_service(room_id, state['fan_speed'])
        
    return jsonify({"status": "success", "current_state": state})

if __name__ == '__main__':
    print("启动 Python 后端计费服务...")
    app.run(port=5000)
