"""
Session Routes Module
Handles all session-related endpoints
"""
from flask import jsonify, render_template
import mysql.connector
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection using environment variables"""
    try:
        return mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', 'root'),
            database=os.getenv('MYSQL_DATABASE', 'eeg_db1')
        )
    except mysql.connector.Error as err:
        logger.error(f"Database connection error: {err}")
        return None

def register_session_routes(app):
    """Register all session-related routes"""
    
    @app.route("/session-history")
    def session_history_page():
        """Render session history page"""
        return render_template("session-history.html")

    @app.route("/api/session-history", methods=['GET'])
    def get_session_history():
        """Get all monitoring sessions with summary statistics"""
        try:
            db = get_db_connection()
            if not db:
                return jsonify({"status": "error", "msg": "Database connection failed"}), 500
                
            cursor = db.cursor(dictionary=True)
            
            # Fetch all monitoring sessions with basic info
            cursor.execute("""
                SELECT 
                    ms.id,
                    ms.teacher_name,
                    ms.subject,
                    ms.start_time,
                    ms.end_time,
                    ms.active,
                    COUNT(DISTINCT e.mac_address) as student_count
                FROM monitoring_sessions ms
                LEFT JOIN eeg_data e ON e.timestamp BETWEEN ms.start_time AND COALESCE(ms.end_time, NOW())
                GROUP BY ms.id, ms.teacher_name, ms.subject, ms.start_time, ms.end_time, ms.active
                ORDER BY ms.start_time DESC
            """)
            
            sessions = cursor.fetchall()
            
            # Convert datetime to ISO format and calculate avg attention span for each session
            for session in sessions:
                session_start = session['start_time']
                session_end = session['end_time']
                
                if session['start_time']:
                    session['start_time'] = session['start_time'].isoformat()
                if session['end_time']:
                    session['end_time'] = session['end_time'].isoformat()
                
                # Calculate average attention span (in minutes) for this session
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT mac_address) as student_count,
                        AVG(attention_minutes) as avg_attention_span
                    FROM (
                        SELECT 
                            mac_address,
                            COUNT(*) * 1.0 / 60 as attention_minutes
                        FROM eeg_data
                        WHERE timestamp BETWEEN %s AND COALESCE(%s, NOW())
                        AND focus >= 60
                        GROUP BY mac_address
                    ) as student_attention
                """, (session_start, session_end))
                
                result = cursor.fetchone()
                session['avg_attention_span'] = round(result['avg_attention_span'] or 0, 1)
                
                # Add status based on active flag
                session['status'] = 'active' if session['active'] else 'completed'
            
            cursor.close()
            db.close()
            
            logger.info(f"Fetched {len(sessions)} sessions")
            return jsonify({"status": "success", "sessions": sessions})
            
        except Exception as e:
            logger.error(f"Error fetching session history: {e}")
            return jsonify({"status": "error", "msg": str(e)}), 500

    @app.route("/api/session-details/<int:session_id>", methods=['GET'])
    def get_session_details(session_id):
        """Get detailed information about a specific monitoring session"""
        try:
            db = get_db_connection()
            if not db:
                return jsonify({"status": "error", "msg": "Database connection failed"}), 500
                
            cursor = db.cursor(dictionary=True)
            
            # Get monitoring session info
            cursor.execute("""
                SELECT id, teacher_name, subject, start_time, end_time, active
                FROM monitoring_sessions
                WHERE id = %s
            """, (session_id,))
            
            session = cursor.fetchone()
            
            if not session:
                cursor.close()
                db.close()
                return jsonify({"status": "error", "msg": "Session not found"}), 404
            
            # Get session statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as data_points,
                    COUNT(DISTINCT mac_address) as unique_students,
                    ROUND(AVG(focus), 1) as avg_focus,
                    ROUND(MAX(focus), 1) as peak_focus
                FROM eeg_data
                WHERE timestamp BETWEEN %s AND COALESCE(%s, NOW())
            """, (session['start_time'], session['end_time']))
            
            stats = cursor.fetchone()
            
            # Calculate total focus time in minutes
            if session['end_time']:
                duration = (session['end_time'] - session['start_time']).total_seconds() / 60
            else:
                duration = (datetime.now() - session['start_time']).total_seconds() / 60
            
            # Estimate focus time (assuming data points with focus >= 60)
            cursor.execute("""
                SELECT COUNT(*) * 1.0 / 60 as focus_minutes
                FROM eeg_data
                WHERE timestamp BETWEEN %s AND COALESCE(%s, NOW())
                AND focus >= 60
            """, (session['start_time'], session['end_time']))
            
            focus_time_result = cursor.fetchone()
            total_focus_minutes = round(focus_time_result['focus_minutes'] or 0, 1)
            
            # Get students in session with their performance
            cursor.execute("""
                SELECT 
                    s.name,
                    s.device_mac as mac_address,
                    AVG(e.focus) as avg_focus,
                    MAX(e.focus) as peak_focus,
                    COUNT(*) as data_points
                FROM students s
                JOIN eeg_data e ON s.device_mac = e.mac_address
                WHERE e.timestamp BETWEEN %s AND COALESCE(%s, NOW())
                GROUP BY s.name, s.device_mac
                ORDER BY avg_focus DESC
            """, (session['start_time'], session['end_time']))
            
            students = cursor.fetchall()
            
            # Format student data
            for student in students:
                student['avg_focus'] = round(student['avg_focus'] or 0, 1)
                student['peak_focus'] = round(student['peak_focus'] or 0, 1)
            
            cursor.close()
            db.close()
            
            return jsonify({
                "status": "success",
                "session": {
                    "id": session['id'],
                    "teacher_name": session['teacher_name'],
                    "subject": session['subject'],
                    "start_time": session['start_time'].isoformat(),
                    "end_time": session['end_time'].isoformat() if session['end_time'] else None,
                    "active": session['active']
                },
                "data_points": stats['data_points'] or 0,
                "avg_focus": stats['avg_focus'] or 0,
                "peak_focus": stats['peak_focus'] or 0,
                "total_focus_minutes": total_focus_minutes,
                "avg_attention_span": total_focus_minutes / (stats['unique_students'] or 1),
                "students": students
            })
            
        except Exception as e:
            logger.error(f"Error fetching session details: {e}")
            return jsonify({"status": "error", "msg": str(e)}), 500
