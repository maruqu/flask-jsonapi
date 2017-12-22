from contextlib import contextmanager

import flask
import pytest
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

from flask_jsonapi.resource_repositories import sqlalchemy_repositories
from flask_jsonapi.resource_repositories import sqlalchemy_permission_decorators as permissions


Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String)
    addresses = orm.relationship("Address", backref="user")


class Address(Base):
    __tablename__ = 'address'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    email = sqlalchemy.Column(sqlalchemy.String)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('user.id'))


@pytest.fixture
def restricted_query_user_repository(db_session):
    class UserRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = User
        instance_name = 'user'
        session = db_session

        def get_query(self):
            query = super().get_query()
            query = query.filter(User.id == flask.request.user_id)
            return query

    return UserRepository()


@pytest.fixture
def restricted_query_address_repository(db_session, restricted_query_user_repository):
    class AddressRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = Address
        instance_name = 'address'
        session = db_session

        @permissions.filter_by_related_objects_permission(Address.user_id, restricted_query_user_repository.get_list)
        def get_query(self):
            return super().get_query()

    return AddressRepository()


@contextmanager
def user_id_in_request(app, user_id):
    with app.test_request_context():
        flask.request.user_id = user_id
        yield


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestFilterByRelatedObjectsPermission:
    def test_restricted_query_user_repository_returns_only_current_user(self, app, restricted_query_user_repository):
        bean = restricted_query_user_repository.create({'name': 'Mr. Bean'})
        restricted_query_user_repository.create({'name': 'Darth Vader'})
        with user_id_in_request(app, bean.id):
            users = restricted_query_user_repository.get_list()
            assert len(users) == 1
            assert users[0].name == 'Mr. Bean'

    def test_filter_by_related_objects_permission_existing(self, app, restricted_query_user_repository,
                                                           restricted_query_address_repository):
        bean_address = Address(email='bean@email.com')
        vader_address = Address(email='vader@email.com')
        other_vader_address = Address(email='vader@sith.com')
        bean = restricted_query_user_repository.create({'name': 'Mr. Bean', 'addresses': [bean_address]})
        restricted_query_user_repository.create({'name': 'Darth Vader', 'addresses': [vader_address, other_vader_address]})
        with user_id_in_request(app, bean.id):
            addresses = restricted_query_address_repository.get_list()
            assert len(addresses) == 1
            assert addresses[0].email == 'bean@email.com'

    def test_filter_by_related_objects_permission_not_existing(self, app, restricted_query_user_repository,
                                                               restricted_query_address_repository):
        vader_address = Address(email='vader@email.com')
        bean = restricted_query_user_repository.create({'name': 'Mr. Bean'})
        restricted_query_user_repository.create({'name': 'Darth Vader', 'addresses': [vader_address]})
        with user_id_in_request(app, bean.id):
            addresses = restricted_query_address_repository.get_list()
            assert len(addresses) == 0
