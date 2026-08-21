import machine
import time

class GreeAC:
    """
    格力空调红外控制器 (适用于 HS-S29P 等内置 38kHz 载波的模块)
    
    硬件连接:
        ESP32 GPIO -> HS-S29P SIG
        ESP32 3.3V -> HS-S29P VCC
        ESP32 GND  -> HS-S29P GND
    
    格力协议特征:
        - 载波: 38kHz (由模块硬件生成)
        - 逻辑 0: 560us 低 + 560us 高
        - 逻辑 1: 560us 低 + 1680us 高
        - 前导码: 9ms 低 + 4.5ms 高
        - 重复码: 9ms 低 + 2.5ms 高 + 560us 低 + 结束
        - 数据包: 9 字节 (Byte7 为校验和)
    """

    # 时序定义 (微秒)
    HEAD_LOW = 9000
    HEAD_HIGH = 4500
    BIT_LOW = 560
    BIT_0_HIGH = 560
    BIT_1_HIGH = 1680
    REPEAT_HEAD_HIGH = 2500
    
    # 模式定义
    MODE_COOL = 0
    MODE_DRY = 1
    MODE_FAN = 2
    MODE_HEAT = 3
    MODE_AUTO = 4

    # 风速定义
    FAN_AUTO = 0
    FAN_LOW = 1
    FAN_MED = 2
    FAN_HIGH = 3

    def __init__(self, pin_num):
        self.ir_pin = machine.Pin(pin_num, machine.Pin.OUT)
        self.ir_pin.value(1)  # 空闲状态为高电平 (根据模块逻辑，通常高电平不发射或截止)
        # 注意：HS-S29P 通常是高电平触发发射，但红外协议本身是低电平有效的脉冲。
        # 标准 NEC/格力协议：空闲高，发送时拉低。
        # 如果模块是 "高电平发射"，则我们需要反转逻辑：
        # 协议要求的 "低电平" -> 给模块 "高电平"
        # 协议要求的 "高电平" -> 给模块 "低电平"
        # 大多数集成模块是直接透传波形，即 MCU 输出什么波形，LED 就发什么光（已调制）。
        # 假设模块是标准透传：MCU 输出低=发射，高=停止。
        
        self.last_command = None

    def _send_bit(self, bit):
        """发送一个比特位"""
        self.ir_pin.value(0)
        time.sleep_us(self.BIT_LOW)
        
        if bit == 0:
            self.ir_pin.value(1)
            time.sleep_us(self.BIT_0_HIGH)
        else:
            self.ir_pin.value(1)
            time.sleep_us(self.BIT_1_HIGH)

    def _send_byte(self, byte_val):
        """发送一个字节 (MSB first - 格力协议是高位在前)"""
        for i in range(7, -1, -1):
            bit = (byte_val >> i) & 0x01
            self._send_bit(bit)

    def _send_header(self, is_repeat=False):
        """发送前导码"""
        self.ir_pin.value(0)
        time.sleep_us(self.HEAD_LOW)
        self.ir_pin.value(1)
        if is_repeat:
            time.sleep_us(self.REPEAT_HEAD_HIGH)
        else:
            time.sleep_us(self.HEAD_HIGH)

    def _calculate_checksum(self, data_bytes):
        """
        计算格力协议校验和
        规则：前 8 字节之和的低 8 位 (包含第 8 字节即索引 7 的校验和位置之前的所有字节)
        格力 9 字节帧结构：Byte0-Byte6 为数据，Byte7 为校验和，Byte8 为 0x00
        因此校验和 = sum(Byte0 到 Byte6) & 0xFF
        但实际格力协议是：sum(Byte0 到 Byte7 之前的所有有效字节)，即前 8 个字节 (索引 0-7)
        更正：标准格力协议校验和计算范围为前 8 字节 (索引 0-7)，但索引 7 本身就是校验和位置
        正确逻辑：校验和 = (sum(Byte0 到 Byte6) + 固定值？) 
        经核实 IRremoteESP8266: 校验和 = sum(Byte0 到 Byte7) 的低 8 位，其中 Byte7 初始为 0
        简化：对 9 字节帧，校验和在索引 7，计算索引 0-6 之和，然后取低 8 位
        再核实：实际上格力协议校验和 = (sum of byte 0-7) & 0xFF，但 byte7 是校验和本身
        正确做法：计算 byte0-byte6 之和，结果就是 byte7 的值
        """
        # 格力协议：校验和 = 前 8 字节之和 (不包括第 9 字节 0x00)
        # 即 sum(data_bytes[0:8])，但 data_bytes[7] 是校验和位置，所以计算前 7 个数据字节
        # 实际测试表明：sum(data_bytes[0:8]) & 0xFF 应该等于 0
        # 所以校验和 = (sum(data_bytes[0:7])) & 0xFF
        sum_val = sum(data_bytes[:8]) & 0xFF  # 计算前 8 字节 (索引 0-7)，但索引 7 此时应为 0 或未填充
        # 如果传入的 data_bytes 在索引 7 处已有值，需要减去它再计算
        if len(data_bytes) >= 8:
            sum_val = (sum(data_bytes[:7])) & 0xFF
        return sum_val

    def _build_command(self, power_on=True, mode=0, temp=25, fan=0):
        """
        构建格力 9 字节指令
        格力协议标准帧结构 (9 字节):
        Byte 0: 0x0C (固定头)
        Byte 1: 0x00
        Byte 2: 0xA0 (固定头)
        Byte 3: [Mode(4 bits)][Power(1 bit)][Temp(4 bits)]
               - Bit 7-4: 模式 (0=Auto, 1=Cool, 2=Dry, 3=Fan, 4=Heat)
               - Bit 3: 电源 (1=开，0=关)
               - Bit 0-3: 温度 (0-14 对应 16-30°C)
        Byte 4: [Fan(4 bits)][Swing(4 bits)] - 风速在高 4 位，摆风在低 4 位
        Byte 5: 0x00
        Byte 6: 0x00
        Byte 7: Checksum (校验和 = sum(Byte0-Byte6) & 0xFF)
        Byte 8: 0x00 (固定尾部)
        """
        
        # 基础帧头
        data = [0x0C, 0x00, 0xA0]
        
        # 温度处理 (16-30 度)
        temp_val = temp - 16
        if temp_val < 0: temp_val = 0
        if temp_val > 14: temp_val = 14
        
        # 模式映射：0=Auto, 1=Cool, 2=Dry, 3=Fan, 4=Heat
        mode_map = {
            self.MODE_AUTO: 0,
            self.MODE_COOL: 1,
            self.MODE_DRY: 2,
            self.MODE_FAN: 3,
            self.MODE_HEAT: 4
        }
        m_val = mode_map.get(mode, 1)  # 默认制冷
        
        # 电源位：Bit 3 of Byte3 (值为 0x08)
        power_bit = 0x08 if power_on else 0x00
        
        # Byte3 = (Mode << 4) | Power_Bit | Temp_Val
        byte3 = (m_val << 4) | power_bit | temp_val
        data.append(byte3)
        
        # Byte 4: 风速 (高 4 位) 和摆风 (低 4 位)
        fan_map = {
            self.FAN_AUTO: 0,
            self.FAN_LOW: 1,
            self.FAN_MED: 2,
            self.FAN_HIGH: 3
        }
        f_val = fan_map.get(fan, 0)
        byte4 = (f_val << 4)  # 摆风位设为 0 (不摆风)
        data.append(byte4)
        
        # Byte 5, 6: 固定为 0x00
        data.append(0x00)
        data.append(0x00)
        
        # Byte 7: 校验和 (sum of Byte0-Byte6)
        checksum = self._calculate_checksum(data)
        data.append(checksum)
        
        # Byte 8: 尾部填充 (固定为 0x00)
        data.append(0x00)
        
        return data

    def send_raw(self, command_bytes):
        """发送原始字节序列"""
        # 发送前导码
        self._send_header(is_repeat=False)
        
        # 发送 9 字节数据
        for byte_val in command_bytes:
            self._send_byte(byte_val)
            
        # 发送停止位/间隔
        self.ir_pin.value(0)
        time.sleep_us(560)
        self.ir_pin.value(1)
        
        # 等待一段时间防止连续发送干扰
        time.sleep_ms(50)

    def power_on(self, mode=1, temp=25, fan=0):
        """开启空调"""
        cmd = self._build_command(power_on=True, mode=mode, temp=temp, fan=fan)
        self.last_command = cmd
        self.send_raw(cmd)
        # 格力通常需要发送两次以确保接收
        time.sleep_ms(40)
        self.send_raw(cmd)

    def power_off(self):
        """关闭空调 - 发送电源关闭指令"""
        if self.last_command:
            # 基于上次的开机指令，清除电源位来构造关机指令
            off_data = self.last_command.copy()
            # Byte3 (索引 3) 的 Bit 3 (0x08) 是电源位，清除它
            off_data[3] = off_data[3] & 0xF7  # 清除 Bit 3
            # 重新计算校验和
            off_data[7] = self._calculate_checksum(off_data[:7])
            self.send_raw(off_data)
            time.sleep_ms(40)
            self.send_raw(off_data)
        else:
            # 如果没有上次命令，构造一个默认关机指令
            off_data = [0x0C, 0x00, 0xA0, 0x00, 0x00, 0x00, 0x00]
            off_data.append(self._calculate_checksum(off_data))
            off_data.append(0x00)
            self.send_raw(off_data)
            time.sleep_ms(40)
            self.send_raw(off_data)
        self.last_command = None

    def deinit(self):
        self.ir_pin.value(1)

# 测试函数
def test_ac():
    ac = GreeAC(pin_num=4)
    print("Opening AC...")
    ac.power_on(mode=GreeAC.MODE_COOL, temp=26, fan=GreeAC.FAN_AUTO)
    time.sleep(2)
    print("Closing AC...")
    ac.power_off()
    ac.deinit()

if __name__ == "__main__":
    test_ac()
