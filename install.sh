#!/bin/bash

# Preliminaries
sudo apt-get update && sudo apt-get upgrade
sudo apt-get install python3-pip
wget https://bootstrap.pypa.io/pip/3.6/get-pip.py
python3 get-pip.py


# jetson-inference installation (also installs PyTorch)
sudo apt-get update
sudo apt-get install git cmake libpython3-dev python3-numpy
git clone --recursive --depth=1 https://github.com/dusty-nv/jetson-inference
cd jetson-inference
mkdir build
cd build
cmake -DENABLE_NVMM=OFF ../
make -j2
sudo make install
sudo ldconfig


# Other packages
sudo pip3 uninstall Pillow && pip3 install Pillow==8.0.1
pip3 install --upgrade setuptools
pip3 install pyzmq
pip3 install keyboard inputs traitlets packaging ipywidgets
cd $HOME
git clone https://github.com/NVIDIA-AI-IOT/torch2trt
cd torch2trt
sudo python3 setup.py install

echo "export PYTHONPATH=$PYTHONPATH:/home/jetbot/jetbot" >> ~/.bashrc
