# jetbot

Software setup for a JetBot controlled by GPIO pins

## Installation

```
cd ~
git clone https://github.com/franklinzhang12/jetbot.git
cd jetbot
./install.sh
```

### Install jetson-inference

Use the spacebar to select PyTorch installation when requested
```
sudo apt-get update
sudo apt-get install git cmake libpython3-dev python3-numpy
git clone --recursive https://github.com/dusty-nv/jetson-inference
cd jetson-inference
mkdir build
cd build
cmake -DENABLE_NVMM=OFF ../
make -j2
sudo make install
sudo ldconfig
```

## Usage

Each time the JetBot is booted, run the setup script in the jetbot folder:
```
cd ~/jetbot
. setup.sh
```

### Testing
Test motors with:
```
python3 motor\_test.py
```
