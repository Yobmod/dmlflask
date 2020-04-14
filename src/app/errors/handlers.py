from flask import render_template

from app import db
from app.errors import bp

from app.types import HTML
from typing import Tuple


@bp.errorhandler(404)
def not_found_error(error: Exception) -> Tuple[HTML, int]:
    rendered: HTML = render_template('errors/404.html')
    return (rendered, 404)


@bp.errorhandler(500)
def internal_error(error: Exception) -> Tuple[HTML, int]:
    db.session.rollback()
    rendered: HTML = render_template('errors/500.html')
    return (rendered, 500)
