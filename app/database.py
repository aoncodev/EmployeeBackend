from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = 'postgresql://aon:ahid1997@13.125.250.152:5432/manager'

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,      # catch & reconnect dead TCP sockets
    pool_recycle=1800,       # recycle connections older than 30 min
    echo_pool="debug")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from app.models import Employee, AttendanceLog, BreakLog, SalaryLog
    Base.metadata.create_all(bind=engine)
