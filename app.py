from icalendar import Calendar
import pandas as pd
from collections import defaultdict
from datetime import datetime, date, timedelta
from io import BytesIO
from flask import Flask, request, render_template, send_file, session, flash
import re
from dateutil.rrule import rrulestr
from dateutil.parser import parse as dateutil_parse
import pytz
# Set a reasonable limit (e.g., 5 years from today)
MAX_RECURRENCE_END_DATE = (datetime.now() + timedelta(days=1*365)).strftime("%Y%m%dT%H%M%SZ")

app = Flask(__name__)

app.secret_key = 'your_secret_key'
# Function to filter the DataFrame by selected month and year
def filter_by_month_year(df, selected_month):
    # Convert the 'Date' column to datetime
    df['Date'] = pd.to_datetime(df['Date'])

    # Extract year and month from the selected month input
    selected_month = pd.to_datetime(selected_month + "-01")  # Adding "-01" to make it a valid date

    # Filter the DataFrame for the selected month and year
    filtered_df = df[(df['Date'].dt.year == selected_month.year) & (df['Date'].dt.month == selected_month.month)]
    return filtered_df

# Function to categorize event based on the summary
def categorize_event(summary):
    summary = summary.lower()
    if 'wfo' in summary:
        return 'WFO'
    elif 'wfh' in summary:
        return 'WFH'
    elif 'pl' in summary or 'ooo' in summary or 'leave' in summary:
        return 'PL'
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
        # Remove 'mailto:' and split multiple attendees
        return [email.strip() for email in re.sub(r'mailto:', '', attendee).split(';')]
    return []

# Generate date range from start to end date (inclusive)
def generate_date_range(start_date, end_date):
    # Ensure both start_date and end_date are datetime objects
    if isinstance(start_date, datetime) is False:
        start_date = datetime.combine(start_date, datetime.min.time())
    if isinstance(end_date, datetime) is False:
        end_date = datetime.combine(end_date, datetime.min.time())

    delta = end_date - start_date
    for i in range(delta.days + 1):  # Include the end date
        yield start_date + timedelta(days=i)


def process_ical(ical_data):
    cal = Calendar.from_ical(ical_data)

    # Dictionary to hold event counts for each attendee by month
    attendee_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    for component in cal.walk():
        if component.name == "VEVENT":
            summary = component.get('summary', '').strip()
            dtstart = component.get('dtstart')
            dtend = component.get('dtend')
            attendees = component.get('attendee')
            rrule = component.get('rrule')  # Get the RRULE property if it exists

            if dtstart:
                dtstart = dtstart.dt  # Extract the start date

                # If dtstart is a date object, convert it to a datetime object at midnight
                if isinstance(dtstart, datetime) is False:
                    dtstart = datetime.combine(dtstart, datetime.min.time())

                dtend = dtend.dt if dtend else dtstart  # Handle single-day events

                # Ensure dtend is exclusive for multi-day events
                if dtstart == dtend:
                    dtend = dtstart  # Single-day event
                else:
                    dtend = dtend - timedelta(days=1)  # Adjust to make dtend exclusive

                event_dates = []

                if rrule:
                    rrule_str = str(rrule.to_ical().decode('utf-8'))

                    # Option 1: Ensure DTSTART is timezone-aware (UTC)
                    if dtstart.tzinfo is None:
                        dtstart = dtstart.replace(tzinfo=pytz.UTC)

                    # If RRULE lacks UNTIL or COUNT, add an UNTIL date to cap it
                    if 'UNTIL' not in rrule and 'COUNT' not in rrule:
                        # Inject an UNTIL value that is 5 years from now
                        rrule_str = rrule_str.strip() + f";UNTIL={MAX_RECURRENCE_END_DATE}"

                    # Parse the updated RRULE with the new UNTIL value
                    rule = rrulestr(rrule_str, dtstart=dtstart)

                    # Generate the list of event dates
                    event_dates = list(rule)
                else:
                    # If no RRULE, treat it as a normal event
                    event_dates = list(generate_date_range(dtstart, dtend))

                # Ensure we have attendees, could be a single value or list
                if attendees:
                    if not isinstance(attendees, list):
                        attendees = [attendees]

                    # Categorize the event and count per attendee
                    category = categorize_event(summary)

                    for attendee in attendees:
                        # Split and clean multiple attendees
                        attendee_emails = clean_attendee(str(attendee))

                        for email in attendee_emails:
                            if email:
                                # For recurring events, iterate over each date in event_dates
                                for event_day in event_dates:
                                    month_year = get_month_year(event_day)
                                    attendee_data[email][month_year][category] += 1
                else:
                    print(f"Error: ATTENDEE not found for event {summary}.")
            else:
                print("Error: DTSTART not found in component")

    return attendee_data


# Generate the final report as a DataFrame
def generate_report(attendee_data, selected_month=None):
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/x-heal')
def automation():
    return render_template('web_index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file uploaded', 400

    file = request.files['file']
    selected_month = request.form.get('month')  # Get selected month from form

    if file.filename.endswith('.ics'):
        ical_data = file.read().decode('utf-8')
        attendee_data = process_ical(ical_data)

        # Generate the report with the selected month filter
        df_report = generate_report(attendee_data, selected_month)

        # Save the DataFrame to session to export later
        session['df_report'] = df_report.to_dict()  # Convert to dictionary to store in session

        # Convert the DataFrame to HTML for display
        html_table = df_report.to_html(classes='table table-striped table-hover table-bordered', index=False)

        # Render the report page with the table and export button
        return render_template('report.html', month=selected_month, table=html_table)

    return 'Invalid file format. Please upload an iCal file (.ics)', 400

@app.route('/export', methods=['POST'])
def export_data():
    # Retrieve the DataFrame from the session
    df_report = pd.DataFrame.from_dict(session.get('df_report'))

    # Convert the DataFrame to Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_report.to_excel(writer, index=False, sheet_name='Filtered Attendance Report')

    output.seek(0)

    # Send the Excel file as a response
    return send_file(output, download_name='filtered_attendance_report.xlsx', as_attachment=True)


@app.route('/confluence', methods=['GET', 'POST'])
def confluence_data_display():
    EMAIL = request.args.get('email')
    API_TOKEN = request.args.get('api_token')
    CALENDAR_ID = request.args.get('calender_id')
    if not EMAIL or not API_TOKEN or not CALENDAR_ID:
        # Render a form for the user to input the missing data
        flash('Missing required parameters: email, API token, and/or calendar ID.', 'warning')
        return render_template('warnning.html')  # Render a form for the user to fill the data

    from utility.calendar_service import Config, CalendarService
    config = Config()
    config.update_datas(EMAIL, API_TOKEN, CALENDAR_ID)
    calendar_service = CalendarService(config)
    selected_month = request.form.get('month')  # Get selected month from form
    df_report = calendar_service.generate_report(calendar_service.process_event_data(), selected_month)
    # Save the DataFrame to session to export later
    session['df_report'] = df_report.to_dict()  # Convert to dictionary to store in session
    html_table = df_report.to_html(classes='table table-striped table-hover table-bordered', index=False)
    # Render the report page with the table and export button
    return render_template('attendance_report.html', month=selected_month, table=html_table)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
