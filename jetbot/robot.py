import RPi.GPIO as GPIO
import atexit
GPIO.setmode(GPIO.BOARD)

class Robot():
    def __init__(self, left_multiplier=1, right_multiplier=1, IN1=22, IN2=32, IN3=23, IN4=33, PWM_freq=100, PWM_forward=False, max_speed=1):
        self.left_multiplier = left_multiplier
        self.right_multiplier = right_multiplier
        self.IN1 = IN1  # right
        self.IN2 = IN2  # right PWM
        self.IN3 = IN3  # left
        self.IN4 = IN4  # left PWM
        self.p_left = GPIO.PWM(IN4, PWM_freq)
        self.p_right = GPIO.PWM(IN2, PWM_freq)
        GPIO.setup(IN1, GPIO.OUT)
        GPIO.setup(IN3, GPIO.OUT)
        self.PWM_forward = PWM_forward    # Are PWM set to drive the motors forward or backward?
        self.max_speed = max_speed
        self.p_left.start(0)
        self.p_right.start(0)
        atexit.register(self.release)


    def release(self):
        print("Cleaning up...")
        self.p_left.stop()  # Turn off PWM signal
        self.p_right.stop()
        GPIO.output(self.IN1, GPIO.LOW)  # Turn off non-PWM signal
        GPIO.output(self.IN3, GPIO.LOW)
        GPIO.cleanup()


    def set_motors(self, left_velocity, right_velocity):
        self.set_left_motor(left_velocity)
        self.set_right_motor(right_velocity)


    def stop(self):
        self.p_left.ChangeDutyCycle(0)
        self.p_right.ChangeDutyCycle(0)
        GPIO.output(self.IN1, GPIO.LOW)
        GPIO.output(self.IN3, GPIO.LOW)


    def forward(self, speed=1.0):
        self.set_motors(speed, speed)


    def backward(self, speed=1.0):
        self.set_motors(-1 * speed, -1 * speed)


    def left(self, speed=1.0):
        self.set_motors(-1 * speed, speed)


    def right(self, speed=1.0):
        self.set_motors(speed, -1 * speed)


    def set_left_motor(self, left_velocity):
        mapped_vel = self.map_velocity(left_velocity) * self.left_multiplier
        if (self.PWM_forward and mapped_vel >= 0) or (not self.PWM_forward and mapped_vel <= 0):
            self.p_left.ChangeDutyCycle(abs(mapped_vel))
            GPIO.output(self.IN3, GPIO.LOW)
        else: 
            GPIO.output(self.IN3, GPIO.HIGH)
            if mapped_vel < 0:
                self.p_left.ChangeDutyCycle(100 + mapped_vel)
            else:
                self.p_left.ChangeDutyCycle(100 - mapped_vel)


    def set_right_motor(self, right_velocity):
        mapped_vel = self.map_velocity(right_velocity) * self.right_multiplier
        if (self.PWM_forward and mapped_vel >= 0) or (not self.PWM_forward and mapped_vel <= 0):
            self.p_right.ChangeDutyCycle(abs(mapped_vel))
            GPIO.output(self.IN1, GPIO.LOW)
        else: 
            GPIO.output(self.IN1, GPIO.HIGH)
            if mapped_vel < 0:
                self.p_right.ChangeDutyCycle(100 + mapped_vel)
            else:
                self.p_right.ChangeDutyCycle(100 - mapped_vel)


    def map_velocity(self, velocity):
        if velocity < -1 * self.max_speed or velocity > self.max_speed:
            raise ValueError('Speed must be between 0 and 100, inclusive')
        else:
            mapped_val = int(100.0 * velocity / self.max_speed)
            # speed = min(max(abs(mapped_val, 0), 100))
            return mapped_val

