"""
ESP32 MicroPython 脚本 - 控制格力空调开关机
使用 HS-S29P 红外发射模块

硬件连接:
- ESP32 GPIO4 -> HS-S29P 信号输入端 (可根据实际情况修改)
- HS-S29P VCC -> ESP32 5V 或 3.3V
- HS-S29P GND -> ESP32 GND

注意：格力空调的红外协议需要特定的编码格式
本脚本实现了格力空调的基本开关功能

依赖库说明:
- machine: MicroPython 标准库 (ESP32 固件内置)
- time: MicroPython 标准库 (ESP32 固件内置)
- micropython: MicroPython 标准库 (ESP32 固件内置)

所有依赖都是 MicroPython 核心库，无需额外安装。
参考文档：http://www.micropython.com.cn/en/latest/library/index.html
"""

from machine import Pin, PWM
import time
import micropython

# 确保启用异常检测 (可选，用于调试)
try:
    micropython.alloc_emergency_exception_buf(100)
except:
    pass

# 配置红外发射引脚 (根据实际接线修改)
IR_PIN = 4

# 格力空调红外协议参数
# 格力使用 38kHz 载波频率
CARRIER_FREQ = 38000

# 时间基准单位 (微秒)
UNIT_US = 560

# 格力协议时序 (单位：微秒)
# 引导码
LEADER_MARK = 9000
LEADER_SPACE = 4500

# 逻辑 "1"
BIT_1_MARK = 560
BIT_1_SPACE = 1640

# 逻辑 "0"
BIT_0_MARK = 560
BIT_0_SPACE = 560

# 重复码
REPEAT_MARK = 560
REPEAT_SPACE = 9540

# 帧间隔
FRAME_INTERVAL = 0.05  # 50ms


