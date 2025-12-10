from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import time
import random
import datetime
from threading import Thread
import database  # Import database module

app = Flask(__name__)
CORS(app)

# Initialize Database
database.init_db()

# --- Configuration ---
class Config:
    # 计费费率 (元/秒)
    FEE_RATES = {
        "High": 1.0 / 60.0,
        "Mid":  1.0 / 120.0,
        "Low":  1.0 / 180.0
    }
    # 温度变化速率 (°C/秒)
    TEMP_RATES = {
        "High": 0.6 / 60.0,
        "Mid":  0.5 / 60.0,
        "Low":  0.4 / 60.0
    }
    # 回温速率: 0.5度/分钟
    RETURN_RATE = 0.5 / 60.0
    
    MAX_SERVICE_SLOTS = 3
    WAIT_DURATION_ALLOC = 120

# --- Room ---
class Room:
    def __init__(self, room_id, floor, initial_temp=28.0):
        self.room_id = room_id
        self.floor = floor
        
        # Room Info
        room_num = int(room_id[-2:])
        
        if floor == 1:
            self.room_type = '豪华大床' if room_num > 8 else '标准间'
            self.room_price = 350.0 if room_num > 8 else 220.0
            self.deposit = 500.0
        else:
            self.room_type = '标准间'
            self.room_price = 220.0
            self.deposit = 0.0
            
        self.is_free = True
        
        # State
        self.power_on = False
        self.is_active = False  # Serving state
        self.fan_speed = "Mid"
        self.initial_temp = initial_temp
        self.current_temp = initial_temp
        self.target_temp = 25.0
        self.total_fee = 0.0
        self.duration = 0  # seconds
        
        # Tenant Info
        self.tenant_id = None
        self.tenant_name = None
        self.tenant_phone = None
        self.stay_days = 0
        
        # Session Info
        self.current_session_start_time = None
        self.current_session_fee_start = 0.0
        
        # Stats
        self.dispatch_count = 0
        self.speed_stats = {
            "High": {"duration": 0, "fee": 0.0},
            "Mid": {"duration": 0, "fee": 0.0},
            "Low": {"duration": 0, "fee": 0.0}
        }

    def to_dict(self):
        return {
            "room_id": self.room_id,
            "type": self.room_type,
            "price": self.room_price,
            "deposit": self.deposit,
            "isFree": self.is_free,
            "power_on": self.power_on,
            "is_active": self.is_active,
            "fan_speed": self.fan_speed,
            "initial_temp": self.initial_temp,
            "current_temp": self.current_temp,
            "target_temp": self.target_temp,
            "total_fee": self.total_fee,
            "duration": self.duration,
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant_name,
            "tenant_phone": self.tenant_phone,
            "stay_days": self.stay_days
        }

    def update_temp_and_fee(self):
        """Update temperature and fee based on current state"""
        if not self.power_on:
            self._handle_return_temp()
            return

        if self.is_active:
            # Active: Cooling/Heating and Charging
            current_rate = Config.FEE_RATES.get(self.fan_speed, 0)
            temp_change = Config.TEMP_RATES.get(self.fan_speed, 0)
            
            self.total_fee += current_rate
            self.duration += 1
            
            # Update stats
            if self.fan_speed in self.speed_stats:
                self.speed_stats[self.fan_speed]['duration'] += 1
                self.speed_stats[self.fan_speed]['fee'] += current_rate
            
            diff = self.current_temp - self.target_temp
            if diff > 0:
                self.current_temp -= temp_change
            else:
                self.current_temp += temp_change
        else:
            # Inactive (Waiting or Idle): Return temp
            self._handle_return_temp()

    def _handle_return_temp(self):
        diff_init = self.current_temp - self.initial_temp
        if abs(diff_init) > 0.01:
            if diff_init > 0:
                self.current_temp -= Config.RETURN_RATE
            else:
                self.current_temp += Config.RETURN_RATE

