from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(250), nullable=False, index=True)


class Catalog(Base):
    __tablename__ = 'catalogs'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship(User)


class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(String(250))
    catalog_id = Column(Integer, ForeignKey('catalogs.id'), nullable=False)
    catalog = relationship(Catalog)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship(User)


engine = create_engine('postgres:///catalog')
Base.metadata.create_all(engine)
