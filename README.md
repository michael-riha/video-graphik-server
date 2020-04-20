
# HTML/CSS/JS video graphics on top of WebRTC live feeds with `gstreamer`

_First I really wanna thank @Centricular and specially  [@MathieuDuponchelle](https://github.com/MathieuDuponchelle) who did all the heavy lifting and made this tiny experiments even possible_

This Code is part of my [Gstreamer 101](https://github.com/michael-riha/gstreamer-101-python/) with `python` where I got familiar with `gstreamer` inside a `docker`-container and the possiblities of `gstreamer` in case of `WebRTC` as well as `CEF`.
<br>
<br>
<br>
## This is - at the moment - 
## just a **remix** of a few other projects:

THX to:

- [@MathieuDuponchelle](https://github.com/MathieuDuponchelle)'s  [gstcefsrc](https://github.com/centricular/gstcefsr)

- [@matthew1000](https://github.com/matthew1000) & [@moschopsuk](https://github.com/moschopsuk) -> [`Brave`](https://github.com/bbc/brave/) 

    _where I copied more ot less the whole webserver/websocket-logic to interact with `gstreamer`_

- [@notedit](https://github.com/notedit) -> [gstreamer-rtc-streamer](https://github.com/notedit/gstreamer-rtc-streamer)

    _which code helped me a lot to get `webRTC` working and structured, because I had not much `python` knowledge_





### Motivation

Years I wanted to have a 'headless' version of `OBS` where I could overlay a `Browser` over a video-stream. As I dug more into `webRTC` I really wanted to bring this into the mix.
I am no `python`-ninja - not even a well enough `python`-dev, I would say - but I did not want to struggle with `C/C++` (or more and less their `build systems`) so I choose `python` to interact with `gstreamer` on a more deep level.

Thanks to a lot of `examples` all over `github`, as well as the work of the `BBC` with [`Brave`](https://github.com/bbc/brave/) (shout out in this case to [@moschopsuk](https://github.com/moschopsuk) & [@matthew1000](https://github.com/matthew1000) )!

#### Goal

- run gstreamer in `Docker`
- build [CEF-plugin](https://github.com/centricular/gstcefsrc) in the `Container` to bundle it 
- experiment with `gstreamer` and `GLib` in `python`
- develop a couple of small demos with `gstreamer``
- try to build something like a news studio with graphik overlay where participants can publish via `webrtc` to be broadcasted

something like

![alt text](https://media.giphy.com/media/3o7WIt8KjmKFIw7m4E/giphy.gif "Logo Title Text 1")

_please ignore the content, it is all about graphics and video mixing, of course!_

---

## build the container

`docker build --tag=riha/gst-video-graphik-server .`

#### what it does

- installs `gstreamer` and all the dependencies on `ubuntu` `19.10` (TODO: update to LTS 20.x.x, asap)
- builds the [`gstcefsrc`](https://github.com/centricular/gstcefsrc)
    
    _look into the `install_scripts/install-cefPlugin.sh`._

    _The version is pinned to a certain working commit of this plugin, just to be sure it works!_

- installs `python dependencies`

TODO: 
- I did not include (`COPY`) the `src`-Folder in the container, yet because I wanna code during runtime of the container!
- I do not provide an `ENTRYPOINT` because it is still a work in progress and not a product

## run the container

`docker run -it -p 7001:7001 -p 8001:8001 -v $PWD/src:/opt riha/gst-video-graphik-server:latest`

#### what it does

- opens port `8001` for the http/websocket-server for 
    - webRTC signaling
    - http-server for the webRtc ingest
        - as well as HTML-graphics for the background
- opens port `7001` to watch the stream with `ffmpeg` (or `gstreamer` of course!)

    `ffplay tcp://127.0.0.1:7001`

- maps the `src/`-folder to `/opt` inside the container to run the code and develop/debug

## run the server-code

_inside the container_

1. `cd /opt`
2. `python3 server.py`
3. "DONE"
<br>
<br>
4. open `TCP`-stream on the host with

    `ffplay tcp://127.0.0.1:7001` 

---



    


