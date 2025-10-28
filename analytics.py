"""
EEG Analytics Module
Handles all complex analytics calculations for student attention tracking
"""
import mysql.connector
from datetime import datetime, timedelta
import logging
import numpy as np
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection using environment variables"""
    try:
        db = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', 'root'),
            database=os.getenv('MYSQL_DATABASE', 'eeg_db1'),
            autocommit=True
        )
        return db
    except mysql.connector.Error as err:
        logger.error(f"Database connection error: {err}")
        return None


def calculate_attention_periods(mac_address, time_window_minutes=60):
    """
    Calculate continuous focus periods for a student
    Returns list of focus periods with quality scores
    """
    try:
        db = get_db_connection()
        if not db:
            return []
        
        cursor = db.cursor(dictionary=True)
        
        # Get student ID
        cursor.execute("SELECT id FROM students WHERE device_mac = %s", (mac_address,))
        student = cursor.fetchone()
        if not student:
            return []
        
        student_id = student['id']
        
        # Get EEG data from last time_window_minutes
        start_time = datetime.now() - timedelta(minutes=time_window_minutes)
        
        cursor.execute("""
            SELECT timestamp, focus, beta, gamma, theta, delta, alpha
            FROM eeg_data 
            WHERE student_id = %s AND timestamp >= %s
            ORDER BY timestamp ASC
        """, (student_id, start_time))
        
        data_points = cursor.fetchall()
        cursor.close()
        db.close()
        
        if not data_points:
            return []
        
        # Analyze focus periods
        periods = []
        current_period = None
        focus_threshold = 0.6  # Minimum focus level to count as "focused"
        
        for point in data_points:
            is_focused = point['focus'] >= focus_threshold
            
            if is_focused:
                if current_period is None:
                    # Start new focus period
                    current_period = {
                        'start_time': point['timestamp'],
                        'end_time': point['timestamp'],
                        'focus_values': [point['focus']],
                        'beta_values': [point['beta']],
                        'gamma_values': [point['gamma']]
                    }
                else:
                    # Continue current period
                    time_gap = (point['timestamp'] - current_period['end_time']).total_seconds()
                    
                    if time_gap <= 10:  # Allow 10 second gap
                        current_period['end_time'] = point['timestamp']
                        current_period['focus_values'].append(point['focus'])
                        current_period['beta_values'].append(point['beta'])
                        current_period['gamma_values'].append(point['gamma'])
                    else:
                        # Gap too large, save current period and start new one
                        if len(current_period['focus_values']) >= 3:  # At least 3 data points
                            periods.append(current_period)
                        
                        current_period = {
                            'start_time': point['timestamp'],
                            'end_time': point['timestamp'],
                            'focus_values': [point['focus']],
                            'beta_values': [point['beta']],
                            'gamma_values': [point['gamma']]
                        }
            else:
                # Not focused - save current period if exists
                if current_period and len(current_period['focus_values']) >= 3:
                    periods.append(current_period)
                current_period = None
        
        # Don't forget the last period
        if current_period and len(current_period['focus_values']) >= 3:
            periods.append(current_period)
        
        # Calculate quality scores for each period
        formatted_periods = []
        for i, period in enumerate(periods):
            duration_seconds = (period['end_time'] - period['start_time']).total_seconds()
            duration_minutes = max(1, int(duration_seconds / 60))
            
            # Calculate quality score (0-100)
            avg_focus = np.mean(period['focus_values'])
            avg_beta = np.mean(period['beta_values'])
            avg_gamma = np.mean(period['gamma_values'])
            
            # Quality = weighted average of focus (60%), beta (25%), gamma (15%)
            quality_score = int((avg_focus * 60 + avg_beta * 25 + avg_gamma * 15))
            
            formatted_periods.append({
                'period_number': i + 1,
                'start_time': period['start_time'].strftime('%H:%M'),
                'end_time': period['end_time'].strftime('%H:%M'),
                'duration_minutes': duration_minutes,
                'quality_score': quality_score,
                'quality_level': 'high' if quality_score >= 75 else ('medium' if quality_score >= 50 else 'low'),
                'is_active': i == len(periods) - 1  # Last period is current
            })
        
        return formatted_periods
        
    except Exception as e:
        logger.error(f"Attention periods calculation error: {e}")
        return []


def calculate_session_stats(mac_address, time_window_minutes=60):
    """
    Calculate today's statistics for a student
    Returns dict with avg attention span, longest span, total focus time
    """
    try:
        periods = calculate_attention_periods(mac_address, time_window_minutes)
        
        if not periods:
            return {
                'avg_attention_span': '0 minutes',
                'longest_span': '0 minutes',
                'total_focus_time': '0 minutes (0%)',
                'total_periods': 0
            }
        
        # Calculate statistics
        durations = [p['duration_minutes'] for p in periods]
        avg_duration = np.mean(durations)
        longest_duration = max(durations)
        total_focus_minutes = sum(durations)
        
        # Calculate percentage (out of time window)
        percentage = min(100, int((total_focus_minutes / time_window_minutes) * 100))
        
        return {
            'avg_attention_span': f"{avg_duration:.1f} minutes",
            'longest_span': f"{longest_duration} minutes",
            'total_focus_time': f"{total_focus_minutes} minutes ({percentage}% of session)",
            'total_periods': len(periods)
        }
        
    except Exception as e:
        logger.error(f"Session stats calculation error: {e}")
        return {
            'avg_attention_span': 'N/A',
            'longest_span': 'N/A',
            'total_focus_time': 'N/A',
            'total_periods': 0
        }


def generate_recommendation(mac_address):
    """
    Generate personalized recommendation based on student's performance
    """
    try:
        stats = calculate_session_stats(mac_address, time_window_minutes=60)
        periods = calculate_attention_periods(mac_address, time_window_minutes=60)
        
        if not periods:
            return "Start monitoring to receive personalized recommendations."
        
        # Extract average duration
        avg_span_str = stats['avg_attention_span']
        try:
            avg_minutes = float(avg_span_str.split()[0])
        except:
            avg_minutes = 0
        
        # Get quality of recent periods
        recent_quality = [p['quality_score'] for p in periods[-3:]] if len(periods) >= 3 else [p['quality_score'] for p in periods]
        avg_quality = np.mean(recent_quality) if recent_quality else 0
        
        # Generate recommendation based on performance
        if avg_minutes >= 20 and avg_quality >= 80:
            return "Excellent focus! You're maintaining great attention spans. Keep up the outstanding work!"
        elif avg_minutes >= 15 and avg_quality >= 70:
            return "Good progress! Try extending your focus sessions to 20+ minutes for optimal performance."
        elif avg_minutes >= 10 and avg_quality >= 60:
            return "You're building good focus habits. Aim for 15+ minute continuous attention spans."
        elif avg_minutes >= 5:
            return "Take short breaks between focus sessions. Try the Pomodoro technique: 25 minutes focus, 5 minutes break."
        else:
            return "Practice mindful breathing before studying. Start with 5-minute focus goals and gradually increase."
        
    except Exception as e:
        logger.error(f"Recommendation generation error: {e}")
        return "Continue monitoring to receive personalized recommendations."


def get_wave_timeline_data(mac_address, time_window_minutes=30):
    """
    Get timeline data for brain wave visualization
    Returns arrays of timestamps and wave values for charting
    """
    try:
        db = get_db_connection()
        if not db:
            return None
        
        cursor = db.cursor(dictionary=True)
        
        # Get student ID
        cursor.execute("SELECT id FROM students WHERE device_mac = %s", (mac_address,))
        student = cursor.fetchone()
        if not student:
            cursor.close()
            db.close()
            return None
        
        student_id = student['id']
        
        # Get last 30 minutes of data
        start_time = datetime.now() - timedelta(minutes=time_window_minutes)
        
        cursor.execute("""
            SELECT timestamp, alpha, beta, theta, delta, gamma, focus
            FROM eeg_data 
            WHERE student_id = %s AND timestamp >= %s
            ORDER BY timestamp ASC
        """, (student_id, start_time))
        
        data_points = cursor.fetchall()
        cursor.close()
        db.close()
        
        if not data_points:
            return None
        
        # Format for charting
        timeline = {
            'timestamps': [point['timestamp'].strftime('%H:%M:%S') for point in data_points],
            'alpha': [float(point['alpha']) for point in data_points],
            'beta': [float(point['beta']) for point in data_points],
            'theta': [float(point['theta']) for point in data_points],
            'delta': [float(point['delta']) for point in data_points],
            'gamma': [float(point['gamma']) for point in data_points],
            'focus': [float(point['focus']) * 100 for point in data_points]  # Convert to percentage
        }
        
        return timeline
        
    except Exception as e:
        logger.error(f"Wave timeline data error: {e}")
        return None


def calculate_performance_metrics(mac_address, time_window_minutes=60):
    """
    Calculate performance metrics: focus level, engagement, quality score
    """
    try:
        db = get_db_connection()
        if not db:
            return {'focus_level': 0, 'engagement': 0, 'quality_score': 0}
        
        cursor = db.cursor(dictionary=True)
        
        # Get student ID
        cursor.execute("SELECT id FROM students WHERE device_mac = %s", (mac_address,))
        student = cursor.fetchone()
        if not student:
            cursor.close()
            db.close()
            return {'focus_level': 0, 'engagement': 0, 'quality_score': 0}
        
        student_id = student['id']
        
        # Get recent data
        start_time = datetime.now() - timedelta(minutes=time_window_minutes)
        
        cursor.execute("""
            SELECT focus, beta, gamma, alpha, theta, delta
            FROM eeg_data 
            WHERE student_id = %s AND timestamp >= %s
            ORDER BY timestamp DESC
        """, (student_id, start_time))
        
        data_points = cursor.fetchall()
        cursor.close()
        db.close()
        
        if not data_points:
            return {'focus_level': 0, 'engagement': 0, 'quality_score': 0}
        
        # Calculate metrics
        focus_values = [point['focus'] for point in data_points]
        beta_values = [point['beta'] for point in data_points]
        gamma_values = [point['gamma'] for point in data_points]
        alpha_values = [point['alpha'] for point in data_points]
        theta_values = [point['theta'] for point in data_points]
        
        # Focus Level: average of recent focus values (0-100%)
        focus_level = int(np.mean(focus_values) * 100)
        
        # Engagement: based on beta and gamma activity (0-100%)
        # High beta + gamma = high engagement
        engagement_scores = [(b + g) / 2 for b, g in zip(beta_values, gamma_values)]
        engagement = int(np.mean(engagement_scores) * 100)
        
        # Quality Score: weighted combination (0-100)
        # Focus 40%, Beta 30%, Gamma 20%, Low Theta 10%
        quality_scores = []
        for f, b, g, t in zip(focus_values, beta_values, gamma_values, theta_values):
            quality = (f * 0.4 + b * 0.3 + g * 0.2 + (1 - t) * 0.1)
            quality_scores.append(quality)
        
        quality_score = int(np.mean(quality_scores) * 100)
        
        return {
            'focus_level': min(100, max(0, focus_level)),
            'engagement': min(100, max(0, engagement)),
            'quality_score': min(100, max(0, quality_score))
        }
        
    except Exception as e:
        logger.error(f"Performance metrics calculation error: {e}")
        return {'focus_level': 0, 'engagement': 0, 'quality_score': 0}
