import RPi.GPIO as GPIO
import time

# 設定 GPIO 模式為 BCM
GPIO.setmode(GPIO.BCM)

# SG90 控制腳位（可以換成你想用的）
servo_pin = 17

# 設定腳位為輸出
GPIO.setup(servo_pin, GPIO.OUT)

# 建立 PWM 物件，頻率 50Hz（SG90 標準）
pwm = GPIO.PWM(servo_pin, 50)
pwm.start(0)  # 初始角度為 0

def set_angle(angle):
    # SG90 通常對應 0~180 度 → 2~12.5% duty cycle
    duty = 2 + (angle / 18)
    GPIO.output(servo_pin, True)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    GPIO.output(servo_pin, False)
    pwm.ChangeDutyCycle(0)

try:
    while True:
        for angle in [0, 90]:
            print(f"Setting angle: {angle}")
            set_angle(angle)
            time.sleep(1)

except KeyboardInterrupt:
    print("退出中...")
    pwm.stop()
    GPIO.cleanup()
