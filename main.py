import time
from machine import Timer
from gree_ac_control import GreeAC
import config

# 从 config 模块导入控制配置
TARGET_HOUR = config.TARGET_HOUR
TARGET_MINUTE = config.TARGET_MINUTE
IR_PIN = config.IR_PIN
AC_MODE = config.AC_MODE
AC_TEMP = config.AC_TEMP
AC_FAN = config.AC_FAN
AC_RUN_DURATION = config.AC_RUN_DURATION

# 初始化空调控制器
try:
    ac = GreeAC(pin=IR_PIN)
    print(f"红外空调控制器已初始化 (GPIO {IR_PIN})")
except Exception as e:
    print(f"红外控制器初始化失败：{e}")
    ac = None

# 状态标志
task_triggered = False
last_trigger_time = None
is_ac_on = False
ac_on_timestamp = 0

# --- 2026年中国节假日与调休工作日 ---
# 节假日 (月, 日)
HOLIDAYS = [
    (1, 1), (1, 2), (1, 3),
    (2, 15), (2, 16), (2, 17), (2, 18), (2, 19), (2, 20), (2, 21), (2, 22), (2, 23),
    (4, 4), (4, 5), (4, 6),
    (5, 1), (5, 2), (5, 3), (5, 4), (5, 5),
    (6, 19), (6, 20), (6, 21),
    (9, 25), (9, 26), (9, 27),
    (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7)
]

# 特殊调休工作日 (月, 日)
ADJUSTED_WORKDAYS = [
    (1, 4),
    (2, 14), (2, 28),
    (5, 9),
    (9, 20), (10, 10)
]

def is_workday(year, month, day, weekday):
    """
    判断是否为中国工作日
    weekday: 0=周一, 6=周日
    """
    if year != 2026:
        # 非2026年仅按周末判断
        return weekday < 5

    if (month, day) in ADJUSTED_WORKDAYS:
        return True
    if (month, day) in HOLIDAYS:
        return False
    if weekday >= 5: 
        return False
    return True

def check_and_run(timer):
    """
    定时器回调函数 (每30秒执行一次)
    仅负责检查时间标志，不执行耗时操作
    """
    global task_triggered, last_trigger_time
    
    current_cst_time = time.localtime()
    year = current_cst_time[0]
    month = current_cst_time[1]
    day = current_cst_time[2]
    hour = current_cst_time[3]
    minute = current_cst_time[4]
    weekday = current_cst_time[6]
    
    # 构造当前时间标记 (用于防重复)
    current_time_mark = (year, month, day, hour, minute)

    # 判断条件：是工作日 且 到达目标时间 且 本分钟内未触发过
    if (is_workday(year, month, day, weekday) and 
        hour == TARGET_HOUR and 
        minute == TARGET_MINUTE and 
        last_trigger_time != current_time_mark):
        
        task_triggered = True
        last_trigger_time = current_time_mark
        print(f"[定时触发] 检测到工作日 {TARGET_HOUR}:{TARGET_MINUTE}，准备执行空调启动任务...")

def manage_ac_task():
    """
    在主循环中管理空调任务
    处理开机、计时、关机逻辑
    """
    global task_triggered, is_ac_on, ac_on_timestamp
    
    if task_triggered:
        task_triggered = False  # 重置标志
        
        if ac is None:
            print("错误：空调控制器未初始化，跳过执行。")
            return

        if not is_ac_on:
            # 执行开机
            print(f">>> 正在发送开机指令：模式={AC_MODE}, 温度={AC_TEMP}°C, 风速={AC_FAN}")
            try:
                ac.power_on(mode=AC_MODE, temp=AC_TEMP, fan=AC_FAN)
                is_ac_on = True
                ac_on_timestamp = time.time()
                print(">>> 空调开机指令发送成功！")
            except Exception as e:
                print(f"!!! 发送开机指令失败: {e}")
        else:
            print("提示：空调已在运行中，跳过本次开机指令。")

    # 如果空调已开启，检查是否需要关闭 (基于运行时长)
    if is_ac_on and AC_RUN_DURATION > 0:
        elapsed = time.time() - ac_on_timestamp
        if elapsed >= AC_RUN_DURATION:
            print(f">>> 运行时间已达 {AC_RUN_DURATION}秒，正在发送关机指令...")
            try:
                ac.power_off()
                is_ac_on = False
                print(">>> 空调关机指令发送成功！")
            except Exception as e:
                print(f"!!! 发送关机指令失败: {e}")

def main():
    """
    主函数
    """
    print("="*30)
    print("格力空调自动定时控制器")
    print(f"目标时间：{TARGET_HOUR}:{TARGET_MINUTE}")
    print(f"运行时长：{AC_RUN_DURATION}秒")
    print("="*30)
    
    # 初始化定时器 (30秒周期)
    timer = Timer(0)
    timer.init(period=30000, mode=Timer.PERIODIC, callback=check_and_run)
    
    print("定时检测已启动。等待触发时间...")
    print(f"当前时间：{time.localtime()}")
    
    # 主循环
    while True:
        # 检查并执行空调任务
        manage_ac_task()
        
        # 短暂休眠，避免占用过多CPU，同时保持看门狗安全
        # 如果需要更精确的关机计时，可减小此值
        time.sleep(1)

if __name__ == "__main__":
    main()