# --- Scheduler ---
class Scheduler:
    def __init__(self):
        self.service_queue = []  # List of dicts
        self.waiting_queue = []  # List of dicts

    def get_speed_val(self, speed_str):
        return {'High': 3, 'Mid': 2, 'Low': 1}.get(speed_str, 0)

    def request_service(self, room_id, fan_speed):
        """Handle service request"""
        # 1. Update existing request
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

        # 2. Add to queue if new
        if not in_queue:
            if len(self.service_queue) < Config.MAX_SERVICE_SLOTS:
                self.add_to_service(room_id, fan_speed)
            else:
                self.add_to_waiting(room_id, fan_speed)

        # 3. Rebalance
        self.rebalance()

    def rebalance(self):
        """Core scheduling logic"""
        # 1. Fill empty slots
        while len(self.service_queue) < Config.MAX_SERVICE_SLOTS and self.waiting_queue:
            best_waiter = self._get_highest_priority_waiter()
            if best_waiter:
                self.waiting_queue.remove(best_waiter)
                self.add_to_service(best_waiter['room_id'], best_waiter['fan_speed'])

        # 2. Preempt if full
        while len(self.service_queue) >= Config.MAX_SERVICE_SLOTS and self.waiting_queue:
            min_service_item = self._get_lowest_priority_service()
            max_wait_item = self._get_highest_priority_waiter()
            
            min_service_val = self.get_speed_val(min_service_item['fan_speed'])
            max_wait_val = self.get_speed_val(max_wait_item['fan_speed'])
            
            if max_wait_val > min_service_val:
                # Preempt
                self.waiting_queue.remove(max_wait_item)
                self.preempt_service(min_service_item, max_wait_item['room_id'], max_wait_item['fan_speed'])
            else:
                break

    def _get_highest_priority_waiter(self):
        if not self.waiting_queue:
            return None
        # Priority: High > Mid > Low, then FIFO
        # Since list is FIFO, we just need to find max priority
        best = None
        max_prio = -1
        for w in self.waiting_queue:
            p = self.get_speed_val(w['fan_speed'])
            if p > max_prio:
                max_prio = p
                best = w
        return best

    def _get_lowest_priority_service(self):
        if not self.service_queue:
            return None
        # Priority: Lowest speed, then Longest service time (smallest start_time)
        min_val = 100
        candidates = []
        for item in self.service_queue:
            val = self.get_speed_val(item['fan_speed'])
            if val < min_val:
                min_val = val
                candidates = [item]
            elif val == min_val:
                candidates.append(item)
        
        # Return the one with smallest start_time (longest duration)
        return min(candidates, key=lambda x: x['start_time'])

    def release_service(self, room_id):
        self.service_queue = [i for i in self.service_queue if i['room_id'] != room_id]
        self.waiting_queue = [i for i in self.waiting_queue if i['room_id'] != room_id]
        self.rebalance()

    def check_time_slices(self):
        for item in self.waiting_queue:
            item['wait_duration'] -= 1
        
        expired_items = [i for i in self.waiting_queue if i['wait_duration'] <= 0]
        
        for waiter in expired_items:
            if self.service_queue:
                victim = min(self.service_queue, key=lambda x: x['start_time'])
                
                if self.get_speed_val(victim['fan_speed']) <= self.get_speed_val(waiter['fan_speed']):
                    self.waiting_queue.remove(waiter)
                    self.preempt_service(victim, waiter['room_id'], waiter['fan_speed'])
                else:
                    waiter['wait_duration'] = Config.WAIT_DURATION_ALLOC

    def add_to_service(self, room_id, fan_speed):
        self.service_queue.append({
            'room_id': room_id,
            'fan_speed': fan_speed,
            'start_time': time.time()
        })
        if room_id in rooms:
            rooms[room_id].is_active = True
        print(f"[Scheduler] Room {room_id} START service.")

    def add_to_waiting(self, room_id, fan_speed):
        for item in self.waiting_queue:
            if item['room_id'] == room_id:
                return
        self.waiting_queue.append({
            'room_id': room_id,
            'fan_speed': fan_speed,
            'wait_duration': Config.WAIT_DURATION_ALLOC
        })
        if room_id in rooms:
            rooms[room_id].is_active = False
            rooms[room_id].dispatch_count += 1
        print(f"[Scheduler] Room {room_id} ENTER waiting queue.")

    def preempt_service(self, victim, new_room_id, new_fan_speed):
        print(f"[Scheduler] Preempting Room {victim['room_id']} for Room {new_room_id}")
        self.service_queue.remove(victim)
        self.add_to_waiting(victim['room_id'], victim['fan_speed'])
        self.add_to_service(new_room_id, new_fan_speed)

