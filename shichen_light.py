"""
============================================================================
  时空光影控制系统  Shichen Light Controller v1.0
  基于奇门遁甲时辰驱动的动态光影装置
  硬件：树莓派 + DMX512 USB + RGBW LED + 造雾机 + PIR传感器 + RTC
============================================================================
  原理：
    - 造雾机在空气中形成薄雾层（<1m³），人眼几乎不可见
    - RGBW LED 光束穿过雾层时，因丁达尔效应形成可见光柱/光晕
    - 程序根据奇门遁甲十二时辰实时调制光的频率（色相）和波变节奏
    - 光束在雾层中自然散射，呈现"虚空造物"般的动态光波效果
    - PIR传感器检测到人时，光效自动加速、变色，实现人与场景的互动
============================================================================
  安装：
    pip install pyserial
    sudo apt-get install python3-serial
  运行：
    sudo python3 shichen_light.py          # 标准模式
    sudo python3 shichen_light.py --demo    # 演示模式（压缩时辰，30秒一轮）
============================================================================
"""

import time
import math
import random
import threading
import argparse
import json
import os
from datetime import datetime, timedelta

# ===========================================================================
#  配置区 —— 你可以根据需要修改下面的参数
# ===========================================================================

CONFIG = {
    # ---------- 串口 (DMX512) ----------
    "dmx_port": "/dev/ttyUSB0",          # USB-DMX512 适配器端口
    "dmx_baud": 250000,                  # DMX512 固定波特率
    "dmx_refresh_hz": 40,                # DMX 刷新频率 (Hz)

    # ---------- DMX 通道映射 ----------
    "dmx_ch_red": 1,                     # LED 红色通道 (0-255)
    "dmx_ch_green": 2,                   # LED 绿色通道 (0-255)
    "dmx_ch_blue": 3,                    # LED 蓝色通道 (0-255)
    "dmx_ch_white": 4,                   # LED 白光通道 (0-255)
    "dmx_ch_master": 5,                  # LED 总调光 (0-255)
    "dmx_ch_fog": 6,                     # 造雾机开关 (0=关, 255=开)
    "dmx_ch_fog_amount": 7,              # 造雾量 (0-255)

    # ---------- 时辰参数 ----------
    "latitude": 38.0,                    # 纬度：石家庄约38°N
    "longitude": 114.5,                  # 经度：石家庄约114.5°E
    "shichen_table": [],                 # 自动生成，见下方

    # ---------- 互动参数 ----------
    "pir_pin": 17,                       # PIR 传感器 GPIO 引脚 (BCM)
    "interact_speed_boost": 1.5,         # 互动时频率加速倍数
    "interact_duration": 8,              # 互动模式持续时间 (秒)
    "fog_release_interval": 30,          # 造雾间隔 (秒)，持续放雾会太浓

    # ---------- 光参 ----------
    "brightness_day": 200,               # 日间亮度 (0-255)
    "brightness_night": 80,              # 夜间亮度 (0-255)
    "brightness_latenight": 30,          # 深夜亮度 (0-255)
}

# ===========================================================================
#  十二时辰光参映射表 —— 这是发明专利的核心
#  每个时辰定义一组光参数，控制系统据此实时合成波变效果
# ===========================================================================

SHICHEN_MAP = [
    # (时辰名称, 起始小时, 起始分钟, 五行,
    #  中心色相°H, 色相偏移A°, 波变周期T秒, 波形, 亮度等级, 色谱扫描范围nm)

    ("子时", 23, 0, "水",
     240, 20,  12.0, "sine",    "latenight", "460-490"),

    ("丑时", 1,  0, "土",
     40,  15,  18.0, "triangle","latenight", "560-600"),

    ("寅时", 3,  0, "木",
     160, 20,  8.0,  "saw_up",  "latenight", "490-530"),

    ("卯时", 5,  0, "木",
     120, 25,  5.0,  "sine",    "night",     "510-540"),

    ("辰时", 7,  0, "土",
     50,  20,  6.0,  "triangle","day",       "560-600"),

    ("巳时", 9,  0, "火",
     30,  30,  4.0,  "saw_up",  "day",       "600-630"),

    ("午时", 11, 0, "火",
     0,   35,  3.0,  "square",  "day",       "620-660"),

    ("未时", 13, 0, "土",
     45,  20,  6.0,  "triangle","day",       "570-600"),

    ("申时", 15, 0, "金",
     50,  15,  8.0,  "sine",    "day",       "570-590"),

    ("酉时", 17, 0, "金",
     35,  20,  10.0, "saw_down","night",     "580-600"),

    ("戌时", 19, 0, "火",
     15,  25,  7.0,  "sine",    "night",     "610-640"),

    ("亥时", 21, 0, "水",
     250, 15,  16.0, "triangle","latenight", "450-480"),
]

