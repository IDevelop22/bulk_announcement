from fastapi import FastAPI, HTTPException, status, Body
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from app.celery_worker import send_announcements
from app.data_access import DataAccess, MessageInput
from app.models import Base, Announcement, UserDTO

app = FastAPI()
data_access = DataAccess(create_engine("mysql+mysqlconnector://fastapi_user:fastapi_password@db/fastapi_db"))

@app.on_event("startup")
async def startup_event():
    data_access.initialize_database()
    data_access.clear_tables()
    data_access.add_users_from_file("app/users.json")

@app.post("/add-message/", response_model=dict)
async def add_message(message: MessageInput):
    result = data_access.add_message(message)
    if result.scheduled_for is None:
        # If the scheduled_for date is not provided then we assume this is for immediate release and queue a direct job
        task = send_announcements.delay(result.id)
    return JSONResponse(content={"id": result.id,"url": "http://localhost:5556/dashboard"})

@app.get("/get-message/{message_id}", status_code=status.HTTP_200_OK)
async def get_message(message_id: int):
    announcement = data_access.get_message(message_id)
    return announcement

@app.get("/get-all-users/", status_code=status.HTTP_200_OK)
async def get_all_users():
    users = data_access.get_all_users()
    return users
