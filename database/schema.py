from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Importamos la configuración para leer la URL
try:
    from config import Config
except ModuleNotFoundError:
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from config import Config

cfg = Config()

# Lógica de conexión híbrida
db_uri = cfg.database_url

if db_uri and db_uri.startswith("postgres"):
    # Ajuste para compatibilidad con SQLAlchemy y Neon (SSL requerido)
    if "sslmode" not in db_uri:
        connector = "&" if "?" in db_uri else "?"
        db_uri += f"{connector}sslmode=require"
    
    # SQLAlchemy a veces requiere 'postgresql://' en lugar de 'postgres://'
    db_uri = db_uri.replace("postgres://", "postgresql://")
    engine = create_engine(db_uri, pool_pre_ping=True)
else:
    # Fallback a local si no hay URL de nube o estás offline
    engine = create_engine('sqlite:///database.db')

Base = declarative_base()

class MarketData(Base):
    __tablename__ = 'market_data'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

class Trades(Base):
    __tablename__ = 'trades'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    symbol = Column(String)
    side = Column(String)
    amount = Column(Float)
    price = Column(Float)

class AIAudit(Base):
    __tablename__ = 'ai_audit'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    decision = Column(String)
    confidence = Column(Float)

class BotState(Base):
    __tablename__ = 'bot_state'
    id = Column(Integer, primary_key=True)
    last_update = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    total_balance = Column(Float)
    daily_pnl = Column(Float)
    current_mode = Column(String)
    is_active = Column(Integer)

# Crear tablas si no existen (en local o en la nube)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