# 亮度等级映射
BRIGHTNESS = {
    "day":        CONFIG["brightness_day"],
    "night":      CONFIG["brightness_night"],
    "latenight":  CONFIG["brightness_latenight"],
}

# ===========================================================================
#  时辰计算模块
# ===========================================================================

class ShichenEngine:
    """奇门遁甲时辰引擎 — 计算当前时辰及其光参"""

    def __init__(self, map_data):
        self.map = map_data  # SHICHEN_MAP

    def get_current_shichen(self):
        """返回当前时辰的光参元组"""
        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute

        candidates = []
        for item in self.map:
            name, start_h, start_m, element = item[:4]
            start_min = start_h * 60 + start_m
            # 计算结束时间（下一个时辰的起始）
            idx = self.map.index(item)
            next_item = self.map[(idx + 1) % len(self.map)]
            _, end_h, end_m, _ = next_item[:4]
            end_min = end_h * 60 + end_m

            # 跨天处理（子时23:00-00:59）
            if end_min <= start_min:
                end_min += 1440

            # 判断是否在此时辰范围内
            if start_min <= current_minutes < end_min:
                params = item[4:]  # 五行, H, A, T, 波形, 亮度, 光谱
                # 计算时辰内的进度占比 (0.0 ~ 1.0)
                duration = end_min - start_min
                progress = (current_minutes - start_min) / duration if duration > 0 else 0
                return {
                    "name": name,
                    "element": element,
                    "hue_center": params[0],
                    "hue_range": params[1],
                    "period": params[2],
                    "waveform": params[3],
                    "brightness_level": params[4],
                    "spectrum_range": params[5],
                    "progress": progress,
                }

        # fallback
        return self.map[0][4]

    def get_shichen_schedule(self):
        """返回24小时的时辰排程（用于日志/界面显示）"""
        schedule = []
        for item in self.map:
            name, start_h, start_m = item[:3]
            schedule.append(f"{name} {start_h:02d}:{start_m:02d}")
        return schedule


# ===========================================================================
#  波形生成器 —— 核心算法
# ===========================================================================

class WaveGenerator:
    """光波生成器 — 根据时辰参数实时合成波形"""

    @staticmethod
    def sine(t, period, offset=0):
        """正弦波: 平滑流动"""
        if period <= 0:
            return 0.5
        return 0.5 + 0.5 * math.sin(2 * math.pi * t / period + offset)

    @staticmethod
    def triangle(t, period, offset=0):
        """三角波: 匀速来回"""
        if period <= 0:
            return 0.5
        phase = ((t + offset * period / (2*math.pi)) % period) / period
        return 2 * (phase if phase < 0.5 else 1 - phase)

    @staticmethod
    def saw_up(t, period, offset=0):
        """上升锯齿波: 缓慢上升，快速回落"""
        if period <= 0:
            return 0.5
        phase = ((t + offset * period / (2*math.pi)) % period) / period
        return phase

    @staticmethod
    def saw_down(t, period, offset=0):
        """下降锯齿波: 缓慢下降，快速回升"""
        if period <= 0:
            return 0.5
        phase = ((t + offset * period / (2*math.pi)) % period) / period
        return 1 - phase

    @staticmethod
    def square(t, period, offset=0):
        """方波: 强脉冲"""
        if period <= 0:
            return 1.0
        phase = ((t + offset * period / (2*math.pi)) % period) / period
        return 1.0 if phase < 0.5 else 0.0

    @classmethod
    def generate(cls, waveform, t, period, offset=0):
        """通用波形生成接口"""
        generators = {
            "sine":     cls.sine,
            "triangle": cls.triangle,
            "saw_up":   cls.saw_up,
            "saw_down": cls.saw_down,
            "square":   cls.square,
        }
        gen = generators.get(waveform, cls.sine)
        return gen(t, period, offset)


