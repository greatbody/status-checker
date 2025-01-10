import requests
import yaml
from datetime import datetime
from flask import current_app
from models import db, StatusCheck
from pathlib import Path

def load_service_config():
    """Load service configurations from YAML file"""
    config_path = Path(current_app.root_path) / 'sites.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config['services']

def check_service_status(service_name, service_config):
    """Check a single service's status"""
    try:
        print(f"checking service status for {service_name}: {service_config['endpoint_url']}")
        response = requests.get(service_config['endpoint_url'], timeout=30)
        success_codes = service_config['success_codes']
        
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
    hourly_status = StatusCheck.get_or_create_hourly_status(service_name, now)
    
    # Update last_success_time if service is operational
    if current_status == 'operational':
        hourly_status.last_success_time = now
    
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
            services = load_service_config()
            for service_name, service_config in services.items():
                check_service_status(service_name, service_config)
    except Exception as e:
        print(f"Error checking status: {e}")  # Log any errors but don't crash the scheduler
