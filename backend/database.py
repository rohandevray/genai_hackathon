from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker , declarative_base

DB_USER = "postgres"
DB_PASSWORD = "VY-_2%7EX79%40tI%2Cnd%24"
DB_HOST = "34.134.79.240"
DB_PORT ="5432"
DB_NAME = "userdb"


DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()