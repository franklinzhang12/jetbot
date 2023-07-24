# Take images on the JetBot with a single camera
# Press ENTER in the terminal while running to save images

import sys
sys.path.insert(1,'/home/jetbot/jetbot/')

import jetson.utils
import argparse
import numpy as np
import os
from jetbot import Robot

import sys
import inputs

import threading
import time

# Set these
DATASET_PATH = './jetbotImg'  # Location to save images (must be created already)
IP = '216.96.192.108'  # IP address of device receiving image over GStreamer

robot = Robot()
pads = inputs.devices.gamepads
num = 0
final_image = None

def save_image(num, image):
    jetson.utils.saveImageRGBA('./image{}.jpg'.format(num), image)

def stream_camera():

    global image1

    # create display window
    display = jetson.utils.videoOutput("rtp://{}:1234".format(IP), argv=sys.argv + is_headless)

    # create camera device
    camera1 = jetson.utils.videoSource("csi://0", argv=sys.argv)
    # camera2 = jetson.utils.videoSource("csi://1", argv=sys.argv)

    while True:
        image1 = camera1.Capture()
        # image2 = camera2.Capture()

        # new_width = image1.width + image2.width
        # new_height=max(image1.height, image2.height)

        # # allocate the output image, with dimensions to fit both inputs side-by-side
        # final_image = jetson.utils.cudaAllocMapped(width=new_width, height=new_height, format="rgb8")

        # # compost the two images (the last two arguments are x,y coordinates in the output image)
        # jetson.utils.cudaOverlay(image1, final_image, 0, 0)
        # jetson.utils.cudaOverlay(image2, final_image, image1.width, 0)

        # final_image = jetson.utils.cudaAllocMapped(width=image1.width, height=image1.height, format="rgb8")

        display.Render(image1)

        if not (camera1.IsStreaming()): #or not display.IsStreaming():
            break

def control_motors():

    global robot
    global pads
    global image1
    global num 

    if len(pads) == 0:
        raise Exception("Couldn't find any Gamepads!")
    
    print('Press ENTER to capture image:' )
    while True:        
        capture = input()
        if capture == '':
            save_image(num, image1)
            num += 1
		# Optionally, comment out the 4 lines above, and uncomment the lines below
		# That will enable use of the gamepad controller
#         # events = inputs.get_gamepad()
#         for event in events:
# 
#             if event.code == 'BTN_TR' and event.state == 1:
#                 save_image(num, image1)
#                 num += 1
 
if __name__ == '__main__':

    try:

        filecount = 0
        
        try:
            os.makedirs(DATASET_PATH)
            os.chdir(DATASET_PATH)
            print('[ACTION] Make directory: ', DATASET_PATH)
        except FileExistsError:
            os.chdir(DATASET_PATH)
            print('[WARNING] Directories not created because they already exist')

        # parse the command line

        parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,epilog=jetson.utils.videoSource.Usage() + jetson.utils.videoOutput.Usage() + jetson.utils.logUsage())
        parser.add_argument("output_URI", type=str, default="", nargs='?', help="URI of the output stream")
        parser.add_argument("--width", type=int, default=640, help="desired width of camera stream (default is 1280 pixels)")
        parser.add_argument("--height", type=int, default=360, help="desired height of camera stream (default is 720 pixels)")
        parser.add_argument("--camera", type=str, default="0", help="index of the MIPI CSI camera to use (NULL for CSI camera 0), or for VL42 cameras the /dev/video node to use (e.g. /dev/video0).  By default, MIPI CSI camera 0 will be used.")
        parser.add_argument('--headless', action='store_true', default=(), help="run without display")

        is_headless = ["--headless"] if sys.argv[0].find('console.py') != -1 else [""]

        try:
            opt = parser.parse_args()
            print(opt)
        except:
            print("")
            parser.print_help()

        for path in os.listdir('./'):
            if os.path.isfile(os.path.join('./', path)):
                filecount += 1

        num = filecount

        capture = threading.Thread(target=stream_camera, args=())
        controls = threading.Thread(target=control_motors, args=())

        capture.start()
        controls.start()
    
    except KeyboardInterrupt:
        print('Program Ended')

	
