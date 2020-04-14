from datetime import datetime, timedelta
import unittest
from app import create_app, db
from app.models import User, Post
from config import Config
import pytest
import os

from flask import Flask

basedir = os.path.abspath(os.path.dirname(__file__))


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///'  # + os.path.join(basedir, 'test.db')
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    REDIS_URL = 'redis://localhost:6379/0'
    LANGUAGES = ['en', 'es']


class UserModelCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_hashing(self) -> None:
        u = User(username='susan')
        u.set_password('cat')
        self.assertFalse(u.check_password('dog'))
        self.assertTrue(u.check_password('cat'))

    def test_avatar(self) -> None:
        u = User(username='john', email='john@example.com')
        self.assertEqual(u.avatar(128), ('https://www.gravatar.com/avatar/'
                                         'd4c74594d841139328695756648b6bd6'
                                         '?d=identicon&s=128'))

    def test_follow(self) -> None:
        u1 = User(username='john', email='john@example.com')
        u2 = User(username='susan', email='susan@example.com')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        self.assertEqual(u1.followed.all(), [])
        self.assertEqual(u1.followers.all(), [])

        u1.follow(u2)
        db.session.commit()
        self.assertTrue(u1.is_following(u2))
        self.assertEqual(u1.followed.count(), 1)
        self.assertEqual(u1.followed.first().username, 'susan')
        self.assertEqual(u2.followers.count(), 1)
        self.assertEqual(u2.followers.first().username, 'john')

        u1.unfollow(u2)
        db.session.commit()
        self.assertFalse(u1.is_following(u2))
        self.assertEqual(u1.followed.count(), 0)
        self.assertEqual(u2.followers.count(), 0)

    def test_follow_posts(self) -> None:
        # create four users
        u1 = User(username='john', email='john@example.com')
        u2 = User(username='susan', email='susan@example.com')
        u3 = User(username='mary', email='mary@example.com')
        u4 = User(username='david', email='david@example.com')
        db.session.add_all([u1, u2, u3, u4])

        # create four posts
        now = datetime.utcnow()
        p1 = Post(body="post from john", author=u1,
                  timestamp=now + timedelta(seconds=1))
        p2 = Post(body="post from susan", author=u2,
                  timestamp=now + timedelta(seconds=4))
        p3 = Post(body="post from mary", author=u3,
                  timestamp=now + timedelta(seconds=3))
        p4 = Post(body="post from david", author=u4,
                  timestamp=now + timedelta(seconds=2))
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        # setup the followers
        u1.follow(u2)  # john follows susan
        u1.follow(u4)  # john follows david
        u2.follow(u3)  # susan follows mary
        u3.follow(u4)  # mary follows david
        db.session.commit()

        # check the followed posts of each user
        f1 = u1.followed_posts().all()
        f2 = u2.followed_posts().all()
        f3 = u3.followed_posts().all()
        f4 = u4.followed_posts().all()
        self.assertEqual(f1, [p2, p4, p1])
        self.assertEqual(f2, [p2, p3])
        self.assertEqual(f3, [p3, p4])
        self.assertEqual(f4, [p4])


@pytest.fixture
def app() -> Flask:
    app = create_app(TestConfig)
    app.debug = True
    return app


class TestApp():
    """
    @pytest.fixture
    def some_db(request_ctx) -> None:
        db.create_all()

        def fin() -> None:
            db.session.remove()
            db.drop_all()
        request_ctx.addfinalizer(fin)

    def setUp(self) -> None:
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        user = User(username='test' password='1', )
    """
    # def tearDown(self) -> None:
    # db.session.remove()
    # db.drop_all()
    #  self.app_context.pop()

    """
    def non_user(self):
        self.user = User(username='test' password='1', )  # , email='john5@example.com')
        db.session.add(self.user)
        db.session.commit()
    """

    def test_home_page(self, client) -> None:
        response = client.get('/')  # test route
        assert response.status_code == 200
        assert b"landing page" in response.data, "'landing page' text not on rendered page"
        assert b"Microblog base" in response.data  # text in base
        assert b"Login" in response.data or b"Logout" in response.data   # text in navbar
        assert b"random text" not in response.data

        response_p = client.post('/')  # test route
        assert response_p.status_code == 405  # POST METHOD not allowed

    def test_index_page(self, client) -> None:
        """
        GIVEN a Flask application WHEN the '/' page is requested (GET)
        THEN check the response is valid
        """
        """
        user = User(username='test', email='test@example.com')
        db.session.add(user)
        user.set_password('1')
        db.session.commit()
        """

        response = client.get('/index')  # test route
        assert response.status_code == 302

        response = client.post('/index')  # test route
        assert response.status_code == 302
        # assert b"Need an account?" in response.data
        # assert b"Existing user?" in response.data

        # self.tearDown()


if __name__ == '__main__':
    unittest.main(verbosity=2)
    # log.INFO("tests passed, date") # but logging turned off during testing?
