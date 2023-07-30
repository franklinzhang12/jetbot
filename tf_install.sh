#!/bin/bash

sudo apt-get update
sudo apt-get install libhdf5-serial-dev hdf5-tools libhdf5-dev zlib1g-dev zip libjpeg8-dev liblapack-dev libblas-dev gfortran -y
sudo apt-get install python3-pip -y
sudo pip3 install -U pip testresources setuptools
sudo ln -s /usr/include/locale.h /usr/include/xlocale.h
sudo pip3 install cython=0.29.16 pkgconfig h5py==2.10.0 
sudo pip3 install -U pip numpy==1.17.5 future==0.17.1 mock==3.0.5 keras_preprocessing==1.0.5 keras_applications==1.0.8 gast==0.3.3 futures protobuf pybind11
sudo pip3 install --pre --extra-index-url https://developer.download.nvidia.com/compute/redist/jp/v45 tensorflow==2.3.1