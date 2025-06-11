import RPi.GPIO as GPIO
import time


CLK = 33
DIO = 35

GPIO.setmode(GPIO.BOARD)
GPIO.setup(CLK, GPIO.OUT)
GPIO.setup(DIO, GPIO.OUT)

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

    GPIO.output(CLK, GPIO.LOW)
    GPIO.output(DIO, GPIO.HIGH)
    GPIO.output(CLK, GPIO.HIGH)
    GPIO.output(CLK, GPIO.LOW)

def display_digits(digits):
    start()
    write_byte(0x40)
    stop()

    start()
    write_byte(0xC0)
    for digit in digits:
        write_byte(SEGMENTS.get(digit, 0x00))
    stop()

    start()
    write_byte(0x88 | 0x07)
    stop()

try:
    cur = 0
    while True:
        display_digits([cur, cur, cur, cur])
        time.sleep(1)
        cur = cur+1
        cur = cur%10
        display_digits([' ', ' ', ' ', ' '])
        time.sleep(1)

except KeyboardInterrupt:
    print("clean GPIO")
    GPIO.cleanup()
