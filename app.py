# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import csv
import datetime

app = Flask(__name__)
CORS(app)

# Path to GTFS static data
GTFS_PATH = "data/static/CT_GTFS/"

# Load routes and trips into memory
routes_data = {}
with open(GTFS_PATH + "routes.txt", newline='', encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        routes_data[row["route_id"]] = {
            "route_short_name": row["route_short_name"],
            "route_long_name": row["route_long_name"]
        }

trips_data = []
with open(GTFS_PATH + "trips.txt", newline='', encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        trips_data.append({
            "trip_id": row["trip_id"],
            "route_id": row["route_id"],
            "service_id": row["service_id"]
        })

# Load calendar to check which service runs on which day
calendar_data = {}
with open(GTFS_PATH + "calendar.txt", newline='', encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        calendar_data[row["service_id"]] = {
            "monday": int(row["monday"]),
            "tuesday": int(row["tuesday"]),
            "wednesday": int(row["wednesday"]),
            "thursday": int(row["thursday"]),
            "friday": int(row["friday"]),
            "saturday": int(row["saturday"]),
            "sunday": int(row["sunday"]),
            "start_date": row["start_date"],
            "end_date": row["end_date"]
        }

@app.route("/routes")
def get_routes():
    # date format: YYYYMMDD
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "Missing date parameter"}), 400

    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYYMMDD"}), 400

    weekday = date_obj.weekday()  # 0 = Monday, 6 = Sunday
    weekday_map = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]

    # Find active service_ids for this date
    active_service_ids = []
    for service_id, info in calendar_data.items():
        start = datetime.datetime.strptime(info["start_date"], "%Y%m%d")
        end = datetime.datetime.strptime(info["end_date"], "%Y%m%d")
        if start <= date_obj <= end:
            if info[weekday_map[weekday]] == 1:
                active_service_ids.append(service_id)

    # Find routes that have trips running today
    route_ids = set()
    for trip in trips_data:
        if trip["service_id"] in active_service_ids:
            route_ids.add(trip["route_id"])

    # Build route info list
    result = []
    for r in route_ids:
        if r in routes_data:
            result.append(routes_data[r])

    return jsonify({"routes": result})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
