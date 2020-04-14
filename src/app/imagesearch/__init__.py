
from flask import Blueprint

bp = Blueprint('imagesearch', __name__)

from app.imagesearch import webstreaming  # NOQA