# --- Initialization ---
rooms = {}
# Load active check-ins from DB
active_check_ins = database.get_active_check_ins()
# Load room states from DB
saved_room_states = database.get_all_room_states()

for floor in range(1, 5):
    for r in range(1, 11):
        room_id = f"{floor}{r:02d}"
        rooms[room_id] = Room(room_id, floor)
        
        # Restore state from DB if exists
        if room_id in active_check_ins:
            info = active_check_ins[room_id]
            rooms[room_id].is_free = False
            rooms[room_id].tenant_id = info['tenant_id']
            rooms[room_id].tenant_name = info['tenant_name']
            rooms[room_id].tenant_phone = info['tenant_phone']
            rooms[room_id].stay_days = info['stay_days']
        else:
            rooms[room_id].is_free = True

# Test Cases
def set_test_case(room_id, temp, price=None):
    if room_id in rooms:
        rooms[room_id].initial_temp = temp
        # Only set current_temp if not restored from DB (we'll handle this by re-applying DB state after)
        rooms[room_id].current_temp = temp
        rooms[room_id].room_price = price

# Cooling cases
set_test_case("101", 32.0, 100.0)
set_test_case("102", 28.0, 125.0)
set_test_case("103", 30.0, 150.0)
set_test_case("104", 29.0, 200.0)
set_test_case("105", 35.0, 100.0)
# Heating cases
set_test_case("106", 10.0, 100.0)
set_test_case("107", 15.0, 125.0)
set_test_case("108", 18.0, 150.0)
set_test_case("109", 12.0, 200.0)
set_test_case("110", 14.0, 100.0)

# Apply saved room states (Overwriting test cases if data exists)
for room_id, state in saved_room_states.items():
    if room_id in rooms:
        rooms[room_id].power_on = state['power_on']
        rooms[room_id].fan_speed = state['fan_speed']
        rooms[room_id].target_temp = state['target_temp']
        rooms[room_id].current_temp = state['current_temp']
        rooms[room_id].total_fee = state['total_fee']
        rooms[room_id].duration = state['duration']
        
        # If power was on, we might need to request service
        if rooms[room_id].power_on:
             # We don't auto-request here to avoid storming, 
             # but the background task auto-reactivate logic might pick it up 
             # if we set is_active to False initially.
             pass

scheduler = Scheduler()
is_simulation_mode = False

def run_simulation_step():
    """Run one second of simulation"""
    scheduler.check_time_slices()
    
    for room_id, room in rooms.items():
        # Auto-reactivate logic for Idle rooms
        if room.power_on and not room.is_active:
            in_waiting = any(i['room_id'] == room_id for i in scheduler.waiting_queue)
            if not in_waiting:
                diff = room.current_temp - room.target_temp
                if abs(diff) > 1.0:
                    # print(f"[Auto Reactivate] Room {room_id} temp diff > 1.0. Requesting service.")
                    scheduler.request_service(room_id, room.fan_speed)
        
        # Check if target reached
        if room.is_active:
            diff = room.current_temp - room.target_temp
            if abs(diff) < 0.01:
                # print(f"[Reached Target] Room {room_id} reached target temp. Releasing service.")
                scheduler.release_service(room_id)
                room.is_active = False
        
        # Update state
        room.update_temp_and_fee()
        
        # Ensure consistency if room is off
        if not room.power_on:
            if room.is_active or any(i['room_id'] == room_id for i in scheduler.waiting_queue):
                scheduler.release_service(room_id)
                room.is_active = False

