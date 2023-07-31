import time
from jetbot import Robot

robot = Robot()
robot.forward(0.6)
print("Forward")
time.sleep(3)
robot.backward(0.4)
print("Backward")
time.sleep(3)
robot.left(0.6)
print("Left")
time.sleep(3)
robot.right(0.6)
print("Right")
time.sleep(3)
robot.right(-0.4)
print("Right, but negative")
time.sleep(3)
