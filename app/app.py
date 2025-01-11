from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from models import db, StatusCheck
from status_checker import check_status, load_service_config
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/status.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

scheduler = BackgroundScheduler()

def init_db():
    """Initialize the database"""
    # Ensure data directory exists
    if not os.path.exists('data'):
        os.makedirs('data')
    
    # Remove old database if exists
    db_path = 'data/status.db'
    if os.path.exists(db_path):
        os.remove(db_path)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database initialized successfully!")

@app.route('/')
def index():
    services = load_service_config()
    service_data = []
    
    for service_name, service_config in services.items():
        # Get status checks for the last 24 hours (1440 minutes)
        end_datetime = datetime.utcnow()
        start_datetime = end_datetime - timedelta(minutes=1440)
        
        # Get minute statuses for the last 24 hours
        status_history = StatusCheck.get_minute_statuses(service_name, start_datetime, end_datetime)
        
        # Get latest status (current minute)
        latest_status = status_history[-1]['status'] if status_history else 'unknown'
        
        # Calculate uptime percentage
        uptime = StatusCheck.calculate_uptime(service_name)
        
        # Get failure duration if service is not operational
        failure_duration = StatusCheck.get_failure_duration(service_name) if latest_status != 'operational' else None
        
        service_data.append({
            'id': service_name,
            'name': service_config['description'],
            'description': service_config['description'],
            'url': service_config['endpoint_url'],
            'current_status': latest_status,
            'status_history': status_history,
            'uptime': uptime,
            'failure_duration': failure_duration
        })
    
    return render_template('index.html', services=service_data)

if __name__ == '__main__':
    init_db()  # Initialize database
    
    # Create the scheduler
    scheduler = BackgroundScheduler()
    
    # Create a wrapper function that ensures app context
    def scheduled_task():
        with app.app_context():
            check_status()
    
    # Run status checks every minute
    scheduler.add_job(scheduled_task, 'interval', seconds=10)
    scheduler.start()
    
    app.run(host='0.0.0.0', port=8243)