# --- Background Task ---
def background_task():
    tick = 0
    while True:
        if not is_simulation_mode:
            tick += 1
            run_simulation_step()
            
            # Save to DB every 5 seconds
            if tick % 5 == 0:
                for room_id, room in rooms.items():
                    if room.power_on or room.total_fee > 0:
                        database.update_room_state(
                            room.room_id, room.power_on, room.fan_speed, 
                            room.target_temp, room.current_temp, 
                            room.total_fee, room.duration
                        )
        time.sleep(1)

thread = Thread(target=background_task)
thread.daemon = True
thread.start()

# --- Routes ---
@app.route('/api/test/start', methods=['POST'])
def start_simulation_mode():
    global is_simulation_mode
    is_simulation_mode = True
    return jsonify({"status": "Simulation mode started"})

@app.route('/api/test/stop', methods=['POST'])
def stop_simulation_mode():
    global is_simulation_mode
    is_simulation_mode = False
    return jsonify({"status": "Simulation mode stopped"})

@app.route('/api/test/tick', methods=['POST'])
def tick_simulation():
    if not is_simulation_mode:
        return jsonify({"error": "Not in simulation mode"}), 400
    
    seconds = request.json.get('seconds', 60)
    for _ in range(seconds):
        run_simulation_step()
        
    return jsonify({"status": f"Advanced {seconds} seconds"})

@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    floors_data = []
    for i in range(1, 5):
        floor_rooms = []
        for j in range(1, 11):
            room_id = f"{i}{j:02d}"
            if room_id in rooms:
                r = rooms[room_id]
                floor_rooms.append({
                    "id": int(r.room_id), 
                    "type": r.room_type,
                    "price": r.room_price,
                    "deposit": r.deposit,
                    "isFree": r.is_free
                })
        floors_data.append({"level": i, "rooms": floor_rooms})
    return jsonify(floors_data)

@app.route('/api/room/<room_id>/status', methods=['GET'])
def get_room_status(room_id):
    if room_id in rooms:
        state = rooms[room_id].to_dict()
        state['is_waiting'] = any(i['room_id'] == room_id for i in scheduler.waiting_queue)
        return jsonify(state)
    else:
        return jsonify({"error": "Room not found"}), 404

@app.route('/api/room/<room_id>/bill', methods=['GET'])
def get_room_bill(room_id):
    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404
    
    room = rooms[room_id]
    if room.is_free:
        return jsonify({"error": "Room is not occupied"}), 400
        
    # Get check-in info from DB
    check_in_info = database.get_room_check_in_info(room_id)
    check_in_date = check_in_info['check_in_time'] if check_in_info else "Unknown"
    
    # Calculate fees
    stay_fee = room.room_price * room.stay_days
    extra_fee = room.total_fee
    
    # Construct bill data
    bill_data = {
        "roomType": room.room_type,
        "checkInDate": check_in_date,
        "days": room.stay_days,
        "stayFee": stay_fee,
        "extraFee": extra_fee,
        "records": [
            {
                "name": "空调费",
                "detail": "累计使用",
                "qty": f"{int(room.duration/60)}min",
                "fee": round(room.total_fee, 2)
            }
        ]
    }
    return jsonify(bill_data)

