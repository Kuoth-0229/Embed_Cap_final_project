import RPi.GPIO as GPIO
import time

# 設定 GPIO 腳位
CLK = 3
DIO = 5

GPIO.setmode(GPIO.BOARD)
GPIO.setup(CLK, GPIO.OUT)
GPIO.setup(DIO, GPIO.OUT)

# 七段顯示對應的位元資料（共陰極）
SEGMENTS = {
    0: 0x3f,
    1: 0x06,
    2: 0x5b,
    3: 0x4f,
    4: 0x66,
    5: 0x6d,
    6: 0x7d,
    7: 0x07,
    8: 0x7f,
    9: 0x6f,
    ' ': 0x00
}

def start():
    GPIO.output(CLK, GPIO.HIGH)
    GPIO.output(DIO, GPIO.HIGH)
    time.sleep(0.001)
    GPIO.output(DIO, GPIO.LOW)

def stop():
    GPIO.output(CLK, GPIO.LOW)
    GPIO.output(DIO, GPIO.LOW)
    time.sleep(0.001)
    GPIO.output(CLK, GPIO.HIGH)
    GPIO.output(DIO, GPIO.HIGH)

def write_byte(data):
    for i in range(8):
        GPIO.output(CLK, GPIO.LOW)
        GPIO.output(DIO, data & 1)
        data >>= 1
        GPIO.output(CLK, GPIO.HIGH)

    # 等待 ACK（這裡簡單處理）
    GPIO.output(CLK, GPIO.LOW)
    GPIO.output(DIO, GPIO.HIGH)
    GPIO.output(CLK, GPIO.HIGH)
    GPIO.output(CLK, GPIO.LOW)

def display_digits(digits):
    # 启动
    start()
    write_byte(0x40)  # 設定自動地址遞增模式
    stop()

    # 設定開始地址 0xC0
    start()
    write_byte(0xC0)
    for digit in digits:
        write_byte(SEGMENTS.get(digit, 0x00))
    stop()

    # 設定顯示控制（開啟顯示+亮度最大）
    start()
    write_byte(0x88 | 0x07)
    stop()

try:
    while True:
        # 顯示數字：1 2 3 4
        display_digits([1, 2, 3, 4])
        time.sleep(1)

        # 顯示空白
        display_digits([' ', ' ', ' ', ' '])
        time.sleep(1)

except KeyboardInterrupt:
    print("清理 GPIO")
    GPIO.cleanup()
