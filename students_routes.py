"""
Students Routes Module
Handles all student-related endpoints
"""
from flask import jsonify, render_template
import mysql.connector  # Only for error handling
import logging
from datetime import datetime, timedelta
import numpy as np

# Import centralized database connection
from db import get_db_connection

logger = logging.getLogger(__name__)

def get_formula_based_state(percentages):
    """
    Formula-based state classification (fallback)
    Uses NASA Engagement Index thresholds
    """
    beta_pct = percentages.get('beta', 0)
    alpha_pct = percentages.get('alpha', 0)
    theta_pct = percentages.get('theta', 0)
    delta_pct = percentages.get('delta', 0)
    
    if beta_pct > 25 and alpha_pct < 35 and theta_pct < 25:
        return "focused"
    elif alpha_pct > 30 and beta_pct < 30 and theta_pct < 25:
        return "relaxed"
    elif delta_pct > 35 or (theta_pct > 30 and alpha_pct < 20):
        return "drowsy"
    elif theta_pct > 35 and alpha_pct < 20 and beta_pct < 20:
        return "distracted"
    else:
        # Default based on dominant band
        if beta_pct >= max(alpha_pct, theta_pct, delta_pct):
            return "focused"
        elif alpha_pct >= max(theta_pct, delta_pct):
            return "relaxed"
        elif delta_pct >= theta_pct:
            return "drowsy"
        else:
            return "distracted"

def register_students_routes(app, device_statuses_ref, predict_state_hybrid_func=None, extract_ml_features_func=None):
    """
    Register all student-related routes
    
    Args:
        app: Flask app instance
        device_statuses_ref: Reference to device statuses dictionary
        predict_state_hybrid_func: Hybrid prediction function from app.py
        extract_ml_features_func: Feature extraction function from app.py
    """
    
    @app.route("/students-page")
    def students_page():
        """Render students page"""
        return render_template("students.html")

    @app.route("/api/students-details-list", methods=['GET'])
    def get_students_details_list():
        """Get all registered students from database WITH detailed session info"""
        try:
            db = get_db_connection()
            if not db:
                return jsonify({"status": "error", "msg": "Database connection failed"}), 500
                
            cursor = db.cursor(dictionary=True)
            
            # Fetch all students - simple query
            cursor.execute("""
                SELECT s.id, s.name, s.device_mac, s.created_at
                FROM students s
                ORDER BY s.name ASC
            """)
            students = cursor.fetchall()
            
            # For each student, get their info AND live state
            students_list = []
            for student in students:
                mac_address = student['device_mac']
                
                # Get total sessions count
                cursor.execute("""
                    SELECT COUNT(DISTINCT DATE(timestamp)) as total_sessions
                    FROM eeg_data
                    WHERE mac_address = %s
                """, (mac_address,))
                
                session_data = cursor.fetchone()
                
                # Get latest EEG data for current state
                cursor.execute("""
                    SELECT delta, theta, alpha, beta, gamma, focus, signal_quality, timestamp
                    FROM eeg_data
                    WHERE mac_address = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (mac_address,))
                
                latest_eeg = cursor.fetchone()
                
                # Check if device is CURRENTLY connected (within last 10 seconds)
                is_connected = False
                current_state = "disconnected"
                focus_value = 0
                band_powers = {"delta": 0, "theta": 0, "alpha": 0, "beta": 0, "gamma": 0}
                
                if latest_eeg and latest_eeg['timestamp']:
                    time_diff = (datetime.now() - latest_eeg['timestamp']).total_seconds()
                    
                    # If data is recent (within 10 seconds), device is connected
                    if time_diff < 10:
                        is_connected = True
                        focus_value = latest_eeg['focus'] if latest_eeg['focus'] else 0
                        
                        # Get band powers
                        band_powers = {
                            "delta": latest_eeg['delta'] or 0,
                            "theta": latest_eeg['theta'] or 0,
                            "alpha": latest_eeg['alpha'] or 0,
                            "beta": latest_eeg['beta'] or 0,
                            "gamma": latest_eeg['gamma'] or 0
                        }
                        
                        # Calculate total for percentages
                        total = sum(band_powers.values())
                        if total > 0:
                            percentages = {k: (v/total)*100 for k, v in band_powers.items()}
                            
                            # 🔥 HYBRID PREDICTION: Use ML + Formula if function provided
                            if predict_state_hybrid_func:
                                try:
                                    current_state = predict_state_hybrid_func(band_powers, focus_value, None)
                                    logger.debug(f"🤖 Hybrid state for {student['name']}: {current_state}")
                                except Exception as e:
                                    logger.error(f"Hybrid prediction failed: {e}, using formula")
                                    current_state = get_formula_based_state(percentages)
                            else:
                                # Fallback to formula-based classification
                                current_state = get_formula_based_state(percentages)
                
                student_info = {
                    'id': str(student['id']),
                    'name': student['name'],
                    'mac_address': mac_address,
                    'created_at': student['created_at'].isoformat() if student['created_at'] else None,
                    'total_sessions': session_data['total_sessions'] if session_data else 0,
                    'last_active': latest_eeg['timestamp'].isoformat() if latest_eeg and latest_eeg['timestamp'] else None,
                    'is_connected': is_connected,
                    'state': current_state,
                    'focus': round(focus_value, 2),
                    'band_powers': band_powers
                }
                students_list.append(student_info)
            
            cursor.close()
            db.close()
            
            logger.info(f"Fetched {len(students_list)} students, Connected: {sum(1 for s in students_list if s['is_connected'])}")
            return jsonify({"status": "success", "students": students_list})
            
        except Exception as e:
            logger.error(f"Error fetching students list: {e}")
            return jsonify({"status": "error", "msg": str(e)}), 500

    @app.route("/api/student-details/<mac_address>", methods=['GET'])
    def get_student_details(mac_address):
        """Get detailed information about a specific student"""
        try:
            db = get_db_connection()
            if not db:
                return jsonify({"status": "error", "msg": "Database connection failed"}), 500
                
            cursor = db.cursor(dictionary=True)
            
            # Get student info
            cursor.execute("""
                SELECT id, name, device_mac, created_at
                FROM students
                WHERE device_mac = %s
            """, (mac_address,))
            
            student = cursor.fetchone()
            if not student:
                cursor.close()
                db.close()
                return jsonify({"status": "error", "msg": "Student not found"}), 404
            
            # Get session statistics
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT DATE(timestamp)) as total_sessions,
                    COUNT(*) as total_data_points,
                    AVG(focus) as avg_focus,
                    MAX(focus) as peak_focus
                FROM eeg_data
                WHERE mac_address = %s
            """, (mac_address,))
            
            stats = cursor.fetchone()
            
            cursor.close()
            db.close()
            
            return jsonify({
                "status": "success",
                "student": {
                    "name": student['name'],
                    "mac_address": student['device_mac'],
                    "total_sessions": stats['total_sessions'] or 0,
                    "total_data_points": stats['total_data_points'] or 0,
                    "avg_focus": round(stats['avg_focus'] or 0, 1),
                    "peak_focus": round(stats['peak_focus'] or 0, 1)
                }
            })
            
        except Exception as e:
            logger.error(f"Error fetching student details: {e}")
            return jsonify({"status": "error", "msg": str(e)}), 500
