
import sys
sys.path.insert(1, '/home/jetbot/jetbot/')
 
print("baa")
import jetson.inference
import jetson.utils
import argparse

import torch
from torch2trt import TRTModule
import torchvision.transforms as transforms
import torch.nn.functional as F

import cv2
import PIL.Image
import numpy as np

import os
import keyboard
import time
import datetime
import inputs
import threading

from operator import attrgetter

#from jetbot import Robot
from robot_gpio import Robot
#robot = Robot(left_multiplier=0.95)
robot = Robot()

max_speed = 0.8

def fractional_coord(bbox, dir, frac):
    """Find location that's a fraction of the way right/down the bounding box"""
    if dir == "x":
        return bbox.Left + frac * (bbox.Right - bbox.Left)
    elif dir == "y":
        return bbox.Top + frac * (bbox.Bottom - bbox.Top)

def rl_follow_dir(rl, conditions=True, offset=0, sharpness = 1.5):
    """Follow a given green line (rl)
    offset_percent: a small decimal indicating how far off center the robot should follow,
        relevant for turning"""
    # Sometimes (when road following), the robot only cares about green lines at the bottom of the image.
    if conditions:
        far_left = rl.Right < image1.width / 2.5
        far_right = rl.Left > 1.5 * image1.width / 2.5
        near_center = not (far_left or far_right)  # near center in the x direction, not necessarily in y
        near_bottom = rl.Bottom > 6 * image1.height / 7
        short = rl.Bottom - rl.Top < image1.height / 6
    if not conditions or ((near_center or not short) and near_bottom):
        # print(rl.Left, rl.Right)

        # Adjust if the line is fully on one side.
        # Otherwise, continue straight.
        center = image1.width / 2 - offset * image1.width / 2
        epsilon = image1.width / 20
        line_center = (rl.Left + rl.Right) / 2
        if rl.Left > center - epsilon or line_center > 2 * image1.width / 3:
            robot.set_motors(0.4 * max_speed, 0.2 * max_speed)
        elif rl.Right < center + epsilon or line_center < image1.width / 3:
            robot.set_motors(0.2 * max_speed, 0.4 * max_speed)
        else:
            robot.set_motors(0.45 * max_speed, 0.45 * max_speed)
        return True
    else:
        return False

def sort_lines(lines, num_labels):
    """Sort lines by given labels into arrays
    lines: list of lines
    labels: list of labels"""

    sorted_lines = [[] for i in range(num_labels)]
    for rl in lines:
        sorted_lines[rl.ClassID - 1].append(rl)
    
    return tuple(sorted_lines)


