import time
from gree_ac_control import GreeAC
import config

# 模式/风速的显示名（仅用于交互提示）
MODE_NAMES = {0: "自动", 1: "制冷", 2: "除湿", 3: "送风", 4: "制热"}
FAN_NAMES = {0: "自动", 1: "低", 2: "中", 3: "高"}

MENU = """
=== 格力空调手动触发测试 ===
1. 开机（可临时覆盖 模式,温度,风速）
2. 关机
3. 完整流程测试（开机 -> 运行 -> 自动关机）
4. 显示当前配置
q. 退出
"""


def load_ac():
    """初始化红外空调控制器，失败时返回 None"""
    try:
        ac = GreeAC(pin_num=config.IR_PIN)
        print(f"红外空调控制器已初始化 (GPIO {config.IR_PIN})")
        return ac
    except Exception as e:
        print(f"红外控制器初始化失败：{e}")
        return None


def show_config():
    """打印当前配置摘要"""
    print("-" * 30)
    print(f"红外引脚 GPIO {config.IR_PIN}")
    print(f"模式={config.AC_MODE}({MODE_NAMES.get(config.AC_MODE, '?')}), "
          f"温度={config.AC_TEMP}°C, 风速={config.AC_FAN}({FAN_NAMES.get(config.AC_FAN, '?')})")
    print(f"运行时长={config.AC_RUN_DURATION} 秒")
    print("-" * 30)


def read_params():
    """
    读取开机参数：直接回车使用 config 配置，
    或输入 "模式,温度,风速"（如 1,26,0）临时覆盖（仅本次生效，不写入 config.py）。
    返回 (mode, temp, fan)。
    """
    raw = input("开机参数 [回车=config 配置, 或 模式,温度,风速 如 1,26,0]: ").strip()
    if not raw:
        return config.AC_MODE, config.AC_TEMP, config.AC_FAN
    try:
        parts = raw.replace("，", ",").split(",")
        mode = int(parts[0])
        temp = int(parts[1])
        fan = int(parts[2])
        if not 0 <= mode <= 4:
            raise ValueError("模式需为 0-4")
        if not 16 <= temp <= 30:
            raise ValueError("温度需为 16-30")
        if not 0 <= fan <= 3:
            raise ValueError("风速需为 0-3")
        return mode, temp, fan
    except Exception as e:
        print(f"输入无效（{e}），改用 config 配置。")
        return config.AC_MODE, config.AC_TEMP, config.AC_FAN


def read_duration():
    """读取运行时长（秒）：回车使用 config.AC_RUN_DURATION，或输入正整数"""
    raw = input(f"运行时长秒数 [回车={config.AC_RUN_DURATION}s]: ").strip()
    if not raw:
        return config.AC_RUN_DURATION
    try:
        val = int(raw)
        if val <= 0:
            raise ValueError("需为正整数")
        return val
    except Exception:
        print(f"输入无效，使用 config 的 {config.AC_RUN_DURATION} 秒。")
        return config.AC_RUN_DURATION


def power_on_flow(ac):
    """开机（可临时覆盖参数）"""
    mode, temp, fan = read_params()
    print(f">>> 发送开机指令：模式={mode}({MODE_NAMES.get(mode, '?')}), "
          f"温度={temp}°C, 风速={fan}({FAN_NAMES.get(fan, '?')})")
    try:
        ac.power_on(mode=mode, temp=temp, fan=fan)
        print(">>> 开机指令发送成功！")
    except Exception as e:
        print(f"!!! 开机指令发送失败: {e}")


def power_off_flow(ac):
    """关机"""
    print(">>> 发送关机指令...")
    try:
        ac.power_off()
        print(">>> 关机指令发送成功！")
    except Exception as e:
        print(f"!!! 关机指令发送失败: {e}")


def run_full_flow(ac):
    """完整流程测试：开机 -> 等待运行时长 -> 关机（模拟 main.py 定时任务的行为）"""
    duration = read_duration()
    mode, temp, fan = config.AC_MODE, config.AC_TEMP, config.AC_FAN
    print(f">>> [1/3] 发送开机指令：模式={mode}({MODE_NAMES.get(mode, '?')}), "
          f"温度={temp}°C, 风速={fan}({FAN_NAMES.get(fan, '?')})")
    try:
        ac.power_on(mode=mode, temp=temp, fan=fan)
    except Exception as e:
        print(f"!!! 开机指令发送失败，中止流程: {e}")
        return
    print(f">>> [2/3] 空调运行中，{duration} 秒后自动关机（Ctrl+C 可中断）...")
    start = time.time()
    last_report = start
    while time.time() - start < duration:
        time.sleep(1)
        now = time.time()
        if now - last_report >= 10:  # 每 10 秒报告一次进度，避免刷屏
            last_report = now
            print(f"    已运行 {int(now - start)} 秒，剩余 {max(0, int(duration - (now - start)))} 秒")
    print(">>> [3/3] 运行时间到，发送关机指令...")
    try:
        ac.power_off()
        print(">>> 完整流程测试完成！")
    except Exception as e:
        print(f"!!! 关机指令发送失败: {e}")


def main():
    ac = load_ac()
    if ac is None:
        return
    show_config()
    try:
        while True:
            print(MENU)
            choice = input("请选择: ").strip().lower()
            if choice == "1":
                power_on_flow(ac)
            elif choice == "2":
                power_off_flow(ac)
            elif choice == "3":
                run_full_flow(ac)
            elif choice == "4":
                show_config()
            elif choice in ("q", "quit", "exit"):
                print("退出。如需恢复定时任务，请重启 ESP32（Thonny 中 Ctrl+D 软重启）。")
                break
            else:
                print("无效选择，请重新输入。")
    except (KeyboardInterrupt, EOFError):
        print("\n已中断。如需恢复定时任务，请重启 ESP32（Thonny 中 Ctrl+D 软重启）。")


if __name__ == "__main__":
    main()
