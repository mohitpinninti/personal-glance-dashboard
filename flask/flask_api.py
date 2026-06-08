from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from notion_client import Client
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="../.env")
NOTION_TOKEN = os.environ.get("NOTION_INTEGRATION_SECRET")
NOTION_CALL_REMINDER_DB_ID = os.environ.get("NOTION_CALL_REMINDER_DB_ID")
NOTION_HABIT_TRACKER_DB_ID = os.environ.get("NOTION_HABIT_TRACKER_DB_ID")
UI_ENDPOINT = os.environ.get("UI_ENDPOINT")

# Create a Flask application instance
app = Flask(__name__)
CORS(app, origins=UI_ENDPOINT, methods=["GET", "POST"], allow_headers=["Content-Type"])

notion = Client(auth=NOTION_TOKEN)

@app.route("/notion/daily-habits")
def get_daily_habits():
    """Fetch today's habits and include the Notion page_id."""
    
    today = datetime.today().strftime('%Y-%m-%d')

    filter_params = {
        "filter": {
            "property": "Date",
            "date": {
                "equals": today
            }
        }
    }

    response = notion.databases.query(
        database_id=NOTION_HABIT_TRACKER_DB_ID,
        **filter_params
    )

    results = []

    for page in response["results"]:
        page_id = page["id"]

        date_column = page["properties"].get("Date", {}).get("date", {}).get("start")

        checkboxes = {
            key: page["properties"][key].get("checkbox")
            for key in page["properties"]
            if "checkbox" in page["properties"][key]
        }

        results.append({
            "page_id": page_id,
            "date": date_column,
            "checkboxes": checkboxes
        })

    return jsonify({"habits": results})

@app.route("/notion/update-habit", methods=["POST"])
def update_habit():
    """Update a checkbox habit using a cached page_id."""

    data = request.get_json()

    print(data)

    habit_name = data.get("habit")
    habit_value = data.get("value")
    page_id = data.get("page_id")

    if habit_name is None or habit_value is None or page_id is None:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                habit_name: {
                    "checkbox": habit_value
                }
            }
        )

        return jsonify({
            "success": True,
            "habit": habit_name,
            "value": habit_value
        })

    except Exception as e:
        print("Error updating habit:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/notion/contacts")
def get_contacts():
    response = notion.databases.query(
        database_id=NOTION_CALL_REMINDER_DB_ID
    )

    results = []
    today = datetime.now(timezone.utc).date()

    for page in response["results"]:
        props = page["properties"]

        name = props["Name"]["title"][0]["plain_text"]

        last_contact = props["Last Contact"]["date"]
        frequency = props["Frequency (days)"]["number"]

        # Getting the status from the "Select" property
        status = None if props.get("Status", {}) is None else props.get("Status", {}).get("name", None)

        # Reasons to skip entry:
        if status == "Paused" or last_contact is None or frequency is None or name is None:
            continue

        if last_contact:
            last_date = datetime.fromisoformat(
                last_contact["start"]
            ).date()
        else:
            last_date = None

        if last_date and frequency:
            next_due = last_date + timedelta(days=frequency)
            overdue = today > next_due
        else:
            next_due = None
            overdue = False

        days_since = (today - last_date).days
        urgency = days_since / frequency

        status = None

        if urgency >= 1.2:
            status = "overdue"
        elif urgency >= 0.8:
            status = "approaching"
        else:
            status = "recent"

        results.append({
            "name": name,
            "days_since": days_since,
            "frequency": frequency,
            "urgency": round(urgency, 2),
            "status": status
        })

    return jsonify({
        "people": results
    })

# Run the application
if __name__ == '__main__':
    # The default port is 5000
    # app.run(debug=True)
    app.run(host="0.0.0.0", port=5000, debug=True)