# ESP32 格力空调红外遥控器

ESP32 配合 MicroPython 和 HS-S29P 红外发射模块，实现对格力空调的开关机控制。

## 项目说明

本项目使用 ESP32 配合 MicroPython 和 HS-S29P 红外发射模块，实现对格力空调的开关机控制。

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
- `README.md` - 项目文档

### 硬件连接

```
ESP32          HS-S29P 红外模块
-----          ------------------
GPIO4   -----> 信号输入端 (SIG)
5V/3.3V -----> VCC
GND     -----> GND
```
