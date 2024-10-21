from flask import Flask, request, render_template, send_file, session
from utility.calendar_service import Config, CalendarService

app = Flask(__name__)


@app.route('/')
def attendance_report():
    # Initialize configuration and calendar service
    config = Config()
    calendar_service = CalendarService(config)

    # Fetch events
    events = calendar_service.fetch_calendar_events()

    # Pass the events data to the template
    return render_template('attendance_report.html', events=events, month="All Months")


@app.route('/upload', methods=['GET'])
def upload_file():
    config = Config()
    calendar_service = CalendarService(config)
    selected_month = request.form.get('month')  # Get selected month from form
    df_report = calendar_service.generate_report(calendar_service.process_event_data(), selected_month)
    # Save the DataFrame to session to export later
    session['df_report'] = df_report.to_dict()  # Convert to dictionary to store in session
    html_table = df_report.to_html(classes='table table-striped table-hover table-bordered', index=False)
    print(html_table)
    # Render the report page with the table and export button
    return render_template('report.html', month=selected_month, table=html_table)


if __name__ == '__main__':
    app.run(debug=True)
