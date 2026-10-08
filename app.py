"""
Nepal EBS - Flask Web Application
Event-Based Surveillance dashboard for Nepal health hazards.
"""
from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO, emit
from datetime import datetime, timedelta
import json
import csv
import io

from scraper import scrape_all_sources, get_demo_articles
from detector import SignalDetector, Deduplicator
from geocoder import Geocoder
from database import Database

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nepal-ebs-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize components
detector = SignalDetector()
deduplicator = Deduplicator()
geocoder = Geocoder()
db = Database()

# In-memory signal storage for real-time access
signals_cache = []
last_scan_time = None


def run_scan(use_demo=True):
    """Run a full scan: scrape, detect, deduplicate, geocode, and store."""
    global signals_cache, last_scan_time
    
    started_at = datetime.now()
    
    # Scrape articles
    articles = scrape_all_sources(use_demo=use_demo)
    
    # Save articles to database
    for article in articles:
        db.save_article(article)
    
    # Detect signals
    raw_signals = detector.analyze_articles(articles)
    
    # Deduplicate
    unique_signals = deduplicator.deduplicate(raw_signals)
    
    # Geocode
    geocoded_signals = geocoder.geocode_signals(unique_signals)
    
    # Save to database
    for signal in geocoded_signals:
        db.save_signal(signal)
    
    # Update cache
    signals_cache = geocoded_signals
    last_scan_time = datetime.now()
    
    # Save scan history
    db.save_scan_history(started_at, len(articles), len(geocoded_signals))
    
    # Emit WebSocket event
    socketio.emit('scan_complete', {
        'signals_found': len(geocoded_signals),
        'articles_processed': len(articles),
        'timestamp': last_scan_time.isoformat()
    })
    
    return geocoded_signals


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


@app.route('/api/signals')
def get_signals():
    """API endpoint to get all signals."""
    severity = request.args.get('severity')
    hazard_type = request.args.get('hazard_type')
    
    filtered = signals_cache
    
    if severity:
        filtered = [s for s in filtered if s['severity'] == severity]
    
    if hazard_type:
        filtered = [s for s in filtered if hazard_type in s.get('hazards', {})]
    
    return jsonify({
        'signals': filtered,
        'total': len(filtered),
        'last_scan': last_scan_time.isoformat() if last_scan_time else None
    })


@app.route('/api/signals/<int:signal_id>')
def get_signal(signal_id):
    """API endpoint to get a specific signal."""
    if 0 <= signal_id < len(signals_cache):
        return jsonify(signals_cache[signal_id])
    return jsonify({'error': 'Signal not found'}), 404


@app.route('/api/scan', methods=['POST'])
def trigger_scan():
    """API endpoint to trigger a new scan."""
    use_demo = request.json.get('use_demo', True) if request.json else True
    signals = run_scan(use_demo=use_demo)
    return jsonify({
        'message': 'Scan completed',
        'signals_found': len(signals),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/stats')
def get_stats():
    """API endpoint to get statistics."""
    if not signals_cache:
        return jsonify({
            'total_signals': 0,
            'by_severity': {},
            'by_hazard': {},
            'by_location': {}
        })
    
    by_severity = {}
    by_hazard = {}
    by_location = {}
    
    for signal in signals_cache:
        # Count by severity
        sev = signal['severity']
        by_severity[sev] = by_severity.get(sev, 0) + 1
        
        # Count by hazard type
        for hazard in signal.get('hazards', {}):
            by_hazard[hazard] = by_hazard.get(hazard, 0) + 1
        
        # Count by location
        loc = signal.get('primary_location')
        if loc:
            loc_name = loc['name']
            by_location[loc_name] = by_location.get(loc_name, 0) + 1
    
    return jsonify({
        'total_signals': len(signals_cache),
        'by_severity': by_severity,
        'by_hazard': by_hazard,
        'by_location': by_location,
        'last_scan': last_scan_time.isoformat() if last_scan_time else None
    })


@app.route('/api/trends')
def get_trends():
    """API endpoint to get historical trends."""
    days = request.args.get('days', 7, type=int)
    trends = db.get_trends(days=days)
    return jsonify(trends)


@app.route('/api/signals/export')
def export_signals():
    """Export signals as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Title', 'Source', 'Severity', 'Score', 'Hazards', 'Location', 'Published', 'URL'])
    
    # Data
    for signal in signals_cache:
        loc = signal.get('primary_location', {})
        writer.writerow([
            signal['article']['title'],
            signal['article']['source'],
            signal['severity'],
            signal['score'],
            ', '.join(signal.get('hazards', {}).keys()),
            loc.get('name', 'Unknown') if loc else 'Unknown',
            signal['article']['published'],
            signal['article']['url']
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=signals.csv'}
    )


@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'signals_count': len(signals_cache),
        'last_scan': last_scan_time.isoformat() if last_scan_time else None
    })


@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection."""
    emit('connected', {'message': 'Connected to Nepal EBS'})


@socketio.on('request_scan')
def handle_scan_request():
    """Handle scan request via WebSocket."""
    signals = run_scan(use_demo=True)
    emit('scan_complete', {
        'signals_found': len(signals),
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    # Run initial scan
    print("Running initial scan...")
    run_scan(use_demo=True)
    print(f"Found {len(signals_cache)} signals")
    
    # Start Flask app with WebSocket support
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
