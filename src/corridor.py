import sys
sys.path.insert(1, '/home/jetbot/jetbot/')
 
import jetson.inference
import jetson.utils
import argparse

import os
import keyboard
import time
import datetime
import inputs

from jetbot import Robot
#robot = Robot(left_multiplier=0.95)
robot = Robot()

max_speed = 1

if __name__ == '__main__':

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
    sign_net = jetson.inference.detectNet(argv=['--threshold=0.8', '--model=/home/jetbot/jetbot/models/full-signs.onnx', '--labels=/home/jetbot/jetbot/models/sign-labels.txt', '--input-blob=input_0', '--output-cvg=scores', '--output-bbox=boxes'] )
    
    # load the recognition network (classification models)
    class_net = jetson.inference.imageNet(opt.network, argv=['--model=/home/jetbot/jetbot/models/corridor_final1.onnx', '--labels=/home/jetbot/jetbot/models/corridorLabels.txt', '--input-blob=input_0', '--output-blob=output_0'])
    
    # create video sources & outputs
    camera1 = jetson.utils.videoSource("csi://0", argv=sys.argv)

    # display = jetson.utils.videoOutput("display://0", argv=sys.argv + is_headless)

    #### ADJUST IP ADDRESS to match the laptop's here
    display = jetson.utils.videoOutput("rtp://216.96.231.106:1234", argv=sys.argv + is_headless)

    font = jetson.utils.cudaFont()
    
    forward = True
    
    while True:
        # capture the next image
        image1 = camera1.Capture()
        img_area = image1.width * image1.height
        
        state = "classify"

        # check if there is any sign detected
        signs = sign_net.Detect(image1, overlay=opt.overlay)
        
        # check the size of the detected sign, ignore the large sign
        for sign in signs:
            if sign.Area < img_area/12:
                state = "detect"
        
        # if there is no sign detected
        if state == "classify":
            class_id, confidence = class_net.Classify(image1)
            class_desc = class_net.GetClassDesc(class_id)
            
            if confidence > 0.4:                
                # overlay the result on the image
                font.OverlayText(image1, image1.width, image1.height, "{:05.2f}% {:s}".format(confidence * 100, class_desc), 5, 5, font.White, font.Gray40)

                # check if it is a return journey, reverse left and right
                if forward == False:
                    if class_id == 0:
                        class_id = 1
                    elif class_id == 1:
                        class_id = 0

                # When the Jetbot is facing straight, go straight
                if class_id == 2:
                    print("Straight")
                    robot.set_motors(0.60 * max_speed, 0.60 * max_speed)
                    time.sleep(0.5)

                # When the Jetbot is facing left, turn right
                elif class_id == 0:
                    print ("Facing Left")
                    robot.set_motors(0.80 * max_speed, 0.40 * max_speed)
                    time.sleep(0.5)

                # When the Jetbot is facing right, turn left
                elif class_id == 1:
                    print ("Facing right")
                    robot.set_motors(0.40 * max_speed, 0.80 * max_speed)  
                    time.sleep(0.5)                           
         
        # if there is a detected sign       
        elif state == "detect":
            for sign in signs:
                # turn depending on what sign is detected

                    # left turn
                    if sign.ClassID == 1:
                        print("LEFT")
                        robot.set_motors(0.20 * max_speed, 0.90 * max_speed)
                        time.sleep(1)
                        robot.stop()
                     
                    # right turn     
                    elif sign.ClassID == 2:
                        print("RIGHT")
                        robot.set_motors(0.90 * max_speed, 0.2 * max_speed)
                        time.sleep(1)
                        robot.stop()
                    
                    # U-turn    
                    elif sign.ClassID == 3:
                        print("U-TURN")
                        robot.set_motors(0.20 * max_speed, 0.90 * max_speed)
                        time.sleep(2)
                        robot.stop()
                        # after the U-turn, it will be a return journey
                        forward = False

        # displaying the image
        # render the image
        display.Render(image1)
        
        if keyboard.is_pressed('q'):
            print('Stop')
            break
    
        # exit on input/output end of stream
        if not camera1.IsStreaming() or not display.IsStreaming():
            break
