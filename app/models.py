from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    endpoint_url = db.Column(db.String(500), nullable=False)  # The URL to check
    success_codes = db.Column(db.String(100), nullable=False, default='200')  # Comma-separated list of success codes
    status_checks = db.relationship('StatusCheck', backref='service', lazy=True)

    def get_success_codes(self):
        """Convert the comma-separated string of success codes to a list of integers"""
        return [int(code.strip()) for code in self.success_codes.split(',')]

class StatusCheck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'operational', 'issue', 'outage'
    date = db.Column(db.Date, nullable=False)
    hour = db.Column(db.Integer, nullable=False)  # 0-23
    
    @staticmethod
    def get_or_create_hourly_status(service_id, timestamp):
        """Get existing hourly status or create new one if doesn't exist"""
        # Extract date and hour from timestamp
        check_date = timestamp.date()
        check_hour = timestamp.hour
        
        # Try to find existing status for this hour
        status = StatusCheck.query.filter_by(
            service_id=service_id,
            date=check_date,
            hour=check_hour
        ).first()
        
        if not status:
            # Create new status if doesn't exist
            status = StatusCheck(
                service_id=service_id,
                status='operational',
                date=check_date,
                hour=check_hour
            )
            db.session.add(status)
            db.session.commit()
        
        return status

    @staticmethod
    def get_daily_status(service_id, date):
        """Get the aggregated status for a specific day"""
        # Get all hourly statuses for the day
        statuses = StatusCheck.query.filter_by(
            service_id=service_id,
            date=date
        ).all()
        
        if not statuses:
            return 'unknown'
        
        # If any status is 'outage', the day is marked as outage
        if any(s.status == 'outage' for s in statuses):
            return 'outage'
        # If any status is 'issue', the day is marked as having issues
        elif any(s.status == 'issue' for s in statuses):
            return 'issue'
        # If all statuses are 'operational', the day is operational
        elif all(s.status == 'operational' for s in statuses):
            return 'operational'
        else:
            return 'unknown'

    @staticmethod
    def get_daily_statuses(service_id, start_date, end_date):
        """Get daily statuses for a date range"""
        daily_statuses = []
        current_date = start_date
        
        while current_date <= end_date:
            status = StatusCheck.get_daily_status(service_id, current_date)
            daily_statuses.append({
                'date': current_date,
                'status': status
            })
            current_date += timedelta(days=1)
        
        return daily_statuses

    @staticmethod
    def get_hourly_statuses(service_id, start_datetime, end_datetime):
        """Get hourly statuses for a datetime range"""
        hourly_statuses = []
        current_datetime = start_datetime
        
        while current_datetime <= end_datetime:
            status = StatusCheck.query.filter_by(
                service_id=service_id,
                date=current_datetime.date(),
                hour=current_datetime.hour
            ).first()
            
            hourly_statuses.append({
                'date': current_datetime.date(),
                'hour': current_datetime.hour,
                'status': status.status if status else 'unknown'
            })
            current_datetime += timedelta(hours=1)
        
        return hourly_statuses

    @staticmethod
    def calculate_uptime(service_id, hours=24):
        """Calculate uptime percentage for the specified period"""
        end_datetime = datetime.utcnow()
        start_datetime = end_datetime - timedelta(hours=hours)
        
        # Get hourly statuses
        hourly_statuses = StatusCheck.get_hourly_statuses(service_id, start_datetime, end_datetime)
        total_hours = len(hourly_statuses)
        
        if total_hours == 0:
            return 100.0
            
        operational_hours = sum(1 for hour in hourly_statuses if hour['status'] == 'operational')
        return round((operational_hours / total_hours) * 100, 2)
