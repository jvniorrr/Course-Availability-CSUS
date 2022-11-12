import requests
import json
import re, os, time, logging, sys, random
from twilio.rest import Client
from notifypy import Notify
from dotenv import load_dotenv

load_dotenv()


API_CSUS = "https://classschedule.webhost.csus.edu/api/cs"

DEPARTMENT_REGEX = re.compile('[a-zA-Z]{2,4}')
COURSE_NUM_REGEX = re.compile('\d{2,4}[A-Za-z]?$')


class SacSchedule():
    def __init__(self) -> None:
        config = open('config.json', 'r', encoding="utf-8")
        _data = json.load(config)
        config.close()

        self.course = _data.get('course')
        self.season = _data.get('season')
        self.year = _data.get('year')
        self.dept = re.search(DEPARTMENT_REGEX, self.course).group(0)
        self.courseNum = re.search(COURSE_NUM_REGEX, self.course).group(0)

        if _data.get('twilio').get('utilize') == True:
            account_sid = os.environ['TWILIO_ACCOUNT_SID']
            auth_token = os.environ['TWILIO_AUTH_TOKEN']
            self.client = Client(account_sid, auth_token)
            self.toNum = _data.get('twilio').get('to')
            self.fromNum = _data.get('twilio').get('from')

        # notification object
        self.notification = Notify()



    def getCatalog(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        found = False

        while not found:
            try:
                logger.info("Searching for availability...")
                response = requests.get(f'{API_CSUS}/{self.season}-{self.year}/{self.dept}', headers=headers)
                response.raise_for_status()
                courses = response.json()

                if not courses:
                    logger.info("No courses found for the specified query. Exiting script")
                    found = True
                    return

                for course in courses:
                    # loop through course section
                    if course.get('catalog_number') == self.courseNum:
                        for section in course.get('sections'):
                            # TODO: Add waitlists checks
                            if int(section.get("seats_available")) > 0 and (section.get('component') == 'Discussion' or section.get('component') == 'Lecture'):
                                logger.info("Available course was found!")

                                courseInfo = f"Course: {section.get('subject_code')} {section.get('catalog_number')} ({section.get('class_section')}) - {section.get('class_title')}\n"
                                professorInfo = f"Professor: {section.get('instructor')}\n"
                                classInfo = f"Schedule: {section.get('days')} {section.get('start_time')}-{section.get('end_time')}"
                                notificationMessage = courseInfo + professorInfo + classInfo
                                logger.info(notificationMessage)
                                if self.client:
                                    message = self.client.messages.create(body=notificationMessage, from_=f"{self.fromNum}", to=f"{self.toNum}")
                                self.notification.title = "Found an available course"
                                self.notification.message = notificationMessage
                                self.notification.send()
                                found = True
                                break
                

            except requests.exceptions.HTTPError as e:
                logger.error("Error retrieving web page.")
                logger.error(e)
                continue
                
            except Exception as e:
                logger.error('Uncaught error')
                logger.error(e)
                continue

            if not found:
                time.sleep(random.randint(30, 60))


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    stdout = logging.StreamHandler(stream=sys.stdout)
    stdout.setFormatter(logging.Formatter("[%(asctime)s.%(msecs)03d] [%(levelname)s] - %(message)s", "%H:%M:%S"))
    logger.addHandler(stdout)
    c = SacSchedule()
    c.getCatalog()
