from flask import Flask, jsonify, request
from flask_cors import CORS
import time
from threading import Thread

app = Flask(__name__)
CORS(app)

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
        self.room_price = self._get_price_by_floor(floor)
        
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

    def _get_price_by_floor(self, floor):
        return {1: 100.0, 2: 150.0, 3: 200.0, 4: 250.0}.get(floor, 100.0)

    def to_dict(self):
        return {
            "room_id": self.room_id,
            "power_on": self.power_on,
            "is_active": self.is_active,
            "fan_speed": self.fan_speed,
            "initial_temp": self.initial_temp,
            "current_temp": self.current_temp,
            "target_temp": self.target_temp,
            "total_fee": self.total_fee,
            "duration": self.duration,
            "room_price": self.room_price,
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

        # 2. Add to waiting queue if new
        if not in_queue:
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
        print(f"[Scheduler] Room {room_id} ENTER waiting queue.")

    def preempt_service(self, victim, new_room_id, new_fan_speed):
        print(f"[Scheduler] Preempting Room {victim['room_id']} for Room {new_room_id}")
        self.service_queue.remove(victim)
        self.add_to_waiting(victim['room_id'], victim['fan_speed'])
        self.add_to_service(new_room_id, new_fan_speed)

# --- Initialization ---
rooms = {}
for floor in range(1, 5):
    for r in range(1, 11):
        room_id = f"{floor}{r:02d}"
        rooms[room_id] = Room(room_id, floor)

# Test Cases
def set_test_case(room_id, temp, price=None):
    if room_id in rooms:
        rooms[room_id].initial_temp = temp
        rooms[room_id].current_temp = temp
        if price:
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

scheduler = Scheduler()

# --- Background Task ---
def background_task():
    while True:
        scheduler.check_time_slices()
        
        for room_id, room in rooms.items():
            # Auto-reactivate logic for Idle rooms
            if room.power_on and not room.is_active:
                in_waiting = any(i['room_id'] == room_id for i in scheduler.waiting_queue)
                if not in_waiting:
                    diff = room.current_temp - room.target_temp
                    if abs(diff) > 1.0:
                        print(f"[Auto Reactivate] Room {room_id} temp diff > 1.0. Requesting service.")
                        scheduler.request_service(room_id, room.fan_speed)
            
            # Check if target reached
            if room.is_active:
                diff = room.current_temp - room.target_temp
                if abs(diff) < 0.01:
                    print(f"[Reached Target] Room {room_id} reached target temp. Releasing service.")
                    scheduler.release_service(room_id)
                    room.is_active = False
            
            # Update state
            room.update_temp_and_fee()
            
            # Ensure consistency if room is off
            if not room.power_on:
                if room.is_active or any(i['room_id'] == room_id for i in scheduler.waiting_queue):
                    scheduler.release_service(room_id)
                    room.is_active = False

        time.sleep(1)

thread = Thread(target=background_task)
thread.daemon = True
thread.start()

# --- Routes ---
@app.route('/api/room/<room_id>/status', methods=['GET'])
def get_room_status(room_id):
    if room_id in rooms:
        state = rooms[room_id].to_dict()
        state['is_waiting'] = any(i['room_id'] == room_id for i in scheduler.waiting_queue)
        return jsonify(state)
    else:
        return jsonify({"error": "Room not found"}), 404

@app.route('/api/room/<room_id>/control', methods=['POST'])
def control_room(room_id):
    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404
    
    data = request.json
    room = rooms[room_id]
    
    if 'power_on' in data:
        room.power_on = data['power_on']
        print(f"[Control] Room {room_id} Power -> {room.power_on}")
        if room.power_on:
            scheduler.request_service(room_id, room.fan_speed)
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
        room.fan_speed = data['fan_speed']
        print(f"[Control] Room {room_id} Fan Speed -> {room.fan_speed}")
        if room.power_on:
            scheduler.request_service(room_id, room.fan_speed)
        
    return jsonify({"status": "success", "current_state": room.to_dict()})

@app.route('/api/check_in', methods=['POST'])
def check_in():
    data = request.json
    room_id = data.get('room_id')
    id_card = data.get('id_card')
    name = data.get('name')
    phone = data.get('phone')
    days = data.get('days')

    if not all([room_id, id_card, name, days]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        days = int(days)
        if days <= 0:
            return jsonify({"error": "Stay days must be greater than 0"}), 400
    except ValueError:
        return jsonify({"error": "Invalid days format"}), 400

    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404

    room = rooms[room_id]
    # Check if room is already occupied (optional, but good practice)
    # For now, we assume we can overwrite or check-in
    
    room.tenant_id = id_card
    room.tenant_name = name
    room.tenant_phone = phone
    room.stay_days = days
    
    print(f"[CheckIn] Room {room_id} checked in by {name} for {days} days.")
    
    return jsonify({"status": "success", "message": "Check-in successful"})

if __name__ == '__main__':
    print("启动 Python 后端计费服务...")
    app.run(port=5000)
