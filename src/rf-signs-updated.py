import sys
sys.path.insert(1, "/home/jetbot/jetbot/")
 
import jetson_inference
import jetson_utils
import argparse

import os
import keyboard
import time

from operator import attrgetter

from jetbot import Robot
robot = Robot()

IP = "10.131.132.162"
max_speed = 1.0

def fractional_coord(bbox, direction, frac):
    """Find location that's a fraction of the way right/down the bounding box"""
    if direction == "x":
        return bbox.Left + frac * (bbox.Right - bbox.Left)
    elif direction == "y":
        return bbox.Top + frac * (bbox.Bottom - bbox.Top)

def rl_follow_dir(rl, conditions=True, offset=0):
    """Follow a given green line (rl)
    offset: a small decimal indicating how far off center the robot should follow,
        relevant for turning"""
    # Sometimes (when road following), the robot only cares about green lines at the bottom of the image.
    if conditions:
        far_left = rl.Right < image1.width / 3.5 or (rl.Left < image1.width / 7 and rl.Right < image1.width * 0.6)
        far_right = rl.Left > 2.5 * image1.width / 3.5
        near_center = not (far_left or far_right)  # near center in the x direction, not necessarily in y
        near_bottom = rl.Bottom > 6 * image1.height / 7
        short = rl.Bottom - rl.Top < image1.height / 3
    if not conditions or ((near_center or not short) and near_bottom):
        # Adjust if the line is fully on one side.
        # Otherwise, continue straight.
        center = image1.width / 2 - offset * image1.width / 2
        epsilon = image1.width / 10
        line_center = (rl.Left + rl.Right) / 2
        if line_center > center + epsilon or rl.Left > center - epsilon / 2:
            robot.set_motors((0.5 + offset / 4) * max_speed, 0.3 * max_speed)
        elif line_center < center - epsilon or rl.Right < center + epsilon / 2:
            robot.set_motors(0.3 * max_speed, (0.5 - offset / 4) * max_speed)
        else:
            robot.set_motors(0.5 * max_speed, 0.5 * max_speed)
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

    parser = argparse.ArgumentParser(description="Classify a live camera stream using an image recognition DNN.",
                                        formatter_class=argparse.RawTextHelpFormatter,
                                        epilog=jetson_inference.imageNet.Usage() +
                                                jetson_utils.videoSource.Usage() + jetson_utils.videoOutput.Usage() + jetson_utils.logUsage())
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
    sign_net = jetson_inference.detectNet(argv=['--threshold=0.8', '--model=/home/jetbot/jetbot/models/full-signs.onnx', '--labels=/home/jetbot/jetbot/models/sign-labels.txt', '--input-blob=input_0', '--output-cvg=scores', '--output-bbox=boxes'] )
    # rf_net = jetson_inference.detectNet(argv=['--model=/home/jetbot/jetbot/models-2/green-line.onnx', '--labels=/home/jetbot/jetbot/models-2/green-line-labels.txt', '--input-blob=input_0', '--output-cvg=scores', '--output-bbox=boxes'] )
    line_net = jetson_inference.detectNet(argv=['--threshold=0.2', '--model=/home/jetbot/jetbot/models/orange-green-lines-100.onnx', '--labels=/home/jetbot/jetbot/models/orange-green-labels.txt', '--input-blob=input_0', '--output-cvg=scores', '--output-bbox=boxes'] )
    high_line_net = jetson_inference.detectNet(argv=['--threshold=0.3', '--model=/home/jetbot/jetbot/models/orange-green-lines-100.onnx', '--labels=/home/jetbot/jetbot/models/orange-green-labels.txt', '--input-blob=input_0', '--output-cvg=scores', '--output-bbox=boxes'] )

    # create video sources & outputs
    camera1 = jetson_utils.videoSource("csi://0", argv=sys.argv)

    #### ADJUST IP ADDRESS to match the laptop's here
    display = jetson_utils.videoOutput(f"rtp://{IP}:1234", argv=sys.argv + is_headless)

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
            road_lines.sort(key=attrgetter("Right"), reverse=True)
            appropriate_line = False
            for rl in road_lines:
                if not appropriate_line and rl_follow_dir(rl):
                    appropriate_line = True
            if not appropriate_line:
                strikes += 1
                if strikes % 4 == 0:
                    robot.set_motors(0.3 * max_speed, 0.3 * max_speed)
                    time.sleep(0.2)
                elif strikes % 4 == 1:
                    robot.set_motors(0.3 * max_speed, 0.3 * max_speed)
                    time.sleep(0.2)
                robot.stop()
                time.sleep(0.2)
            if strikes == 10:
                # After the robot fails to detect any road lines many frames in a row,
                # stop and look for signs.
                state = "signs"
                strikes = 0
                robot.stop()
        elif state == "signs":
            # Look for signs.
            signs = sign_net.Detect(image1, overlay=opt.overlay)
            valid_sign = False
            for sign in signs:
                # The robot may see other signs, but it only cares about sufficiently large signs
                # on the right side of the image - that's where the sign is placed.
                if sign.Right > image1.width / 2 and sign.Area > img_area / 50:
                    # Turn depending on what sign is detected,
                    # then stop and look for the road.
                    valid_sign = True
                    strikes = 0
                    if sign.ClassID == 1:
                        # Turn left a little bit, then start looking for the
                        # correct green line (new state).
                        state = "left-turn"
                        print("LEFT")
                        robot.set_motors(0.47 * max_speed, 0.7 * max_speed)
                        time.sleep(0.6 / max_speed)
                        robot.stop()
                    elif sign.ClassID == 2:
                        state = "right-turn"
                        print("RIGHT")
                        robot.set_motors(0.80 * max_speed, -0.30 * max_speed)
                        time.sleep(0.2 / max_speed)
                        robot.stop()
                    elif sign.ClassID == 3:
                        state = "u-turn-finish"
                        print("U-TURN")
                        robot.set_motors(0.2 * max_speed, 0.9 * max_speed)
                        time.sleep(0.7 / max_speed)
                        robot.stop()
            if len(signs) == 0 or not valid_sign:
                strikes += 1
                if strikes == 3:
                    # After the robot fails to detect any signs 3 frames in a row, proceed straight forward.
                    print("STRAIGHT")
                    robot.set_motors(0.50 * max_speed, 0.50 * max_speed)
                    time.sleep(0.8 / max_speed)
                    state = "straight"
                    strikes = 0
                    count = 0
                    robot.stop()
        elif state == "straight":
            road_lines = line_net.Detect(image1, overlay=opt.overlay)

            best_green_line = None
            green_lines, orange_lines = sort_lines(road_lines, 2)

            final_green_candidates = []
            for gl in green_lines:
                above_orange = False
                far_right = False
                far_left = False
                for ol in orange_lines:
                    # good green lines are not largely above an orange line
                    if fractional_coord(gl, "x", 0.75) < ol.Right and fractional_coord(gl, "x", 0.25) > ol.Left:
                        above_orange = True
                    if ol.Left > image1.width/2 and gl.Left > ol.Left and fractional_coord(gl, "y", 0.6) > ol.Top:
                        above_orange = True
                    # if the above isn't disqualifying already,
                    # good green lines do not have their center on the right half
                    elif fractional_coord(gl, "x", 0.5) > image1.width/2 and gl.Right > image1.width * 0.9:
                        far_right = True
                    #elif fractional_coord(gl, "x", 0.3) < image1.width/4:
                    elif gl.Left < image1.width/10:
                        far_left = True
                if not above_orange and not far_right and not far_left:
                    final_green_candidates.append(gl)

            if len(final_green_candidates) > 0:
                # if there are still multiple lines, follow the right-most one
                best_green_line = max(final_green_candidates, key=attrgetter("Right"))
                rl_follow_dir(best_green_line, conditions=False)
                if best_green_line.Bottom > 6 * image1.height / 7 and best_green_line.Right - best_green_line.Left < image1.width / 3:
                    state = "rf"
                    print("RF")
            else:
                count += 1
                if count % 4 == 0:
                    robot.set_motors(0.23 * max_speed, 0.39 * max_speed)
                elif count % 4 == 2:
                    robot.set_motors(0.39 * max_speed, 0.23 * max_speed)

                time.sleep(0.2)
                robot.stop()
            
        elif state == "left-turn":
            road_lines = line_net.Detect(image1, overlay=opt.overlay)

            best_green_line = None
            green_lines, orange_lines = sort_lines(road_lines, 2)
            
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
                best_green_line = max(final_green_candidates, key=attrgetter("Right"))    
                rl_follow_dir(best_green_line, conditions=False, offset=-0.1)
                if best_green_line.Bottom > 6 * image1.height / 7 and best_green_line.Right - best_green_line.Left < image1.width * 0.4 and best_green_line.Right > image1.width / 2:
                    state = "rf"
                    print("RF")
            else:
                robot.set_motors(0.36 * max_speed, 0.6 * max_speed)
                time.sleep(0.2)
                robot.stop()

        elif state == "right-turn":
            road_lines = line_net.Detect(image1, overlay=opt.overlay)

            best_green_line = None
            green_lines, orange_lines = sort_lines(road_lines, 2)

            final_green_candidates = []
            for gl in green_lines:
                #above_orange = False
                far_left = False
                for ol in orange_lines:
                    # good green lines do not have their center on the left half
                    if fractional_coord(gl, "x", 0.5) < image1.width/2:
                        far_left = True
                if not far_left:
                    final_green_candidates.append(gl)

            if len(final_green_candidates) > 0:
                # if there are still multiple lines, follow the bottom-most one
                best_green_line = max(final_green_candidates, key=attrgetter("Bottom"))
                rl_follow_dir(best_green_line, conditions=False, offset=0.4)
                if best_green_line.Bottom > 6 * image1.height / 7 and best_green_line.Right - best_green_line.Left < image1.width / 4 and best_green_line.Left < image1.width / 2:
                    state = "rf"
                    print("RF")
            else:
                robot.set_motors(0.6 * max_speed, 0.2 * max_speed)
                time.sleep(0.2)
                robot.stop()

        elif state == "u-turn-finish":
            road_lines = high_line_net.Detect(image1, overlay=opt.overlay)

            best_green_line = None
            green_lines, orange_lines = sort_lines(road_lines, 2)

            if len(green_lines) == 1:
                best_green_line = green_lines[0]
            elif len(green_lines) > 1:
                best_green_line = max(green_lines, key=attrgetter("Area"))

            
            if best_green_line is not None and rl_follow_dir(best_green_line, conditions=False, offset=-0.2) and best_green_line.Bottom > 6 * image1.height / 7 and best_green_line.Right - best_green_line.Left < image1.width * 0.6 and fractional_coord(best_green_line, "x", 0.5) > image1.width * 0.3 and fractional_coord(best_green_line, "x", 0.5) < image1.width * 0.7:
                    robot.set_motors(0.25 * max_speed, 0.8*max_speed)
                    time.sleep(0.2)
                    robot.stop()
                    time.sleep(0.1)
                    state = "rf"
                    print("RF")
            else:
                robot.set_motors(0.25 * max_speed, 0.9*max_speed)
                time.sleep(0.2)
                robot.stop()
                time.sleep(0.1)
                
        # render the image
        display.Render(image1)
        
        if keyboard.is_pressed('q'):
            print('Stop')
            break
        # exit on input/output end of stream
        if not camera1.IsStreaming() or not display.IsStreaming():
            break
