import functools
from typing import Callable, TypeVar, List

from sqlalchemy.orm import attributes
from sqlalchemy.orm import query as orm_query

from flask_jsonapi import exceptions
from flask_jsonapi.resource_repositories import sqlalchemy_utils


Id = TypeVar('Id')


def check_related_object_permission(id_attribute, has_permission_to_object: Callable[[Id], bool]):
    def wrap(func):
        @functools.wraps(func)
        def wrapped(self, data, **kwargs):
            id = data.get(id_attribute)
            if id:
                if not has_permission_to_object(id):
                    raise exceptions.ForbiddenError(
                        detail="Access to instance with id '{}' forbidden".format(id))
            return func(self, data, **kwargs)
        return wrapped
    return wrap


def filter_by_related_objects_permission(model_attribute: attributes.InstrumentedAttribute,
                                         get_object_list: Callable[[], list]):
    def wrap(get_query):
        @functools.wraps(get_query)
        def wrapped(self):
            obj_id_list = [obj.id for obj in get_object_list()]
            query = get_query(self)
            query = query.filter(model_attribute.in_(obj_id_list))
            return query

        return wrapped

    return wrap


def filter_by_permission_method(filter_method: Callable[[orm_query.Query], orm_query.Query],
                                relationships_to_join: List[attributes.InstrumentedAttribute]=None):
    if relationships_to_join is None:
        relationships_to_join = []

    def wrap(get_query):
        @functools.wraps(get_query)
        def wrapped(self):
            query = get_query(self)
            query = sqlalchemy_utils.join_query_on_many_relationships_if_needed(query, relationships_to_join)
            query = filter_method(query)
            return query
        return wrapped
    return wrap
