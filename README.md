# ESP32 格力空调智能定时控制器

基于 ESP32 和 MicroPython 的智能家居项目，通过红外遥控实现格力空调的自动化定时控制，支持 WiFi 时间同步、节假日识别和调休日管理。

## 项目说明

本项目使用 ESP32 配合 MicroPython、HS-S29P 红外发射模块和 HS-S23P 红外接收模块，实现对格力空调的智能定时控制。系统可每天在指定时间自动开启空调，运行指定时长后自动关闭，并智能识别节假日和调休日。

### 主要功能

#### 空调控制功能
- ✅ 格力空调电源开关控制
- ✅ 温度设置 (16-30°C)
- ✅ 模式切换 (自动/制冷/除湿/送风/制热)
- ✅ 风速调节 (自动/低/中/高)

#### 智能定时功能
- ✅ 每日定时启动（可配置小时和分钟）
- ✅ 运行时长控制（可配置运行秒数）
- ✅ 防止重复触发机制
- ✅ 2026 年中国节假日自动识别
- ✅ 调休工作日自动识别

#### 网络与时间功能
- ✅ WiFi 自动连接（带超时保护）
- ✅ NTP 时间同步（阿里云 NTP 服务器）
- ✅ 中国标准时间 (UTC+8) 自动转换
- ✅ RTC 实时时钟维护

### 依赖库说明

本脚本仅使用 MicroPython **标准核心库**，无需额外安装任何第三方库：

| 库名 | 说明 | 来源 |
|------|------|------|
| `machine` | 硬件抽象层 (Pin, Timer, RTC) | ESP32 MicroPython 固件内置 |
| `time` | 时间处理函数 | ESP32 MicroPython 固件内置 |
| `network` | WiFi 网络管理 | ESP32 MicroPython 固件内置 |
| `ntptime` | NTP 时间同步 | ESP32 MicroPython 固件内置 |
| `micropython` | MicroPython 运行时功能 | ESP32 MicroPython 固件内置 |

所有依赖库都是 MicroPython 核心库的一部分，已包含在 ESP32 固件中。  
参考文档：[MicroPython 库文档](http://www.micropython.com.cn/en/latest/library/index.html)

### 文件说明

| 文件名 | 说明 |
|--------|------|
| `boot.py` | 启动脚本，负责 WiFi 连接和中国时间同步 |
| `main.py` | 主程序，实现定时任务逻辑和节假日判断 |
| `gree_ac_control.py` | 空调控制核心库，包含 GreeAC 类及红外协议实现 |
| `ir_receiver_test.py` | 红外接收测试工具，用于学习其他红外遥控码 |
| `README.md` | 项目文档 |

### 硬件连接

#### 红外发射模块 (HS-S29P)
```
ESP32          HS-S29P 红外发射模块
-----          --------------------
GPIO4   -----> 信号输入端 (SIG)
3.3V    -----> VCC
GND     -----> GND
```

#### 红外接收模块 (HS-S23P，可选，用于学习遥控码)
```
ESP32          HS-S23P 红外接收模块
-----          --------------------
GPIO4   -----> 信号输出端 (OUT)
3.3V    -----> VCC
GND     -----> GND
```

> ⚠️ **注意**: 发射和接收模块不要同时连接到同一个 GPIO 引脚。如需使用接收功能学习遥控码，请暂时断开红外发射模块。

## 快速开始

### 1. 硬件准备

- ESP32 开发板 × 1
- HS-S29P 红外发射模块 × 1（用于控制空调）
- HS-S23P 红外接收模块 × 1（可选，用于学习遥控码）
- 杜邦线若干

### 2. 软件环境

- MicroPython 固件（ESP32 版本）
- 推荐使用 Thonny IDE 或 rshell 进行代码上传

### 3. 配置步骤

#### 修改 WiFi 配置 (`boot.py`)
```python
WIFI_SSID = "你的 WiFi 名称"
WIFI_PASSWORD = "你的 WiFi 密码"
WIFI_CONNECT_TIMEOUT = 15  # 连接超时时间（秒）
```

#### 修改定时配置 (`main.py`)
```python
TARGET_HOUR = 7           # 目标触发时间（小时，24 小时制）
TARGET_MINUTE = 20        # 目标触发时间（分钟）
IR_PIN = 4                # 红外发射引脚
AC_MODE = 1               # 0:自动，1:制冷，2:除湿，3:送风，4:制热
AC_TEMP = 26              # 目标温度 (16-30)
AC_FAN = 0                # 0:自动，1:低，2:中，3:高
AC_RUN_DURATION = 300     # 运行时长（秒）
```

#### 配置节假日 (`main.py`)
编辑 `HOLIDAYS` 和 `ADJUSTED_WORKDAYS` 列表以匹配当前年份的放假安排。

### 4. 上传代码

将以下文件上传到 ESP32：
- `boot.py`
- `main.py`
- `gree_ac_control.py`

> `ir_receiver_test.py` 仅在需要学习红外遥控码时上传使用。

### 5. 运行

ESP32 重启后会自动执行 `boot.py` 连接 WiFi 并同步时间，然后运行 `main.py` 开始定时监控。

## 格力红外协议说明

本项目实现的格力空调红外协议特征：

- **载波频率**: 38kHz（由 HS-S29P 模块硬件生成）
- **逻辑 0**: 560μs 低 + 560μs 高
- **逻辑 1**: 560μs 低 + 1680μs 高
- **前导码**: 9ms 低 + 4.5ms 高
- **数据包**: 9 字节（第 7 字节为校验和）

## 使用示例

### 基本控制
```python
from gree_ac_control import GreeAC

# 初始化（GPIO 4）
ac = GreeAC(pin_num=4)

# 开机（制冷模式，26°C，自动风速）
ac.turn_on(mode=1, temp=26, fan=0)

# 关机
ac.turn_off()
```

### 定时任务逻辑
系统每分钟检查一次当前时间，当满足以下条件时触发空调：
1. 当前时间等于设定的目标时间
2. 今天不是节假日
3. 如果是周末，必须是调休工作日
4. 当天尚未触发过

触发后空调将运行设定的时长，然后自动关闭。

## 注意事项

1. **首次使用**: 建议先使用 `ir_receiver_test.py` 测试红外接收，验证空调遥控码格式
2. **WiFi 依赖**: 时间同步需要网络连接，如 WiFi 不可用系统将使用本地 RTC 时间
3. **节假日更新**: 每年需手动更新 `HOLIDAYS` 和 `ADJUSTED_WORKDAYS` 配置
4. **红外角度**: 确保红外发射模块正对空调接收器，距离建议在 5 米以内
5. **电源稳定**: 建议使用稳定的 3.3V 电源供电，避免电压波动导致复位

## 故障排除

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| WiFi 连接失败 | 密码错误或信号弱 | 检查配置，靠近路由器 |
| 时间同步失败 | NTP 服务器不可达 | 检查网络连接，更换 NTP 服务器 |
| 空调无响应 | 红外模块接线错误 | 检查 GPIO 引脚和电源连接 |
| 定时不触发 | 时间未同步 | 检查 RTC 时间是否准确 |
| 节假日判断错误 | 配置未更新 | 更新当年的节假日配置 |

## License

MIT License

## 参考资源

- [MicroPython 官方文档](https://docs.micropython.org/)
- [ESP32 技术规格书](https://www.espressif.com/zh-hans/products/socs/esp32)
- [格力空调红外协议分析](https://github.com/ToniA/arduino-heatpumpir)