class GreeAC:
    """格力空调红外控制器"""
    
    def __init__(self, pin=IR_PIN):
        """初始化红外发射器"""
        self.ir_pin = Pin(pin, Pin.OUT)
        self.pwm = PWM(self.ir_pin, freq=CARRIER_FREQ, duty=512)
        self.pwm.duty(0)  # 初始关闭
        
    def _send_pulse(self, duration_us):
        """发送指定时长的脉冲"""
        # 计算需要保持高电平的时间 (单位：微秒)
        self.pwm.duty(512)  # 50% 占空比，开启载波
        time.sleep_us(duration_us)
        self.pwm.duty(0)    # 关闭载波
        
    def _send_space(self, duration_us):
        """发送指定时长的间隔 (无载波)"""
        time.sleep_us(duration_us)
        
    def _send_bit(self, bit):
        """发送一个比特位"""
        if bit == 1:
            self._send_pulse(BIT_1_MARK)
            self._send_space(BIT_1_SPACE)
        else:
            self._send_pulse(BIT_0_MARK)
            self._send_space(BIT_0_SPACE)
            
    def _send_byte(self, byte_val):
        """发送一个字节 (低位在前)"""
        for i in range(8):
            self._send_bit((byte_val >> i) & 1)
            
    def _calculate_checksum(self, data):
        """计算校验和 (格力协议：前 8 字节的和的低 8 位)"""
        return sum(data[:8]) & 0xFF
        
    def _send_command(self, command_bytes):
        """发送完整的红外命令"""
        # 发送引导码
        self._send_pulse(LEADER_MARK)
        self._send_space(LEADER_SPACE)
        
        # 发送数据 (9 字节)
        for byte_val in command_bytes:
            self._send_byte(byte_val)
            
        # 发送停止位 (低电平)
        self._send_pulse(BIT_0_MARK)
        
        # 帧间隔
        time.sleep(FRAME_INTERVAL)
        
    def _build_gree_command(self, power_on=True, mode=0, temp=25, fan=0, swing=False):
        """
        构建格力空调红外命令
        
        参数:
        - power_on: True=开机，False=关机
        - mode: 0=自动，1=制冷，2=除湿，3=送风，4=制热
        - temp: 温度 (16-30)
        - fan: 风速 0=自动，1=低，2=中，3=高
        - swing: 扫风 True/False
        
        返回：9 字节的命令数组
        """
        # 格力空调红外协议格式 (9 字节):
        # 字节 0-2: 固定头 [0x02, 0x20, 0x0A]
        # 字节 3: 温度 + 模式 + 风速
        # 字节 4: 功能标志
        # 字节 5: 扩展功能
        # 字节 6: 校验和低 8 位
        # 字节 7-8: 固定 [0x00, 0x00] 或其他
        
        # 构建命令
        cmd = bytearray(9)
        
        # 固定头
        cmd[0] = 0x02
        cmd[1] = 0x20
        cmd[2] = 0x0A
        
        # 字节 3: 温度编码 (16°C = 0x00, 每度 +1) + 模式 + 风速
        temp_code = temp - 16  # 16°C对应 0, 30°C对应 14
        mode_code = mode & 0x07
        fan_code = fan & 0x03
        
        cmd[3] = temp_code | (mode_code << 5)
        cmd[4] = fan_code
        
        # 字节 5: 功能标志
        # bit0: 电源 (1=开，0=关)
        # bit1: 模式切换标志
        # bit2: 风速标志
        # bit3: 扫风
        # bit4: 强力
        # bit5: 静音
        # bit6: 健康
        # bit7: 干燥/辅热
        
        if power_on:
            cmd[5] = 0x08  # 电源开标志
        else:
            cmd[5] = 0x00  # 电源关标志
            
        if swing:
            cmd[5] |= 0x04  # 扫风标志
            
        # 字节 6: 校验和 (前 8 字节的和)
        cmd[6] = self._calculate_checksum(cmd)
        
        # 字节 7-8: 固定
        cmd[7] = 0x00
        cmd[8] = 0x00
        
        return cmd
        
    def toggle_power(self):
        """切换空调电源状态 (发送开关命令)"""
        # 格力空调的开关是通过发送特定的电源切换命令实现的
        # 这里发送一个标准的电源切换命令
        
        # 电源切换命令 (通用格力协议)
        power_cmd = bytearray([
            0x02, 0x20, 0x0A,  # 固定头
            0x00,              # 温度/模式
            0x00,              # 风速
            0x08,              # 电源标志
            0x00,              # 校验和 (会重新计算)
            0x00, 0x00         # 尾部
        ])
        
        # 重新计算校验和
        power_cmd[6] = self._calculate_checksum(power_cmd)
        
        print("发送电源切换命令...")
        self._send_command(power_cmd)
        
    def power_on(self, mode=1, temp=25, fan=0):
        """打开空调"""
        print(f"打开空调 - 模式:{mode}, 温度:{temp}°C, 风速:{fan}")
        cmd = self._build_gree_command(power_on=True, mode=mode, temp=temp, fan=fan)
        self._send_command(cmd)
        
    def power_off(self):
        """关闭空调"""
        print("关闭空调...")
        cmd = self._build_gree_command(power_on=False)
        self._send_command(cmd)
        
    def set_temperature(self, temp):
        """设置温度 (16-30°C)"""
        if temp < 16 or temp > 30:
            print("温度必须在 16-30°C 之间")
            return
        print(f"设置温度：{temp}°C")
        cmd = self._build_gree_command(power_on=True, temp=temp)
        self._send_command(cmd)
        
    def set_mode(self, mode):
        """
        设置模式
        0=自动，1=制冷，2=除湿，3=送风，4=制热
        """
        mode_names = ["自动", "制冷", "除湿", "送风", "制热"]
        if mode < 0 or mode > 4:
            print("无效的模式")
            return
        print(f"设置模式：{mode_names[mode]}")
        cmd = self._build_gree_command(power_on=True, mode=mode)
        self._send_command(cmd)
        
    def set_fan(self, fan):
        """
        设置风速
        0=自动，1=低，2=中，3=高
        """
        fan_names = ["自动", "低", "中", "高"]
        if fan < 0 or fan > 3:
            print("无效的风速")
            return
        print(f"设置风速：{fan_names[fan]}")
        cmd = self._build_gree_command(power_on=True, fan=fan)
        self._send_command(cmd)
        
    def send_raw_command(self, command_bytes):
        """发送原始命令字节"""
        if len(command_bytes) != 9:
            print("命令必须是 9 字节")
            return
        print(f"发送原始命令：{[hex(b) for b in command_bytes]}")
        self._send_command(command_bytes)
        
    def deinit(self):
        """释放资源"""
        self.pwm.deinit()


def test_basic():
    """基本测试函数"""
    print("=" * 50)
    print("格力空调红外控制器测试")
    print("=" * 50)
    
    ac = GreeAC(pin=IR_PIN)
    
    try:
        # 等待一下
        time.sleep(1)
        
        # 测试开关机
        print("\n[测试 1] 打开空调 (制冷模式，25°C)")
        ac.power_on(mode=1, temp=25, fan=0)
        time.sleep(2)
        
        print("\n[测试 2] 关闭空调")
        ac.power_off()
        time.sleep(2)
        
        print("\n[测试 3] 再次打开空调 (制热模式，28°C)")
        ac.power_on(mode=4, temp=28, fan=2)
        time.sleep(2)
        
        print("\n[测试 4] 切换电源状态")
        ac.toggle_power()
        time.sleep(2)
        
        print("\n测试完成!")
        
    except Exception as e:
        print(f"发生错误：{e}")
    finally:
        ac.deinit()


def simple_toggle():
    """简单的开关切换函数 (用于快速测试)"""
    ac = GreeAC(pin=IR_PIN)
    try:
        print("发送电源切换命令...")
        ac.toggle_power()
        time.sleep(0.5)
        # 通常红外遥控需要发送两次以确保接收
        ac.toggle_power()
    finally:
        ac.deinit()


if __name__ == "__main__":
    # 运行基本测试
    test_basic()
    
    # 或者只运行简单切换 (取消注释使用)
    # simple_toggle()
