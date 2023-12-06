## bulk_announcement

### Problem Statement
CASE STUDY:
We have identified an issue in our current system. Employers send announcements to
their employees (1000+) via our WhatsApp chatbot. An employer logs into our system,
types in the announcement (e.g., "Our end of year party is on Saturday evening!") and has
a choice to send it immediately or schedule the announcement to go out at a specific
future time. We have a scheduler (cron job) that runs every 5 minutes to check whether
any announcements need to be sent. However, we have found that some employees are
receiving the same announcements more than once.

______________________________________________________________
### TASK:
  * Propose at least 2 reasons why employees might be receiving the same
    announcement more than once.
  * Propose an architecture that could fix this problem.
  *  Develop a quick Proof of Concept (PoC) using FastAPI and any other frameworks
    you choose, to show how your solution could work.
      1. Please do not connect the PoC to the WhatsApp Cloud API.
      2. You only need to simulate the Employer Web Portal with an API that such a
    portal would call.
  *  Write unit tests for the PoC.


     ## Investigation
  * From the problem statement I can suspect a few causes that might be the problem
      1. The Cron Job could overlapping and kicking off multiple "runs" to process the same message,this could be as a result of a few things:-
          * The sendmessage cloud api task could be taking long resulting in the total time to process taking longer than 5 minutes.This would be an issue if the cron job only updates the job at the end of the               run and not as soon as the job has begun processing.
          * There are multiple worker nodes that run in parallel to process the announcements in the DB and there may be overlapping processing due to improper transaction locks or improper reads due to not                 using database transactions.The 2 above are assuming the cron job runs directtly on the database without any queue management.
          *  There retry/timeout mechanism,if there is one implemented,could be misconfigured resulting in multiple retries without proper exception checking and proper back off to cater for temporary network               issues
          * Depending on the database design,a message could be targeted to groups of users instead of indivisual users and some users might belong to more than one group.
        
      2. An architecture that could possibly fix this would be to use a dedicated queuing system instead of cron because such a framework would have support for.
          * Sequential queue processing,even if you have multiple worker nodes,there is minimal chance of them accessing the same message
          * Easily Configurable retry and timeout properties to target specific errors for retry and limiting long running tasks with timeouts
          * Built in data store like redis,reducing load on the database.
          * GUI tools to monitor jobs
     ## Proposed Solution
    * Based on the requirements to implement the solution with FastAPI,I have decided to try and resolve the issue by replacing the cron job with a dedicated queue managagment framework called Celery.
    * I have chosen Celery for the following reasons:
          1. It has good support for Fast API with good community support(which is helpful as I am not a seasoned python developer)
          2. It uses Redis as a message store which means it is easy to run on docker and can be queried to build monitoring dashboards 
          3. It has a built in gui tool : Flower that you can use to monitor jobs without building a ui from scratch
          4.It supports periodic and manual tasks that suits the current scenario veery well.      

    ## Actual Solution
    * The POC that I have built is divided into 2 parts(an API for accepting new annoucements and storing them ) and celery worker tasks that check the database for updates and create subtasks for each message       sent out
     * The flow is a follows
         1. User adds a message from the web portal and can choose whether -with the following atributes(message_content,scheduled_for_date(optional))- a message without a scheduled_for_date is marked for                  immediate release.
         2. The API saves the message in a mysql database with job_status property,If the message does not have a schedule for date then a send_announcement celery task will also be created.
         3.There is a periodic celery task that checks every 5 minutes for new messages in the database that have a past scheduled_for date and have not been qued.
         4.Once a job is qued the task will first check in the database to compile a list of users that should recieve the text,currently it is all users.Once the list is compiled,The task will create                     individual sub tasks within the main task for each of the users to provide a more granular way of tracking which message has been processed successfully.
      ## Possible Improvements
    * Due to time constraints there is a few things that I still would want to improve on that I couldn't because I wanted to try and stick to the 4 hour limit as close as possbile
        1. Learn and write more Idiomatic Python,currently the project is not well structured and would not adhere to Python specific ways of doing this,it is more of a mix and mash of concepts from different             languages that I have used before but implemented in python.
        2. Add domain validations like checking if a similar message has been scheduled before within a specific period.
        3. Decouple my celery tasks from the concrete db layer for easier mocking
        4. Add Tests,no one likes cowbow developers.
        5. Properly store Config in secrets and environment variables and not out in the wild,had some issues with python virtual environment on my machine thats why my config is all over.
      
      ### Additional Info
        1. There is a json file that prepolulates the users in the database on startup.
        2. The actual send message function checks the user's name to simulate different scenarios like long running tasks and excpected errors.
        3. docker-compose up should be sufficient to run the project,
        