# ===========================================================================
#  色彩空间转换
# ===========================================================================

class ColorConverter:
    """色彩转换：HSV ↔ RGBW + DMX"""

    @staticmethod
    def hsv_to_rgb(h, s, v):
        """
        将 HSV 色彩空间转换为 RGB
        h: 色相 0-360 (度)
        s: 饱和度 0-1
        v: 明度 0-1
        返回 (R, G, B) 0-255
        """
        h = h % 360
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c

        if h < 60:
            r, g, b = c, x, 0
        elif h < 120:
            r, g, b = x, c, 0
        elif h < 180:
            r, g, b = 0, c, x
        elif h < 240:
            r, g, b = 0, x, c
        elif h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x

        return int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)

    @staticmethod
    def rgb_to_dmx(r, g, b, w=0):
        """RGBW → DMX512 通道值 (确保在0-255范围)"""
        return (
            max(0, min(255, int(r))),
            max(0, min(255, int(g))),
            max(0, min(255, int(b))),
            max(0, min(255, int(w))),
        )


# ===========================================================================
#  效果合成引擎 —— 虚空中造光
# ===========================================================================

class VoidLightEngine:
    """
    虚空光影引擎
    —— 不依赖水幕、屏幕等实体介质
    —— 通过雾层丁达尔效应 + 精确调频，在虚空中显现动态光波
    """

    def __init__(self, shichen_engine, wave_gen, color_conv):
        self.shichen = shichen_engine
        self.wave = wave_gen
        self.color = color_conv
        self.interact_mode = False
        self.interact_end_time = 0
        self.fog_on = False
        self.runtime = 0.0
        self.current_dmx = [0] * 512  # DMX buffer

    def update(self, dt, pir_triggered=False):
        """主更新循环 —— 每秒调用"""
        self.runtime += dt

        # 1. 获取当前时辰参数
        sc = self.shichen.get_current_shichen()
        period = sc["period"]
        hue_center = sc["hue_center"]
        hue_range = sc["hue_range"]
        waveform = sc["waveform"]
        brightness_level = sc["brightness_level"]

        # 2. 互动检测
        if pir_triggered:
            self.interact_mode = True
            self.interact_end_time = time.time() + CONFIG["interact_duration"]
        if self.interact_mode and time.time() > self.interact_end_time:
            self.interact_mode = False

        # 3. 互动时加速波变
        speed = CONFIG["interact_speed_boost"] if self.interact_mode else 1.0

        # 4. 使用时辰的progress作为相位偏移
        phase_offset = sc["progress"] * 2 * math.pi

        # 5. 生成波形值 (0.0 - 1.0)
        wave_value = self.wave.generate(waveform, self.runtime, period / speed, phase_offset)

        # 6. 加入随机扰动（模拟雾层湍流的自然随机性）
        turbulence = random.gauss(0, 0.03)  # ±3% 的随机扰动
        wave_value = max(0.0, min(1.0, wave_value + turbulence))

        # 7. 互动时额外增加闪烁随机
        if self.interact_mode:
            flicker = random.uniform(-0.1, 0.2)
            wave_value = max(0.0, min(1.0, wave_value + flicker))

        # 8. 计算实时色相 —— 在中心色相 ± 范围之间随波形摆动
        hue = hue_center + (wave_value - 0.5) * 2 * hue_range

        # 9. 第二层波变：色谱扫描（在光谱范围内缓慢漂移）
        #    随一天时间缓慢变化，模拟日照色温变化
        day_progress = sc["progress"]
        spectrum_shift = math.sin(day_progress * 2 * math.pi) * 5  # ±5度

        # 互动时加入旋涡效果——多色谱叠加
        if self.interact_mode:
            spectrum_shift += math.sin(self.runtime * 3) * 15  # 大幅色相跳跃
            hue += spectrum_shift

        # 10. 饱和度（纯色vs白色）
        saturation = 0.85 if not self.interact_mode else 0.95

        # 11. 亮度
        brightness = BRIGHTNESS.get(brightness_level, CONFIG["brightness_night"])
        if self.interact_mode:
            brightness = int(brightness * 1.3)  # 互动时亮20%
        brightness = min(255, brightness)

        # 12. HSV → RGB
        r, g, b = self.color.hsv_to_rgb(hue, saturation, brightness / 255.0)

        # 13. 互动时的漩涡特效：加入白光脉冲
        w = 0
        if self.interact_mode:
            pulse = abs(math.sin(self.runtime * 8))  # 快速脉冲
            w = int(pulse * 80)  # 白光闪烁

        # 14. 写入 DMX 缓冲区
        ch = CONFIG["dmx_ch_red"]
        self.current_dmx[CONFIG["dmx_ch_red"] - 1] = r
        self.current_dmx[CONFIG["dmx_ch_green"] - 1] = g
        self.current_dmx[CONFIG["dmx_ch_blue"] - 1] = b
        self.current_dmx[CONFIG["dmx_ch_white"] - 1] = w
        self.current_dmx[CONFIG["dmx_ch_master"] - 1] = 255  # 总调全开

        # 15. 造雾控制：每隔一段时间开一次雾
        if int(self.runtime) % CONFIG["fog_release_interval"] < 3:  # 每次3秒
            self.current_dmx[CONFIG["dmx_ch_fog"] - 1] = 255
            self.current_dmx[CONFIG["dmx_ch_fog_amount"] - 1] = 100  # 中等雾量
            self.fog_on = True
        else:
            self.current_dmx[CONFIG["dmx_ch_fog"] - 1] = 0
            self.current_dmx[CONFIG["dmx_ch_fog_amount"] - 1] = 0
            self.fog_on = False

        return {
            "shichen": sc["name"],
            "element": sc["element"],
            "hue": round(hue, 1),
            "waveform": waveform,
            "wave_value": round(wave_value, 3),
            "brightness": brightness,
            "interact": self.interact_mode,
            "fog": self.fog_on,
            "rgbw": (r, g, b, w),
        }

    def get_dmx_frame(self):
        """返回当前 DMX 帧数据"""
        return bytes(self.current_dmx)


