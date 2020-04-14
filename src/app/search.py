from flask import current_app

from typing import List, Tuple
from flask_sqlalchemy.model import Model


def add_to_index(index: str, model: Model) -> None:
    if not current_app.elasticsearch:
        return  # if no elasticsearch url in env, do nothing
    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model, field)
    current_app.elasticsearch.index(index=index, doc_type=index, id=model.id, body=payload)


def remove_from_index(index: str, model: Model) -> None:
    if not current_app.elasticsearch:
        return  # if no elasticsearch url in env, do nothing
    current_app.elasticsearch.delete(index=index, doc_type=index, id=model.id)


def query_index(index: str, query: str, page: int, per_page: int) -> Tuple[List[int], int]:
    if not current_app.elasticsearch:
        return ([], 0)
    search = current_app.elasticsearch.search(
        index=index, doc_type=index,
        body={'query': {'multi_match': {'query': query, 'fields': ['*']}},
              'from': (page - 1) * per_page, 'size': per_page})
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return (ids, search['hits']['total'])


def delete_index(index: str) -> None:
    if not current_app.elasticsearch:
        return
    if index in current_app.elasticsearch.indices.get_alias():
        current_app.elasticsearch.indices.delete(index=index)
