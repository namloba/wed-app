# Hướng Dẫn Sử Dụng Hệ Thống IoT EdgeX

## 📋 Tổng Quan Hệ Thống

### Kiến Trúc Hệ Thống

Hệ thống này được xây dựng dựa trên **EdgeX Foundry Framework** kết hợp với **Flask Web Application** để tạo ra một nền tảng IoT hoàn chỉnh.

#### Các Thành Phần Chính:

- **EdgeX Core Services**: Quản lý thiết bị, dữ liệu và lệnh điều khiển
- **Flask Web App**: Giao diện web để giám sát và điều khiển
- **Rule Engine (Kuiper)**: Xử lý logic tự động hóa
- **MQTT Broker**: Giao tiếp và thông báo

### Sơ Đồ Kiến Trúc

```
[Thiết bị IoT] ↔ [EdgeX Core] ↔ [Flask Web App] ↔ [Người dùng]
                      ↓
                [Rule Engine] → [MQTT Notifications]
```

## 🔧 Cấu Hình Hệ Thống

### 1. Biến Môi Trường (.env)

Cấu hình các URL dịch vụ EdgeX trong file `.env`:

```env
# EdgeX Core Services
CORE_METADATA_URL=http://192.168.164.218:59881
CORE_COMMAND_URL=http://192.168.164.218:59882
CORE_DATA_URL=http://192.168.164.218:59880
RULE_ENGINE_URL=http://192.168.164.218:59720
```

### 2. Thiết Bị Được Hỗ Trợ

- **Tên thiết bị chính**: `Tu-1`
- **Các cảm biến**:
  - `NhietDo` (Nhiệt độ) - °C
  - `DoAm` (Độ ẩm) - %
  - `AnhSang` (Ánh sáng) - lux
- **Thiết bị điều khiển**:
  - `Relay1`, `Relay2`, etc. - Bật/tắt thiết bị

## 🌐 API Endpoints

### 1. Đọc Dữ Liệu Cảm Biến

#### Đọc Giá Trị Hiện Tại

```http
GET /api/reading?resource=NhietDo
```

**Response:**

```json
{
  "value": 28.5
}
```

#### Lấy Dữ Liệu Lịch Sử (Thống Kê)

```http
GET /api/statistics/temperature?timeRange=day&date=2025-08-03
```

**Response:**

```json
[
  {"time": "08:00", "value": 26.5},
  {"time": "09:00", "value": 27.2},
  {"time": "10:00", "value": 28.1}
]
```

### 2. Điều Khiển Thiết Bị

#### Bật/Tắt Relay

```http
POST /api/device/Tu-1/control/Relay1
Content-Type: application/json

{
  "state": "true"  // "true" để bật, "false" để tắt
}
```

**Response:**

```json
{
  "success": true,
  "response": {...}
}
```

## 🎮 Cách Điều Khiển Thiết Bị

### 1. Thông Qua Web Interface

#### Truy cập các trang:

- **Dashboard**: `/index` - Giám sát tổng quan
- **Automation**: `/automation` - Thiết lập tự động hóa
- **Statistics**: `/statistics` - Xem thống kê dữ liệu

### 2. Điều Khiển Trực Tiếp qua API

#### Ví dụ bật đèn LED:

```bash
curl -X POST http://localhost:5000/api/device/Tu-1/control/Relay1 \
  -H "Content-Type: application/json" \
  -d '{"state": "true"}'
```

#### Ví dụ tắt quạt:

```bash
curl -X POST http://localhost:5000/api/device/Tu-1/control/Relay2 \
  -H "Content-Type: application/json" \
  -d '{"state": "false"}'
```

### 3. Điều Khiển qua JavaScript (Frontend)

```javascript
// Bật thiết bị
async function turnOnDevice(device, command) {
    const response = await fetch(`/api/device/${device}/control/${command}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            state: 'true'
        })
    });
  
    const result = await response.json();
    if (result.success) {
        console.log('Thiết bị đã được bật!');
    } else {
        console.error('Lỗi:', result.error);
    }
}

// Sử dụng
turnOnDevice('Tu-1', 'Relay1');
```

## 🤖 Tự Động Hóa (Rule Engine)

### 1. Tạo Rule Tự Động

#### Rule Khi Nhiệt Độ Trong Khoảng

```python
import edgex_interface as edgex

# Tạo rule bật quạt khi nhiệt độ 28-35°C
edgex.create_threshold_rule(
    rule_id="auto_fan_on",
    stream_name="sensor_stream",
    device_name="Tu-1",
    resource_name="NhietDo",
    lower=28.0,
    upper=35.0,
    relay_command="Relay2",
    relay_state="true"
)

# Kích hoạt rule
edgex.start_rule("auto_fan_on")
```

#### Rule Cảnh Báo Khi Vượt Ngưỡng

```python
# Cảnh báo khi nhiệt độ < 20°C hoặc > 40°C
edgex.create_out_of_range_rule(
    rule_id="temp_warning",
    stream_name="sensor_stream", 
    device_name="Tu-1",
    resource_name="NhietDo",
    lower=20.0,
    upper=40.0,
    relay_command="Relay3",  # Đèn cảnh báo
    relay_state="true"
)
```

### 2. Quản Lý Rules

```python
# Liệt kê tất cả rules
rules = edgex.list_rules()

# Dừng rule
edgex.stop_rule("auto_fan_on")

# Xóa rule
edgex.delete_rule("temp_warning")
```

## 📊 Giám Sát Dữ Liệu

### 1. Đọc Dữ Liệu Theo Thời Gian

```python
import edgex_interface as edgex
from datetime import datetime, timedelta

# Lấy dữ liệu 24h qua
end_time = int(datetime.now().timestamp() * 1000)
start_time = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)

readings = edgex.get_readings(
    device_name="Tu-1",
    resource_name="NhietDo", 
    start_ms=start_time,
    end_ms=end_time,
    limit=100
)
```

### 2. Mapping Sensors

```python
sensor_map = {
    "humidity": "DoAm",      # Độ ẩm
    "temperature": "NhietDo", # Nhiệt độ  
    "light": "AnhSang"       # Ánh sáng
}
```

## 🔧 Troubleshooting

### Lỗi Thường Gặp:

1. **Kết nối EdgeX thất bại**

   - Kiểm tra URL trong file `.env`
   - Đảm bảo EdgeX services đang chạy
2. **Thiết bị không phản hồi**

   - Kiểm tra tên thiết bị: `Tu-1`
   - Xác nhận command name chính xác
3. **Rule không hoạt động**

   - Kiểm tra stream đã được tạo
   - Xác nhận rule đã được start

### Debug Commands:

```python
# Kiểm tra tất cả thiết bị
devices = edgex.get_all_devices()
print(devices)

# Kiểm tra thiết bị cụ thể
device = edgex.get_device_by_name("Tu-1")
print(device)

# Test gửi lệnh
result = edgex.send_command("Tu-1", "Relay1", "PUT", {"Relay1": "true"})
print(result)
```

## 🚀 Khởi Động Hệ Thống

1. **Khởi động EdgeX services**
2. **Cấu hình file `.env`**
3. **Chạy Flask application**
4. **Truy cập web interface**
5. **Bắt đầu giám sát và điều khiển!**

## 📞 Hỗ Trợ

Nếu gặp vấn đề, hãy kiểm tra:

- Log của EdgeX services
- Console của web browser (F12)
- Network connectivity giữa các services
- Cấu hình thiết bị IoT

---

*Hướng dẫn này được tạo cho hệ thống IoT EdgeX - Flask Integration*