if __name__ == '__main__':
    print("BA")

    parser = argparse.ArgumentParser(description="Classify a live camera stream using an image recognition DNN.",
                                        formatter_class=argparse.RawTextHelpFormatter,
                                        epilog=jetson.inference.imageNet.Usage() +
                                                jetson.utils.videoSource.Usage() + jetson.utils.videoOutput.Usage() + jetson.utils.logUsage())
    parser.add_argument("input_URI", type=str, default="", nargs='?', help="URI of the input stream")
    parser.add_argument("output_URI", type=str, default="", nargs='?', help="URI of the output stream")
    parser.add_argument("--network", type=str, default="resnet18",
                        help="pre-trained model to load (see below for options)")
    parser.add_argument("--overlay", type=str, default="box,labels,conf", help="detection overlay flags (e.g. --overlay=box,labels,conf)\nvalid combinations are:  'box', 'labels', 'conf', 'none'")
    parser.add_argument("--threshold", type=float, default=0.5, help="minimum detection threshold to use") 
    parser.add_argument("--camera", type=str, default="0",
                        help="index of the MIPI CSI camera to use (e.g. CSI camera 0)\nor for VL42 cameras, the /dev/video device to use.\nby default, MIPI CSI camera 0 will be used.")
    parser.add_argument("--width", type=int, default=640, help="desired width of camera stream (default is 1280 pixels)")
    parser.add_argument("--height", type=int, default=720, help="desired height of camera stream (default is 720 pixels)")
    parser.add_argument('--headless', action='store_true', default=(), help="run without display")

    # For rtp streaming
    is_headless = ["--headless"] if sys.argv[0].find('console.py') != -1 else [""]
    
    try:
        opt = parser.parse_known_args()[0]
    except:
        print("")
        parser.print_help()
        sys.exit(0)

    # load the recognition network (object detection models)
    # intersection_net = jetson.inference.detectNet(argv=['--model=/home/jetbot/jetbot/models/intersect.onnx', '--labels=/home/jetbot/jetbot/models/intersection-labels.txt', '--input-blob=input_0', '--output-cvg=scores', '--output-bbox=boxes', '--threshold=0.3'])
    sign_net = jetson.inference.detectNet(argv=['--threshold=0.8', '--model=/home/jetbot/jetbot/models/full-signs.onnx', '--labels=/home/jetbot/jetbot/models/sign-labels.txt', '--input-blob=input_0', '--output-cvg=scores', '--output-bbox=boxes'] )
    # rf_net = jetson.inference.detectNet(argv=['--model=/home/jetbot/jetbot/models-2/green-line.onnx', '--labels=/home/jetbot/jetbot/models-2/green-line-labels.txt', '--input-blob=input_0', '--output-cvg=scores', '--output-bbox=boxes'] )
    line_net = jetson.inference.detectNet(argv=['--threshold=0.2', '--model=/home/jetbot/jetbot/models/orange-green-lines.onnx', '--labels=/home/jetbot/jetbot/models/orange-green-labels.txt', '--input-blob=input_0', '--output-cvg=scores', '--output-bbox=boxes'] )
    high_line_net = jetson.inference.detectNet(argv=['--threshold=0.3', '--model=/home/jetbot/jetbot/models/orange-green-lines.onnx', '--labels=/home/jetbot/jetbot/models/orange-green-labels.txt', '--input-blob=input_0', '--output-cvg=scores', '--output-bbox=boxes'] )

    # create video sources & outputs
    camera1 = jetson.utils.videoSource("csi://0", argv=sys.argv)

    #display = jetson.utils.videoOutput("display://0", argv=sys.argv + is_headless)

    #### ADJUST IP ADDRESS to match the laptop's here
    display = jetson.utils.videoOutput("rtp://10.131.132.162:1234", argv=sys.argv + is_headless)
    print("ba")

    font = jetson.utils.cudaFont()

    state = "rf" # The robot starts with road following.
    strikes = 0

    # process frames until the user exits
    while True:
        # capture the next image
        image1 = camera1.Capture()
        
        img_area = image1.width * image1.height
        
        ###### ROAD FOLLOWING AND SIGN DETECTION #######
        # At any given time, the robot will be focused on either
        # road following or responding to signs.
        # These are represented by different "states."
        # Motor values are part hardcoded and part dynamically adjusted.

        if state == "rf":
            # Look for road line. 
            road_lines = high_line_net.Detect(image1, overlay=opt.overlay)
            appropriate_line = False
            for rl in road_lines:
                if rl_follow_dir(rl):
                    appropriate_line = True
            if not appropriate_line:
                strikes += 1
                if strikes % 4 == 0:
                    robot.set_motors(0.3 * max_speed, -0.3 * max_speed)
                    time.sleep(0.2)
                elif strikes % 4 == 1:
                    robot.set_motors(-0.3 * max_speed, 0.3 * max_speed)
                    time.sleep(0.2)
                robot.stop()
                time.sleep(0.2)
                # if dir == "R":
                #     robot.set_motors(0.75 * max_speed, 0.5 * max_speed)
                # elif dir == "L":
                #     robot.set_motors(0.5 * max_speed, 0.75 * max_speed)
                # elif dir == "S":
                #     robot.set_motors(0.75 * max_speed, 0.75 * max_speed)
            if strikes == 10:
                # After the robot fails to detect any road lines many frames in a row,
                # stop and look for signs.
                state = "signs"
                strikes = 0
                robot.stop()
        elif state == "signs":
            # Look for signs.
            signs = sign_net.Detect(image1, overlay=opt.overlay)
            if len(signs) == 0:
                strikes += 1
                if strikes == 3:
                    # After the robot fails to detect any signs 3 frames in a row,
                    # proceed straight forward, then stop and look for the road.
                    print("STRAIGHT")
                    #robot.set_motors(0.4 * max_speed, 0.4 * max_speed)
                    #time.sleep(7.5 * 0.2 / max_speed)
                    state = "straight"
                    #state = "rf"
                    #print("RF")
                    robot.stop()
            else:
                strikes = 0
                for sign in signs:
                    # The robot may see other signs, but it only cares about the
                    # the right side of the image - that's where the sign is placed.
                    if sign.Left > image1.width/2 and sign.Area > img_area / 50:
                        # Turn depending on what sign is detected,
                        # then stop and look for the road.
                        if sign.ClassID == 1:
                            # Turn left a little bit, then start looking for the
                            # correct green line (new state).
                            state = "left-turn"
                            print("LEFT")
                            robot.set_motors(0.40 * max_speed, 0.8*max_speed)
                            time.sleep(2.9 * 0.2 / max_speed)
                            # robot.set_motors(0.17, 0.2)
                            # time.sleep(3.3)
                            robot.stop()
                            # state = "rf"
                        elif sign.ClassID == 2:
                            state = "right-turn"
                            print("RIGHT")
                            robot.set_motors(0.70 * max_speed, -0.30 * max_speed)
                            time.sleep(0.5)
                            robot.stop()
                            # robot.set_motors(0.50 * max_speed, 0.50 * max_speed)
                            # time.sleep(0.4)
                            # robot.set_motors(0.19, 0.13)
                            # time.sleep(0.7)
                            # robot.stop()
                            # state = "rf"
                        elif sign.ClassID == 3:
                            state = "u-turn-finish"
                            print("U-TURN")
                            robot.set_motors(0.2 * max_speed, 0.9*max_speed)
                            time.sleep(1.2 / max_speed)
                            #robot.set_motors(-0.4 * max_speed, -0.4*max_speed)
                            #time.sleep(2.5* 0.5 / max_speed)
                            #robot.set_motors(0.40 * max_speed, 1.0*max_speed)
                            #time.sleep(4 * 0.4 / max_speed)
                            robot.stop()
                            # state = "rf"
        elif state == "straight":
            # Straight is still hard coded -- this is not complete
            road_lines = line_net.Detect(image1, overlay=opt.overlay)

            best_green_line = None
            green_lines, orange_lines = sort_lines(road_lines, 2)

            # Check if it's time to be done turning (when orange lines insignificant)
            if len(orange_lines) == 0 or (len(orange_lines) == 1 and orange_lines[0].Area < img_area / 200):
                state = "rf"
                print("RF")
                robot.set_motors(0.3 * max_speed, 0.3 * max_speed)
                time.sleep(1 / max_speed)

            final_green_candidates = []
            for gl in green_lines:
                above_orange = False
                far_right = False
                far_left = False
                for ol in orange_lines:
                    # good green lines are not largely above an orange line
                    if fractional_coord(gl, "x", 0.75) < ol.Right and fractional_coord(gl, "x", 0.25) > ol.Left:
                        above_orange = True
                    # if the above isn't disqualifying already,
                    # good green lines do not have their center on the right half
                    elif fractional_coord(gl, "x", 0.5) > 3*image1.width/4:
                        far_right = True
                    elif fractional_coord(gl, "x", 0.5) < image1.width/4:
                        far_left = True
                if not above_orange and not far_right:
                    final_green_candidates.append(gl)

            if len(final_green_candidates) > 0:
                # if there are still multiple lines, follow the top-most one
                best_green_line = max(final_green_candidates, key=attrgetter("Top"))
                rl_follow_dir(best_green_line, conditions=False, offset=0.4)
            else:
                robot.set_motors(0.3 * max_speed, 0.3 * max_speed)
                time.sleep(0.2)
                robot.stop()
            
        elif state == "left-turn":
            road_lines = line_net.Detect(image1, overlay=opt.overlay)

            best_green_line = None
            green_lines, orange_lines = sort_lines(road_lines, 2)

            # Check if it's time to be done turning (when orange lines insignificant)
            if len(orange_lines) == 0 or (len(orange_lines) == 1 and orange_lines[0].Area < img_area / 200):
                state = "rf"
                print("RF")
                robot.set_motors(0.3 * max_speed, 0.4 * max_speed)
                time.sleep(1 / max_speed)
            
            # find_best_line([green_lines, orange_lines], [
            #     (fractional_coord(gl, "x", 0.75) < ol.Right, "strict"),
            #     (fractional_coord(gl, "x", 0.25) > ol.Left, "strict"),
            #     (fractional_coord(gl, "x", 0.5) > image1.width/2, "strict"),
            #     ("Right", "max_attr")
            # ])
            
            # this for loop doesn't work because gl.Intersects doesn't exist
            #for ol in orange_lines:
                # remove anything that overlaps with the yellow line
                #left_green_lines = [gl for gl in left_green_lines if not gl.Intersects(ol, areaThreshold=0.15f)]
            final_green_candidates = []
            for gl in green_lines:
                above_orange = False
                far_right = False
                for ol in orange_lines:
                    # good green lines are not largely above an orange line
                    if fractional_coord(gl, "x", 0.75) < ol.Right and fractional_coord(gl, "x", 0.25) > ol.Left:
                        above_orange = True
                    # if the above isn't disqualifying already,
                    # good green lines do not have their center on the right half
                    elif fractional_coord(gl, "x", 0.5) > image1.width/2:
                        far_right = True
                if not above_orange and not far_right:
                    final_green_candidates.append(gl)
            
            if len(final_green_candidates) > 0:
                # if there are still multiple lines, follow the rightmost one
                best_green_line = max(final_green_candidates, key=attrgetter('Right'))    
                rl_follow_dir(best_green_line, conditions=False, offset=-0.1)
            else:
                robot.set_motors(0.3 * max_speed, 0.5 * max_speed)
                time.sleep(0.2)
                robot.stop()

        elif state == "right-turn":
            road_lines = line_net.Detect(image1, overlay=opt.overlay)

            best_green_line = None
            green_lines, orange_lines = sort_lines(road_lines, 2)

            # Check if it's time to be done turning (when orange lines insignificant)
            if len(orange_lines) == 0 or (len(orange_lines) == 1 and orange_lines[0].Area < img_area / 200):
                state = "rf"
                print("RF")

            final_green_candidates = []
            for gl in green_lines:
                #above_orange = False
                far_left = False
                for ol in orange_lines:
                    # # good green lines are not largely above an orange line
                    # if fractional_coord(gl, "x", 0.75) < ol.Right and fractional_coord(gl, "x", 0.25) > ol.Left:
                    #     above_orange = True
                    # if the above isn't disqualifying already,
                    # good green lines do not have their center on the right half
                    if fractional_coord(gl, "x", 0.5) < image1.width/2:
                        far_left = True
                if not far_left:
                    final_green_candidates.append(gl)

            if len(final_green_candidates) > 0:
                # if there are still multiple lines, follow the bottom-most one
                best_green_line = max(final_green_candidates, key=attrgetter("Bottom"))
                rl_follow_dir(best_green_line, conditions=False, offset=0.4)
            else:
                robot.set_motors(0.5 * max_speed, 0.3 * max_speed)
                time.sleep(0.3)
                robot.stop()

        elif state == "u-turn":
            robot.set_motors(0.5 * max_speed, 1.0*max_speed)
            time.sleep(2.5 * 0.4 / max_speed)
            robot.stop()
            time.sleep(0.2)
            for i in range(8):
                road_lines = high_line_net.Detect(image1, overlay=opt.overlay)
                if len(road_lines) > 0:
                    state = "u-turn-finish"
                    print("u-turn-finish")
            #for rl in road_lines:
            #    if rl_follow_dir(rl):
            #        state = "rf"
            #        print("RF")
            robot.set_motors(-0.4 * max_speed, -0.4*max_speed)
            time.sleep(1.3* 0.5 / max_speed)
            robot.stop()
            time.sleep(0.2)
            print("u-turn")
        elif state == "u-turn-finish":
            road_lines = line_net.Detect(image1, overlay=opt.overlay)

            best_green_line = None
            green_lines, orange_lines = sort_lines(road_lines, 2)

            if len(green_lines) == 1:
                best_green_line = green_lines[0]
            elif len(green_lines) > 1:
                best_green_line = max(green_lines, key=attrgetter("Area"))

            if best_green_line is not None:
                rl_follow_dir(best_green_line, conditions=False, offset=-0.2)
                if best_green_line.Bottom > 6 * image1.height / 7 and best_green_line.Height > image1.height / 2:
                    state = "rf"
                    print("RF")
                    

        #displaying the image
        # render the image
        display.Render(image1)

        # print out performance info
        #collision_net.PrintProfilerTimes()
        #intersection_net.PrintProfilerTimes()
        #detect_net.PrintProfilerTimes()
        
        if keyboard.is_pressed('q'):
            print('Stop')
            break
        # exit on input/output end of stream
        if not camera1.IsStreaming() or not display.IsStreaming():
            break
