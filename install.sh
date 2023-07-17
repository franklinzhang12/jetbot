#!/bin/bash

sudo apt-get update && sudo apt-get upgrade
sudo apt-get install python3-pip
wget https://bootstrap.pypa.io/pip/3.6/get-pip.py
python3 get-pip.py
sudo pip3 uninstall Pillow && pip3 install Pillow==8.0.1
pip3 install --upgrade setuptools
pip3 install pyzmq
pip3 install keyboard inputs traitlets packaging ipywidgets
cd $HOME
git clone https://github.com/NVIDIA-AI-IOT/torch2trt
cd torch2trt
sudo python3 setup.py install
