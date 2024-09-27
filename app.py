from icalendar import Calendar
import pandas as pd
from collections import defaultdict
from datetime import datetime, date
from io import BytesIO
import re

# Function to categorize event based on the summary
def categorize_event(summary):
    if 'WFO' in summary:
        return 'WFO'
    elif 'WFH' in summary:
        return 'WFH'
    elif 'PL' in summary:
        return 'PL'
    elif 'OOO' in summary or 'Leave' in summary:
        return 'Leave'
    else:
        return 'Other'

# Function to extract month and year
def get_month_year(dt):
    if isinstance(dt, (datetime, date)):
        return dt.strftime('%Y-%m')
    return None

# Clean up the attendee email
def clean_attendee(attendee):
    if attendee:
        return re.sub(r'mailto:', '', attendee)
    return None

# Read the iCal file
def process_ical(ical_data):
    cal = Calendar.from_ical(ical_data)

    # Dictionary to hold event counts for each attendee by month
    attendee_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    for component in cal.walk():
        if component.name == "VEVENT":
            summary = component.get('summary', '')
            dtstart = component.get('dtstart')
            attendees = component.get('attendee')

            # Handle DTSTART as DATE or DATE-TIME
            if dtstart:
                dtstart = dtstart.dt  # Extract the date object

                if isinstance(dtstart, (datetime, date)):
                    month_year = get_month_year(dtstart)

                    # Ensure we have attendees, could be a single value or list
                    if attendees:
                        if not isinstance(attendees, list):
                            attendees = [attendees]

                        # Categorize the event and count per attendee
                        category = categorize_event(summary)
                        for attendee in attendees:
                            attendee_email = clean_attendee(str(attendee))
                            if attendee_email:
                                attendee_data[attendee_email][month_year][category] += 1
                    else:
                        print(f"Error: ATTENDEE not found for event {summary}.")
                else:
                    print("Error: DTSTART is not a valid date")
            else:
                print("Error: DTSTART not found in component")

    return attendee_data

# Generate the final report as a DataFrame
def generate_report(attendee_data):
    report_rows = []

    for attendee, months in attendee_data.items():
        for month, categories in months.items():
            row = {
                'Attendee': attendee,
                'Month': month,
                'WFO_count': categories.get('WFO', 0),
                'WFH_count': categories.get('WFH', 0),
                'Leave_count': categories.get('Leave', 0),
                'PL_count': categories.get('PL', 0),
                'Other_count': categories.get('Other', 0)
            }
            report_rows.append(row)

    # Create a DataFrame from the rows
    df = pd.DataFrame(report_rows)
    return df

# Read the iCal file
with open('7ded0e9a-ead7-4b7d-85d7-e1bf3d474c5a.ics', 'r') as file:
    ical_data = file.read()

# Process the iCal data
attendee_data = process_ical(ical_data)

# Generate the report
df_report = generate_report(attendee_data)

# Save the report to Excel
output = "output.xlsx"
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df_report.to_excel(writer, index=False, sheet_name='Monthly Attendance Report')

# Print the DataFrame or return it
print(df_report)

# Optionally, save t
