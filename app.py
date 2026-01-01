from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import csv
import datetime
import os

app = Flask(__name__)
CORS(app)

# Serve the frontend HTML at /routes
@app.route('/routes')
def serve_routes_html():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'routes.html')

@app.route('/trip')
def serve_trip_html():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'trip.html')

# Path to GTFS static data
GTFS_PATH = os.path.join('data', 'static', 'CT_GTFS')

# Load GTFS static files into memory at startup
routes_data = {}
trips_data = []
calendar_data = {}
stop_times_data = {}
stops_data = {}

def load_gtfs():
    global routes_data, trips_data, calendar_data
    routes_data = {}
    trips_data = []
    calendar_data = {}

    routes_path = os.path.join(GTFS_PATH, 'routes.txt')
    trips_path = os.path.join(GTFS_PATH, 'trips.txt')
    calendar_path = os.path.join(GTFS_PATH, 'calendar.txt')
    stop_times_path = os.path.join(GTFS_PATH, 'stop_times.txt')

    if os.path.exists(routes_path):
        with open(routes_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                routes_data[row['route_id']] = {
                    'route_short_name': row.get('route_short_name', '').strip(),
                    'route_long_name': row.get('route_long_name', '').strip()
                }

    if os.path.exists(trips_path):
        with open(trips_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                trips_data.append({
                    'trip_id': row.get('trip_id', ''),
                    'route_id': row.get('route_id', ''),
                    'service_id': row.get('service_id', '')
                })

    # load stop_times: map trip_id -> list of departure_time strings
    if os.path.exists(stop_times_path):
        with open(stop_times_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tid = row.get('trip_id', '')
                st = {
                    'stop_id': row.get('stop_id', ''),
                    'arrival_time': row.get('arrival_time', ''),
                    'departure_time': row.get('departure_time', ''),
                    'stop_sequence': int(row.get('stop_sequence', 0)) if row.get('stop_sequence') and row.get('stop_sequence').isdigit() else None
                }
                stop_times_data.setdefault(tid, []).append(st)

    # load stops
    stops_path = os.path.join(GTFS_PATH, 'stops.txt')
    if os.path.exists(stops_path):
        with open(stops_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stops_data[row.get('stop_id', '')] = {
                    'stop_name': row.get('stop_name', ''),
                    'stop_lat': row.get('stop_lat', ''),
                    'stop_lon': row.get('stop_lon', '')
                }

    if os.path.exists(calendar_path):
        with open(calendar_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                calendar_data[row['service_id']] = {
                    'monday': int(row.get('monday', 0)),
                    'tuesday': int(row.get('tuesday', 0)),
                    'wednesday': int(row.get('wednesday', 0)),
                    'thursday': int(row.get('thursday', 0)),
                    'friday': int(row.get('friday', 0)),
                    'saturday': int(row.get('saturday', 0)),
                    'sunday': int(row.get('sunday', 0)),
                    'start_date': row.get('start_date', ''),
                    'end_date': row.get('end_date', '')
                }

# Call load on import
load_gtfs()

# Time parsing helpers (used by multiple endpoints)
import re

def parse_time_str(t):
    if not t or not isinstance(t, str):
        return None
    s = t.strip().replace('.', ':')
    # handle formats like 2359 or 759 -> 23:59 or 7:59
    if re.match(r'^\d{3,4}$', s):
        if len(s) == 3:
            h = int(s[0]); m = int(s[1:3])
        else:
            h = int(s[0:2]); m = int(s[2:4])
        return h * 3600 + m * 60
    m = re.match(r'^(\d+):(\d{1,2})(?::(\d{1,2}))?$', s)
    if m:
        h = int(m.group(1))
        mm = int(m.group(2))
        ss = int(m.group(3)) if m.group(3) else 0
        return h * 3600 + mm * 60 + ss
    return None

def seconds_to_time(sec):
    if sec is None:
        return None
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


@app.route('/api/routes')
def api_routes():
    # date format: YYYYMMDD
    date_str = request.args.get('date')
    if not date_str:
        date_obj = datetime.datetime.now()
        date_str = date_obj.strftime('%Y%m%d')
    else:
        try:
            date_obj = datetime.datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYYMMDD'}), 400

    weekday = date_obj.weekday()  # 0 = Monday
    weekday_map = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    # Determine active service_ids from calendar.txt
    active_service_ids = []
    for service_id, info in calendar_data.items():
        try:
            start = datetime.datetime.strptime(info['start_date'], '%Y%m%d')
            end = datetime.datetime.strptime(info['end_date'], '%Y%m%d')
        except Exception:
            continue
        if start <= date_obj <= end and info.get(weekday_map[weekday], 0) == 1:
            active_service_ids.append(service_id)

    # Collect route_ids for trips running today
    route_ids = set()
    for trip in trips_data:
        if trip.get('service_id') in active_service_ids:
            route_ids.add(trip.get('route_id'))

    import re

    def parse_time_str(t):
        if not t or not isinstance(t, str):
            return None
        s = t.strip().replace('.', ':')
        # handle formats like 2359 or 759 -> 23:59 or 7:59
        if re.match(r'^\d{3,4}$', s):
            if len(s) == 3:
                h = int(s[0])
                m = int(s[1:3])
            else:
                h = int(s[0:2])
                m = int(s[2:4])
            return h * 3600 + m * 60
        m = re.match(r'^(\d+):(\d{1,2})(?::(\d{1,2}))?$', s)
        if m:
            h = int(m.group(1))
            mm = int(m.group(2))
            ss = int(m.group(3)) if m.group(3) else 0
            return h * 3600 + mm * 60 + ss
        return None

    def seconds_to_time(sec):
        if sec is None:
            return None
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    # Build result with trip counts and first/last departure
    result = []
    for r in sorted(route_ids):
        info = routes_data.get(r)
        if not info:
            continue

        # find trip_ids for this route that run today
        trip_ids = [t['trip_id'] for t in trips_data if t.get('route_id') == r and t.get('service_id') in active_service_ids]

        # collect all departure times for those trips
        secs = []
        for tid in trip_ids:
            for st in stop_times_data.get(tid, []):
                dep_str = (st.get('departure_time') or st.get('arrival_time') or '')
                sec = parse_time_str(dep_str)
                if sec is not None:
                    secs.append(sec)

        first = seconds_to_time(min(secs)) if secs else None
        last = seconds_to_time(max(secs)) if secs else None

        result.append({
            'route_id': r,
            'route_short_name': info.get('route_short_name'),
            'route_long_name': info.get('route_long_name'),
            'trips_count': len(trip_ids),
            'first_departure': first,
            'last_departure': last
        })

    # optional filtering by query 'q' (search)
    q = request.args.get('q')
    if q:
        ql = q.lower()
        result = [r for r in result if (r.get('route_short_name') or '').lower().find(ql) != -1 or (r.get('route_long_name') or '').lower().find(ql) != -1]

    return jsonify({'routes': result})


@app.route('/api/route_trips')
def api_route_trips():
    route_id = request.args.get('route_id')
    if not route_id:
        return jsonify({'error': 'Missing route_id parameter'}), 400

    # ahead window in minutes
    ahead_min = request.args.get('ahead')
    try:
        ahead_min = int(ahead_min) if ahead_min is not None else 120
    except Exception:
        ahead_min = 120

    # determine today's active services
    date_str = request.args.get('date')
    if not date_str:
        date_obj = datetime.datetime.now()
    else:
        try:
            date_obj = datetime.datetime.strptime(date_str, '%Y%m%d')
        except Exception:
            date_obj = datetime.datetime.now()

    weekday = date_obj.weekday()
    weekday_map = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    active_service_ids = []
    for service_id, info in calendar_data.items():
        try:
            start = datetime.datetime.strptime(info['start_date'], '%Y%m%d')
            end = datetime.datetime.strptime(info['end_date'], '%Y%m%d')
        except Exception:
            continue
        if start <= date_obj <= end and info.get(weekday_map[weekday], 0) == 1:
            active_service_ids.append(service_id)

    now_dt = datetime.datetime.now()
    now_seconds = now_dt.hour * 3600 + now_dt.minute * 60 + now_dt.second
    window_end = now_seconds + ahead_min * 60

    trips_out = []
    for trip in trips_data:
        if trip.get('route_id') != route_id:
            continue
        if trip.get('service_id') not in active_service_ids:
            continue
        tid = trip.get('trip_id')
        # compute earliest departure for trip
        secs = []
        for st in stop_times_data.get(tid, []):
            dep = st.get('departure_time') or st.get('arrival_time') or ''
            sec = parse_time_str(dep)
            if sec is not None:
                secs.append(sec)
        if not secs:
            continue
        earliest = min(secs)
        if now_seconds <= earliest <= window_end:
            trips_out.append({'trip_id': tid, 'earliest_departure': seconds_to_time(earliest)})

    trips_out.sort(key=lambda x: parse_time_str(x.get('earliest_departure') or '') or 10**9)
    return jsonify({'route_id': route_id, 'trips': trips_out})


@app.route('/api/stops')
def api_stops():
    # optional: return stops that have trips today only
    date_str = request.args.get('date')
    if not date_str:
        date_obj = datetime.datetime.now()
        date_str = date_obj.strftime('%Y%m%d')
    else:
        try:
            date_obj = datetime.datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYYMMDD'}), 400

    weekday = date_obj.weekday()
    weekday_map = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    # compute active services
    active_service_ids = []
    for service_id, info in calendar_data.items():
        try:
            start = datetime.datetime.strptime(info['start_date'], '%Y%m%d')
            end = datetime.datetime.strptime(info['end_date'], '%Y%m%d')
        except Exception:
            continue
        if start <= date_obj <= end and info.get(weekday_map[weekday], 0) == 1:
            active_service_ids.append(service_id)

    # find stops which have trips today
    stops_with_trips = set()
    for trip in trips_data:
        if trip.get('service_id') in active_service_ids:
            for st in stop_times_data.get(trip.get('trip_id'), []):
                stops_with_trips.add(st.get('stop_id'))

    # return list of stops (id and name)
    result = []
    for sid, info in stops_data.items():
        if sid in stops_with_trips:
            result.append({'stop_id': sid, 'stop_name': info.get('stop_name')})

    # sort by name
    result.sort(key=lambda x: x.get('stop_name') or '')
    return jsonify({'stops': result})


@app.route('/api/stop_trips')
def api_stop_trips():
    stop_id = request.args.get('stop_id')
    if not stop_id:
        return jsonify({'error': 'Missing stop_id parameter'}), 400

    date_str = request.args.get('date')
    if not date_str:
        date_obj = datetime.datetime.now()
        date_str = date_obj.strftime('%Y%m%d')
    else:
        try:
            date_obj = datetime.datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYYMMDD'}), 400

    weekday = date_obj.weekday()
    weekday_map = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    # compute active services
    active_service_ids = []
    for service_id, info in calendar_data.items():
        try:
            start = datetime.datetime.strptime(info['start_date'], '%Y%m%d')
            end = datetime.datetime.strptime(info['end_date'], '%Y%m%d')
        except Exception:
            continue
        if start <= date_obj <= end and info.get(weekday_map[weekday], 0) == 1:
            active_service_ids.append(service_id)

    # collect trips at this stop for active services
    trips_at_stop = []
    for trip in trips_data:
        if trip.get('service_id') not in active_service_ids:
            continue
        tid = trip.get('trip_id')
        for st in stop_times_data.get(tid, []):
            if st.get('stop_id') == stop_id:
                # find route info
                route_id = trip.get('route_id')
                route_info = routes_data.get(route_id, {})
                dep = st.get('departure_time') or st.get('arrival_time')
                trips_at_stop.append({
                    'trip_id': tid,
                    'route_id': route_id,
                    'route_short_name': route_info.get('route_short_name'),
                    'route_long_name': route_info.get('route_long_name'),
                    'departure_time': dep,
                    'arrival_time': st.get('arrival_time'),
                    'stop_sequence': st.get('stop_sequence')
                })

    # sort by departure time
    def time_to_seconds(t):
        try:
            parts = t.split(':')
            h = int(parts[0]); m = int(parts[1]) if len(parts)>1 else 0; s = int(parts[2]) if len(parts)>2 else 0
            return h*3600 + m*60 + s
        except Exception:
            return 10**9
    trips_at_stop.sort(key=lambda x: time_to_seconds(x.get('departure_time') or x.get('arrival_time') or ''))
    return jsonify({'stop_id': stop_id, 'trips': trips_at_stop})


@app.route('/api/trip_stops')
def api_trip_stops():
    trip_id = request.args.get('trip_id')
    if not trip_id:
        return jsonify({'error': 'Missing trip_id parameter'}), 400

    stops_for_trip = stop_times_data.get(trip_id, [])
    # sort by stop_sequence if present
    try:
        stops_for_trip = sorted(stops_for_trip, key=lambda x: (x.get('stop_sequence') is None, x.get('stop_sequence') or 0))
    except Exception:
        pass

    result = []
    for st in stops_for_trip:
        sid = st.get('stop_id')
        stop_info = stops_data.get(sid, {})
        result.append({
            'stop_id': sid,
            'stop_name': stop_info.get('stop_name'),
            'arrival_time': st.get('arrival_time'),
            'departure_time': st.get('departure_time'),
            'stop_sequence': st.get('stop_sequence')
        })

    return jsonify({'trip_id': trip_id, 'stops': result})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
