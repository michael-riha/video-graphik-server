#!/bin/bash

#https://github.com/centricular/gstcefsrc
git clone -n https://github.com/centricular/gstcefsrc.git
cd gstcefsrc
#https://coderwall.com/p/xyuoza/git-cloning-specific-commits
git checkout eec5c5acc0bbf76cc8f4ea8c586b9e879e9ad54e
#https://github.com/centricular/gstcefsrc/blob/master/README.md
mkdir build && cd build
cmake -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release ..
make

# finally copy the plugin to the plugin destination of gstreamer
cp -r /gstcefsrc/build/Release/ /usr/lib/x86_64-linux-gnu/gstreamer-1.0/