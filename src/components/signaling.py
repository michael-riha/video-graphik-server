#import sys
import asyncio
import uvloop
from sanic import Sanic
import sanic.response
from sanic.websocket import WebSocketProtocol
from sanic.exceptions import NotFound, InvalidUsage

import gi
gi.require_version('GstSdp', '1.0')
from gi.repository import GstSdp
gi.require_version('GstWebRTC', '1.0')
from gi.repository import GstWebRTC

gi.require_version('Gst', '1.0')
from gi.repository import Gst

import pdb


from components.input import WebRTC
from components.source import TestSource, FileSource

import json
from pprint import pprint

from pyee import EventEmitter, ExecutorEventEmitter, BaseEventEmitter

import logging

logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(message)s',)

class SignalingServer():
    def __init__(self, rtc, output):
        self.rtcClient= rtc
        self.websocket= None

        @rtc.on('candidate')
        def on_candidate(candidate):
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self.websocket.send(json.dumps({
                'candidate':candidate
            })))
            print('send candidate', candidate)

        @rtc.on('answer')
        def on_answer(answer):
            rtc.set_local_description(answer)
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self.websocket.send(json.dumps({
                'answer':answer.sdp.as_text()
            })))
            print('send answer', answer.sdp.as_text())

        @rtc.on('offer')
        def on_offer(offer):
            rtc.set_local_description(offer)
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self.websocket.send(json.dumps({
                'offer':offer.sdp.as_text()
            })))
            print('send offer', offer.sdp.as_text())

        @rtc.on('negotiation-needed')
        def on_negotiation_needed(element):
            print('negotiation-needed', element)

        @rtc.on('incoming-audio-intersink')
        def on_incoming_audio(channel_name):
            print('incoming-audio-intersink', channel_name)
            output.add_audio_input(channel_name)
            #output.draw_pipeline("after_incoming_audio")

        @rtc.on('incoming-video-intersink')
        def on_incoming_video(channel_name):
            print('incoming-video-intersink', channel_name)
            print("add {channel} to LIVE Mixer".format(channel=channel_name))
            output.add_video_input(channel_name, 520, 100)
            output.draw_pipeline("after_incoming_video")
            
        


        # gives you an proper offer
        source  = TestSource()
        rtc.add_stream(source)

        #alternative ? https://stackoverflow.com/questions/57430215/how-to-use-webrtcbin-create-offer-only-receive-video
        '''
        direction = GstWebRTC.WebRTCRTPTransceiverDirection.RECVONLY
        caps = Gst.caps_from_string("application/x-rtp,media=video,encoding-name=VP8/9000,payload=96")
        rtc.emit('add-transceiver', direction, caps)
        '''

        logging.debug("SignalingServer initiated with!", rtc)
        app = Sanic()
        app.config.KEEP_ALIVE = False
        app.static('/', './www/index.html', name='index.html')
        app.static('/bg', './www/background.html', name='background.html')
        
        async def api(request):
            return sanic.response.json({"response": "api"})
        app.add_route(api, "/api")

        # avoid favicon.ico - Error
        app.error_handler.add(
            sanic.exceptions.NotFound,
            lambda r, e: sanic.response.empty(status=404)
        )

        # https://sanic.readthedocs.io/en/latest/sanic/websocket.html
        app.config.WEBSOCKET_MAX_SIZE = 2 ** 20
        app.config.WEBSOCKET_MAX_QUEUE = 32
        app.config.WEBSOCKET_READ_LIMIT = 2 ** 16
        app.config.WEBSOCKET_WRITE_LIMIT = 2 ** 16

        
        clients= []
        async def signaling(request, ws):
            logging.debug("is called!")
            clients.append(id(ws))
            self.websocket= ws
            while True:
                #pprint(ws)
                #print("websocket id: {id}".format(id=id(ws)))
                # a Python object (dict):
                data = {
                "name": "John"
                }
                logging.debug('Sending: ' + str(data))
                await ws.send(json.dumps(data))
                message = await ws.recv()
                logging.debug('Received: ' + message)
                # https://realpython.com/python-json/
                msg = json.loads(message)
                if msg.get('join'):
                    self.rtcClient.create_offer()

                if msg.get('answer'):
                    sdp = msg['answer']
                    _,sdpmsg = GstSdp.SDPMessage.new()
                    GstSdp.sdp_message_parse_buffer(bytes(sdp.encode()), sdpmsg)
                    answer = GstWebRTC.WebRTCSessionDescription.new(GstWebRTC.WebRTCSDPType.ANSWER, sdpmsg)
                    self.rtcClient.set_remote_description(answer)

                if msg.get('candidate') and msg['candidate'].get('candidate'):
                    print('add_ice_candidate')
                    self.rtcClient.add_ice_candidate(msg['candidate'])

        app.add_websocket_route(signaling, '/signaling')
        
        def start_server():
            # https://docs.telethon.dev/en/latest/concepts/asyncio.html -> it uses asyncio.get_event_loop(), which only works in the main thread
            asyncio.set_event_loop(uvloop.new_event_loop())
            loop = asyncio.get_event_loop()
            server = app.create_server(host="0.0.0.0", port=8001, access_log=False, return_asyncio_server=True)
            asyncio.ensure_future(server)
            #loop.create_task(self.webockets_handler.periodic_check())
            loop.run_forever()
        
        start_server()
    
