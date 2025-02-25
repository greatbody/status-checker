from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from models import db, StatusCheck
from status_checker import check_status, load_service_config
import os
from datetime import datetime, time, timedelta, date, UTC
from functools import lru_cache

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/status.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

scheduler = BackgroundScheduler()

# Cache service config for 5 minutes
@lru_cache(maxsize=1)
def get_cached_service_config():
    return load_service_config()

# Function to invalidate cache
def invalidate_service_config_cache():
    get_cached_service_config.cache_clear()

def init_db():
    """Initialize the database"""
    # Ensure data directory exists
    if not os.path.exists('data'):
        os.makedirs('data')
    
    with app.app_context():
        # Create all tables if they don't exist
        db.create_all()
        print("Database initialized successfully!")

def get_service_data():
    """Get service status data for all services"""
    services = get_cached_service_config()
    service_data = []
    
    for service_name, service_config in services.items():
        # Get status checks for the last 24 hours (48 30-minute blocks)
        end_datetime = datetime.now(UTC)
        start_datetime = end_datetime - timedelta(minutes=4300)
        
        # Get aggregated 30-minute statuses
        status_history = StatusCheck.get_aggregated_statuses(service_name, start_datetime, end_datetime)
        
        # Get first status history timestamp
        first_status_history_timestamp = datetime.combine(status_history[0]['date'], 
                                                        time(hour=status_history[0]['hour'], 
                                                             minute=status_history[0]['minute']), 
                                                        tzinfo=UTC) if status_history else datetime.now(UTC)
        # Calculate hours ago from first status
        hours_ago = int((datetime.now(UTC) - first_status_history_timestamp).total_seconds() // 3600)
        
        # Get latest status (current 30-minute block)
        latest_status = status_history[-1]['status'] if status_history else 'unknown'
        
        # Calculate uptime percentage
        uptime = StatusCheck.calculate_uptime(service_name)
        
        # Get failure duration if service is not operational
        failure_duration = StatusCheck.get_failure_duration(service_name) if latest_status != 'operational' else None
        
        # Convert date objects to string for JSON serialization
        serializable_status_history = []
        for status in status_history:
            serializable_status_history.append({
                'date': status['date'].isoformat() if isinstance(status['date'], date) else status['date'],
                'hour': status['hour'],
                'minute': status['minute'],
                'status': status['status']
            })
        
        service_data.append({
            'id': service_name,
            'name': service_config['description'],
            'description': service_config['description'],
            'url': service_config['endpoint_url'],
            'current_status': latest_status,
            'status_history': serializable_status_history,
            'uptime': uptime,
            'failure_duration': failure_duration,
            'hours_ago': hours_ago
        })
    
    return service_data

@app.route('/')
def index():
    """Serve the static HTML page"""
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    """API endpoint to get service status data"""
    service_data = get_service_data()
    return jsonify(service_data)

if __name__ == '__main__':
    init_db()  # Initialize database
    
    # Create the scheduler
    scheduler = BackgroundScheduler()
    
    # Create a wrapper function that ensures app context
    def scheduled_task():
        with app.app_context():
            check_status()
            # Invalidate cache every hour to ensure we pick up any config changes
            if datetime.now(UTC).minute == 0:
                invalidate_service_config_cache()
    
    # Run status checks every minute instead of every 10 seconds
    scheduler.add_job(scheduled_task, 'interval', seconds=30)
    scheduler.start()
    
    app.run(host='0.0.0.0', port=8243)
