# JetBot

Software setup for a simpler, cheaper JetBot controlled by GPIO pins

## Installation

```
cd ~
git clone https://github.com/franklinzhang12/jetbot.git
cd jetbot
./install.sh
```
Use the spacebar to select PyTorch installation when requested.

## Usage

Each time the JetBot is booted, run the setup script in the jetbot folder:
```
cd ~/jetbot
./setup.sh
```

### Testing
Test motors with:
```
cd ~/jetbot/jetbot
python3 motor_test.py
```
For camera testing:
- If the Jetson Nano is connected to a monitor, run

```nvgstcapture-1.0```
- Otherwise, to view the camera feed remotely, run the following with jetson-inference installed (replace ```IP``` with address of receiving device):

```video-viewer csi://0 rtp://IP:1234 --input-flip=rotate-180```

and run the following on the receiving device:
```
gst-launch-1.0 -v udpsrc port=1234 \
 caps = "application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264, payload=(int)96" ! \
 rtph264depay ! decodebin ! videoconvert ! autovideosink
```

### Movement
A gamepad controller can be used to move the robot:
```
cd ~/jetbot/src/basic-motion
sudo python3 gamepad-control.py
```

### Running
Run the track with
```
cd ~/jetbot/src
sudo python3 rf-signs-updated.py --flip-method=rotate-180
```

### Data Collection
```
cd ~/jetbot/src/data-collection
sudo python3 image-capture-single.py --flip-method=rotate-180
```
Other options for data collection are also present - see the data-collection folder.
