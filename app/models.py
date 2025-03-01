from datetime import datetime, timedelta, time
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class StatusCheck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'operational', 'issue', 'outage'
    date = db.Column(db.Date, nullable=False)
    hour = db.Column(db.Integer, nullable=False)  # 0-23
    minute = db.Column(db.Integer, nullable=False)  # 0-59
    
    @staticmethod
    def get_or_create_minute_status(service_name, timestamp):
        """Get existing minute status or create new one if doesn't exist"""
        # Extract date, hour and minute from timestamp
        check_date = timestamp.date()
        check_hour = timestamp.hour
        check_minute = timestamp.minute
        
        # Try to find existing status for this minute
        status = StatusCheck.query.filter_by(
            service_name=service_name,
            date=check_date,
            hour=check_hour,
            minute=check_minute
        ).first()
        
        if not status:
            # Create new status if doesn't exist
            status = StatusCheck(
                service_name=service_name,
                status='operational',
                date=check_date,
                hour=check_hour,
                minute=check_minute
            )
            db.session.add(status)
            db.session.commit()
        
        return status

    @staticmethod
    def get_minute_statuses(service_name, start_datetime, end_datetime):
        """Get minute statuses for a datetime range"""
        # Get all statuses in the time range with a single query
        statuses = StatusCheck.query.filter(
            StatusCheck.service_name == service_name,
            StatusCheck.date >= start_datetime.date(),
            StatusCheck.date <= end_datetime.date()
        ).order_by(StatusCheck.date, StatusCheck.hour, StatusCheck.minute).all()

        # Create a dictionary for quick lookup
        status_dict = {
            (s.date, s.hour, s.minute): s.status 
            for s in statuses
        }

        minute_statuses = []
        current_datetime = start_datetime
        found_first_status = False

        while current_datetime <= end_datetime:
            key = (current_datetime.date(), current_datetime.hour, current_datetime.minute)
            status = status_dict.get(key)
            
            if status:
                found_first_status = True
            
            if found_first_status:
                minute_statuses.append({
                    'date': current_datetime.date(),
                    'hour': current_datetime.hour,
                    'minute': current_datetime.minute,
                    'status': status if status else 'unknown'
                })
            current_datetime += timedelta(minutes=1)
        
        return minute_statuses

    @staticmethod
    def calculate_uptime(service_name, minutes=1440):  # 1440 minutes = 24 hours
        """Calculate uptime percentage for the specified period"""
        end_datetime = datetime.utcnow()
        start_datetime = end_datetime - timedelta(minutes=minutes)
        
        # Get minute statuses
        minute_statuses = StatusCheck.get_minute_statuses(service_name, start_datetime, end_datetime)
        total_minutes = len(minute_statuses)
        
        if total_minutes == 0:
            return 100.0
            
        operational_minutes = sum(1 for minute in minute_statuses if minute['status'] == 'operational')
        return round((operational_minutes / total_minutes) * 100, 2)

    @staticmethod
    def get_last_success_time(service_name):
        """Get the last time the service was operational"""
        last_success = StatusCheck.query.filter_by(
            service_name=service_name,
            status='operational'
        ).order_by(StatusCheck.date.desc(), StatusCheck.hour.desc(), StatusCheck.minute.desc()).first()
        
        if last_success:
            return datetime.combine(last_success.date, time(hour=last_success.hour, minute=last_success.minute))
        return None

    @staticmethod
    def get_failure_duration(service_name):
        """Get how long the service has been failing"""
        last_success = StatusCheck.get_last_success_time(service_name)
        if not last_success:
            return "Never operational"
        
        current_time = datetime.utcnow()
        duration = current_time - last_success
        
        if duration.days > 0:
            return f"Failed for {duration.days} days, {duration.seconds // 3600} hours"
        elif duration.seconds // 3600 > 0:
            return f"Failed for {duration.seconds // 3600} hours, {(duration.seconds % 3600) // 60} minutes"
        else:
            return f"Failed for {duration.seconds // 60} minutes"

    @staticmethod
    def get_aggregated_statuses(service_name, start_datetime, end_datetime):
        """Get 30-minute aggregated statuses for a datetime range"""
        # Get all statuses in the time range with a single query
        statuses = StatusCheck.query.filter(
            StatusCheck.service_name == service_name,
            StatusCheck.date >= start_datetime.date(),
            StatusCheck.date <= end_datetime.date()
        ).order_by(StatusCheck.date, StatusCheck.hour, StatusCheck.minute).all()

        # Create a dictionary for quick lookup
        status_dict = {}
        failed_count = 0
        last_status = 'unknown'
        for s in statuses:
            last_status = s.status
            timestamp = datetime.combine(s.date, time(hour=s.hour, minute=s.minute))
            # Calculate the 30-minute block key (floor to nearest 30 minutes)
            block_timestamp = timestamp.replace(minute=(timestamp.minute // 30) * 30)
            if block_timestamp not in status_dict:
                status_dict[block_timestamp] = s.status
            else:
                if s.status == 'issue' or s.status == 'outage':
                    failed_count += 1
                if failed_count > 15:
                    status_dict[block_timestamp] = 'outage'
                elif failed_count > 0:
                    status_dict[block_timestamp] = 'issue'
                else:
                    status_dict[block_timestamp] = 'operational'

        aggregated_statuses = []

        current = start_datetime
        while current <= end_datetime:
            block_timestamp = datetime.combine(current.date(), time(hour=current.hour, minute=current.minute)).replace(minute=(timestamp.minute // 30) * 30)
            status = status_dict.get(block_timestamp, 'unknown')
            display_timestamp = block_timestamp + timedelta(hours=8)
            aggregated_statuses.append({
                'date': display_timestamp.date(),
                'hour': display_timestamp.hour,
                'minute': display_timestamp.minute,
                'status': status
            })
            current += timedelta(minutes=30)
        
        # Replace the last status of aggregated_statuses with the last status of status_dict
        aggregated_statuses[-1]['status'] = last_status

        return aggregated_statuses
