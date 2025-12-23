import csv
from datetime import timedelta

FILE_PATH = "data/static/ct_gtfs/stop_times.txt"

scheduled = {}

def parse_time(t):
    """Convert HH:MM:SS string to timedelta (handles 24+ hours)."""
    hours, minutes, seconds = map(int, t.split(":"))
    days = hours // 24
    hours = hours % 24
    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

with open(FILE_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        trip_id = row["trip_id"]
        stop_id = row["stop_id"]
        arrival_str = row["arrival_time"]

        if arrival_str.strip() == "":
            continue

        arrival_td = parse_time(arrival_str)

        if trip_id not in scheduled:
            scheduled[trip_id] = {}

        scheduled[trip_id][stop_id] = arrival_td

# Example: print first 5 trips
for trip_id, stops in list(scheduled.items())[:5]:
    print(trip_id, stops)
