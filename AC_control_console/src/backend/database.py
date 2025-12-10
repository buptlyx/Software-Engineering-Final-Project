import sqlite3
import os

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'hotel.db')

def init_db():
    """初始化数据库表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 创建入住记录表
    # status: 'active' (在住), 'checked_out' (已退房)
    c.execute('''
        CREATE TABLE IF NOT EXISTS check_ins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            tenant_name TEXT NOT NULL,
            tenant_phone TEXT,
            check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            check_out_time TIMESTAMP,
            stay_days INTEGER,
            status TEXT DEFAULT 'active'
        )
    ''')

    # 创建房间状态表 (用于保存空调控制信息)
    c.execute('''
        CREATE TABLE IF NOT EXISTS room_states (
            room_id TEXT PRIMARY KEY,
            power_on INTEGER DEFAULT 0,
            fan_speed TEXT DEFAULT 'Mid',
            target_temp REAL DEFAULT 25.0,
            current_temp REAL DEFAULT 28.0,
            total_fee REAL DEFAULT 0.0,
            duration INTEGER DEFAULT 0
        )
    ''')

    # 创建空调详单表
    c.execute('''
        CREATE TABLE IF NOT EXISTS ac_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL,
            request_time TIMESTAMP,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration INTEGER,
            fan_speed TEXT,
            fee REAL,
            total_fee_snapshot REAL
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

def log_ac_session(room_id, request_time, start_time, end_time, duration, fan_speed, fee, total_fee_snapshot):
    """记录一次空调使用会话"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO ac_sessions (room_id, request_time, start_time, end_time, duration, fan_speed, fee, total_fee_snapshot)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (room_id, request_time, start_time, end_time, duration, fan_speed, fee, total_fee_snapshot))
    conn.commit()
    conn.close()

def get_ac_sessions(room_id):
    """获取房间的所有空调详单"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT request_time, start_time, end_time, duration, fan_speed, fee, total_fee_snapshot
        FROM ac_sessions
        WHERE room_id = ?
        ORDER BY start_time ASC
    ''', (room_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def add_check_in(room_id, tenant_id, name, phone, days):
    """添加入住记录"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 先把该房间之前的 active 记录标记为 checked_out (防止异常状态)
    c.execute('''
        UPDATE check_ins 
        SET status = 'checked_out', check_out_time = CURRENT_TIMESTAMP
        WHERE room_id = ? AND status = 'active'
    ''', (room_id,))
    
    # 插入新记录
    c.execute('''
        INSERT INTO check_ins (room_id, tenant_id, tenant_name, tenant_phone, stay_days, status)
        VALUES (?, ?, ?, ?, ?, 'active')
    ''', (room_id, tenant_id, name, phone, days))
    
    conn.commit()
    conn.close()

def check_out_db(room_id):
    """办理退房"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        UPDATE check_ins 
        SET status = 'checked_out', check_out_time = CURRENT_TIMESTAMP
        WHERE room_id = ? AND status = 'active'
    ''', (room_id,))
    conn.commit()
    conn.close()

def get_active_check_ins():
    """获取所有当前在住的记录，用于系统启动时恢复状态"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT room_id, tenant_id, tenant_name, tenant_phone, stay_days 
        FROM check_ins 
        WHERE status = 'active'
    ''')
    rows = c.fetchall()
    conn.close()
    
    # 转换为字典格式: {room_id: {data...}}
    result = {}
    for row in rows:
        result[row[0]] = {
            'tenant_id': row[1],
            'tenant_name': row[2],
            'tenant_phone': row[3],
            'stay_days': row[4]
        }
    return result

def get_room_check_in_info(room_id):
    """获取指定房间的当前入住信息"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT check_in_time, stay_days 
        FROM check_ins 
        WHERE room_id = ? AND status = 'active'
    ''', (room_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            'check_in_time': row[0],
            'stay_days': row[1]
        }
    return None

def update_stay_days(room_id, days):
    """更新入住天数"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        UPDATE check_ins 
        SET stay_days = ?
        WHERE room_id = ? AND status = 'active'
    ''', (days, room_id))
    conn.commit()
    conn.close()

def update_room_state(room_id, power_on, fan_speed, target_temp, current_temp, total_fee, duration):
    """更新房间空调状态"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO room_states (room_id, power_on, fan_speed, target_temp, current_temp, total_fee, duration)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(room_id) DO UPDATE SET
            power_on=excluded.power_on,
            fan_speed=excluded.fan_speed,
            target_temp=excluded.target_temp,
            current_temp=excluded.current_temp,
            total_fee=excluded.total_fee,
            duration=excluded.duration
    ''', (room_id, int(power_on), fan_speed, target_temp, current_temp, total_fee, duration))
    conn.commit()
    conn.close()

def get_all_room_states():
    """获取所有房间的空调状态"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM room_states')
    rows = c.fetchall()
    conn.close()
    
    result = {}
    for row in rows:
        # row: room_id, power_on, fan_speed, target_temp, current_temp, total_fee, duration
        result[row[0]] = {
            'power_on': bool(row[1]),
            'fan_speed': row[2],
            'target_temp': row[3],
            'current_temp': row[4],
            'total_fee': row[5],
            'duration': row[6]
        }
    return result
