from app import create_app, db, cli
import argparse
# from app.imagesearch.webstreaming import detect_motion
from app.models import User, Post, Notification, Message, Task
# from flask_sqlalchemy import SQLAlchemy

from config import Config


import typing as typ

# initialize the output frame and a lock used to ensure thread-safe exchanges of the
# output frames (useful when multiple browsers/tabs are viewing the stream)
#outputFrame = None
#lock = threading.Lock()

# initialize a flask object
app = create_app(Config)
cli.register(app)


@app.shell_context_processor
def make_shell_context() -> typ.Dict[str, typ.Union[object, User, Post, Message, Notification, Task]]:
    return {'db': db,
            'User': User,
            'Post': Post,
            'Message': Message,
            'Notification': Notification,
            'Task': Task,
            }


# construct the argument parser and parse command line arguments
"""
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--ip", type=str, nargs='?', const="0:0:0:0",
                help="ip address of the device")
ap.add_argument("-o", "--port", type=int, nargs='?', const=5000,
                help="ephemeral port number of the server (1024 to 65535)")
ap.add_argument("-f", "--frame-count", type=int, required=False, default=32,
                help="# of frames used to construct the background model")
args = vars(ap.parse_args())
"""

"""
# start a thread that will perform motion detection
thrd = threading.Thread(target=detect_motion, args=(args["frame_count"],))
thrd.daemon = True
thrd.start()
"""

print("App running...")

"""
# start the flask app
app.run(host=args["ip"],
        port=args["port"],
        debug=True,
        threaded=True,
        use_reloader=False)
"""
