# -*- coding: utf-8 -*-

import sys
sys.path.insert(1, '/home/jetbot/jetbot')

import inputs
from jetbot import Robot

robot = Robot()

pads = inputs.devices.gamepads
left_spd, right_spd = 0, 0

if __name__ == "__main__":
    
    MAX_SPD = 0.8

    if len(pads) == 0:
        raise Exception("[ERROR] Couldn't find any Gamepads! Program TERMINATED!\n")

    print("[SUCCESS] Program STARTED ...")

    while True:
        events = inputs.get_gamepad()
        for event in events:
            print(event.code, event.state)
            if event.code == 'ABS_Y':
                state = event.state - 128
                if state < 0:
                   left_spd = ( state / 127 ) / 2
                   left_spd = max (left_spd, MAX_SPD*-1) - 0.01
                elif state > 0:
                   left_spd = ( state / 128 ) / 2
                   left_spd = min (left_spd, MAX_SPD) + 0.01
                else:
                    left_spd = 0
            if event.code == 'ABS_RZ':
                state = event.state - 128
                if state < 0:
                    right_spd = ( state / 127 ) / 2
                    right_spd = max (right_spd, MAX_SPD*-1)
                elif state > 0:
                    right_spd = ( state / 128 ) / 2
                    right_spd = min (right_spd, MAX_SPD)
                else:
                    right_spd = 0
            if event.code == 'BTN_TL' and event.state == 1:
                if left_spd >= 0 or right_spd >= 0:
                    left_spd == left_spd - 0.01
                    right_spd == right_spd - 0.01
                else:
                    left_spd == 0
                    right_spd == 0
            if event.code == 'BTN_TL2' and event.state == 1:
                left_spd = 0
                right_spd = 0
                robot.stop()
                continue
            if event.code == 'BTN_WEST' and event.state == 1:
                robot.stop()
                print('EXIT')
                break
            
            #print(left_spd*-1, right_spd*-1)
            robot.set_motors(left_spd*-1, right_spd*-1)

    print("[SUCCESS] Program TERMINATED ...")
            

    
        