@app.route('/api/room/<room_id>/export/ac_bill', methods=['GET'])
def export_ac_bill(room_id):
    if room_id not in rooms:
        return "Room not found", 404
    
    room = rooms[room_id]
    check_in_info = database.get_room_check_in_info(room_id)
    check_in_date = check_in_info['check_in_time'] if check_in_info else "Unknown"
    check_out_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    sessions = database.get_ac_sessions(room_id)
    
    # Header
    content = f"=== 空调费用详单 ===\n"
    content += f"房间号: {room_id}\n"
    content += f"入住时间: {check_in_date}\n"
    content += f"离开时间: {check_out_date}\n"
    content += f"空调总费用: {room.total_fee:.2f}元\n"
    content += f"空调调度次数: {room.dispatch_count}次\n"
    content += f"--------------------------------------------------\n"
    content += f"风速统计:\n"
    for speed in ["High", "Mid", "Low"]:
        s = room.speed_stats.get(speed, {"duration": 0, "fee": 0})
        content += f"  {speed}: 时长 {s['duration']:.2f}秒, 费用 {s['fee']:.2f}元\n"
    content += f"--------------------------------------------------\n"
    content += f"{'开始时间':<20} | {'结束时间':<20} | {'时长(秒)':<8} | {'风速':<5} | {'费用':<8} | {'累积费用':<8}\n"
    content += f"--------------------------------------------------\n"
    
    for s in sessions:
        # s: request_time, start_time, end_time, duration, fan_speed, fee, total_fee_snapshot
        start = s[1]
        end = s[2]
        dur = s[3]
        speed = s[4]
        fee = s[5]
        total = s[6]
        content += f"{start:<20} | {end:<20} | {dur:<8} | {speed:<5} | {fee:<8.4f} | {total:<8.4f}\n"
        
    return Response(content, mimetype='text/plain', headers={"Content-Disposition": f"attachment;filename=ac_bill_{room_id}.txt"})

@app.route('/api/room/<room_id>/export/stay_bill', methods=['GET'])
def export_stay_bill(room_id):
    if room_id not in rooms:
        return "Room not found", 404
    
    room = rooms[room_id]
    check_in_info = database.get_room_check_in_info(room_id)
    check_in_date = check_in_info['check_in_time'] if check_in_info else "Unknown"
    check_out_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    stay_fee = room.room_price * room.stay_days
    total_fee = stay_fee + room.total_fee
    
    content = f"=== 住宿费用账单 ===\n"
    content += f"房间号: {room_id}\n"
    content += f"入住时间: {check_in_date}\n"
    content += f"离开时间: {check_out_date}\n"
    content += f"入住天数: {room.stay_days}\n"
    content += f"--------------------------------------------------\n"
    content += f"房费单价: {room.room_price}元/晚\n"
    content += f"住宿费小计: {stay_fee:.2f}元\n"
    content += f"空调费小计: {room.total_fee:.2f}元\n"
    content += f"--------------------------------------------------\n"
    content += f"总应付金额: {total_fee:.2f}元\n"
    
    return Response(content, mimetype='text/plain', headers={"Content-Disposition": f"attachment;filename=stay_bill_{room_id}.txt"})