# ===========================================================================
#  DMX512 通信
# ===========================================================================

class DMXController:
    """DMX512 控制器 — 通过 USB-DMX 适配器发送数据"""

    def __init__(self, port=None):
        self.port = port or CONFIG["dmx_port"]
        self.serial = None
        self.running = False
        self.thread = None

    def connect(self):
        """连接 DMX 适配器"""
        try:
            import serial
            self.serial = serial.Serial(
                port=self.port,
                baudrate=CONFIG["dmx_baud"],
                bytesize=8,
                parity='N',
                stopbits=2,
                timeout=0.1
            )
            print(f"[DMX] 连接成功: {self.port}")
            return True
        except Exception as e:
            print(f"[DMX] 连接失败: {e}")
            print("[DMX] 将运行模拟模式（不输出到硬件）")
            return False

    def send_frame(self, dmx_data):
        """发送一帧 DMX512 数据"""
        if self.serial and self.serial.is_open:
            try:
                # DMX512 协议：BREAK + MAB + 起始码0x00 + 512通道数据
                self.serial.break_condition = True
                time.sleep(0.0001)  # 100μs BREAK
                self.serial.break_condition = False
                time.sleep(0.000012)  # 12μs MAB
                self.serial.write(bytes([0x00]))  # 起始码
                self.serial.write(dmx_data)  # 512字节通道数据
                self.serial.flush()
            except:
                pass

    def close(self):
        if self.serial and self.serial.is_open:
            self.serial.close()


# ===========================================================================
#  控制台显示
# ===========================================================================

