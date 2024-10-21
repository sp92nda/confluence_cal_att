import re

import requests
from requests.auth import HTTPBasicAuth
import dotenv
import os
from collections import defaultdict
from datetime import datetime, date, timedelta
from dateutil.rrule import rrulestr
import pytz
import pandas as pd
from dateutil import parser
# Load environment variables
dotenv.load_dotenv()
# Set a reasonable limit (e.g., 5 years from today)
MAX_RECURRENCE_END_DATE = (datetime.now() + timedelta(days=1 * 365)).strftime("%Y%m%dT%H%M%SZ")


class Config:
    """
    Configuration class to manage environment variables and settings.
    """

    def __init__(self):
        self.confluence_base_url = os.getenv('CONFLUENCE_BASE_URL')  # Confluence base URL
        self.email = os.getenv('EMAIL')  # Atlassian account email
        self.api_token = os.getenv('API_TOKEN')  # API token
        self.calendar_id = os.getenv('CALENDAR_ID', '').split(',')  # Calendar ID

    def update_datas(self, email, api_token, calendar_id):
        self.email = email  # Atlassian account email
        self.api_token = api_token  # API token
        self.calendar_id = calendar_id.split(',') if calendar_id else ''  # Calendar ID


class CalendarService:
    """
    CalendarService class to handle calendar-related operations.
    """

    def __init__(self, config: Config, user_time_zone="Asia%2FKolkata"):
        self.config = config
        self.user_time_zone = user_time_zone

    def generate_url(self, _cal_id):
        """
        Generate the URL to fetch calendar events.
        """
        current_date = datetime.utcnow()
        start_date = (current_date - timedelta(days=90)).strftime("%Y-%m-%dT18:30:00Z")
        end_date = (current_date + timedelta(days=90)).strftime("%Y-%m-%dT18:30:00Z")

        url = (
            f"{self.config.confluence_base_url}/rest/calendar-services/1.0/calendar/events.json?"
            f"subCalendarId={_cal_id}&userTimeZoneId={self.user_time_zone}"
            f"&start={start_date}&end={end_date}"
        )
        return url

    def fetch_calendar_events(self):
        """
        Fetch the calendar data using the generated URL and authentication details.
        """
        _event_datas = []
        for _id in self.config.calendar_id:
            calendar_url = self.generate_url(_id)
            response = requests.get(calendar_url, auth=HTTPBasicAuth(self.config.email, self.config.api_token))

            if response.status_code == 200:
                _event_datas.extend(response.json().get('events', []))
            else:
                print(f"Failed to fetch calendar data. Status code: {response.status_code}")
                print(response.content)
        return _event_datas

    def clean_attendee(self, attendee):
        if attendee:
            return [attendee.get('displayName')]
        return []

    def generate_date_range(self, start_date, end_date):
        # Ensure both start_date and end_date are datetime objects
        if isinstance(start_date, datetime) is False:
            start_date = datetime.combine(start_date, datetime.min.time())
        if isinstance(end_date, datetime) is False:
            end_date = datetime.combine(end_date, datetime.min.time())

        delta = end_date - start_date
        for i in range(delta.days + 1):  # Include the end date
            yield start_date + timedelta(days=i)

    def categorize_event(self, summary):
        summary = summary.lower()
        if 'conference' in summary:
            return 'WFO'
        elif 'home' in summary:
            return 'WFH'
        elif 'leaves' in summary or 'pl' in summary or 'ooo' in summary or 'leave' in summary:
            return 'PL'
        else:
            return 'Other'

    def process_event_data(self):
        events = self.fetch_calendar_events()

        # Dictionary to hold event counts for each attendee by month
        attendee_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

        for event in events:
            summary = event.get('className', '').strip()
            dtstart = event.get('start')
            dtend = event.get('end')
            attendees = event.get('invitees', [])
            # Parse the event start and end times
            if dtstart:
                dtstart = parser.parse(dtstart)

                # If dtend is not provided, assume it's the same as dtstart (single-day event)
                if dtend:
                    dtend = parser.parse(dtend)
                else:
                    dtend = dtstart

                # Handle recurring events (if supported) - Confluence API might not return recurring events like iCal
                event_dates = list(self.generate_date_range(dtstart, dtend))  # Single event or multi-day event

                # Ensure we have attendees, could be a single value or list
                if attendees:
                    if not isinstance(attendees, list):
                        attendees = [attendees]

                    # Categorize the event and count per attendee
                    category = self.categorize_event(summary)

                    for attendee in attendees:
                        # Clean the attendee email
                        attendee_emails = self.clean_attendee(attendee)

                        for email in attendee_emails:
                            if email:
                                # For recurring events, iterate over each date in event_dates
                                for event_day in event_dates:
                                    month_year = self.get_month_year(event_day)
                                    attendee_data[email][month_year][category] += 1
                else:
                    print(f"Error: ATTENDEE not found for event {summary}.")
            else:
                print("Error: DTSTART not found in event")

        return attendee_data

    def get_month_year(self, dt):
        if isinstance(dt, (datetime, date)):
            return dt.strftime('%Y-%m')
        return None

    def generate_report(self, attendee_data, selected_month='2024-10'):
        report_rows = []
        for attendee, months in attendee_data.items():
            for month, categories in months.items():
                if selected_month and selected_month != month:
                    continue  # Filter by the selected month if provided
                row = {
                    'Attendee': attendee,
                    'Month': month,
                    'WFO': categories.get('WFO', 0),
                    'WFH': categories.get('WFH', 0),
                    'Leave': categories.get('Leave', 0) + categories.get('PL', 0),
                    'Other': categories.get('Other', 0),
                    'Total Days': categories.get('WFO', 0) + categories.get('WFH', 0) + categories.get('Leave', 0) +
                                  categories.get('Leave', 0) + categories.get('PL', 0) + categories.get('Other', 0),
                }
                report_rows.append(row)
        # Create a DataFrame from the rows
        df = pd.DataFrame(report_rows)
        return df

if __name__ == "__main__":
    cal = CalendarService(Config())
    event_data = cal.process_event_data()
    cal.generate_report(event_data)
