import RPi.GPIO as GPIO
import time

# 使用 BOARD 模式（實體腳位編號）
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

# LED 與感測器對應腳位
led_pins = [22, 24, 26, 32, 18, 36, 38, 40]
sensor_pins = [1, 2, 3, 4, 5, 6, 7, 8]  # 暫定，之後替換為真實腳位

# 設定 LED 腳為輸出，初始關閉
for pin in led_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# 設定感測器腳為輸入（上拉）
for pin in sensor_pins:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# 建立 LED 狀態（False 表示尚未亮）
led_states = [False] * 8

try:
    while True:
        for i in range(8):
            if GPIO.input(sensor_pins[i]) == GPIO.LOW:  # 感測器被觸發（按下）
                if not led_states[i]:
                    GPIO.output(led_pins[i], GPIO.HIGH)
                    led_states[i] = True  # 更新狀態
        time.sleep(0.1)

except KeyboardInterrupt:
    print("結束程式，清除 GPIO")
    GPIO.cleanup()
