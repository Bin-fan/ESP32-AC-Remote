# ESP32 格力空调红外遥控器

ESP32 配合 MicroPython 和 HS-S29P 红外发射模块，实现对格力空调的开关机控制。

### 主要功能

- 格力空调电源开关控制
- 温度设置 (16-30°C)
- 模式切换 (自动/制冷/除湿/送风/制热)
- 风速调节 (自动/低/中/高)

### 依赖库说明

本脚本仅使用 MicroPython **标准核心库**，无需额外安装任何第三方库：

| 库名 | 说明 | 来源 |
|------|------|------|
| `machine` | 硬件抽象层 (Pin, PWM) | ESP32 MicroPython 固件内置 |
| `time` | 时间延迟函数 | ESP32 MicroPython 固件内置 |
| `micropython` | MicroPython 运行时功能 | ESP32 MicroPython 固件内置 |

所有依赖库都是 MicroPython 核心库的一部分，已包含在 ESP32 固件中。  
参考文档：[MicroPython 库文档](http://www.micropython.com.cn/en/latest/library/index.html)

### 文件说明

- `gree_ac_control.py` - 主控制脚本，包含 GreeAC 类和使用示例
- `main.py` - 自动定时控制器主程序
- `boot.py` - ESP32 启动脚本，负责 WiFi 连接和时间同步
- `config.py` - **敏感配置文件**（WiFi 密码等，请勿提交到版本控制系统）
- `README.md` - 项目文档

### ⚠️ 安全配置说明

本项目已将敏感信息（如 WiFi 名称、密码等）提取到独立的 `config.py` 文件中。

**重要安全提示：**
1. `config.py` 文件包含您的 WiFi 凭据等敏感信息
2. **请勿将 `config.py` 提交到 Git 或其他版本控制系统**
3. 建议在 `.gitignore` 中添加 `config.py`
4. 首次使用时，请根据您的实际情况修改 `config.py` 中的配置

#### config.py 配置项说明

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| `WIFI_SSID` | WiFi 网络名称 | `"maria"` |
| `WIFI_PASSWORD` | WiFi 密码 | `"your_password"` |
| `WIFI_CONNECT_TIMEOUT` | WiFi 连接超时时间（秒） | `15` |
| `NTP_SERVER` | NTP 时间服务器 | `"ntp1.aliyun.com"` |
| `TIMEZONE_OFFSET` | 时区偏移（小时） | `8` (中国 UTC+8) |
| `LED_PIN` | LED 指示灯 GPIO 引脚 | `2` |
| `TARGET_HOUR` | 空调定时开启时间（小时，24 小时制） | `7` |
| `TARGET_MINUTE` | 空调定时开启时间（分钟） | `20` |
| `IR_PIN` | 红外发射模块 GPIO 引脚 | `4` |
| `AC_MODE` | 空调模式：0=自动，1=制冷，2=除湿，3=送风，4=制热 | `1` |
| `AC_TEMP` | 目标温度（16-30°C） | `26` |
| `AC_FAN` | 风速：0=自动，1=低，2=中，3=高 | `0` |
| `AC_RUN_DURATION` | 空调运行时长（秒） | `300` |

### 使用步骤

1. **配置所有参数**
   - 编辑 `config.py` 文件
   - 填入您的 WiFi 名称和密码
   - 根据需要修改 NTP 服务器和时区设置
   - 调整空调控制参数：定时时间、运行模式、温度、风速、运行时长等

2. **上传文件到 ESP32**
   - 使用 Thonny、ampy 或其他 MicroPython IDE
   - 上传所有 `.py` 文件到 ESP32
   - 确保 `config.py` 和 `boot.py` 在根目录

3. **重启 ESP32**
   - 设备上电后会自动执行 `boot.py`
   - 连接 WiFi 并同步时间
   - LED 常亮表示成功，闪烁表示失败

4. **运行空调控制**
   - `main.py` 会自动运行定时任务
   - 如需修改定时参数，编辑 `config.py` 后重启设备

### 硬件连接

```
ESP32          HS-S29P 红外模块
-----          ------------------
GPIO4   -----> 信号输入端 (SIG)
5V/3.3V -----> VCC
GND     -----> GND
```
