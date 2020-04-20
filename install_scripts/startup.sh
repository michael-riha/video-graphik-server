#!/bin/bash
#cd /gstcefsrc/build
#export GST_PLUGIN_PATH=$PWD/Release:$GST_PLUGIN_PATH
# http://elementalselenium.com/tips/38-headless
#export GST_PLUGIN_PATH=/gstcefsrc/build/Release/

# or copy?
# cd /usr/lib/x86_64-linux-gnu/gstreamer-1.0/
# cp -r /gstcefsrc/build/Release/ ./
# gst-inspect-1.0 cefsrc

# kill Xvfb and all it's traces
pkill Xvfb
rm -r /tmp/pulse*
rm -r GPUCache/
rm /tmp/.X1-*
rm -r /tmp/.X11*

Xvfb :1 -screen 0 1024x768x16 &
echo "IS VIRTUAL DISPLAY STATED"
#ps aux | grep X
#export DISPLAY=:0
#/bin/bash

