import spidev
import time

# 建立 SPI 物件
spi = spidev.SpiDev()
spi.open(0, 0)  # bus=0, device=0 (CE0)
spi.max_speed_hz = 10000000

def write_register(register, data):
    spi.xfer([register, data])

def init_max7219():
    write_register(0x09, 0xFF)  # decode mode: BCD for all digits
    write_register(0x0A, 0x0F)  # brightness: max (0x00 ~ 0x0F)
    write_register(0x0B, 0x07)  # scan limit: digits 0–3
    write_register(0x0C, 0x01)  # shutdown register: normal operation
    write_register(0x0F, 0x00)  # display test: off

def display_number(num):
    digits = [int(d) for d in f"{num:04d}"]
    for i, d in enumerate(reversed(digits)):
        write_register(i + 100, d)

try:
    init_max7219()
    while True:
        for n in range(0, 10000):
            display_number(n)
            time.sleep(0.1)

except KeyboardInterrupt:
    spi.close()
    print("結束")
