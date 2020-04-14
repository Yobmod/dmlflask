import time
import sys
from rq import get_current_job
import json
from flask import render_template
from redis import exceptions

from app import create_app
from app import db
from app.models import User, Post, Task
from app.email import send_email

from typing import List, Dict
from sqlalchemy import Integer


app = create_app()  # create shadow app instance for RQ
app.app_context().push()  # make shadow app the current_app


def _set_task_progress(progress: int) -> None:
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        task.user.add_notification('task_progress', {'task_id': job.get_id(),
                                                     'progress': progress})
        if progress >= 100:
            task.complete = True
        db.session.commit()


def export_posts(user_id: Integer) -> None:
    try:
        user = User.query.get(user_id)
        _set_task_progress(0)
        data: List[Dict[str, str]] = []
        i = 0
        total_posts = user.posts.count()
        for post in user.posts.order_by(Post.timestamp.asc()):
            data.append({'body': post.body, 'timestamp': post.timestamp.isoformat() + 'Z'})  # 'Z' -> UTC
            time.sleep(5)  # 5 for progress bar demo
            i += 1
            _set_task_progress(100 * i // total_posts)

        send_email('[Microblog] Your blog posts',
                   sender=app.config['ADMINS'][0],
                   recipients=[user.email],
                   text_body=render_template('email/export_posts.txt', user=user),
                   html_body=render_template('email/export_posts.html', user=user),
                   attachments=[('posts.json', 'application/json', json.dumps({'posts': data}, indent=4))],
                   sync=True)
    except exceptions.ConnectionError as ce:
        app.logger.error('Redis server ConnectionError', exc_info=sys.exc_info())
    except Exception:
        _set_task_progress(100)
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())


"""
$ rq worker dmlmicro-tasks                  # start redis is cmd
>>> from redis import Redis                 # in python cmd (separate)
>>> import rq
>>> queue = rq.Queue('dmlmicro-tasks', connection=Redis.from_url('redis://'))  # make a queue
>>> job = queue.enqueue('app.tasks.example', 23)                               # add a task
>>> job.get_id()        # get string id
>>> job.is_finished     # get bool of if done
>>> job.refresh()       # update job.meta
"""
