import jetson.utils
import argparse
import numpy as np
import os

import sys

# SET THIS
IP = '10.131.132.162'  # IP address of device receiving image over GStreamer

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

num = 0
while os.path.isfile('video{}.mp4'.format(num)):
    num += 1

# create display window
display = jetson.utils.videoOutput("rtp://{}:1234".format(IP), argv=sys.argv + is_headless)
output = jetson.utils.videoOutput('video{}.mp4'.format(num), argv=sys.argv + is_headless)

# create camera device
camera1 = jetson.utils.videoSource("csi://0", argv=sys.argv)
camera2 = jetson.utils.videoSource("csi://1", argv=sys.argv)


# capture frames until user exits
while True:
	image1 = camera1.Capture()
	image2 = camera2.Capture()

	new_width = image1.width + image2.width
	new_height=max(image1.height, image2.height)
        
    # allocate the output image, with dimensions to fit both inputs side-by-side
	imgOutput = jetson.utils.cudaAllocMapped(width=new_width, height=new_height, format="rgb8")

	# compost the two images (the last two arguments are x,y coordinates in the output image)
	jetson.utils.cudaOverlay(image1, imgOutput, 0, 0)
	jetson.utils.cudaOverlay(image2, imgOutput, image1.width, 0)
	
	display.Render(imgOutput)
	output.Render(imgOutput)
	
	if not (camera1.IsStreaming() and camera2.IsStreaming()) or not display.IsStreaming():
		break
	
