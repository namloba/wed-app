import requests
import time
import os

# ==== Base URLs ====
CORE_METADATA_URL = os.getenv('CORE_METADATA_URL', 'http://192.168.164.218:59881')
CORE_COMMAND_URL  = os.getenv('CORE_COMMAND_URL', 'http://192.168.164.218:59882')
CORE_DATA_URL     = os.getenv('CORE_DATA_URL', 'http://192.168.164.218:59880')
RULE_ENGINE_URL   = os.getenv('RULE_ENGINE_URL', 'http://192.168.164.218:59720')


# ==== DEVICE & COMMAND ====

def get_all_devices():
    try:
        url = f"{CORE_METADATA_URL}/api/v3/device/all"
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get("devices", [])
    except Exception as e:
        print("Error fetching devices:", e)
        return []

def get_device_by_name(name):
    try:
        url = f"{CORE_METADATA_URL}/api/v3/device/name/{name}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("Error fetching device:", e)
        return {}

def send_command(device_name, command_name, method="PUT", body=None):
    """
    Gửi lệnh đến thiết bị qua core-command (GET hoặc PUT)
    """
    try:
        url = f"{CORE_COMMAND_URL}/api/v3/device/name/{device_name}/{command_name}"
        if method.upper() == "PUT":
            response = requests.put(url, json=body or {})
        else:
            response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("Error sending command:", e)
        return {}


# ==== CORE-DATA (Reading History) ====

def get_readings(device_name, resource_name, start_ms=None, end_ms=None, limit=100):
    """
    Truy vấn readings theo thiết bị + resource trong khoảng thời gian
    """
    try:
        url = f"{CORE_DATA_URL}/api/v3/reading/device/name/{device_name}/resourceName/{resource_name}"
        params = {"limit": limit}
        if start_ms: params["start"] = start_ms
        if end_ms: params["end"] = end_ms
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("readings", [])
    except Exception as e:
        print("Error fetching readings:", e)
        return []


# ==== RULE ENGINE (KUIPER) ====

def create_stream(stream_name):
    """
    Tạo stream cho rule engine, sử dụng định dạng JSON và nguồn từ edgex
    """
    try:
        url = f"{RULE_ENGINE_URL}/streams"
        sql = f'CREATE STREAM {stream_name} () WITH (FORMAT = "JSON", TYPE = "edgex");'
        payload = {"sql": sql}
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return {"success": True}
    except Exception as e:
        print("Error creating stream:", e)
        return {"success": False, "error": str(e)}

def create_rule(rule_id, sql_query, actions):
    """
    Tạo rule mới (với SQL query và danh sách actions)
    """
    try:
        url = f"{RULE_ENGINE_URL}/rules"
        payload = {
            "id": rule_id,
            "sql": sql_query,
            "actions": actions
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return {"success": True}
    except Exception as e:
        print("Error creating rule:", e)
        return {"success": False, "error": str(e)}

def start_rule(rule_id):
    try:
        url = f"{RULE_ENGINE_URL}/rules/{rule_id}/start"
        response = requests.post(url)
        response.raise_for_status()
        return {"success": True}
    except Exception as e:
        print("Error starting rule:", e)
        return {"success": False, "error": str(e)}

def stop_rule(rule_id):
    try:
        url = f"{RULE_ENGINE_URL}/rules/{rule_id}/stop"
        response = requests.post(url)
        response.raise_for_status()
        return {"success": True}
    except Exception as e:
        print("Error stopping rule:", e)
        return {"success": False, "error": str(e)}

def delete_rule(rule_id: str):
    """
    Xóa rule khỏi Rule Engine (Kuiper) theo ID.
    """
    try:
        url = f"{RULE_ENGINE_URL}/rules/{rule_id}"
        response = requests.delete(url)
        response.raise_for_status()
        return {"success": True}
    except Exception as e:
        print(f"Error deleting rule '{rule_id}':", e)
        return {"success": False, "error": str(e)}

def list_rules():
    try:
        url = f"{RULE_ENGINE_URL}/rules"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("Error listing rules:", e)
        return []


def create_threshold_rule(
    rule_id: str,
    stream_name: str,
    device_name: str,
    resource_name: str,
    lower: float,
    upper: float,
    relay_command: str,
    relay_state: str,
    mqtt_topic: str = "hou/edge-gatewa/noti"
):
    """
    Tạo rule với điều kiện resource nằm trong khoảng [lower, upper],
    kích hoạt relay (PUT) và gửi thông báo MQTT.

    - rule_id: tên rule (id duy nhất)
    - stream_name: tên stream (đã tạo trước đó)
    - device_name: tên thiết bị để gửi command
    - resource_name: tên trường cần giám sát (ví dụ NhietDo)
    - lower, upper: khoảng ngưỡng cho resource
    - relay_command: tên lệnh điều khiển relay (ví dụ Relay1)
    - relay_state: giá trị bật relay (ví dụ "true")
    """

    # Tạo SQL truy vấn
    sql = f"""
        SELECT {resource_name} FROM {stream_name}
        WHERE {resource_name} >= {lower} AND {resource_name} <= {upper}
    """

    # Định nghĩa actions
    actions = [
        {
            "rest": {
                "bodyType": "json",
                "dataTemplate": f'{{"{relay_command}":"{relay_state}"}}',
                "method": "PUT",
                "url": f"http://edgex-core-command:59882/api/v3/device/name/{device_name}/{relay_command}"
            }
        },
        {
            "mqtt": {
                "server": "tcp://broker.emqx.io:1883",
                "topic": mqtt_topic,
                "dataTemplate": f"\"rule:{rule_id} da kich hoat\""
            }
        }
    ]

    # Gọi hàm create_rule sẵn có
    return create_rule(rule_id=rule_id, sql_query=sql.strip(), actions=actions)

def create_out_of_range_rule(
    rule_id: str,
    stream_name: str,
    device_name: str,
    resource_name: str,
    lower: float,
    upper: float,
    relay_command: str,
    relay_state: str,
    mqtt_topic: str = "hou/edge-gatewa/noti"
):
    """
    Tạo rule khi resource nằm ngoài khoảng [lower, upper],
    dùng để cảnh báo hoặc bật relay khi điều kiện bất thường xảy ra.

    - rule_id: tên rule
    - stream_name: tên stream đã tạo
    - device_name: tên thiết bị
    - resource_name: tên cảm biến (VD: NhietDo)
    - lower / upper: ngưỡng cho phép
    - relay_command: tên command điều khiển (VD: Relay1)
    - relay_state: trạng thái cần set (VD: "true")
    - mqtt_topic: topic thông báo (mặc định: hou/edge-gatewa/noti)
    """

    sql = f"""
        SELECT {resource_name} FROM {stream_name}
        WHERE {resource_name} < {lower} OR {resource_name} > {upper}
    """

    actions = [
        {
            "rest": {
                "bodyType": "json",
                "dataTemplate": f'{{"{relay_command}":"{relay_state}"}}',
                "method": "PUT",
                "url": f"http://edgex-core-command:59882/api/v3/device/name/{device_name}/{relay_command}"
            }
        },
        {
            "mqtt": {
                "server": "tcp://broker.emqx.io:1883",
                "topic": mqtt_topic,
                "dataTemplate": f"\"rule:{rule_id} da kich hoat\""
            }
        }
    ]

    return create_rule(rule_id=rule_id, sql_query=sql.strip(), actions=actions)

# ==== (Optional) Epoch helper ====

def now_ms():
    """Trả về thời gian hiện tại dạng epoch milliseconds"""
    return int(time.time() * 1000)
