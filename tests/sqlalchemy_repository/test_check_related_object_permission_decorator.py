import flask
import pytest
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

from flask_jsonapi import exceptions
from flask_jsonapi.resource_repositories import sqlalchemy_repositories
from flask_jsonapi.resource_repositories.sqlalchemy_permission_decorators import check_related_object_permission
from tests.sqlalchemy_repository import conftest


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
def user_repository(db_session):
    class UserRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = User
        instance_name = 'user'
        session = db_session

    return UserRepository()


@pytest.fixture
def restricted_address_repository(db_session):
    class AddressRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = Address
        instance_name = 'address'
        session = db_session

        @check_related_object_permission('user_id', check_user_id)
        def create(self, data, **kwargs):
            return super().create(data, **kwargs)

    return AddressRepository()


def check_user_id(id):
    return flask.request.user_id == id


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestCheckRelatedObjectPermission:
    def test_check_permission_valid(self, app, user_repository, restricted_address_repository):
        bean = user_repository.create({'name': 'Mr. Bean'})
        user_repository.create({'name': 'Darth Vader'})
        with conftest.request_with_user_id(app, bean.id):
            address = restricted_address_repository.create({'email': 'bean@email.com', 'user_id': bean.id})
            assert address.user_id == bean.id

    def test_check_permission_invalid(self, app, user_repository, restricted_address_repository):
        bean = user_repository.create({'name': 'Mr. Bean'})
        vader = user_repository.create({'name': 'Darth Vader'})
        with conftest.request_with_user_id(app, bean.id):
            with pytest.raises(exceptions.ForbiddenError):
                restricted_address_repository.create({'email': 'bean@email.com', 'user_id': vader.id})
