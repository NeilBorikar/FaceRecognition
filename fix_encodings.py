import sqlite3
import pickle
import numpy as np

def fix_encodings():
    conn = sqlite3.connect('face_recognition.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT encoding_id, user_id, encoding FROM face_encodings')
    rows = cursor.fetchall()
    
    for encoding_id, user_id, encoding_blob in rows:
        try:
            # Test if encoding is valid
            encoding = pickle.loads(encoding_blob)
            np.frombuffer(encoding, dtype=np.float64)
            print(f"Encoding {encoding_id} for user {user_id} is valid")
        except Exception as e:
            print(f"Fixing invalid encoding {encoding_id} for user {user_id}")
            cursor.execute('DELETE FROM face_encodings WHERE encoding_id = ?', (encoding_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    print("Database repair complete")

if __name__ == '__main__':
    fix_encodings()