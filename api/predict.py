from flask import Flask, request, jsonify
import os

app = Flask(__name__)

MODEL_PATH = os.path.join('models', 'model.joblib')
ENC_PATH = os.path.join('models', 'encoders.joblib')

# lazy-loaded heavy deps
model = None
enc = None
_np = None
_joblib = None

def load_model():
    global model, enc
    if model is None:
        # If model not present in bundle, try downloading from MODEL_URL env var (useful for Vercel)
        model_url = os.environ.get('MODEL_URL')
        if (not os.path.exists(MODEL_PATH) or not os.path.exists(ENC_PATH)) and model_url:
            try:
                import requests, gzip
                from io import BytesIO
                os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
                print('Downloading model from', model_url)
                r = requests.get(model_url, timeout=60)
                r.raise_for_status()
                content = r.content
                # If served as gzipped asset (.gz), decompress before saving
                if model_url.endswith('.gz') or r.headers.get('content-type','').lower() in ('application/gzip','application/x-gzip'):
                    try:
                        content = gzip.decompress(content)
                    except Exception:
                        # try streaming decompression fallback
                        buf = BytesIO(content)
                        with gzip.open(buf, 'rb') as gf:
                            content = gf.read()

                with open(MODEL_PATH, 'wb') as f:
                    f.write(content)
            except Exception as e:
                raise RuntimeError('Failed to download model: ' + str(e))

        if not os.path.exists(MODEL_PATH) or not os.path.exists(ENC_PATH):
            raise FileNotFoundError('Model artifacts not found. Ensure models/model.joblib exists in the repository or set MODEL_URL.')

        # Import heavy libraries only when loading the model to avoid bundling them at module import
        global _joblib, _np, model, enc
        import joblib as _joblib_local
        import numpy as _np_local
        _joblib = _joblib_local
        _np = _np_local
        model = _joblib.load(MODEL_PATH)
        enc = _joblib.load(ENC_PATH)


@app.route('/', methods=['GET'])
def predict():
    try:
        load_model()
    except Exception as e:
        return jsonify({'error': 'Model not available', 'detail': str(e)}), 503

    route_id = request.args.get('route_id')
    stop_id = request.args.get('stop_id')
    scheduled_seconds = request.args.get('scheduled_seconds')
    when = request.args.get('when')

    if not route_id or not stop_id:
        return jsonify({'error': 'route_id and stop_id required'}), 400

    try:
        scheduled_seconds = int(scheduled_seconds) if scheduled_seconds is not None else 0
    except Exception:
        scheduled_seconds = 0

    try:
        hour = None
        weekday = None
        if when:
            import datetime
            try:
                ts = int(when)
                dt = datetime.datetime.fromtimestamp(ts)
            except Exception:
                dt = datetime.datetime.fromisoformat(when)
            hour = dt.hour
            weekday = dt.weekday()
        else:
            import datetime
            dt = datetime.datetime.now()
            hour = dt.hour
            weekday = dt.weekday()

        arr = _np.array([[route_id, stop_id]])
        try:
            cat = enc.transform(arr)
        except Exception:
            cat = _np.array([[0,0]])

        X = [cat[0,0], cat[0,1], scheduled_seconds % 86400, hour, weekday]
        pred = float(model.predict([X])[0])
        return jsonify({'predicted_delay_seconds': pred})
    except Exception as e:
        return jsonify({'error': 'prediction failed', 'detail': str(e)}), 500

# When deployed to Vercel, the framework will expose this WSGI `app`.
