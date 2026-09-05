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

def wait_falling_edge(timeout_ms=10000, poll_us=50):
    """
    等待引脚从空闲高电平变为低电平（一帧的开始），带超时。
    返回 True 表示检测到下降沿，False 表示超时。

    检测到下降沿后立即返回，由调用方随即开始计时，
    保证捕获从引导码下降沿对齐开始（引导码完整计入 timings[0]）。
    """
    start = time.ticks_ms()
    while ir_pin.value() == 1:
        if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
            return False
        time.sleep_us(poll_us)  # 空闲期间低频轮询即可
    return True

def read_ir_signal(max_segments=200, idle_timeout_us=15000):
    """
    从当前电平沿开始，记录交替电平的持续时间（微秒），返回 timings 列表。

    HS-S23P 输出反相信号：
    - 空闲: High (1)
    - 载波脉冲: Low (0)

    timings 结构（从引导码下降沿开始计时）：
    [引导低电平(~9000), 引导高间隔(~4500), 位0脉冲, 位0间隔, 位1脉冲, ...]

    idle_timeout_us: 电平保持超过该时长视为帧结束（线路回到空闲），立即返回。
    取 15000us 的原因：远大于最长位间隔 1680us 与引导间隔 4500us（不会切断帧内电平），
    又小于本项目发送器连发两帧之间的 40ms 间隔（可干净地按帧分割）。
    """
    timings = []
    last_edge = time.ticks_us()

    while len(timings) < max_segments:
        cur = ir_pin.value()
        # 等待电平翻转，或超时（= 帧结束，超时的空闲段不记录）
        while ir_pin.value() == cur:
            if time.ticks_diff(time.ticks_us(), last_edge) > idle_timeout_us:
                return timings

        now = time.ticks_us()
        duration = time.ticks_diff(now, last_edge)
        last_edge = now

        # 过滤噪声毛刺（<100us）：丢弃该段，其时长并入下一段
        if duration < 100:
            continue
        timings.append(duration)

    return timings

def analyze_gree_signal(timings):
    """
    尝试解析格力协议特征
    格力协议特征 (38kHz):
    - 引导码: 9ms 载波 + 4.5ms 无载波
      发射端: 9ms载波(低), 4.5ms无载波(高)
      接收端OUT输出反相: 9ms低, 4.5ms高
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
        # 由于捕获从引导码下降沿对齐开始：
        # 偶数项 (0, 2, 4...) 对应载波脉冲宽度 (应接近 560)
        # 奇数项 (1, 3, 5...) 对应间隔宽度 (560 为 0, 1680 为 1)

        gaps = timings[3::2]  # 跳过引导码，取数据位的间隔部分
        if gaps:
            low_gap_count = sum(1 for g in gaps if g < 1000)
            high_gap_count = sum(1 for g in gaps if g >= 1000)
            print(f"\n--- Data Bit Estimation ---")
            print(f"Detected '0's (gap < 1000us): {low_gap_count}")
            print(f"Detected '1's (gap >= 1000us): {high_gap_count}")
            print(f"Total data bits estimated: {low_gap_count + high_gap_count}")

            total_bits = low_gap_count + high_gap_count
            # 本项目格力帧为 9 字节 = 72 位（帧尾另有 1 个停止位脉冲，不计入间隔）
            if 70 <= total_bits <= 74:
                print("✅ Bit count matches the Gree 9-byte frame (72 bits).")
            elif total_bits >= 60:
                print("⚠️ Bit count differs from the expected 72-bit Gree frame.")
            else:
                print("⚠️ Bit count is low. This might be a partial capture or noise.")

while True:
    # 等待一帧开始（空闲高电平 -> 检测到下降沿）
    if wait_falling_edge(timeout_ms=10000):
        data = read_ir_signal()
        if len(data) > 10:
            analyze_gree_signal(data)
            print("\nWaiting for next signal...")
        # 发送器/遥控器通常会连发两帧，稍等以跳过重复帧
        time.sleep_ms(200)
