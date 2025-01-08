from flask import Flask, render_template, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from models import db, Service, StatusCheck
from status_checker import check_status
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/status.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable the warning
db.init_app(app)

scheduler = BackgroundScheduler()

def init_db():
    """Initialize the database and create default services"""
    # Ensure data directory exists
    if not os.path.exists('data'):
        os.makedirs('data')
    
    # Remove old database if exists
    db_path = 'data/status.db'
    if os.path.exists(db_path):
        os.remove(db_path)
    
    with app.app_context():
        # Drop all tables (if they exist)
        db.drop_all()
        
        # Create all tables
        db.create_all()
        
        try:
            # Create default services
            services = [
                {
                    'name': 'Oneview API',
                    'description': 'Oneview API Status',
                    'endpoint_url': 'https://oneview.gba4pl.com/',
                    'success_codes': '200,201,202'
                },
                {
                    'name': '网页对话服务 (Web Chat Service)',
                    'description': 'Web Chat Service Status',
                    'endpoint_url': 'https://test.nothing.com/health',
                    'success_codes': '200'
                }
            ]
            
            # Create services
            for service_data in services:
                service = Service(**service_data)
                db.session.add(service)
            db.session.commit()
            print("Database initialized successfully!")
        except Exception as e:
            print(f"Error initializing database: {e}")
            db.session.rollback()
            raise

@app.route('/')
def index():
    services = Service.query.all()
    service_data = []
    
    for service in services:
        # Get status checks for the last 24 hours
        end_datetime = datetime.utcnow()
        start_datetime = end_datetime - timedelta(hours=24)
        
        # Get hourly statuses for the last 24 hours
        status_history = StatusCheck.get_hourly_statuses(service.id, start_datetime, end_datetime)
        
        # Get latest status (current hour)
        latest_status = status_history[-1]['status'] if status_history else 'unknown'
        
        # Calculate uptime percentage
        uptime = StatusCheck.calculate_uptime(service.id)
        
        service_data.append({
            'id': service.id,
            'name': service.name,
            'description': service.description,
            'current_status': latest_status,
            'uptime': uptime,
            'status_history': status_history
        })
    
    return render_template('index.html', services=service_data)

@app.route('/api/services', methods=['POST'])
def add_service():
    data = request.json
    new_service = Service(
        name=data['name'],
        description=data.get('description', ''),
        endpoint_url=data['endpoint_url'],
        success_codes=data.get('success_codes', '200')
    )
    db.session.add(new_service)
    db.session.commit()
    
    # Create initial status check
    now = datetime.utcnow()
    StatusCheck.get_or_create_hourly_status(new_service.id, now)
    
    return jsonify({'message': 'Service added', 'id': new_service.id}), 201

if __name__ == '__main__':
    init_db()  # Initialize database and create default services
    
    # Create the scheduler
    scheduler = BackgroundScheduler()
    
    # Create a wrapper function that ensures app context
    def scheduled_task():
        with app.app_context():
            check_status()
    
    # Run status checks every 5 seconds
    scheduler.add_job(scheduled_task, 'interval', seconds=5)
    scheduler.start()
    
    app.run(host='0.0.0.0', port=5002)
