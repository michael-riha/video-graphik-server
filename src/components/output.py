import time
import os
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

import pdb

Gst.init(None)

class Output(Gst.Bin):

    def __init__(self):
        Gst.Bin.__init__(self)
        self.pipeline= None

    '''
    @property
    def channel_name(self):
        raise 'need have audio src pad'
    '''

    # https://lazka.github.io/pgi-docs/Gst-1.0/functions.html#Gst.debug_bin_to_dot_file
    def draw_pipeline(self, filename):
        #Gst.debug_bin_to_dot_file(pipe, Gst.DebugGraphDetails.ALL, "pipeline-dot")
        # https://pygraphviz.github.io/documentation/pygraphviz-1.3rc1/reference/agraph.html
        import pygraphviz as pgv
        dot_data= Gst.debug_bin_to_dot_data(self.pipeline, Gst.DebugGraphDetails.ALL)
        G= pgv.AGraph(dot_data)
        print("now let's print some graph: "+filename+".png")
        file_path = '{name}.png'.format(
        grandparent=os.path.dirname(os.path.dirname(__file__)),
        name=filename)
        G.draw(file_path, format="png",prog="dot")

class TCPOutput(Output):

    def __init__(self):
        Output.__init__(self)

        self.pipeline = Gst.Pipeline()
        self.inputs= []

        # Let's start with a video mixer where Inputs/Sources can connect to
        v_mixer = Gst.ElementFactory.make("videomixer", "videomix")
        #mixer.set_property("background", 1) # black if needed
        self.pipeline.add(v_mixer)
        self.v_mixer= v_mixer

        # Let's also add an audio mixer
        a_mixer = Gst.ElementFactory.make("audiomixer", "audiomix")
        #a_pad= a_mixer.get_request_pad("sink_%u")
        self.pipeline.add(a_mixer)
        self.a_mixer= a_mixer
        
        queue_a_before = Gst.ElementFactory.make('queue', None)
        self.pipeline.add(queue_a_before)

        queue_a_after = Gst.ElementFactory.make('queue', None)
        self.pipeline.add(queue_a_after)

        aacEnc = Gst.ElementFactory.make('avenc_aac', None)
        self.pipeline.add(aacEnc)

        a_mixer.link(queue_a_before)
        queue_a_before.link(aacEnc)
        aacEnc.link(queue_a_after)

        #set size if the mixer
        mixer_size_cap = Gst.ElementFactory.make("capsfilter", "videomix_size")
        value= "video/x-raw,width=1920,height=1080"
        value= Gst.Caps.from_string(value)
        mixer_size_cap.set_property("caps", value)
        self.pipeline.add(mixer_size_cap)

        # Outgoing server sink
        videoconvert0 = Gst.ElementFactory.make("videoconvert", "videoconvert1")

        queue0 = Gst.ElementFactory.make('queue', None)

        x264enc = Gst.ElementFactory.make('x264enc', None)
        x264enc.set_property("byte-stream", True)
        x264enc.set_property("tune", "zerolatency")

        h264parse = Gst.ElementFactory.make('h264parse', None)
        h264parse.set_property("config-interval", 1)

        queue1 = Gst.ElementFactory.make('queue', None)

        matroskamux = Gst.ElementFactory.make('matroskamux', None)

        queue2 = Gst.ElementFactory.make('queue', None)
        queue2.set_property("leaky", 2)

        tcpserversink = Gst.ElementFactory.make('tcpserversink', None)
        tcpserversink.set_property("port", 7001)
        tcpserversink.set_property("host", "0.0.0.0")
        tcpserversink.set_property("recover-policy", "keyframe")
        tcpserversink.set_property("sync-method", "latest-keyframe")
        tcpserversink.set_property("sync", False)

        self.pipeline.add(videoconvert0)
        self.pipeline.add(queue0)
        self.pipeline.add(x264enc)
        self.pipeline.add(h264parse)
        self.pipeline.add(queue1)
        self.pipeline.add(matroskamux)
        self.pipeline.add(queue2)
        self.pipeline.add(tcpserversink)

        queue0.link(x264enc)
        x264enc.link(h264parse)
        h264parse.link(queue1)
        #queue1.link(matroskamux)
        
        # use video & audio pad
        video_pad= matroskamux.get_request_pad("video_%u")
        queue1.get_static_pad("src").link(video_pad)
        '''
        audio_pad= matroskamux.get_request_pad("audio_%u")
        queue_a_after.get_static_pad("src").link(audio_pad)
        '''        
        #pdb.set_trace()
        matroskamux.link(queue2)
        queue2.link(tcpserversink)

        # `videoconvert` needed for alpha, otherwise directly link to queue0
        
        #v_mixer.link(videoconvert0)
        

        #with capsfilter to give mixer a size
        v_mixer.link(mixer_size_cap)
        mixer_size_cap.link(videoconvert0)

        videoconvert0.link(queue0)

    def add_video_input(self, channel_name, xPos=0, yPos=0):
        pad = self.v_mixer.get_request_pad("sink_%u")
        # temp helper
        #pos= len(self.inputs)*200
        #pos= 0
        pad.set_property('xpos',xPos)
        pad.set_property('ypos',yPos)
        #pad.set_property('alpha',0.8)
        #pad1.set_property('width',720)
        #pad1.set_property('height',540)

        video_src = Gst.ElementFactory.make("intervideosrc", channel_name)
        video_src.set_property('channel', channel_name)
        self.pipeline.add(video_src)
        # connect intervideosrc to mixer!
        video_src.get_static_pad("src").link(pad)

        input = {
            "mixer_pad": pad,
            "video_src": video_src
        }
        #if added during runtime this might be necessary
        video_src.sync_state_with_parent()

        self.inputs.append(input)
        return input

    def add_audio_input(self, channel_name):
        pad = self.a_mixer.get_request_pad("sink_%u")

        audio_src = Gst.ElementFactory.make("interaudiosrc", channel_name)
        audio_src.set_property('channel', channel_name)
        self.pipeline.add(audio_src)

        # connect intervideosrc to mixer!
        audio_src.get_static_pad("src").link(pad)

        input = {
            "mixer_pad": pad,
            "audio_src": audio_src
        }
        #if added during runtime this might be necessary
        audio_src.sync_state_with_parent()

        #self.inputs.append(input)
        #return input

    def start(self):
        self.pipeline.set_state(Gst.State.PLAYING)