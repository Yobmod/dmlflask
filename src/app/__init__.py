import os
import atexit
from flask import Flask, request, current_app
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_babel import Babel, lazy_gettext as _l
from elasticsearch import Elasticsearch
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
from redis import Redis
import rq
from imutils.video import VideoStream
from app.imagesearch.pyimagesearch.motion_detection import SingleMotionDetector
import imutils
import threading
import time
import cv2
import argparse
import datetime

from typing import Union, Tuple, Type
import typing as typ

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
mail = Mail()
bootstrap = Bootstrap()
moment = Moment()
babel = Babel()

login.login_view = 'auth.login'  # name of view
login.login_message = _l('Please log in to access this page.')

outputFrame = None
lock = threading.Lock()

## vs = VideoStream(usePiCamera=1).start()
vs = VideoStream(src=0).start()
time.sleep(2.0)


def detect_motion(frameCount: int) -> None:
    # grab global references to the video stream, output frame, and
    # lock variables
    global vs, outputFrame, lock
    # initialize the motion detector and the total number of frames
    # read thus far
    md = SingleMotionDetector(accumWeight=0.1)
    total = 0

    # loop over frames from the video stream
    while True:
        # read the next frame from the video stream, resize it,
        # convert the frame to grayscale, and blur it
        frame = vs.read()
        frame = imutils.resize(frame, width=400)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7, 7), 0)
        # grab the current timestamp and draw it on the frame
        timestamp = datetime.datetime.now()
        cv2.putText(frame, timestamp.strftime(
            "%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        # if the total number of frames has reached a sufficient
        # number to construct a reasonable background model, then
        # continue to process the frame
        if total > frameCount:
            # detect motion in the image
            motion = md.detect(gray)
            # check to see if motion was found in the frame
            if motion is not None:
                # unpack the tuple and draw the box surrounding the
                # "motion area" on the output frame
                (thresh, (minX, minY, maxX, maxY)) = motion
                cv2.rectangle(frame, (minX, minY), (maxX, maxY), (0, 0, 255), 2)

        # update the background model and increment the total number
        # of frames read thus far
        md.update(gray)
        total += 1
        # acquire the lock, set the output frame, and release the
        # lock
        with lock:
            outputFrame = frame.copy()


def generate() -> typ.Generator[bytes, None, None]:
    # grab global references to the output frame and lock variables
    global outputFrame, lock
    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if outputFrame is None:
                continue
            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
            # ensure the frame was successfully encoded
            if not flag:
                continue
        # yield the output frame in the byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')


def create_app(config_class: Type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)
    babel.init_app(app)
    app.redis = Redis.from_url(app.config['REDIS_URL'])

    app.task_queue = rq.Queue('microblog-tasks', connection=app.redis)

    thrd = threading.Thread(target=detect_motion, args=(5, ))  # =(args["frame_count"],))
    thrd.daemon = True
    thrd.start()

    if app.config['ELASTICSEARCH_URL']:
        app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']])
    else:
        app.elasticsearch = None

    from app.auth import bp as auth_bp
    from app.main import bp as main_bp
    from app.imagesearch import bp as is_bp
    from app.errors import bp as errors_bp

    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(is_bp, url_prefix='/is')
    app.register_blueprint(errors_bp)
    print('blueprints loaded')

    if not app.debug and not app.testing:
        if current_app.config['MAIL_SERVER']:
            auth = None
            if current_app.config['MAIL_USERNAME'] or current_app.config['MAIL_PASSWORD']:
                auth = (current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
            if current_app.config['MAIL_USE_TLS']:
                secure: Union[None, Tuple[str], Tuple[str, str]] = ('', )
            else:
                secure = None

            mail_handler = SMTPHandler(
                mailhost=(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']),
                fromaddr=current_app.config['ADMINS'][0],
                toaddrs=current_app.config['ADMINS'], subject='Microblog Failure',
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.INFO)
            app.logger.addHandler(mail_handler)

        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/microblog.log', maxBytes=10240,
                                           backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Microblog startup')

    def close_vs(vs: VideoStream) -> None:
        vs.stop()
        print("\n videostream stopped")

    atexit.register(close_vs, vs)

    return app


@babel.localeselector
def get_locale() -> typ.Optional[str]:
    lang = request.accept_languages.best_match(current_app.config['LANGUAGES'])
    # lang = 'es'
    return lang
# Commands to generate .po files:
# pybabel extract -F babel.cfg -k _l -o messages.pot . ## create .pot file
# pybabel init -i messages.pot -d app/translations -l es  ## create .po files
# pybabel compile - d app/translations  # compile to .mo files (after trans added to .po)
# pybabel update - i messages.pot - d app/translations  # remake .pot file first, then this updates .po


# from app import models
