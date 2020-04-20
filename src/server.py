#!/usr/bin/env python
'''
To run this, set the environment variables $SRC and $SRC2 to full paths to two mp4 files.

This has three pipelines:

- Pipeline 1 plays the file $SRC
- Pipeline 2 plays the file $SRC2
- Pipeline 3 displays them mixed

Pipeline-1 --\
              ---> Output-pipe
Pipeline 2 --/

This demo shows how, by splitting into pipelines, each soure can be seeked independently.
And if one fails (e.g. file not found), the other continues.
'''
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
import os
from time import sleep
from threading import Thread

import pdb

Gst.init(None)

Gst.debug_set_active(True)
Gst.debug_set_default_threshold(4)

from components.input import WebRTC
from components.signaling import SignalingServer
from components.output import TCPOutput 

import threading
import signal

from pprint import pprint

import logging

logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(message)s',)

mainloop = GObject.MainLoop()
# https://lazka.github.io/pgi-docs/Gst-1.0/functions.html#Gst.debug_bin_to_dot_file
def draw_pipeline(pipe, filename):
    #Gst.debug_bin_to_dot_file(pipe, Gst.DebugGraphDetails.ALL, "pipeline-dot")
    # https://pygraphviz.github.io/documentation/pygraphviz-1.3rc1/reference/agraph.html
    import pygraphviz as pgv
    dot_data= Gst.debug_bin_to_dot_data(pipe, Gst.DebugGraphDetails.ALL)
    G= pgv.AGraph(dot_data)
    print("now let's print some graph: "+filename+".png")
    file_path = '{name}.png'.format(
    grandparent=os.path.dirname(os.path.dirname(__file__)),
    name=filename)
    G.draw(file_path, format="png",prog="dot")

rtcClient = WebRTC(stun_server="stun://stun.l.google.com:19302")
#output = None
output = TCPOutput()
def main():
    global output
    # We make the two pipelines
    pipe1 = Gst.Pipeline()
    pipe2 = Gst.Pipeline()

    '''
    video_sink_1 = Gst.ElementFactory.make("videotestsrc", "test_src0")
    video_sink_1.set_property("is-live", True)
    video_sink_1.set_property("pattern", "black")
    pipe1.add(video_sink_1)
    '''

    video_sink_1 = Gst.ElementFactory.make('cefsrc', "test_src")
    #video_sink_1.set_property("url", "https://sms.at")
    video_sink_1.set_property("url", "http://127.0.0.1:8001/bg")
    pipe1.add(video_sink_1)
    video_sink_1_caps = Gst.ElementFactory.make('capsfilter', "test_src0")
    video_sink_1_caps.set_property("caps", Gst.Caps.from_string("video/x-raw,width=1920,height=1080"))
    #video_sink_1_caps.set_property("caps", Gst.Caps.from_string("video/x-raw,width=3840,height=2160")) #4k  3840 × 2160 Pixel NOT WORKING
    pipe1.add(video_sink_1_caps)
    video_sink_1.link(video_sink_1_caps)

    video_sink_2 = Gst.ElementFactory.make("videotestsrc", "test_src")
    video_sink_2.set_property("is-live", True)
    video_sink_2.set_property("pattern", "smpte")
    pipe2.add(video_sink_2)
    
    video_sink_2_caps = Gst.ElementFactory.make('capsfilter', "test_src1")
    video_sink_2_caps.set_property("caps", Gst.Caps.from_string("video/x-raw,width=480,height=320"))
    pipe2.add(video_sink_2_caps)
    video_sink_2.link(video_sink_2_caps)
    

    #output= TCPOutput()

    # Make the sinks for the first two pipelines:
    video_sink_1 = Gst.ElementFactory.make("intervideosink", "video_sink_1")
    video_sink_2 = Gst.ElementFactory.make("intervideosink", "video_sink_2")
    pipe1.add(video_sink_1)
    pipe2.add(video_sink_2)
    src0= pipe1.get_by_name('test_src0')
    src1 = pipe2.get_by_name('test_src1')
    src0.link(video_sink_1)
    src1.link(video_sink_2)

    #Make also a audio Test pipeline
    # audio testing
    a_test_pipeline = Gst.Pipeline()
    audio_test_src= Gst.ElementFactory.make("audiotestsrc", "auditest")
    audio_test_src.set_property("wave", 2)
    audio_test_src.set_property("freq", 200)
    a_test_pipeline.add(audio_test_src)
    

    audio_intersrc= Gst.ElementFactory.make("interaudiosink", "audiotest_intersink")
    audio_intersrc.set_property('channel', 'audio-channel-1')
    a_test_pipeline.add(audio_intersrc)
    # link them
    audio_test_src.link(audio_intersrc)
    output.add_audio_input("audio-channel-1")

    # We use 'channel' to name the two different connections between
    video_sink_1.set_property('channel', 'video-channel-1')
    output.add_video_input("video-channel-1", 0, 0)
    video_sink_2.set_property('channel', 'video-channel-2')
    output.add_video_input("video-channel-2", 20, 100)

    # Off we go!
    pipe1.set_state(Gst.State.PLAYING)
    draw_pipeline(pipe1, "pipeline_1")
    pipe2.set_state(Gst.State.PLAYING)
    #pipe3.set_state(Gst.State.PLAYING)
    draw_pipeline(pipe2, "pipeline_2")
    a_test_pipeline.set_state(Gst.State.PLAYING)
    draw_pipeline(a_test_pipeline, "audio test pipeline")

    output.start()
    output.draw_pipeline("Output_TCPOutput_after_intersink_audio")
    #draw_pipeline(pipe1, "pipeline_1_after_start")
    #draw_pipeline(pipe2, "pipeline_2_after_start")  

def start_server():
    global rtcClient
    global output
    def start_signaling_in_separate_thread(rtcInput, output):
        pprint(rtcInput)
        pprint(output)
        try:
            signaling= SignalingServer(rtcInput, output)
            logging.debug('Server has been started')
        except Exception as e:
            print('Cannot start Rest API:', e)
        

    threading.Thread(target=start_signaling_in_separate_thread, name='api-thread', daemon=True, kwargs=dict(rtcInput=rtcClient, output=output)).start()
    #start_signaling_in_separate_thread(rtcClient)

def keyboard_exit(signal, frame):
        logging.debug("Received keyboard interrupt to exit, so tidying up...")
        #session.end()

if __name__ == '__main__':
  #https://stackoverflow.com/questions/4205317/capture-keyboardinterrupt-in-python-without-try-except
  try:
    # escape from this 
    signal.signal(signal.SIGINT, keyboard_exit)
    #main()
    start_server()
    # we need the webserver first to display the HTML-background
    main()
    mainloop.run()
  except KeyboardInterrupt:
      # do nothing here
      pass