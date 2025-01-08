import requests
from datetime import datetime
from flask import current_app
from models import db, Service, StatusCheck

def check_service_status(service):
    """Check a single service's status"""
    try:
        print("checking service status", service.endpoint_url)
        response = requests.get(service.endpoint_url, timeout=5)
        success_codes = service.get_success_codes()
        
        if response.status_code in success_codes:
            current_status = 'operational'
            print("service is operational")
        elif response.status_code >= 500:
            current_status = 'outage'
            print("service is outage")
        else:
            current_status = 'issue'
            print("service is issue")
    except requests.RequestException:
        current_status = 'outage'
        print("service is outage")
    
    # Get or create hourly status
    now = datetime.utcnow()
    hourly_status = StatusCheck.get_or_create_hourly_status(service.id, now)
    
    # Only update if current hour's status is operational and we detected an issue
    # This ensures that once an hour is marked as having an issue, it stays that way
    if hourly_status.status == 'operational' and current_status != 'operational':
        hourly_status.status = current_status
        db.session.commit()
    
    return hourly_status

def check_status():
    """Check all services' status"""
    try:
        with current_app.app_context():
            services = Service.query.all()
            for service in services:
                check_service_status(service)
    except Exception as e:
        print(f"Error checking status: {e}")  # Log any errors but don't crash the scheduler
