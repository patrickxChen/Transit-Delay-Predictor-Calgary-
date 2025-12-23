from google.transit import gtfs_realtime_pb2

feed = gtfs_realtime_pb2.FeedMessage()

with open("tripupdates.pb", "rb") as f:
    feed.ParseFromString(f.read())

print("Entities:", len(feed.entity))

for entity in feed.entity[:5]:  #==
    if entity.HasField("trip_update"):
        trip = entity.trip_update.trip
        print("Trip ID:", trip.trip_id)

        for stu in entity.trip_update.stop_time_update:
            if stu.HasField("arrival"):
                print(
                    "  Stop:", stu.stop_id,
                    "Arrival time:", stu.arrival.time
                )
