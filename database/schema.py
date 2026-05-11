from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime\
from sqlalchemy.ext.declarative import declarative_base\
from sqlalchemy.orm import sessionmaker\
\
engine = create_engine('sqlite:///database.db')\
Base = declarative_base()\
\
class MarketData(Base):\
    __tablename__ = 'market_data'\
    id = Column(Integer, primary_key=True)\
    timestamp = Column(DateTime)\
    open = Column(Float)\
    high = Column(Float)\
    low = Column(Float)\
    close = Column(Float)\
    volume = Column(Float)\
\
class Trades(Base):\
    __tablename__ = 'trades'\
    id = Column(Integer, primary_key=True)\
    timestamp = Column(DateTime)\
    symbol = Column(String)\
    side = Column(String)\
    amount = Column(Float)\
    price = Column(Float)\
\
class AIAudit(Base):\
    __tablename__ = 'ai_audit'\
    id = Column(Integer, primary_key=True)\
    timestamp = Column(DateTime)\
    decision = Column(String)\
    confidence = Column(Float)\
\
Base.metadata.create_all(engine)