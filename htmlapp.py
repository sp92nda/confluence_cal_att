from icalendar import Calendar
import pandas as pd
from collections import defaultdict
from datetime import datetime, date, timedelta
from io import BytesIO
from flask import Flask, request, render_template, send_file, session
import re

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
    delta = end_date - start_date
    for i in range(delta.days + 1):  # Include the end date
        yield start_date + timedelta(days=i)

# Read the iCal file and process events
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

            if dtstart:
                dtstart = dtstart.dt  # Extract the start date
                dtend = dtend.dt if dtend else dtstart  # Handle single-day events

                # Ensure dtend is exclusive for multi-day events
                if dtstart == dtend:
                    dtend = dtstart  # Single-day event
                else:
                    dtend = dtend - timedelta(days=1)  # Adjust to make dtend exclusive

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
                                # Handle multi-day events by iterating over each day
                                for event_day in generate_date_range(dtstart, dtend):
                                    month_year = get_month_year(event_day)
                                    if "2024-08" in str(month_year):
                                        sequence = component.get('sequence')  # Get the sequence property of the event
                                        print(attendee_data[email][month_year][category], sequence, email, summary,dtstart ,dtend)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
