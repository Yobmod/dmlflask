import typing as t
from app.imagesearch import bp
#from imutils.video import VideoStream
from flask import Response
from flask import Flask
from flask import render_template
#import threading
#import argparse
#import datetime
#import imutils
import time
import cv2

# initialize the output frame and a lock used to ensure thread-safe exchanges of the
# output frames (useful when multiple browsers/tabs are viewing the stream)
# outputFrame = None
# lock = threading.Lock()

# initialize a flask object
# app = Flask(__name__)

# initialize the video stream and allow the camera sensor to warmup
# vs = VideoStream(usePiCamera=1).start()
# vs = VideoStream(src=0).start()
# time.sleep(2.0)


@bp.route("/")
def index() -> str:
    return render_template("imagesearch/index.html")


@bp.route("/video_feed")
def video_feed() -> Response:
    from app import generate

    # return the response generated along with the specific media
    # type (mime type)
    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


"""

# check to see if this is the main thread of execution
if __name__ == '__main__':
    # construct the argument parser and parse command line arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--ip", type=str, nargs='?', const="0:0:0:0",
                    help="ip address of the device")
    ap.add_argument("-o", "--port", type=int, nargs='?', const=5000,
                    help="ephemeral port number of the server (1024 to 65535)")
    ap.add_argument("-f", "--frame-count", type=int, required=False, default=32,
                    help="# of frames used to construct the background model")
    args = vars(ap.parse_args())

    # start a thread that will perform motion detection
    thrd = threading.Thread(target=detect_motion, args=(args["frame_count"],))
    thrd.daemon = True
    thrd.start()

    # start the flask app
    bp.run(host=args["ip"],
           port=args["port"],
           debug=True,
           threaded=True,
           use_reloader=False)

# release the video stream pointer
vs.stop()
print("\n videostream stopped")
# TODO put functions in a class to avoid globals. Initiate vs in __main__ with flask app, or only when route?
"""
