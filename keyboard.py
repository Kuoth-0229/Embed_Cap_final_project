import RPi.GPIO as GPIO
import time

# 使用實體腳位（BOARD 模式）
GPIO.setmode(GPIO.BOARD)

# 定義列（Rows）和行（Cols）接的實體腳位編號
ROWS = [29, 31, 33, 35]  # 對應原本 BCM: 5, 6, 13, 19
COLS = [32, 36, 38, 40]  # 對應原本 BCM: 12, 16, 20, 21

KEYS = [
    ['1','2','3','A'],
    ['4','5','6','B'],
    ['7','8','9','C'],
    ['*','0','#','D']
]

# 設定 GPIO
for row in ROWS:
    GPIO.setup(row, GPIO.IN, pull_up_down=GPIO.PUD_UP)

for col in COLS:
    GPIO.setup(col, GPIO.OUT)
    GPIO.output(col, GPIO.HIGH)

try:
    print("請按鍵盤上的任意按鍵...")
    while True:
        for col_idx, col in enumerate(COLS):
            GPIO.output(col, GPIO.LOW)
            for row_idx, row in enumerate(ROWS):
                if GPIO.input(row) == GPIO.LOW:
                    print(f"你按下的是: {KEYS[row_idx][col_idx]}")
                    while GPIO.input(row) == GPIO.LOW:
                        time.sleep(0.1)  # 等待放開
            GPIO.output(col, GPIO.HIGH)
        time.sleep(0.05)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("程式結束")
