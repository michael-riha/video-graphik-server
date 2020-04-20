import asyncio
import os
import sys
import pdb

import attr
from pyee import EventEmitter

from pprint import pprint

import pdb

import gi
gi.require_version('GObject', '2.0')
from gi.repository import GObject
gi.require_version('Gst', '1.0')
from gi.repository import Gst
gi.require_version('GstWebRTC', '1.0')
from gi.repository import GstWebRTC
gi.require_version('GstSdp', '1.0')
from gi.repository import GstSdp
from gi.repository import GLib

Gst.init(None)

#Gst.debug_set_active(True)
#Gst.debug_set_default_threshold(4)

VP8_CAPS = Gst.Caps.from_string('application/x-rtp,media=video,encoding-name=VP8,payload=97,clock-rate=90000')
H264_CAPS = Gst.Caps.from_string('application/x-rtp,media=video,encoding-name=H264,payload=98,clock-rate=90000')
OPUS_CAPS = Gst.Caps.from_string('application/x-rtp,media=audio,encoding-name=OPUS,payload=100,clock-rate=48000')



class WebRTC(EventEmitter):

    INACTIVE = GstWebRTC.WebRTCRTPTransceiverDirection.INACTIVE
    SENDONLY = GstWebRTC.WebRTCRTPTransceiverDirection.SENDONLY
    RECVONLY = GstWebRTC.WebRTCRTPTransceiverDirection.RECVONLY
    SENDRECV = GstWebRTC.WebRTCRTPTransceiverDirection.SENDRECV

    def __init__(self,stun_server=None, turn_server=None,):
        super().__init__()

        self.stun_server = stun_server
        self.turn_server = turn_server
        self.streams = []

        self.pipe = Gst.Pipeline.new('webrtc')
        self.webrtc = Gst.ElementFactory.make('webrtcbin')
        self.webrtc.set_state(Gst.State.READY) #new for gst 1.16 https://gitlab.freedesktop.org/gstreamer/gst-plugins-bad/issues/992
        self.pipe.add(self.webrtc)

        self.webrtc.connect('on-negotiation-needed', self.on_negotiation_needed)
        self.webrtc.connect('on-ice-candidate', self.on_ice_candidate)
        self.webrtc.connect('pad-added', self.on_add_stream)
        self.webrtc.connect('pad-removed', self.on_remove_stream)
        # inspect transceiver
        self.webrtc.connect('get-transceiver', self.on_get_transceiver)

        if self.stun_server:
            self.webrtc.set_property('stun-server', self.stun_server)

        if self.turn_server:
            self.webrtc.set_property('turn-server', self.turn_server)

        #self.webrtc.set_property('bundle-policy','max-bundle')
        bus = self.pipe.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._bus_call, None)

        #trans = self.webrtc.emit('get-transceiver', 0)
        #pdb.set_trace()

        self.pipe.set_state(Gst.State.PLAYING)

        #self.outsink = outsink if outsink else FakeSink()



    @property
    def connection_state(self):
        return self.webrtc.get_property('connection-state')

    @property
    def ice_connection_state(self):
        return self.webrtc.get_property('ice-connection-state')

    @property
    def local_description(self):
        return self.webrtc.get_property('local-description')

    @property
    def remote_description(self):
        return self.webrtc.get_property('remote-description')

    def on_get_transceiver(self, object, idx, udata):
        #python callback for the 'get-transceiver' signal
        pdb.set_trace()

    def on_negotiation_needed(self, element):
        self.emit('negotiation-needed', element)

    def on_ice_candidate(self, element, mlineindex, candidate):
        self.emit('candidate', {
            'sdpMLineIndex': mlineindex,
            'candidate': candidate
        })

    def add_transceiver(self, direction, codec):
        upcodec = codec.upper()
        caps = None
        if upcodec == 'H264':
            caps = H264_CAPS
        elif upcodec == 'VP8':
            caps = VP8_CAPS
        elif upcodec == 'OPUS':
            caps = OPUS_CAPS
        return self.webrtc.emit('add-transceiver', direction, caps)


    def create_offer(self):
        print("create_offer")
        promise = Gst.Promise.new_with_change_func(self.on_offer_created, self.webrtc, None)
        self.webrtc.emit('create-offer', None, promise)


    def on_offer_created(self, promise, element, _):
        print("offer created")
        promise.wait()
        reply = promise.get_reply()
        pprint(reply)
        self.draw_pipeline("on_offer_created_WebRTC_Pipeline")
        offer = reply.get_value('offer')
        if offer:
            self.emit('offer', offer)

    def add_stream(self, stream):
        self.pipe.add(stream)

        if stream.audio_pad:
            audio_sink_pad = self.webrtc.get_request_pad('sink_%u')
            stream.audio_pad.link(audio_sink_pad)

        if stream.video_pad:
            video_sink_pad = self.webrtc.get_request_pad('sink_%u')
            stream.video_pad.link(video_sink_pad)

        stream.sync_state_with_parent()
        self.streams.append(stream)

    def remove_stream(self, stream):
        if not stream in self.streams:
            return
        # todo need fix create offer error  when remove source
        if stream.audio_pad:
            sink_pad = stream.audio_pad.get_peer()
            self.webrtc.release_request_pad(sink_pad)

        if stream.video_pad:
            sink_pad = stream.video_pad.get_peer()
            self.webrtc.release_request_pad(sink_pad)

        if stream in self.pipe.children:
            self.pipe.remove(stream)
        self.streams.remove(stream)


    def create_answer(self):
        print("create answer")
        promise = Gst.Promise.new_with_change_func(self.on_answer_created, self.webrtc, None)
        self.webrtc.emit('create-answer', None, promise)

    def on_answer_created(self, promise, element, _):
        print("on_answer_created")
        ret = promise.wait()
        if ret != Gst.PromiseResult.REPLIED:
            return
        reply = promise.get_reply()
        answer = reply.get_value('answer')
        if answer:
            self.emit('answer', answer)


    def add_ice_candidate(self, ice):
        sdpMLineIndex = ice['sdpMLineIndex']
        candidate = ice['candidate']
        self.webrtc.emit('add-ice-candidate', sdpMLineIndex, candidate)


    def set_local_description(self, sdp):
        #promise = Gst.Promise.new_with_change_func(self.set_description_result, self.webrtc, None)
        promise = Gst.Promise.new()
        print("set_remote_description")
        self.webrtc.emit('set-local-description', sdp, promise)
        promise.interrupt()

    def set_remote_description(self, sdp):
        print("set remote description")
        #promise = Gst.Promise.new_with_change_func(self.set_description_result, self.webrtc, None)
        promise = Gst.Promise.new()
        self.webrtc.emit('set-remote-description', sdp, promise)
        promise.interrupt()

    def get_stats(self):
        pass

    def set_description_result(self, promise, element, _):
        ret = promise.wait()
        if ret != Gst.PromiseResult.REPLIED:
            return
        reply = promise.get_reply()


    def _bus_call(self, bus, message, _):
        t = message.type
        if t == Gst.MessageType.EOS:
            print('End-of-stream')
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print('Error: %s: %s\n' % (err, debug))
        return True


    def on_add_stream(self,element, pad):
        # local stream or `if pad.direction != Gst.PadDirection.SRC:`
        if pad.direction == Gst.PadDirection.SINK:
            return

        decodebin = Gst.ElementFactory.make('decodebin')
        decodebin.connect('pad-added', self.on_incoming_decodebin_pad)
        self.pipe.add(decodebin)
        decodebin.sync_state_with_parent()
        self.webrtc.link(decodebin)
        print("on_add_stream", element, pad)

    def on_remove_stream(self, element, pad):
        # local stream
        if pad.direction == Gst.PadDirection.SINK:
            return

    def on_incoming_decodebin_pad(self, element, pad):

        if not pad.has_current_caps():
            print(pad, 'has no caps, ignoring')
            return

        caps = pad.get_current_caps()
        name = caps.to_string()
        print("on_incoming_decodebin_pad:"+name)
        if name.startswith('video'):
            q = Gst.ElementFactory.make('queue')
            self.pipe.add(q)
            conv = Gst.ElementFactory.make('videoconvert')
            self.pipe.add(conv)
            
            #make the right size
            video_caps = Gst.ElementFactory.make('capsfilter', "rtc_video_caps")
            video_caps.set_property("caps", Gst.Caps.from_string("video/x-raw,width=480,height=320"))
            self.pipe.add(video_caps)

            # use videoscale otherwise if fails!
            video_scale = Gst.ElementFactory.make('videoscale', "video_scale")
            # https://stackoverflow.com/questions/36489794/how-to-change-aspect-ratio-with-gstreamer
            video_scale.set_property("method", 0)
            video_scale.set_property("add-borders", False)
            self.pipe.add(video_scale)

            video_sink_1 = Gst.ElementFactory.make("intervideosink", "video_sink_1")
            self.pipe.add(video_sink_1)
            video_sink_1.set_property('channel', 'video-rtc-channel')

            #link all
            pad.link(q.get_static_pad('sink'))
            q.link(conv)
            # with caps
            #conv.link(video_scale)
            #video_scale.link(video_caps)
            #video_caps.link(video_sink_1)
            conv.link(video_sink_1)
            q.sync_state_with_parent()
            conv.sync_state_with_parent()
            video_sink_1.sync_state_with_parent()
            #pad.link(video_sink_1.get_static_pad("sink"))
            self.draw_pipeline("on_incoming_video_decodebin_pad")
            self.emit('incoming-video-intersink', 'video-rtc-channel')

        elif name.startswith('audio'):
            q = Gst.ElementFactory.make('queue')
            self.pipe.add(q)
            conv = Gst.ElementFactory.make('audioconvert')
            self.pipe.add(conv)
            resample = Gst.ElementFactory.make('audioresample')
            self.pipe.add(resample)

            audio_sink_1 = Gst.ElementFactory.make("interaudiosink", "audio_sink_1")
            self.pipe.add(audio_sink_1)
            audio_sink_1.set_property('channel', 'audio-rtc-channel')
            #link all
            pad.link(q.get_static_pad('sink'))
            q.link(conv)
            #conv.link(resample)
            #is_linked_to_intersink= resample.link(audio_sink_1)

            # negiotiation error http://gstreamer-devel.966125.n4.nabble.com/Negotiation-issues-when-adding-audioconvert-td4670796.html
            #audio/x-raw, rate=48000, channels=1,format=S16LE

            #inter_audio_cap = Gst.ElementFactory.make("capsfilter", None)
            #value= "audio/x-raw, rate=48000, channels=1,format=S16LE"
            #value= Gst.Caps.from_string(value)
            #inter_audio_cap.set_property("caps", value)
            #self.pipeline.add(inter_audio_cap)
            #q.link(inter_audio_cap)
            #inter_audio_cap.link(conv)

            is_linked_to_intersink= conv.link(audio_sink_1)
            print("is_linked_to_intersink", is_linked_to_intersink)
            q.sync_state_with_parent()
            conv.sync_state_with_parent()
            audio_sink_1.sync_state_with_parent()
            #pad.link(audio_sink_1.get_static_pad("sink"))
            self.draw_pipeline("on_incoming_audio_decodebin_pad")
            self.emit('incoming-audio-intersink', 'audio-rtc-channel')

    def draw_pipeline(self, filename):
        #Gst.debug_bin_to_dot_file(pipe, Gst.DebugGraphDetails.ALL, "pipeline-dot")
        # https://pygraphviz.github.io/documentation/pygraphviz-1.3rc1/reference/agraph.html
        import pygraphviz as pgv
        dot_data= Gst.debug_bin_to_dot_data(self.pipe, Gst.DebugGraphDetails.ALL)
        G= pgv.AGraph(dot_data)
        print("now let's print some graph: "+filename+".png")
        file_path = '{name}.png'.format(
        grandparent=os.path.dirname(os.path.dirname(__file__)),
        name=filename)
        G.draw(file_path, format="png",prog="dot")
