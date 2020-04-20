
# HTML/CSS/JS video graphics on top of WebRTC live feeds with `gstreamer`

_First I really wanna thank @Centricular and specially  [@MathieuDuponchelle](https://github.com/MathieuDuponchelle) who did all the heavy lifting and made this tiny experiments even possible_

This Code is part of my [Gstreamer 101](https://github.com/michael-riha/gstreamer-101-python/) with `python` where I got familiar with `gstreamer` inside a `docker`-container and the possiblities of `gstreamer` in case of `WebRTC` as well as `CEF`.

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

---



