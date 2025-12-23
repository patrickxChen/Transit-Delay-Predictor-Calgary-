import pandas as pd
from datetime import datetime

GTFS_PATH = "data/static/CT_GTFS/"

# Load files
calendar = pd.read_csv(GTFS_PATH + "calendar.txt")
calendar_dates = pd.read_csv(GTFS_PATH + "calendar_dates.txt")
trips = pd.read_csv(GTFS_PATH + "trips.txt")
stop_times = pd.read_csv(GTFS_PATH + "stop_times.txt")
stops = pd.read_csv(GTFS_PATH + "stops.txt")
routes = pd.read_csv(GTFS_PATH + "routes.txt")

def get_active_services(date_str):
    """Return service_ids active on a given YYYYMMDD date"""
    dt = datetime.strptime(date_str, "%Y%m%d")
    weekday = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"][dt.weekday()]
    
    # Services from calendar.txt
    active = calendar[
        (calendar[weekday]==1) &
        (calendar.start_date.astype(str) <= date_str) &
        (calendar.end_date.astype(str) >= date_str)
    ]["service_id"].tolist()
    
    # Apply exceptions from calendar_dates.txt
    for _, row in calendar_dates[calendar_dates.date==int(date_str)].iterrows():
        if row.exception_type == 1:  # added service
            active.append(row.service_id)
        elif row.exception_type == 2:  # removed service
            if row.service_id in active:
                active.remove(row.service_id)
    
    return active

def get_routes_for_date(date_str):
    active_services = get_active_services(date_str)
    trips_today = trips[trips.service_id.isin(active_services)]
    routes_today = trips_today.merge(routes, on="route_id")[["route_id","route_short_name","route_long_name"]].drop_duplicates()
    return routes_today.to_dict(orient="records")
