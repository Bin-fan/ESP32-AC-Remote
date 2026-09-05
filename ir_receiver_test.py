import machine
import time

# 配置接收引脚
# 请根据实际接线修改 PIN_NUM，HS-S23P OUT 引脚接这里
PIN_NUM = 4 

# 初始化引脚为输入模式
ir_pin = machine.Pin(PIN_NUM, machine.Pin.IN)

print(f"--- IR Receiver Test Started on GPIO {PIN_NUM} ---")
print("Point your Gree Remote at the sensor and press any button.")
print("Waiting for signal...")

def read_ir_signal():
    """
    读取原始红外时序数据。
    HS-S23P 输出反相信号：
    - 空闲: High (1)
    - 脉冲: Low (0)
    
    我们需要测量 Low 状态的持续时间 (us) 来对应发射端的 High 脉冲宽度。
    """
    
    # 1. 等待起始信号 (通常是长低电平)
    # 先等待变为低电平 (开始接收)
    while ir_pin.value() == 1:
        if time.ticks_ms() % 1000 < 10: # 防止死循环打印太多，简单防抖
            pass 
        # 超时处理可在此添加，这里简化为无限等待
    
    # 2. 开始捕获时序
    timings = []
    start_time = time.ticks_us()
    
    # 我们期望捕获至少 100 个脉冲段，或者直到信号结束超过一定时间
    # 格力空调遥控码很长，通常需要捕获 100-200 个时间段
    max_segments = 200 
    timeout_threshold = 600 # 微秒，如果高电平间隔超过这个值，认为一帧结束 (实际引导码间隔更长)
    
    last_edge = time.ticks_us()
    
    # 循环读取边沿
    while len(timings) < max_segments:
        # 等待电平变化 (无论是从高变低 还是 从低变高)
        current_val = ir_pin.value()
        
        # 简单的轮询检测边沿 (MicroPython 在中断中处理更准，但轮询对于调试足够)
        # 为了更精准，我们检测从高到低 和 从低到高 的变化
        
        # 等待下一个状态改变
        while ir_pin.value() == current_val:
            if time.ticks_diff(time.ticks_us(), last_edge) > 5000: # 5ms 无信号，认为帧结束
                break
        
        now = time.ticks_us()
        duration = time.ticks_diff(now, last_edge)
        last_edge = now
        
        # 过滤掉极短的噪声 (< 100us) 和极长的等待 (> 20ms)
        if 100 < duration < 20000:
            timings.append(duration)
        
        # 如果检测到超长间隔 (通常是帧之间的间隔)，停止
        if duration > 1500: # 引导码后的间隔通常很大，或者帧结束
             # 格力协议一帧数据很长，这里主要看是否连续数据流断了
             if len(timings) > 50: # 如果已经收集了不少数据，且出现长间隔，可能是一帧结束
                 break

    return timings

def analyze_gree_signal(timings):
    """
    尝试解析格力协议特征
    格力协议特征 (38kHz):
    - 引导码: 9ms 低 + 4.5ms 高 (接收端看到的是 9ms 低 + 4.5ms 低？不，接收端输出反相)
      发射端: 9ms载波(低), 4.5ms无载波(高)
      接收端OUT: 9ms低, 4.5ms高
      所以 timings[0] 应约为 9000us, timings[1] 应约为 4500us
      
    - 数据位 '0': 0.56ms 载波 + 0.56ms 无载波 (接收端: 560低, 560高)
    - 数据位 '1': 0.56ms 载波 + 1.69ms 无载波 (接收端: 560低, 1690高)
    """
    if len(timings) < 10:
        print("Signal too short or noise.")
        return

    print("\n--- Raw Timings (First 20 samples) ---")
    # 打印前20个数据以便观察
    for i, t in enumerate(timings[:20]):
        print(f"{i}: {t} us")
    
    if len(timings) > 2:
        lead_low = timings[0]
        lead_high = timings[1]
        print(f"\n--- Header Analysis ---")
        print(f"Header Low (Target ~9000us): {lead_low}")
        print(f"Header High (Target ~4500us): {lead_high}")
        
        if 8000 < lead_low < 10000 and 4000 < lead_high < 5000:
            print("✅ Header looks like a standard IR protocol (NEC/Gree style).")
        else:
            print("⚠️ Header timing seems off. Check distance or interference.")

        # 简单统计脉宽分布，区分 0 和 1
        # 在格力协议中，低电平(载波)宽度基本固定 (~560us)，高电平(间隔)宽度变化代表 0 或 1
        # 由于接收端反相，timings 中的偶数项 (0, 2, 4...) 对应载波宽度 (应接近 560)
        # 奇数项 (1, 3, 5...) 对应间隔宽度 (560 为 0, 1690 为 1)
        
        gaps = timings[3::2] # 跳过引导码，取数据位的间隔部分
        if gaps:
            low_gap_count = sum(1 for g in gaps if g < 1000)
            high_gap_count = sum(1 for g in gaps if g >= 1000)
            print(f"\n--- Data Bit Estimation ---")
            print(f"Detected '0's (gap < 1000us): {low_gap_count}")
            print(f"Detected '1's (gap >= 1000us): {high_gap_count}")
            print(f"Total data bits estimated: {low_gap_count + high_gap_count}")
            
            if 50 < (low_gap_count + high_gap_count) < 80:
                 print("⚠️ Bit count is low. This might be just the header or a short command.")
            elif (low_gap_count + high_gap_count) >= 100:
                 print("✅ Bit count looks sufficient for a full AC command (Gree is long).")

while True:
    # 短暂延时防止重复触发
    time.sleep_ms(200)
    
    # 等待信号
    if ir_pin.value() == 0:
        # 去抖动
        time.sleep_ms(10)
        if ir_pin.value() == 0:
            data = read_ir_signal()
            if data:
                analyze_gree_signal(data)
                print("\nWaiting for next signal...")
