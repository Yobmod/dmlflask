from typing import Any, List, Union, Dict, cast, NewType, Optional as Opt, TypeVar, Type  # noqa: F401
from werkzeug import Response
from sqlalchemy.orm import Session

# jsonType = Dict[str, Any]
jsonType = NewType('jsonType', Dict[str, Any])
HTML = str
URL = str


# class httpResponse(Response):
#     """Subclass of flask.Response for type hinting"""

#     def __init__(self) -> None:
#         self.__class__.__name__ = 'Response'
#     # pass


httpResponse = Response


# class jsonResponse(Response):
#     """Subclass of flask.Response for type hinting"""
#     pass


jsonResponse = Response


class SearchSession(Session):
    """Subclass of sqlalchemy.Session for type hinting"""
    _changes: Dict[str, List[Any]] = {'add': [], 'update': [], 'delete': []}
