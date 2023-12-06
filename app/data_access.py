from datetime import datetime
import json
from operator import and_
from fastapi import Body, FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, MetaData
from sqlalchemy.orm import sessionmaker
from typing import List, Optional

from app.models import Announcement, Base, User

# Define a Pydantic model for input validation
class MessageInput(BaseModel):
    content: str
    job_status: int
    task_id: str
    scheduled_for: Optional[datetime]

# Define a class for data access operations
class DataAccess:
    def __init__(self, engine):
        self.engine = engine
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.metadata = MetaData()

    def initialize_database(self):
        # Create database tables
        Base.metadata.create_all(bind=self.engine)

    def clear_tables(self):
        # Clear user and announcement tables
        db = self.SessionLocal()
        db.query(User).delete()
        db.query(Announcement).delete()
        db.commit()
        db.close()

    def add_users_from_file(self, file_path):
        # Add users from a JSON file to the database
        db = self.SessionLocal()
        try:
            with open(file_path) as file:
                users_data = json.load(file)
                users = [User(**user) for user in users_data]
                db.add_all(users)
                db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        finally:
            db.close()

    def add_message(self, message_input: MessageInput):
        # Add a new message to the database
        db = self.SessionLocal()
        announcement = Announcement(
            content=message_input.content,
            job_status=message_input.job_status,
            task_id=message_input.task_id,
            scheduled_for=message_input.scheduled_for,
        )

        db.add(announcement)
        db.commit()
        db.refresh(announcement)
        db.close()

        return announcement

    def get_message(self, message_id: int):
        # Retrieve a message by ID
        db = self.SessionLocal()
        message = db.query(Announcement).filter(Announcement.id == message_id).first()
        db.close()
        if message is None:
            raise HTTPException(status_code=404, detail="Message not found")
        return message

    def get_all_users(self):
        # Retrieve all users from the database
        db = self.SessionLocal()
        users = db.query(User).all()
        db.close()
        return users

    def update_message_status(self, message_id: int, new_status: int):
        # Update the job_status of a message in the database
        db = self.SessionLocal()
        try:
            db.query(Announcement).filter(Announcement.id == message_id).update({"job_status": new_status})
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    def get_unprocessed_announcements_after_datetime(self, before_datetime: datetime) -> list:
        # Retrieve unprocessed announcements scheduled after a given datetime
        db = self.SessionLocal()
        try:
            messages = (
                db.query(Announcement)
                .filter(and_(Announcement.scheduled_for < before_datetime, Announcement.job_status < 2))
                .all()
            )
            return messages
        finally:
            db.close()
