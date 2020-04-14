from __future__ import annotations
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from flask_login import UserMixin
from hashlib import md5
from time import time
import json
import jwt
import redis
import rq


from app import db, login
from app.search import add_to_index, remove_from_index, query_index, delete_index

from typing import List, Optional as Opt, TypeVar, Tuple, Dict, Any
from sqlalchemy import Column, String
from sqlalchemy.orm.query import Query
from app.types import jsonType, SearchSession


@login.user_loader
def load_user(id: str) -> User:
    user_from_id: User = User.query.get(int(id))
    return user_from_id


followers = db.Table('followers',
                     db.Column('follower_id', db.Integer,
                               db.ForeignKey('user.id')),
                     db.Column('followed_id', db.Integer,
                               db.ForeignKey('user.id'))
                     )


class Message(db.Model):        # type: ignore
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self) -> str:
        return '<Message {}>'.format(self.body)


class Task(db.Model):       # type: ignore
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self) -> Opt[rq.job.Job]:
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError) as e:
            # logger.ERROR(e)
            print(e)
            return None
        else:
            return rq_job

    def get_progress(self) -> int:
        job = self.get_rq_job()
        progress: int = job.meta.get('progress', 0) if job is not None else 100
        return progress


class SearchableMixin(object):

    __tablename__: str
    id: Column
    query: Query  # Any should be an index? or class type?

    @classmethod
    def search(cls, expression: str, page: int, per_page: int) -> Tuple[List[Tuple[int]], int]:
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return (cls.query.filter_by(id=0), 0)
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        query_set: List[Tuple[int]] = cls.query.filter(cls.id.in_(ids)).order_by(db.case(when, value=cls.id))
        return (query_set, total)

    @classmethod
    def before_commit(cls, session: SearchSession) -> None:
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session: SearchSession) -> None:
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = {}

    @classmethod
    def reindex(cls) -> None:
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)

    @classmethod
    def deleteindex(cls) -> None:
        delete_index(cls.__tablename__)


db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


class Notification(db.Model):       # type: ignore
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self) -> jsonType:
        json_data: jsonType = json.loads(str(self.payload_json))
        return json_data


class User(UserMixin, db.Model):        # type: ignore
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    followed = db.relationship('User',
                               secondary=followers,
                               primaryjoin=(followers.c.follower_id == id),
                               secondaryjoin=(followers.c.followed_id == id),
                               backref=db.backref('followers', lazy='dynamic'),
                               lazy='dynamic')
    messages_sent = db.relationship('Message',
                                    foreign_keys='Message.sender_id',
                                    backref='author', lazy='dynamic')
    messages_received = db.relationship('Message',
                                        foreign_keys='Message.recipient_id',
                                        backref='recipient', lazy='dynamic')
    last_message_read_time = db.Column(db.DateTime)
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    def __repr__(self) -> str:
        return '<User {}>'.format(self.username)

    def avatar(self, size: int) -> str:
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, size)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        password_hash_match: bool = check_password_hash(
            self.password_hash, password)
        return password_hash_match

    def follow(self, user: User) -> None:
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user: User) -> None:
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user: User) -> bool:
        is_follow: bool = (self.followed.filter(
            followers.c.followed_id == user.id).count() > 0)
        return is_follow

    def followed_posts(self) -> List[Post]:
        followed = Post.query.join(followers,
                                   (followers.c.followed_id == Post.user_id)).filter(
            followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        my_follow_posts: List[Post] = followed.union(
            own).order_by(Post.timestamp.desc())
        return my_follow_posts

    def new_messages(self) -> int:
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        all_user_msges = Message.query.filter_by(recipient=self)
        new_msges = all_user_msges.filter(Message.timestamp > last_read_time)
        new_msg_count: int = new_msges.count()
        return new_msg_count

    def add_notification(self, name: String, data: jsonType) -> Notification:
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    def get_reset_password_token(self, expires_in: int = 600) -> str:
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token: str) -> Opt[User]:
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except Exception as e:
            # logger(ERROR)
            print(e)
            return None
        else:
            verified_user: User = User.query.get(id)
            return verified_user

    def launch_task(self, taskname: str, description: str, *args: object, **kwargs: object) -> Task:
        rq_job = current_app.task_queue.enqueue('app.tasks.' + taskname, self.id,
                                                *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=taskname, description=description,
                    user=self)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self) -> List[Opt[Task]]:
        task_list: List[Opt[Task]] = Task.query.filter_by(user=self, complete=False).all()
        return task_list

    def get_task_in_progress(self, taskname: str) -> Opt[Task]:
        current_task: Opt[Task] = Task.query.filter_by(name=taskname, user=self,
                                                       complete=False).first()
        return current_task


class Post(SearchableMixin, db.Model):       # type: ignore
    __tablename__ = 'post'
    __searchable__ = ['body']

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    language = db.Column(db.String(5))

    def __repr__(self) -> str:
        return '<Post {}>'.format(self.body)
