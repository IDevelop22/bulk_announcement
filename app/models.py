from click import DateTime
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, MetaData,DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String(255), index=True)
    job_status = Column(Integer, index=True)  #1-Added , 2- Queued, 3-Completed,4 - Partially Completed,5 - Failed
    task_id = Column(String(255), index=True)
    scheduled_for = Column(DateTime)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    number = Column(String(20), index=True)

class UserDTO(BaseModel):
    name: str   
    number:str