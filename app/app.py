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
        # Get status checks for the last 24 hours
        end_datetime = datetime.utcnow()
        start_datetime = end_datetime - timedelta(hours=72)
        
        # Get hourly statuses for the last 24 hours
        status_history = StatusCheck.get_hourly_statuses(service_name, start_datetime, end_datetime)
        
        # Get latest status (current hour)
        latest_status = status_history[-1]['status'] if status_history else 'unknown'
        
        # Calculate uptime percentage
        uptime = StatusCheck.calculate_uptime(service_name)
        
        # Get failure duration if service is not operational
        failure_duration = None
        if latest_status != 'operational':
            failure_duration = StatusCheck.get_failure_duration(service_name)
        
        service_data.append({
            'name': service_name,
            'description': service_config['description'],
            'current_status': latest_status,
            'uptime': uptime,
            'status_history': status_history,
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
    
    # Run status checks every 5 seconds
    scheduler.add_job(scheduled_task, 'interval', seconds=60)
    scheduler.start()
    
    app.run(host='0.0.0.0', port=8243)