class ConsoleDisplay:
    """终端显示 — 实时展示运行状态"""

    @staticmethod
    def render(status, engine):
        """显示当前状态"""
        os.system('cls' if os.name == 'nt' else 'clear')

        print("=" * 60)
        print("  时空光影控制系统  Shichen Light Controller v1.0")
        print("  " + "=" * 60)
        print()

        sc = engine.shichen.get_current_shichen()
        print(f"  ⏰ 当前时辰：{sc['name']} ｜ 五行：{sc['element']}")
        print(f"  🔄 时辰进度：{sc['progress']*100:.0f}%")
        print()
        print(f"  💡 色相：{status['hue']}° ｜ 波形：{status['waveform']}")
        print(f"  📊 波形值：{status['wave_value']}")
        print(f"  ☀️  亮度：{status['brightness']}")
        print(f"  🌈 RGBW：({status['rgbw'][0]}, {status['rgbw'][1]}, "
              f"{status['rgbw'][2]}, {status['rgbw'][3]})")
        print()

        if status['interact']:
            print(f"  ✨✨✨ 互动模式激活！ ✨✨✨")
        else:
            print(f"  💤 待机模式")
        print(f"  🌫  {'雾中' if status['fog'] else '静置'}")
        print()

        schedule = engine.shichen.get_shichen_schedule()
        print(f"  📋 时辰排程:")
        for i, s in enumerate(schedule):
            marker = "→" if s.startswith(sc['name']) else " "
            print(f"    {marker} {s}")
        print()
        print(f"  {'─' * 50}")
        print(f"  按 Ctrl+C 退出")


# ===========================================================================
#  PIR 传感器模拟/硬件
# ===========================================================================

class PIRSimulator:
    """PIR 模拟器（无硬件时使用）— 按随机间隔触发互动"""

    def __init__(self):
        self.last_trigger = 0
        self.cooldown = 15  # 模拟触发的最小间隔

    def check(self):
        now = time.time()
        if now - self.last_trigger > self.cooldown:
            if random.random() < 0.02:  # 2% 概率每帧触发
                self.last_trigger = now
                return True
        return False


class PIRHardware:
    """PIR 硬件接口（树莓派 GPIO）"""

    def __init__(self, pin=17):
        self.pin = pin
        self.inited = False
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.IN)
            self.gpio = GPIO
            self.inited = True
        except:
            print("[PIR] GPIO 不可用，使用模拟模式")

    def check(self):
        if self.inited:
            return self.gpio.input(self.pin) == 1
        return False


# ===========================================================================
#  主程序
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(description="时空光影控制系统")
    parser.add_argument('--demo', action='store_true',
                       help='演示模式：时辰压缩至30秒一轮')
    parser.add_argument('--port', type=str, default=None,
                       help='DMX512 串口 (默认: /dev/ttyUSB0)')
    parser.add_argument('--no-dmx', action='store_true',
                       help='纯模拟模式（不连接硬件）')
    parser.add_argument('--simulate-pir', action='store_true',
                       help='使用 PIR 模拟器（自动触发互动）')
    args = parser.parse_args()

    print("=" * 60)
    print("  时空光影控制系统 启动中...")
    print("=" * 60)

    # 初始化组件
    sc_engine = ShichenEngine(SHICHEN_MAP)
    wave_gen = WaveGenerator()
    color_conv = ColorConverter()
    light_engine = VoidLightEngine(sc_engine, wave_gen, color_conv)
    display = ConsoleDisplay()

    # DMX
    dmx = DMXController(args.port)
    dmx_connected = dmx.connect()

    # PIR
    pir = PIRHardware() if not args.simulate_pir else PIRSimulator()

    print("\n系统就绪！\n")
    time.sleep(1)

    # 主循环
    dmx_refresh = 1.0 / CONFIG["dmx_refresh_hz"]
    last_time = time.time()
    pir_triggered = False

    try:
        while True:
            now = time.time()
            dt = now - last_time
            last_time = now

            # PIR 检测
            pir_triggered = pir.check()

            # 更新光影引擎
            status = light_engine.update(dt, pir_triggered)

            # 发送 DMX
            if dmx_connected:
                dmx_frame = light_engine.get_dmx_frame()
                dmx.send_frame(dmx_frame)

            # 显示状态（每500ms刷新一次）
            if int(now * 2) > int((now - dt) * 2):
                display.render(status, light_engine)

            # 保持帧率
            sleep_time = dmx_refresh - (time.time() - now)
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n\n关闭系统...")
    finally:
        if dmx_connected:
            # 发送全关指令
            blank = bytes([0] * 512)
            dmx.send_frame(blank)
            dmx.close()
        print("系统已安全关闭。")

if __name__ == "__main__":
    main()
