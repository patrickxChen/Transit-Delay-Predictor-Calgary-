from flask import *
from parse_routes import get_routes_for_date

app = Flask(__name__)

@app.route("/routes")
def routes_endpoint():
    date = request.args.get("date")  # expected YYYYMMDD
    if not date:
        from datetime import datetime
        date = datetime.now().strftime("%Y%m%d")
    
    try:
        routes = get_routes_for_date(date)
        return jsonify({"date": date, "routes": routes})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def home():
    return jsonify({"status": "running"})

if __name__ == "__main__":
    app.run(debug=True)
