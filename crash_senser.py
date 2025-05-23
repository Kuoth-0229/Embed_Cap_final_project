import RPi.GPIO as GPIO
import time

INPUT_PIN = 3

GPIO.setmode(GPIO.BOARD)
GPIO.setup(INPUT_PIN, GPIO.IN)

blink_delay = 0.0001

try:
    while (GPIO.input(INPUT_PIN)):

        # if blink_delay:
        #     GPIO.output(INPUT_PIN, GPIO.HIGH)
        #     print (INPUT_PIN)
        #     time.sleep(blink_delay)
        #     GPIO.output(INPUT_PIN, GPIO.LOW)
        #     time.sleep(blink_delay)
        # else:
        #     GPIO.output(LED_PIN, GPIO.LOW)
        #     time.sleep(0.5)  # 無需閃爍時，每0.5秒重新測量一次
        # print (GPIO.input(INPUT_PIN))
        print ("timer")
        time.sleep(blink_delay)


        

except KeyboardInterrupt:
    print("Exception: KeyboardInterrupt")

finally:
    GPIO.cleanup()
