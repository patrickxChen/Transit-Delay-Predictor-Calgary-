from google.transit import gtfs_realtime_pb2
from datetime import datetime

FILE_PATH = "tripupdates.pb"

feed = gtfs_realtime_pb2.FeedMessage()

with open(FILE_PATH, "rb") as f:
    feed.ParseFromString(f.read())

records = []

for entity in feed.entity:
    if not entity.HasField("trip_update"):
        continue

    trip_id = entity.trip_update.trip.trip_id

    for stu in entity.trip_update.stop_time_update:
        if not stu.HasField("arrival"):
            continue

        arrival_time = stu.arrival.time
        if arrival_time <= 0:
            continue

        arrival_dt = datetime.utcfromtimestamp(arrival_time)

        records.append({
            "trip_id": trip_id,
            "stop_id": stu.stop_id,
            "arrival_time": arrival_dt
        })
        

for r in records[:5]:
    print(r)
