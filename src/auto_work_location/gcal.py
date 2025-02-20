import os
from datetime import datetime, timedelta
from time import strptime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import logging

logger = logging.getLogger("auto_work_location")
logger.setLevel(logging.DEBUG)
conversion_map = {
    'homeOffice': 'HOME',
    'officeLocation': 'OFFICE'
}

def get_calendar_service(token_file, credentials_file, scopes):
    """Authenticate and return the Google Calendar API service."""
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
            creds = flow.run_local_server(port=0)
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)


def get_todays_workingLocation_event(service):
    """Get today's work event from the calendar."""
    today = datetime.today().strftime('%Y-%m-%d')
    event = get_workingLocation_event(service, today)
    return event

def get_workingLocation_event(service, day):
    """Get the workingLocationEvent from the calendar for the given date."""
    day_date = strptime(day, "%Y-%m-%d")
    day_start = datetime(day_date.tm_year, day_date.tm_mon, day_date.tm_mday, 0, 0, 0)

    day_end = (day_start + timedelta(days=1)).isoformat() + 'Z'  # Start of tomorrow (end of today)

    events_result = service.events().list(calendarId="primary",
                                        timeMin=day_start.isoformat() + 'Z',
                                        timeMax=day_end,
                                        singleEvents=True, # Important for recurring events
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])

    workingLocationEvents = [event for event in events if event.get("eventType") == "workingLocation" and event.get("start").get("date") == day]
    if len(workingLocationEvents) == 0:
        logger.info(f"No workingLocationEvent found for {day}")
        return None

    if len(workingLocationEvents) > 1:
        logger.warning(f"Multiple workingLocationEvents found for {day}")
        raise ValueError(f"Multiple workingLocationEvents found for {day}")

    return workingLocationEvents[0]

def get_working_location(day, service):
    """Get the office location from the calendar for the given date."""
    event = get_workingLocation_event(service, day)

    if event:
        workingLocation = event['workingLocationProperties']['type']
        return conversion_map.get(workingLocation, "OTHER")

    return None

def update_working_location(day, location, service):
    event = get_workingLocation_event(service, day)
    create = False

    if event:
        if conversion_map.get(event['workingLocationProperties']['type'], "OTHER") == location:
            logger.info(f"Location already set to {location}")
            return event
    else:
        create = True
        next_day = (datetime.strptime(day, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        # Create the event :
        event = {
            'eventType': 'workingLocation',
            'transparency': 'transparent',
            'visibility': 'public',
            'start': {
                'date': day
            },
            'end': {
                'date': next_day
            }
        }

        
    """Update the calendar event with the new location."""
    if location == "HOME":
        event['workingLocationProperties'] = {'homeOffice': {}, 'type': 'homeOffice'}
        event['summary'] = 'Domicile'

    elif location == "OFFICE":
        event['workingLocationProperties'] = {'type': 'officeLocation', 'officeLocation': {}}
        event['summary'] = 'Bureau'

    if create:
        event = service.events().insert(calendarId='primary', body=event).execute()
        logger.info(f"Created event: {event['summary']} with location: {event['workingLocationProperties']['type']}")
    else:
        event = service.events().update(calendarId='primary', eventId=event['id'], body=event).execute()
        logger.info(f"Updated event: {event['summary']} with location: {event['workingLocationProperties']['type']}")

    return event