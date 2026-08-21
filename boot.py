import network
import time
import ntptime
from machine import RTC
from machine import Pin

WIFI_SSID = "maria"
WIFI_PASSWORD = "meiling1106"
WIFI_CONNECT_TIMEOUT = 15  # WiFi 连接超时时间（秒）

def connect_wifi():
    """
    连接到 WiFi 网络，带有超时机制。
    返回 True 表示连接成功，False 表示失败。
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('正在连接到 WiFi...')
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        start_time = time.time()
        while not wlan.isconnected():
            if time.time() - start_time > WIFI_CONNECT_TIMEOUT:
                print("WiFi 连接超时！")
                wlan.disconnect()
                return False
            time.sleep(1)
            
    print('WiFi 已连接，网络配置:', wlan.ifconfig())
    return True

def sync_china_time():
    """
    从 NTP 服务器同步 UTC 时间，并设置为中国标准时间 (UTC+8)。
    返回 True 表示同步成功，False 表示失败。
    """
    print("正在从 NTP 服务器同步时间...")
    try:
        ntptime.host = 'ntp1.aliyun.com'
        
        utc_timestamp = ntptime.time()
        cst_offset = 8 * 3600
        cst_timestamp = utc_timestamp + cst_offset
        time_tuple = time.localtime(cst_timestamp)
        
        rtc = RTC()
        rtc.datetime((time_tuple[0], time_tuple[1], time_tuple[2], time_tuple[6], time_tuple[3], time_tuple[4], time_tuple[5], 0))
        
        print("成功同步中国时间 (UTC+8):", time.localtime())
        return True  # 增加返回成功标志

    except Exception as e:
        print("时间同步错误:", repr(e))
        return False # 增加返回失败标志


def blink_led_and_turn_off(led_pin, duration_sec):
    """
    让指定的 LED 引脚闪烁指定秒数后熄灭
    """
    print(f"执行失败指示：LED 将闪烁 {duration_sec} 秒后熄灭...")
    start_time = time.time()
    state = 0
    # 在指定的时间内循环闪烁
    while time.time() - start_time < duration_sec:
        state = 1 - state # 切换状态 (0 变 1，1 变 0)
        led_pin.value(state)
        time.sleep(0.5)   # 每 0.5 秒闪烁一次
        
    led_pin.value(0)      # 确保闪烁结束后灯是熄灭的


def main():
    # 初始化 LED (ESP32 常见的板载指示灯连接在 GPIO 2 上)
    led = Pin(2, Pin.OUT)
    led.value(0) # 初始先熄灭
    
    # 逻辑判断：如果 WiFi 连接成功 并且 时间同步成功
    if connect_wifi() and sync_china_time():
        print("网络及系统时间更新成功！LED 指示灯保持常亮。")
        led.value(1) # 常亮
    else:
        print("网络连接或时间同步失败，请检查 WiFi 凭据、网络环境或 NTP 服务器。")
        # 失败则闪烁 10 秒后熄灭
        blink_led_and_turn_off(led, 10)
    
    print("等待 10 秒后打印当前时间...")
    time.sleep(10)
    print("当前系统时间:", time.localtime())


if __name__ == "__main__":
    main()
