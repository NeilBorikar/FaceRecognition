from database import FaceDatabase
import logging
from datetime import datetime

db=FaceDatabase()
logging.basicConfig(filename='attendance.log',level=logging.INFO,format='%(asctime)s-%(message)s')



def mark_attendance(user_id, name):
    """Record attendance in the database"""
    try:
        
        today = datetime.now().date()
        existing = db.get_attendance_report(today)
        present_today = any(record[0] == name for record in existing)
        
        if not present_today:
            db.record_attendance(user_id)
            logging.info(f"Marked attendance for {name}")
            return True
        else:
            logging.warning(f"{name} already marked today")
            return False
    except Exception as e:
        logging.error(f"Error marking attendance: {str(e)}")
        return False

def load_known_faces():
    """Load encodings from database"""
    encodings_data = db.get_all_encodings()
    encodings = [data['encoding'] for data in encodings_data]
    names = [data['name'] for data in encodings_data]
    user_ids = [data['user_id'] for data in encodings_data]
    return encodings, names, user_ids
