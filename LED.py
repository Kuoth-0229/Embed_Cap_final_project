import RPi.GPIO as GPIO
import time
# 使用 BOARD 編號模式
GPIO.setmode(GPIO.BOARD)

# 8 個 LED 對應的 GPIO 腳位 1 to 8
led_pins = [22, 24, 26, 32, 18, 36, 38, 40]
# 初始化 GPIO 腳位為輸出並設為 LOW（關閉 LED）
for pin in led_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

print("開始閃爍 LED（按 Ctrl+C 停止）")
try:
    while True:
        # 全部 LED 亮
        for pin in led_pins:
            GPIO.output(pin, GPIO.HIGH)
        time.sleep(1)

        # 全部 LED 滅
        for pin in led_pins:
            GPIO.output(pin, GPIO.LOW)
        time.sleep(1)

except KeyboardInterrupt:
    print("\n結束程序，清理 GPIO")
    GPIO.cleanup()
