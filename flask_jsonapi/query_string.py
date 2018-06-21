import math

import flask
from six.moves.urllib import parse
from werkzeug import datastructures

from flask_jsonapi import exceptions


class QueryStringParserBase:
    def parse(self):
        raise NotImplementedError


class PaginationBase(QueryStringParserBase):
    def get_links(self, *args, **kwargs):
        raise NotImplementedError


class SizeNumberPagination(PaginationBase):
    def parse(self):
        size = flask.request.args.get('page[size]')
        number = flask.request.args.get('page[number]')
        if size is None and number is None:
            return {}
        elif size is None or number is None:
            raise exceptions.InvalidPage('One of page parameters wrongly or not specified.')
        else:
            try:
                size = int(size)
                number = int(number)
            except ValueError:
                raise exceptions.InvalidPage('Page parameters must be integers.')
            return {'size': size, 'number': number}

    def get_links(self, page_size, current_page, total_count):
        last_page = math.ceil(total_count / page_size)
        previous_page = current_page - 1 if current_page > 1 else None
        next_page = current_page + 1 if current_page < last_page else None
        return self._format_links(current_page, previous_page, next_page, last_page)

    def _format_links(self, current_page, previous_page, next_page, last_page):
        request_args = flask.request.args.copy()
        request_args.pop('page[number]')
        base_link = '{}?{}'.format(flask.request.base_url, parse.unquote(parse.urlencode(request_args)))
        format_query_string = base_link + '&page[number]={}'
        return {
            'self': format_query_string.format(current_page),
            'first': format_query_string.format(1),
            'previous': format_query_string.format(previous_page) if previous_page else None,
            'next': format_query_string.format(next_page) if next_page else None,
            'last': format_query_string.format(last_page),
        }


class IncludeParser:
    def __init__(self, schema):
        self.schema_object = schema()

    def parse(self):
        include_parameter = flask.request.args.get('include')
        if include_parameter:
            include_fields = tuple(include_parameter.replace('-', '_').split(','))
            try:
                self.schema_object.check_relations(include_fields)
            except ValueError as exc:
                raise exceptions.InvalidInclude(detail=str(exc))
            return include_fields
        else:
            return tuple()


class SparseFieldsParser:
    def __init__(self, schema):
        self.schema_object = schema()

    @property
    def request_filters(self) -> datastructures.MultiDict:
        return datastructures.MultiDict(
            [(key, value) for key, value
             in flask.request.args.items(multi=True)
             if key.startswith('fields')]
        )

    def parse(self):
        sparse_fields = []
        for key, value in self.request_filters.items(multi=True):
            resource = key.replace('fields[', '').replace(']', '')
            fields_list = value.replace('-', '_').split(',')
            if resource == self.schema_object.opts.type_:
                field_paths = fields_list
            else:
                field_paths = ['{}.{}'.format(resource.replace('-', '_'), value) for value in fields_list]
            sparse_fields += field_paths
        if not sparse_fields:
            return None
        return tuple(sparse_fields)