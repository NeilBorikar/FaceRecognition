import sqlite3
import pickle
from datetime import datetime
from logging.handlers import RotatingFileHandler


class FaceDatabase:
    """
    Manages the face recognition database using SQLite.
    """
    def __init__(self, db_path: str = 'face_recognition.db'):
        # Connect to the SQLite database, enabling parsing of declared types (for TIMESTAMP).
        self.conn = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,check_same_thread=False
            # check_same_thread=False  # Uncomment if using across multiple threads.
        )
        # Enforce foreign key constraints for referential integrity.
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Create tables if they don't exist.
        self._create_tables()

    def _create_tables(self):
        """Create necessary tables for users, face_encodings, and attendance."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                email       TEXT UNIQUE,
                department  TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_encodings (
                encoding_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                encoding    BLOB NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance_records (
                record_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        # Indexes to improve query performance.
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_email ON users(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_user ON attendance_records(user_id)')
        self.conn.commit()
        cursor.close()

    def add_user(self, name: str, email: str = None, department: str = None) -> int:
        """
        Add a new user and return the generated user_id.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO users (name, email, department) 
            VALUES (?, ?, ?)
        ''', (name, email, department))
        user_id = cursor.lastrowid
        self.conn.commit()
        cursor.close()
        return user_id

    def add_face_encoding(self, user_id: int, encoding) -> None:
        """
        Store a face encoding (e.g. a list or array) for the given user.
        """
        # Serialize the encoding to bytes.
        encoding_blob = pickle.dumps(encoding)
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO face_encodings (user_id, encoding) 
            VALUES (?, ?)
        ''', (user_id, encoding_blob))
        self.conn.commit()
        cursor.close()

    def get_all_encodings(self):
        """
        Retrieve all face encodings with corresponding user_id and name.
        Returns a list of dicts: [{'user_id': ..., 'name': ..., 'encoding': ...}, ...].
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT u.user_id, u.name, fe.encoding
            FROM face_encodings fe
            JOIN users u ON fe.user_id = u.user_id
        ''')
        rows = cursor.fetchall()
        cursor.close()
        encodings = []
        for (user_id, name, encoding_blob) in rows:
            encoding = pickle.loads(encoding_blob)
            encodings.append({'user_id': user_id, 'name': name, 'encoding': encoding})
        return encodings

    def record_attendance(self, user_id: int) -> None:
        """
        Record attendance for the specified user with the current timestamp.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO attendance_records (user_id)
            VALUES (?)
        ''', (user_id,))
        self.conn.commit()
        cursor.close()

    def get_attendance_report(self, date: str = None):
        """
        Generate an attendance report. If a date (YYYY-MM-DD) is given, filter by that date.
        Returns a list of (name, attendance_count) tuples.
        """
        cursor = self.conn.cursor()
        query = '''
            SELECT u.name, COUNT(ar.record_id) AS attendance_count
            FROM users u
            LEFT JOIN attendance_records ar ON u.user_id = ar.user_id
        '''
        params = ()
        if date:
            query += ' WHERE DATE(ar.timestamp) = ?'
            params = (date,)
        query += ' GROUP BY u.name ORDER BY attendance_count DESC'
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        return results

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()