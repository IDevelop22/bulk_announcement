from datetime import datetime
import time
from celery import Celery, group
from celery.schedules import crontab
from sqlalchemy import create_engine

from app.data_access import DataAccess

# Create a Celery instance
celery = Celery(__name__)

# Configure Celery to use Redis as the message broker and result backend
celery.conf.broker_url = "redis://redis:6379/0"
celery.conf.result_backend = "redis://redis:6379/0"

# Initialize the DataAccess instance with a MySQL database engine
data_access = DataAccess(create_engine("mysql+mysqlconnector://fastapi_user:fastapi_password@db/fastapi_db"))

# Celery task to send scheduled announcements
@celery.task(name="send_scheduled_announcements", ignore_result=True)
def send_scheduled_announcements():
    try:
        # Get unprocessed announcements scheduled after the current datetime
        messages = data_access.get_unprocessed_announcements_after_datetime(before_datetime=datetime.now())
        
        print(f"Number of waiting messages: {len(messages) > 0}")

        if messages:
            # Iterate through the scheduled messages and delay the send_announcements task
            for message in messages:
                send_announcements.delay(message.id)
        else:
            print("No tasks to schedule")

    except Exception as e:
        print(f"An error occurred processing scheduled announcements: {e}")

# Celery task to send announcements based on a unqueued records in the database
@celery.task(name="send_announcements", max_retries=5, retry_backoff=2)
def send_announcements(message_id):
    try:
        # Retrieve the message with the given message_id
        message = data_access.get_message(message_id)

        if message:
            # Update the job_status in the database to queued
            message.job_status = 2
            data_access.update_message_status(message.id, 2)

        # Get all users,Ideally we would have user groups(either by department,
        #   function,Business Unit etc) so that we can better segment announcements
        users = data_access.get_all_users()

        # Create subtasks for each user and send them as a group
        subtasks = [send_message_task.subtask((user.name, message.content)) for user in users]
        subtasks_group = group(subtasks)
        results = subtasks_group.apply_async()

        # Wait for subtasks to complete and count successful ones
        subtasks_results = results.join()
        successful_subtasks = sum(result.result == "task completed" for result in subtasks_results)

        # Check success criteria and update message status accordingly
        if successful_subtasks == len(subtasks_results):
            data_access.update_message_status(message.id, 3)
        elif successful_subtasks >= 0.8 * len(subtasks_results):
            data_access.update_message_status(message.id, 4)
        else:
            data_access.update_message_status(message.id, 5)
            raise ValueError("Failed to meet success criteria")

    except Exception as e:
        print(f"An error occurred: {e}")
        data_access.update_message_status(message.id, 5)

# Celery task to send a message for a specific user
@celery.task(name="send_message_task", max_retries=3, retry_backoff=2, soft_timeout=5)
def send_message_task(user, message):
    try:
        # Call the send_message function for the user and message
        send_message(user, message)
    except Exception as e:
        print(f"An error occurred: {e}")
        # Retry the task after a backoff period
        raise send_message_task.retry(countdown=2, exc=e)

# Function to simulate sending a message for a specific user
def send_message(user, message):
    print(f"Processing user Number: {user}, Message Content: {message}")

    if user == "long":
        # Simulate a long running task (e.g., 10 seconds sleep)
        time.sleep(10)
        return "task completed"

    if user == "error":
        # Raise an expected error to simulate retry
        raise ValueError("Encountered a retriably expected error condition")

    return "task completed"

# Configure the Celery Beat schedule to run send_scheduled_announcements every 5 minutes
celery.conf.beat_schedule = {
    'check-database-every-5-minutes': {
        'task': 'send_scheduled_announcements',
        'schedule': crontab(minute='*/1'),  # Reduce to 1 for easier testing
    }
}
