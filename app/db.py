# app/db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "postgresql+psycopg2://postgres:123@localhost/gennis_bot"


engine = create_engine(DATABASE_URL, echo=True)  # echo=True for debug
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

