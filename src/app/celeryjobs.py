from celery import Celery

from flask import Flask
from celery import Task


def make_celery(app: Flask) -> Celery:
    celery = Celery(app.import_name, backend=app.config['CELERY_RESULT_BACKEND'],
                    broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase: Task = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args: tuple, **kwargs: dict) -> Task:
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery
