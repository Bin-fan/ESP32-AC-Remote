import time
from machine import Timer
from machine import Pin

# --- 中国标准时间 (CST) UTC+8 ---
# 假设设备的系统时间已经是准确的UTC时间
TARGET_HOUR = 7
TARGET_MINUTE = 20
pin_do = 15
pin_sign = 2

# 定义引脚
target_pin = Pin(pin_do, Pin.OUT)
sign_pin = Pin(pin_sign, Pin.OUT)

# --- 2026年中国节假日与调休工作日 ---
# 提示: 当进入新的一年时，您需要手动更新此处的列表。
# 节假日 (月, 日)
HOLIDAYS = [
    (1, 1), (1, 2), (1, 3),  # 元旦 (1月1日-3日)
    (2, 15), (2, 16), (2, 17), (2, 18), (2, 19), (2, 20), (2, 21), (2, 22), (2, 23),  # 春节 (2月15日-23日)
    (4, 4), (4, 5), (4, 6),  # 清明节 (4月4日-6日)
    (5, 1), (5, 2), (5, 3), (5, 4), (5, 5),  # 劳动节 (5月1日-5日)
    (6, 19), (6, 20), (6, 21),  # 端午节 (6月19日-21日)
    (9, 25), (9, 26), (9, 27),  # 中秋节 (9月25日-27日)
    (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7)  # 国庆节 (10月1日-7日)
]

# 特殊调休工作日 (月, 日)
ADJUSTED_WORKDAYS = [
    (1, 4),            # 元旦调休 (周日上班)
    (2, 14), (2, 28),  # 春节调休 (周六上班)
    (5, 9),            # 劳动节调休 (周六上班)
    (9, 20), (10, 10)  # 国庆节调休 (周日、周六上班)
]

def is_workday(year, month, day, weekday):
    """
    判断是否为中国工作日
    weekday: 0=周一, 6=周日
    """
    # 警告: 节假日数据仅适用于2026年。
    if year != 2026:
        # 对于非2026年，此函数仅基于周末判断，可能不准确
        # 如果需要支持多年，应使用更复杂的数据结构
        return weekday < 5 # 周一到周五

    if (month, day) in ADJUSTED_WORKDAYS:
        return True
    if (month, day) in HOLIDAYS:
        return False
    # 默认情况下，周六(5)和周日(6)为休息日
    if weekday >= 5: 
        return False
    return True

# 全局状态变量
task_running = False
last_trigger_time = None

def check_and_run(timer):
    """定时器回调函数，仅检查时间并设置标志位"""
    global task_running, last_trigger_time
    
    # 如果任务正在运行，不重复触发
    if task_running:
        return
        
    # time.time() 获取的是UTC+8时间（从epoch开始的秒数）
    current_cst_time = time.localtime()

    year = current_cst_time[0]
    month = current_cst_time[1]
    day = current_cst_time[2]
    hour = current_cst_time[3]
    minute = current_cst_time[4]
    weekday = current_cst_time[6] # 0=周一, 6=周日
    
    # 构造当前时间的唯一标识 (用于防重复触发)
    current_time_key = (year, month, day, hour, minute)

    # 检查是否是工作日的早上7:20
    if is_workday(year, month, day, weekday) and hour == TARGET_HOUR and minute == TARGET_MINUTE:
        # 防止同一分钟内多次触发
        if last_trigger_time != current_time_key:
            last_trigger_time = current_time_key
            task_running = True
            print(f"[{time.localtime()}] 触发定时任务!")

def run_task_logic():
    """
    在主循环中执行的耗时任务逻辑：
    打开引脚 5 分钟，关闭 1 分钟，重复两次。
    """
    global task_running
    
    print("开始执行任务...")
    
    for i in range(2):  # 循环两次
        # 打开引脚，持续 5 分钟 (300秒)
        target_pin.value(1)
        sign_pin.value(1)
        print(f"第 {i+1} 次循环: Pins are ON for 5 minutes.")
        
        # 使用短时间切片睡眠，避免长时间阻塞导致看门狗复位
        for _ in range(30):  # 30 * 10秒 = 300秒
            time.sleep(10)
            # 可选：在此处可以处理其他非阻塞任务
        
        # 关闭引脚，持续 1 分钟 (60秒)
        target_pin.value(0)
        sign_pin.value(0)
        print(f"第 {i+1} 次循环: Pins are OFF for 1 minute.")
        
        # 使用短时间切片睡眠
        for _ in range(6):  # 6 * 10秒 = 60秒
            time.sleep(10)
    
    print("任务执行完毕.")
    task_running = False  # 重置任务状态

# --- 主程序 ---
def main():
    """
    主函数，启动定时器并进入主循环。
    本脚本假定设备的系统时间已通过外部程序（如boot.py）同步。
    """
    
    # 初始化并启动定时器，ID为0，周期为30000毫秒（30秒）
    timer = Timer(0)
    timer.init(period=30000, mode=Timer.PERIODIC, callback=check_and_run)
    
    print(f"定时任务已启动，每30秒检查一次时间。执行时间：{TARGET_HOUR}:{TARGET_MINUTE}")
    print(f"当前UTC+8时间: {time.localtime()}")
    
    # 主循环
    while True:
        if task_running:
            run_task_logic()
        else:
            # 空闲时短暂休眠，降低CPU占用
            time.sleep(1)

# 运行主程序
if __name__ == "__main__":
    main()
