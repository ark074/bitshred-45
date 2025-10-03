from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from pymongo import MongoClient
import os, datetime, json

app = Flask(__name__)

# MongoDB connection
MONGO_URI = os.environ.get('MONGO_URI')
MONGO_DB = os.environ.get('MONGO_DB', 'marine_platform')

if not MONGO_URI:
    # Local fallback (only for local testing)
    MONGO_URI = "mongodb://localhost:27017/"

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def seed_data():
    """Seed MongoDB with sample_data.json if collections are empty."""
    try:
        base = os.path.dirname(__file__)
        sample_file = os.path.join(base, 'sample_data.json')
        if os.path.exists(sample_file):
            with open(sample_file) as f:
                data = json.load(f)
                for col, docs in data.items():
                    if db[col].count_documents({}) == 0:
                        db[col].insert_many(docs)
    except Exception as e:
        print("Seed error:", e)

seed_data()

@app.route('/')
def index():
    return render_template('index.html')

# --- Ingestion ---
@app.route('/ingestion', methods=['GET', 'POST'])
def ingestion():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        file = request.files.get('file')
        filename = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(path)
        db.ingestion.insert_one({
            'title': title,
            'description': description,
            'filename': filename,
            'timestamp': datetime.datetime.utcnow()
        })
        return redirect(url_for('ingestion'))
    items = list(db.ingestion.find({}, {'_id': 0}).sort('timestamp', -1))
    return render_template('ingestion.html', items=items)

# --- Otolith ---
@app.route('/otolith', methods=['GET', 'POST'])
def otolith():
    if request.method == 'POST':
        species = request.form.get('species')
        length_mm = request.form.get('length_mm')
        file = request.files.get('file')
        filename = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(path)
        db.otolith.insert_one({
            'species': species,
            'length_mm': float(length_mm) if length_mm else None,
            'filename': filename,
            'timestamp': datetime.datetime.utcnow()
        })
        return redirect(url_for('otolith'))
    items = list(db.otolith.find({}, {'_id': 0}).sort('timestamp', -1))
    return render_template('otolith.html', items=items)

# --- eDNA ---
@app.route('/edna', methods=['GET', 'POST'])
def edna():
    if request.method == 'POST':
        sample_id = request.form.get('sample_id')
        species_list = request.form.get('species')
        species_arr = [s.strip() for s in species_list.split(',')] if species_list else []
        db.edna.insert_one({
            'sample_id': sample_id,
            'species_detected': species_arr,
            'timestamp': datetime.datetime.utcnow()
        })
        return redirect(url_for('edna'))
    items = list(db.edna.find({}, {'_id': 0}).sort('timestamp', -1))
    return render_template('edna.html', items=items)

# --- Visualization ---
@app.route('/visualization')
def visualization():
    return render_template('visualization.html')

@app.route('/api/visualization_data')
def api_visualization_data():
    ingestion = list(db.ingestion.find({}, {'_id': 0}))
    otolith = list(db.otolith.find({}, {'_id': 0}))
    edna = list(db.edna.find({}, {'_id': 0}))

    ingestion_count = db.ingestion.count_documents({})
    otolith_count = db.otolith.count_documents({})
    edna_count = db.edna.count_documents({})

    species_counts = {}
    for doc in otolith:
        sp = doc.get('species', 'Unknown')
        species_counts[sp] = species_counts.get(sp, 0) + 1
    for doc in edna:
        for sp in doc.get('species_detected', []):
            species_counts[sp] = species_counts.get(sp, 0) + 1

    # Timeseries by ingestion date (YYYY-MM-DD)
    ts = {}
    for doc in ingestion:
        t = doc.get('timestamp')
        if hasattr(t, 'isoformat'):
            date_str = t.date().isoformat()
        else:
            date_str = str(t)[:10]
        ts[date_str] = ts.get(date_str, 0) + 1
    timeseries = sorted(
        [{'date': k, 'count': v} for k, v in ts.items()],
        key=lambda x: x['date']
    )

    return jsonify({
        'ingestion_count': ingestion_count,
        'otolith_count': otolith_count,
        'edna_count': edna_count,
        'species_counts': species_counts,
        'timeseries': timeseries
    })

# --- Uploaded files ---
@app.route('/static/uploads/<path:filename>')
def uploaded(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
