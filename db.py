import sqlalchemy
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import os
import sys

Base = declarative_base()

class Volume(Base):
    __tablename__ = 'volumes'

    id = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    label = sqlalchemy.Column(sqlalchemy.String)
    applications = relationship("Application", back_populates="volume")

class Application(Base):
    __tablename__ = 'applications'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    appid = sqlalchemy.Column(sqlalchemy.BigInteger)
    name = sqlalchemy.Column(sqlalchemy.String)
    volume_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('volumes.id'))
    volume = relationship("Volume", back_populates="applications")
    manifests = relationship("Manifest", back_populates="application", single_parent=True, cascade="all, delete-orphan")
    location = sqlalchemy.Column(sqlalchemy.String)

    def find(session, appid):
        try:
            return session.query(Application).filter_by(appid=appid).first().volume
        except AttributeError:
            return None

class Manifest(Base):
    __tablename__ = 'manifests'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    application_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('applications.id'))
    application = relationship("Application", back_populates="manifests")
    depot = sqlalchemy.Column(sqlalchemy.BigInteger)
    manifest = sqlalchemy.Column(sqlalchemy.String)

engine = None

def init():
    global engine
    engine = sqlalchemy.create_engine(f'sqlite:///{os.path.join(os.getenv('HOMEPATH'), 'shura.db')}')
    Base.metadata.create_all(engine)
    return engine

def session():
    if engine is None:
        init()
    Session = sessionmaker(bind=engine)
    return Session()