@app.route('/api/room/<room_id>/control', methods=['POST'])
def control_room(room_id):
    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404
    
    room = rooms[room_id]

    # Check if room is occupied
    if room.is_free:
        return jsonify({"error": "Room is not checked in. AC control disabled."}), 403
    
    data = request.json
    
    if 'power_on' in data:
        new_power_state = data['power_on']
        
        # Logic: Manual ON -> OFF cycle counts as 1 day stay
        if room.power_on and not new_power_state:
            room.stay_days += 1
            print(f"[Billing] Room {room_id} stay_days increased to {room.stay_days}")
            database.update_stay_days(room_id, room.stay_days)
            
            # Log AC Session
            if room.current_session_start_time:
                end_time = datetime.datetime.now()
                duration = int((end_time - room.current_session_start_time).total_seconds())
                session_fee = room.total_fee - room.current_session_fee_start
                
                database.log_ac_session(
                    room_id,
                    room.current_session_start_time, # Request time (approx)
                    room.current_session_start_time, # Start time
                    end_time,
                    duration,
                    room.fan_speed,
                    session_fee,
                    room.total_fee
                )
                room.current_session_start_time = None
            
        room.power_on = new_power_state
        print(f"[Control] Room {room_id} Power -> {room.power_on}")
        if room.power_on:
            scheduler.request_service(room_id, room.fan_speed)
            # Start Session Logging
            room.current_session_start_time = datetime.datetime.now()
            room.current_session_fee_start = room.total_fee
        else:
            scheduler.release_service(room_id)
            room.is_active = False

    if 'target_temp' in data:
        room.target_temp = data['target_temp']
        print(f"[Control] Room {room_id} Target Temp -> {room.target_temp}")
        if room.power_on and not room.is_active:
             diff = room.current_temp - room.target_temp
             if abs(diff) > 1.0:
                 scheduler.request_service(room_id, room.fan_speed)

    if 'fan_speed' in data:
        new_speed = data['fan_speed']
        
        # If speed changes while ON, log the previous session segment
        if room.power_on and room.fan_speed != new_speed:
             if room.current_session_start_time:
                end_time = datetime.datetime.now()
                duration = int((end_time - room.current_session_start_time).total_seconds())
                session_fee = room.total_fee - room.current_session_fee_start
                
                database.log_ac_session(
                    room_id,
                    room.current_session_start_time,
                    room.current_session_start_time,
                    end_time,
                    duration,
                    room.fan_speed, # Log with OLD speed
                    session_fee,
                    room.total_fee
                )
                # Start new session segment
                room.current_session_start_time = end_time
                room.current_session_fee_start = room.total_fee

        room.fan_speed = new_speed
        print(f"[Control] Room {room_id} Fan Speed -> {room.fan_speed}")
        if room.power_on:
            scheduler.request_service(room_id, room.fan_speed)
            
    # Save state to DB immediately on control action
    database.update_room_state(
        room.room_id, room.power_on, room.fan_speed, 
        room.target_temp, room.current_temp, 
        room.total_fee, room.duration
    )
        
    return jsonify({"status": "success", "current_state": room.to_dict()})

@app.route('/api/check_in', methods=['POST'])
def check_in():
    data = request.json
    room_id = data.get('room_id')
    id_card = data.get('id_card')
    name = data.get('name')
    phone = data.get('phone')
    # days is no longer required from frontend, default to 0
    days = 0

    if not all([room_id, id_card, name]):
        return jsonify({"error": "Missing required fields"}), 400

    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404

    room = rooms[room_id]
    # Check if room is already occupied (optional, but good practice)
    # For now, we assume we can overwrite or check-in
    
    room.tenant_id = id_card
    room.tenant_name = name
    room.tenant_phone = phone
    room.stay_days = days
    room.is_free = False # Mark as occupied
    
    # Save to DB
    database.add_check_in(room_id, id_card, name, phone, days)
    
    print(f"[CheckIn] Room {room_id} checked in by {name} for {days} days.")
    
    return jsonify({"status": "success", "message": "Check-in successful"})

@app.route('/api/check_out', methods=['POST'])
def check_out():
    data = request.json
    room_id = data.get('room_id')
    
    if not room_id or room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404
        
    room = rooms[room_id]
    
    # Clear memory state
    room.is_free = True
    room.tenant_id = None
    room.tenant_name = None
    room.tenant_phone = None
    room.stay_days = 0
    room.power_on = False # Turn off AC
    room.is_active = False
    scheduler.release_service(room_id) # Stop service
    
    # Update DB
    database.check_out_db(room_id)
    
    print(f"[CheckOut] Room {room_id} checked out.")
    return jsonify({"status": "success", "message": "Check-out successful"})

if __name__ == '__main__':
    print("启动 Python 后端计费服务...")
    app.run(port=5000)
