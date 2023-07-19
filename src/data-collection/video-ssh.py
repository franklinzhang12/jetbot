# Take video on Jetson Nano, filter out blurry frames, and send them live over SSH to /tmp/test on a desired device
# Must specify target device username and IP, and make /tmp/test directory
# Must setup automatic SSH login from this device to target device: https://linuxize.com/post/how-to-setup-passwordless-ssh-login/

import jetson.utils
import argparse
import numpy as np
import cv2
import paramiko
from PIL import Image
from io import BytesIO
from pathlib import Path
import os

import sys

# Fill these two in
IP = 'ADD.IP.ADDRESS.HERE'
username = 'USERNAME'

def dirSetup(dirOut=None, logname='log.txt'):
    """Set up output directories, creating individual directories for thresholds and a logfile.

    Returns the name of the log file and the directories.

    Arguments:
    dirOut (string) - directory name containing output images (need not already exist), or None (auto-create)
    logname (string) - desired name of log file
    """
    frameDirs = []
    num = 0
    while os.path.exists('video{}.mp4'.format(num)) or os.path.exists('video{}'.format(num)):
        num += 1

    if dirOut is None:
        vidDir = './video' + str(num)
    else:
        vidDir = dirOut

    Path(vidDir).mkdir(exist_ok=True)

    logfile = open(vidDir + '/' + logname, 'a')
    logfile.write('-------------- NEW --------------\n')

    return vidDir, logfile, num


# From https://stackoverflow.com/a/19202764
# Login over ssh and write PIL image to dirname/filename
def put_file(machinename, username, dirname, filename, image):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(machinename, username=username)
    sftp = ssh.open_sftp()
    try:
        sftp.mkdir(dirname)
    except IOError:
        pass
    #print(dirname + '/' + filename)
    f = sftp.open(dirname + '/' + filename, 'w')
    #res = cv2.imencode('.jpg', image)[1]
    #print(type(res))
    #f.write(cv2.imencode('.jpg', image)[1])
    buf = BytesIO()
    image.save(buf, format="JPEG")

    f.write(buf.getbuffer())
    f.close()
    ssh.close()


# parse the command line
parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,epilog=jetson.utils.videoSource.Usage() + jetson.utils.videoOutput.Usage() + jetson.utils.logUsage())
#parser.add_argument("output_URI", type=str, default="", nargs='?', help="URI of the output stream")
parser.add_argument("--width", type=int, default=640, help="desired width of camera stream (default is 1280 pixels)")
parser.add_argument("--height", type=int, default=360, help="desired height of camera stream (default is 720 pixels)")
parser.add_argument("--camera", type=str, default="0", help="index of the MIPI CSI camera to use (NULL for CSI camera 0), or for VL42 cameras the /dev/video node to use (e.g. /dev/video0).  By default, MIPI CSI camera 0 will be used.")
parser.add_argument('--headless', action='store_true', default=(), help="run without display")
parser.add_argument("--dirOut", default=None, help="desired output directory name (optional)")

is_headless = ["--headless"] if sys.argv[0].find('console.py') != -1 else [""]
try:
    opt, unknown = parser.parse_known_args()
    print(opt)
except:
    print("COULDN'T PARSE")
    parser.print_help()


frame_count = 0
skipped_frames = 0
image_num = 0
threshold = 70

vidDir, logfile, num = dirSetup(dirOut=opt.dirOut)
#logfile.close()

# create display window
display = jetson.utils.videoOutput("rtp://10.131.132.162:1234", argv=sys.argv + is_headless)
output = jetson.utils.videoOutput('{}/video{}.mp4'.format(vidDir, num), argv=sys.argv + is_headless)

# create camera device
camera1 = jetson.utils.videoSource("csi://0", argv=sys.argv)
# camera2 = jetson.utils.videoSource("csi://1", argv=sys.argv)

# capture frames until user exits
while True:
    try:
        frame_count += 1
        skipped_frames += 1
        image1 = camera1.Capture()

        npimg = jetson.utils.cudaToNumpy(image1)
        im = Image.fromarray(npimg)
        frame_str = '/frame' + str(frame_count) + '.jpg' 
        im.save('./npimgs' + frame_str)
        cvimg = cv2.imread('./npimgs' + frame_str)
        gray_img = cv2.cvtColor(cvimg, cv2.COLOR_BGR2GRAY)
        lap = cv2.Laplacian(gray_img, cv2.CV_64F).var()
        print('Lap', lap, 'frame', frame_count)
        logfile.write('Lap: ' + str(lap) + '; frame:' + str(frame_count))
        if skipped_frames > 3 and lap > threshold:
            f = 'image{}.jpg'.format(image_num)
            print('Sending', f)
            logfile.write('Sending ' + f)
            put_file(IP, username, '/tmp/test', f, im)
            image_num += 1
            skipped_frames = 0

        if (image_num + 1) * 50 < frame_count:
            threshold -= 15

        display.Render(image1)
        output.Render(image1)

        if not camera1.IsStreaming() or not display.IsStreaming():
            break
    except KeyboardInterrupt:
        logfile.close()
        print('Closed logfile')

