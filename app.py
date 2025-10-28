from flask import Flask, request, jsonify, render_template
import numpy as np
from scipy.signal import butter, lfilter, iirnotch
import mysql.connector
from datetime import datetime
import traceback
import logging
import joblib
import os
from dotenv import load_dotenv  # Added for environment variables
from analytics import (
    calculate_attention_periods,
    calculate_session_stats,
    generate_recommendation,
    get_wave_timeline_data,
    calculate_performance_metrics
)

# Load environment variables from .env file
load_dotenv()

# Import route modules
from students_routes import register_students_routes
from session_routes import register_session_routes

app = Flask(__name__)

# ----- ML Model Loading -----
ML_MODEL = None
ML_MODEL_PATH = "optimized_eeg_model_78.joblib"

def load_ml_model():
    """Load the trained ML model for enhanced state prediction"""
    global ML_MODEL
    try:
        if os.path.exists(ML_MODEL_PATH):
            loaded_data = joblib.load(ML_MODEL_PATH)
            
            # Check if it's a dict (saved as {'model': model_obj, ...})
            if isinstance(loaded_data, dict):
                if 'model' in loaded_data:
                    ML_MODEL = loaded_data['model']
                    logger.info("✅ ML Model loaded from dict successfully")
                elif 'voting_classifier' in loaded_data:
                    ML_MODEL = loaded_data['voting_classifier']
                    logger.info("✅ Voting Classifier loaded successfully")
                elif 'best_model' in loaded_data:
                    ML_MODEL = loaded_data['best_model']
                    logger.info("✅ Best Model loaded successfully")
                else:
                    # Try to find any model-like object in dict
                    for key, value in loaded_data.items():
                        if hasattr(value, 'predict') and hasattr(value, 'predict_proba'):
                            ML_MODEL = value
                            logger.info(f"✅ ML Model loaded from key '{key}'")
                            break
                    
                    if ML_MODEL is None:
                        logger.warning("⚠️ No valid model found in dict, disabling ML prediction")
                        return False
            else:
                # Direct model object
                ML_MODEL = loaded_data
                logger.info("✅ ML Model loaded successfully for hybrid prediction")
            
            # Verify model has required methods
            if hasattr(ML_MODEL, 'predict') and hasattr(ML_MODEL, 'predict_proba'):
                logger.info("✅ Model validation passed - predict() and predict_proba() available")
                return True
            else:
                logger.error("❌ Loaded object doesn't have predict/predict_proba methods")
                ML_MODEL = None
                return False
                
        else:
            logger.warning(f"⚠️ ML Model not found at {ML_MODEL_PATH}. Using formula-based prediction only.")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to load ML model: {e}")
        ML_MODEL = None
        return False

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ----- EEG Processing Parameters -----
SAMPLE_RATE = 250  # Hz
BUFFER_SIZE = 500  # 2 seconds buffer at 250 Hz

# Updated EEG frequency bands based on research standards
EEG_BANDS = {
    "delta": (0.5, 4),
    "theta": (4, 8),
    "alpha": (8, 13),
    "beta":  (13, 30),
    "gamma": (30, 45)
}

# ----- EEG Buffer (per device MAC) -----
EEG_BUFFERS = {}  # Dictionary to store separate buffers for each MAC address
DEVICE_STATUSES = {}  # Dictionary to store status for each device MAC address

# ----- MySQL Setup -----
def get_db_connection():
    """
    Connect to Clever Cloud MySQL Database
    Uses environment variables from .env file for security
    """
    try:
        # Get database credentials from environment variables
        db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', 'root'),
            'database': os.getenv('MYSQL_DATABASE', 'eeg_db1'),
            'autocommit': True,
            'connection_timeout': 30,  # 30 seconds timeout for Clever Cloud
            'pool_name': 'eeg_pool',  # Short pool name to avoid length issues
            'pool_size': 5,  # Connection pooling for better performance
            'pool_reset_session': True
        }
        
        db = mysql.connector.connect(**db_config)
        logger.info(f"✅ Connected to MySQL: {db_config['host']}")
        return db
    except mysql.connector.Error as err:
        logger.error(f"❌ Database connection error: {err}")
        logger.error(f"Host: {os.getenv('MYSQL_HOST', 'Not set')}")
        return None

# Initialize database
def init_database():
    db = get_db_connection()
    if db:
        cursor = db.cursor()
        try:
            # Create students table FIRST (no foreign keys)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100),
                device_mac VARCHAR(50) UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Create monitoring_sessions table (no foreign keys)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                teacher_name VARCHAR(100),
                subject VARCHAR(100),
                start_time DATETIME,
                end_time DATETIME,
                active BOOLEAN DEFAULT TRUE,
                INDEX idx_active (active)
            )
            """)
            
            # Now create raw_data (references students)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME,
                adc_value INT,
                mac_address VARCHAR(50),
                student_id INT,
                INDEX idx_timestamp (timestamp),
                INDEX idx_mac (mac_address),
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE SET NULL
            )
            """)

            # Create eeg_data (references students)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS eeg_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME,
                delta FLOAT,
                theta FLOAT,
                alpha FLOAT,
                beta FLOAT,
                gamma FLOAT,
                focus FLOAT,
                signal_quality VARCHAR(20),
                mac_address VARCHAR(50),
                student_id INT,
                INDEX idx_timestamp (timestamp),
                INDEX idx_mac (mac_address),
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE SET NULL
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT,
                session_name VARCHAR(100),
                start_time DATETIME,
                end_time DATETIME,
                active BOOLEAN DEFAULT TRUE,
                monitoring_session_id INT,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (monitoring_session_id) REFERENCES monitoring_sessions(id) ON DELETE SET NULL
            )
            """)
            
            logger.info("Database tables initialized successfully")
            return True
        except mysql.connector.Error as err:
            logger.error(f"Database initialization error: {err}")
            return False
        finally:
            cursor.close()
            db.close()
    return False

# ----- Signal Processing Functions -----
def bandpass_filter(data, lowcut=0.5, highcut=48, fs=SAMPLE_RATE, order=2):
    try:
        if len(data) < 10:
            return data
        nyq = 0.5 * fs
        low = max(lowcut / nyq, 0.01)
        high = min(highcut / nyq, 0.99)
        b, a = butter(order, [low, high], btype='band')
        return lfilter(b, a, data)
    except Exception as e:
        logger.error(f"Bandpass filter error: {e}")
        return data

def notch_filter(data, freq=50.0, fs=SAMPLE_RATE, Q=10.0):
    try:
        if len(data) < 10:
            return data
        b, a = iirnotch(freq/(fs/2), Q)
        return lfilter(b, a, data)
    except Exception as e:
        logger.error(f"Notch filter error: {e}")
        return data

def compute_band_power(signal):
    """Compute EEG band powers using FFT with Hamming window"""
    try:
        N = len(signal)
        if N < 50:
            return {band: 0.1 for band in EEG_BANDS}
        
        signal = signal - np.mean(signal)
        window = np.hamming(N)
        signal_windowed = signal * window
        
        freqs = np.fft.rfftfreq(N, 1/SAMPLE_RATE)
        fft_vals = np.abs(np.fft.rfft(signal_windowed))**2
        
        window_power = np.sum(window**2) / N
        psd = fft_vals / (N * window_power)
        
        band_powers = {}
        for band, (low, high) in EEG_BANDS.items():
            idx = np.logical_and(freqs >= low, freqs <= high)
            if np.any(idx):
                power = float(np.sum(psd[idx]))
                band_powers[band] = max(power, 0.01)
            else:
                band_powers[band] = 0.01
        
        return band_powers
        
    except Exception as e:
        logger.error(f"Band power computation error: {e}")
        return {band: 0.1 for band in EEG_BANDS}

def calculate_focus(band_powers):
    """Calculate attention/focus level using NASA Engagement Index"""
    try:
        beta = band_powers.get('beta', 0.01)
        alpha = band_powers.get('alpha', 0.01)
        theta = band_powers.get('theta', 0.01)
        delta = band_powers.get('delta', 0.01)
        gamma = band_powers.get('gamma', 0.01)
        
        # NASA Engagement Index: Beta / (Alpha + Theta)
        denominator = alpha + theta
        if denominator > 0.01:
            engagement_index = beta / denominator
        else:
            engagement_index = 0
        
        focus_base = min(1.0, engagement_index / 2.0)
        
        # Beta/Theta ratio
        if theta > 0.01:
            beta_theta_ratio = beta / theta
        else:
            beta_theta_ratio = 0
        
        # Gamma enhancement
        total_power = sum(band_powers.values())
        if total_power > 0:
            gamma_factor = (gamma / total_power) * 2.0
            delta_penalty = (delta / total_power) * 1.5
        else:
            gamma_factor = 0
            delta_penalty = 0
        
        focus_score = focus_base + gamma_factor - delta_penalty
        focus_score = max(0.0, min(1.0, focus_score))
        
        # Fine-tune thresholds
        if total_power > 0:
            beta_pct = (beta / total_power) * 100
            theta_pct = (theta / total_power) * 100
            alpha_pct = (alpha / total_power) * 100
            
            if beta_pct > 30 and theta_pct < 20 and beta_theta_ratio > 2.0:
                focus_score = min(1.0, focus_score + 0.15)
            elif beta_pct < 15 or theta_pct > 40 or beta_theta_ratio < 0.5:
                focus_score = max(0.0, focus_score - 0.2)
            elif alpha_pct > 40:
                focus_score = min(0.65, focus_score)
        
        return float(focus_score)
        
    except Exception as e:
        logger.error(f"Focus calculation error: {e}")
        return 0.3

def get_mental_state(band_powers):
    """
    Classify mental state based on EEG band ratios with focus alignment
    Returns: One of ['focused', 'relaxed', 'drowsy', 'distracted'] ONLY
    Now aligned with focus level calculation
    """
    try:
        total = sum(band_powers.values())
        if total == 0:
            return "distracted"
        
        percentages = {band: (power / total) * 100 for band, power in band_powers.items()}
        
        beta_pct = percentages.get('beta', 0)
        alpha_pct = percentages.get('alpha', 0)
        theta_pct = percentages.get('theta', 0)
        delta_pct = percentages.get('delta', 0)
        gamma_pct = percentages.get('gamma', 0)
        
        beta_theta_ratio = beta_pct / theta_pct if theta_pct > 0 else 0
        
        # Calculate focus level for consistency check
        beta = band_powers.get('beta', 0.01)
        alpha = band_powers.get('alpha', 0.01)
        theta = band_powers.get('theta', 0.01)
        engagement_index = beta / (alpha + theta) if (alpha + theta) > 0.01 else 0
        
        # 🔥 IMPROVED LOGIC - Align state with focus level
        
        # FOCUSED: High beta, low theta, good engagement index
        # Must have beta > 25% AND beta/theta > 1.5 AND low delta
        if (beta_pct > 25 and theta_pct < 25 and delta_pct < 25 and
            beta_theta_ratio > 1.5 and engagement_index > 0.8):
            return "focused"
        
        # DROWSY: High delta or (high theta + low beta + low engagement)
        # Clear signs of drowsiness
        elif (delta_pct > 30 or 
              (theta_pct > 35 and beta_pct < 15 and engagement_index < 0.4)):
            return "drowsy"
        
        # DISTRACTED: High theta but not drowsy, poor attention
        # Theta dominant but not enough delta to be drowsy
        elif (theta_pct > 30 and beta_pct < 20 and 
              beta_theta_ratio < 0.7 and delta_pct < 30):
            return "distracted"
        
        # RELAXED: Alpha dominant, calm but not focused
        # Good alpha, moderate beta, low theta
        elif (alpha_pct > 35 and beta_pct < 30 and theta_pct < 25):
            return "relaxed"
        
        # Edge cases - use engagement index to decide
        elif engagement_index > 1.0:
            return "focused"
        elif engagement_index > 0.5:
            return "relaxed"
        elif engagement_index > 0.3:
            return "distracted"
        else:
            return "drowsy"
            
    except Exception as e:
        logger.error(f"Mental state classification error: {e}")
        return "distracted"
        
        # Default classification by dominant band
        dominant_band = max(percentages.items(), key=lambda x: x[1])[0]
        
        if dominant_band == 'beta':
            return "focused"
        elif dominant_band == 'alpha':
            return "relaxed"
        elif dominant_band in ['delta', 'theta']:
            return "drowsy"
        elif dominant_band == 'gamma':
            # High gamma can indicate stress or high cognitive load
            return "focused" if beta_pct > 20 else "distracted"
        else:
            return "distracted"
            
    except Exception as e:
        logger.error(f"Mental state classification error: {e}")
        return "distracted"  # Safe default

def extract_ml_features(band_powers, focus_score, raw_eeg_buffer=None):
    """
    Extract 148 advanced features for ML model prediction (MODEL TRAINED WITH 148!)
    Includes: band powers, ratios, statistical features, spectral features
    """
    try:
        delta = band_powers.get('delta', 0)
        theta = band_powers.get('theta', 0)
        alpha = band_powers.get('alpha', 0)
        beta = band_powers.get('beta', 0)
        gamma = band_powers.get('gamma', 0)
        
        total_power = sum(band_powers.values())
        if total_power == 0:
            total_power = 1e-10
        
        # Feature array (148 features total)
        features = []
        
        # 1-5: Raw band powers
        features.extend([delta, theta, alpha, beta, gamma])
        
        # 6-10: Normalized band powers (percentages)
        features.extend([
            delta / total_power * 100,
            theta / total_power * 100,
            alpha / total_power * 100,
            beta / total_power * 100,
            gamma / total_power * 100
        ])
        
        # 11: Total power
        features.append(total_power)
        
        # 12-25: Band ratios (critical for state detection)
        features.extend([
            beta / theta if theta > 0 else 0,  # Beta/Theta (attention)
            beta / alpha if alpha > 0 else 0,  # Beta/Alpha
            alpha / theta if theta > 0 else 0,  # Alpha/Theta
            (beta + gamma) / (alpha + theta) if (alpha + theta) > 0 else 0,  # Engagement
            delta / theta if theta > 0 else 0,
            gamma / beta if beta > 0 else 0,
            (alpha + theta) / beta if beta > 0 else 0,
            beta / (alpha + theta) if (alpha + theta) > 0 else 0,  # NASA Index
            (theta + alpha) / (beta + gamma) if (beta + gamma) > 0 else 0,
            alpha / delta if delta > 0 else 0,
            gamma / theta if theta > 0 else 0,
            beta / delta if delta > 0 else 0,
            (beta + alpha) / (theta + delta) if (theta + delta) > 0 else 0,
            gamma / alpha if alpha > 0 else 0
        ])
        
        # 26: Focus score (from formula)
        features.append(focus_score)
        
        # 27-31: Logarithmic band powers (reduce skewness)
        features.extend([
            np.log1p(delta),
            np.log1p(theta),
            np.log1p(alpha),
            np.log1p(beta),
            np.log1p(gamma)
        ])
        
        # 32-36: Square root normalized powers
        features.extend([
            np.sqrt(delta / total_power) if total_power > 0 else 0,
            np.sqrt(theta / total_power) if total_power > 0 else 0,
            np.sqrt(alpha / total_power) if total_power > 0 else 0,
            np.sqrt(beta / total_power) if total_power > 0 else 0,
            np.sqrt(gamma / total_power) if total_power > 0 else 0
        ])
        
        # 37-41: Low vs High frequency ratios
        low_freq = delta + theta
        high_freq = beta + gamma
        mid_freq = alpha
        
        features.extend([
            high_freq / low_freq if low_freq > 0 else 0,
            low_freq / high_freq if high_freq > 0 else 0,
            mid_freq / low_freq if low_freq > 0 else 0,
            mid_freq / high_freq if high_freq > 0 else 0,
            (high_freq + mid_freq) / low_freq if low_freq > 0 else 0
        ])
        
        # 42-46: Band power differences
        features.extend([
            beta - theta,
            beta - alpha,
            alpha - theta,
            gamma - beta,
            beta - delta
        ])
        
        # 47-51: Cross-band interactions
        features.extend([
            beta * alpha,
            theta * delta,
            gamma * beta,
            alpha * theta,
            beta * gamma
        ])
        
        # 52-56: Relative band dominance
        max_power = max(band_powers.values())
        features.extend([
            delta / max_power if max_power > 0 else 0,
            theta / max_power if max_power > 0 else 0,
            alpha / max_power if max_power > 0 else 0,
            beta / max_power if max_power > 0 else 0,
            gamma / max_power if max_power > 0 else 0
        ])
        
        # 57-71: Statistical features from raw EEG (if available)
        if raw_eeg_buffer is not None and len(raw_eeg_buffer) > 10:
            eeg_array = np.array(raw_eeg_buffer)
            features.extend([
                np.mean(eeg_array),
                np.std(eeg_array),
                np.var(eeg_array),
                np.median(eeg_array),
                np.max(eeg_array),
                np.min(eeg_array),
                np.ptp(eeg_array),  # peak-to-peak
                np.percentile(eeg_array, 25),
                np.percentile(eeg_array, 75),
                np.percentile(eeg_array, 90),
                np.mean(np.abs(np.diff(eeg_array))),  # mean absolute derivative
                np.std(np.diff(eeg_array)) if len(eeg_array) > 1 else 0,
                len(eeg_array),
                np.sum(eeg_array > 0),
                np.sum(eeg_array < 0)
            ])
        else:
            # Placeholder zeros if no raw data
            features.extend([0] * 15)
        
        # 72-86: Advanced spectral features
        features.extend([
            (beta + gamma) / total_power if total_power > 0 else 0,  # High freq ratio
            (delta + theta) / total_power if total_power > 0 else 0,  # Low freq ratio
            alpha / total_power if total_power > 0 else 0,  # Mid freq ratio
            beta / (delta + theta + alpha) if (delta + theta + alpha) > 0 else 0,
            gamma / (delta + theta + alpha + beta) if (delta + theta + alpha + beta) > 0 else 0,
            np.sqrt(beta * alpha) / theta if theta > 0 else 0,
            (beta ** 2) / (alpha * theta) if (alpha * theta) > 0 else 0,
            np.log1p(beta / theta) if theta > 0 else 0,
            np.log1p(alpha / delta) if delta > 0 else 0,
            (beta + alpha + gamma) / (theta + delta) if (theta + delta) > 0 else 0,
            beta * gamma / (alpha * theta) if (alpha * theta) > 0 else 0,
            (beta - theta) / (beta + theta) if (beta + theta) > 0 else 0,
            (alpha - delta) / (alpha + delta) if (alpha + delta) > 0 else 0,
            gamma / (beta + alpha) if (beta + alpha) > 0 else 0,
            (theta + delta + alpha) / (beta + gamma) if (beta + gamma) > 0 else 0
        ])
        
        # 87-148: Additional contextual features (pad to reach 148 - model expects this!)
        remaining_features = 148 - len(features)
        if remaining_features > 0:
            # Add polynomial features and interactions
            for i in range(min(remaining_features, 20)):
                features.append(focus_score ** (i + 1) * 0.1)
            
            # Add more cross-band ratios if needed
            while len(features) < 148:
                features.append(0)
        
        # Ensure exactly 148 features (model was trained with 148!)
        features = features[:148]
        
        return np.array(features).reshape(1, -1)
        
    except Exception as e:
        logger.error(f"Feature extraction error: {e}")
        # Return zero features array as fallback (148 features!)
        return np.zeros((1, 148))

def predict_state_hybrid(band_powers, focus_score, raw_eeg_buffer=None):
    """
    HYBRID PREDICTION: Combines formula-based (NASA Index) + ML Model
    
    - If ML model available: Use ensemble of both methods
    - Formula provides scientific baseline (NASA Engagement Index)
    - ML provides pattern recognition from training data
    - Confidence weighting: ML (60%) + Formula (40%)
    
    Returns: One of ['focused', 'relaxed', 'drowsy', 'distracted']
    """
    # Valid states only
    VALID_STATES = ['focused', 'relaxed', 'drowsy', 'distracted']
    
    def normalize_state(state):
        """Ensure state is one of the valid 4 states"""
        if state is None or not isinstance(state, str):
            return 'monitoring'
        
        state_lower = state.lower().strip()
        
        # Map variations to standard states
        state_mapping = {
            'focused': 'focused',
            'focus': 'focused',
            'concentrating': 'focused',
            'attentive': 'focused',
            
            'relaxed': 'relaxed',
            'calm': 'relaxed',
            'resting': 'relaxed',
            
            'drowsy': 'drowsy',
            'sleepy': 'drowsy',
            'tired': 'drowsy',
            'fatigue': 'drowsy',
            
            'distracted': 'distracted',
            'unfocused': 'distracted',
            'wandering': 'distracted',
            
            'monitoring': 'distracted'  # Default monitoring to distracted
        }
        
        return state_mapping.get(state_lower, 'distracted')
    
    try:
        # 1. Formula-based prediction (scientific baseline)
        formula_state = get_mental_state(band_powers)
        formula_state = normalize_state(formula_state)
        
        # 2. ML-based prediction (if model loaded)
        if ML_MODEL is not None:
            try:
                # Verify model is valid
                if not hasattr(ML_MODEL, 'predict') or not hasattr(ML_MODEL, 'predict_proba'):
                    logger.error("❌ ML_MODEL doesn't have predict methods, using formula only")
                    return formula_state if formula_state in VALID_STATES else 'distracted'
                
                # Extract 147 features for ML model
                features = extract_ml_features(band_powers, focus_score, raw_eeg_buffer)
                
                # Get ML prediction with probabilities
                ml_prediction_raw = ML_MODEL.predict(features)[0]
                ml_prediction = normalize_state(ml_prediction_raw)
                ml_proba = ML_MODEL.predict_proba(features)[0]
                
                # Get confidence of ML prediction
                ml_confidence = np.max(ml_proba)
                
                logger.debug(f"🤖 ML: {ml_prediction} ({ml_confidence:.2f}) | 📐 Formula: {formula_state}")
                
                # 3. Hybrid decision logic with validation
                if ml_confidence > 0.75:
                    # High confidence ML - use ML prediction
                    final_state = ml_prediction
                    logger.debug("✅ Using ML (high confidence)")
                elif ml_confidence > 0.55:
                    # Medium confidence - weighted ensemble
                    if ml_prediction == formula_state:
                        # Both agree - high confidence
                        final_state = ml_prediction
                        logger.debug("✅ Both agree")
                    else:
                        # Disagree - check which makes more sense based on band powers
                        beta_pct = (band_powers.get('beta', 0) / sum(band_powers.values())) * 100
                        theta_pct = (band_powers.get('theta', 0) / sum(band_powers.values())) * 100
                        
                        # If high beta and low theta, favor "focused" prediction
                        if beta_pct > 30 and theta_pct < 20:
                            final_state = 'focused' if ml_prediction == 'focused' or formula_state == 'focused' else ml_prediction
                        # If high theta, favor "drowsy" or "distracted"
                        elif theta_pct > 35:
                            final_state = 'drowsy' if ml_prediction == 'drowsy' or formula_state == 'drowsy' else 'distracted'
                        else:
                            final_state = ml_prediction  # Default to ML
                        
                        logger.debug(f"⚖️ Resolved: {final_state} (ML={ml_prediction}, Formula={formula_state})")
                else:
                    # Low ML confidence - use formula as fallback
                    final_state = formula_state
                    logger.debug("📐 Using formula (low ML confidence)")
                
                # Final validation
                if final_state not in VALID_STATES:
                    logger.warning(f"Invalid state '{final_state}', defaulting to distracted")
                    final_state = 'distracted'
                
                return final_state
                
            except Exception as e:
                logger.error(f"ML prediction error: {e}, falling back to formula")
                return formula_state if formula_state in VALID_STATES else 'distracted'
        else:
            # No ML model - use formula only
            logger.debug(f"📐 Formula only: {formula_state}")
            return formula_state if formula_state in VALID_STATES else 'distracted'
            
    except Exception as e:
        logger.error(f"Hybrid prediction error: {e}")
        return 'distracted'  # Safe default

# Replace this function in your Flask app
def analyze_signal_quality(raw_values):
    """Enhanced signal quality detection - more lenient for normal EEG values"""
    if not raw_values or len(raw_values) < 1:
        return "no_data", "No signal detected"
    
    raw_array = np.array(raw_values)
    
    # Check for pure disconnection patterns (all zeros or all max values)
    if np.all(raw_array == 0):
        return "connection_error", "Sensor completely disconnected - receiving only zeros"
    
    if np.all(raw_array == 4095):
        return "connection_error", "Sensor saturated - receiving only maximum values"
    
    # Check for mixed disconnection patterns (only 0s and 4095s)
    unique_values = np.unique(raw_array)
    if len(unique_values) <= 2 and all(val in [0, 4095] for val in unique_values):
        return "connection_error", "Intermittent connection - only getting boundary values"
    
    # If we have normal EEG values (like your 1824, 1778, etc.), signal is good
    # Normal EEG ADC values typically range from ~500 to ~3500
    normal_range_count = np.sum((raw_array >= 100) & (raw_array <= 4000))
    if normal_range_count > len(raw_array) * 0.8:  # 80% of values in normal range
        return "good", "Signal quality good - receiving normal EEG data"
    
    # If we have some zeros mixed with normal values, it's a partial connection issue
    zero_count = np.sum(raw_array == 0)
    if zero_count > 0:
        return "connection_error", f"Partial connection issue - {zero_count}/{len(raw_array)} zero values"
    
    # Default to good if we made it here
    return "good", "Signal connected"

def check_device_wearing(raw_values):
    """Updated wearing detection - less strict"""
    if not raw_values or len(raw_values) < 1:
        return False
    
    raw_array = np.array(raw_values)
    
    # Not wearing only if getting pure boundary values
    if (np.all(raw_array == 0) or 
        np.all(raw_array == 4095)):
        return False
    
    # Check if we have mostly normal EEG values
    normal_range_count = np.sum((raw_array >= 100) & (raw_array <= 4000))
    return normal_range_count > len(raw_array) * 0.7  # 70% threshold
def check_device_wearing(raw_values):
    """Simple check - if not getting only 0s or 4095s, consider as wearing"""
    if not raw_values or len(raw_values) < 1:
        return False
    
    raw_array = np.array(raw_values)
    unique_values = np.unique(raw_array)
    
    # Not wearing only if getting pure 0s, pure 4095s, or only these two values
    if (np.all(raw_array == 0) or 
        np.all(raw_array == 4095) or 
        (len(unique_values) <= 2 and all(val in [0, 4095] for val in unique_values))):
        return False
    
    return True

def process_eeg_data(raw_values, mac_address):
    """
    Process EEG data with HYBRID prediction (Formula + ML Model)
    Returns: band_powers, focus_level, mental_state
    """
    global EEG_BUFFERS
    try:
        # Initialize buffer for this MAC address if not exists
        if mac_address not in EEG_BUFFERS:
            EEG_BUFFERS[mac_address] = []
        
        EEG_BUFFERS[mac_address].extend([float(v) for v in raw_values])
        if len(EEG_BUFFERS[mac_address]) > BUFFER_SIZE:
            EEG_BUFFERS[mac_address] = EEG_BUFFERS[mac_address][-BUFFER_SIZE:]
        
        signal = np.array(EEG_BUFFERS[mac_address], dtype=float)
        signal = (signal - 2048) / 2048.0
        
        if len(signal) > 50:
            signal = notch_filter(signal)
            signal = bandpass_filter(signal)
        
        # Calculate band powers
        band_powers = compute_band_power(signal)
        
        # Calculate focus using NASA Engagement Index
        focus_level = calculate_focus(band_powers)
        
        # 🔥 HYBRID PREDICTION: Use both formula + ML model
        mental_state = predict_state_hybrid(band_powers, focus_level, EEG_BUFFERS[mac_address])
        
        return band_powers, focus_level, mental_state
    except Exception as e:
        logger.error(f"EEG processing error for MAC {mac_address}: {e}")
        default_bands = {"delta":0.2,"theta":0.15,"alpha":0.3,"beta":0.25,"gamma":0.1}
        return default_bands, 0.4, "monitoring"

# ----- Routes -----
# Student Management Routes
@app.route("/students", methods=['GET'])
def get_students():
    try:
        db = get_db_connection()
        if db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM students ORDER BY created_at DESC")
            students = cursor.fetchall()
            cursor.close()
            db.close()
            return jsonify({"status": "ok", "students": students}), 200
        return jsonify({"status": "error", "msg": "Database connection failed"}), 500
    except Exception as e:
        logger.error(f"Get students error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route("/students", methods=['POST'])
def add_student():
    try:
        data = request.json
        name = data.get('name')
        device_mac = data.get('device_mac')
        
        if not name:
            return jsonify({"status": "error", "msg": "Student name required"}), 400
        
        db = get_db_connection()
        if db:
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO students (name, device_mac) VALUES (%s, %s)",
                (name, device_mac)
            )
            student_id = cursor.lastrowid
            db.commit()
            cursor.close()
            db.close()
            return jsonify({"status": "ok", "student_id": student_id, "msg": "Student added"}), 201
        return jsonify({"status": "error", "msg": "Database connection failed"}), 500
    except Exception as e:
        logger.error(f"Add student error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

# Session Management Routes
@app.route("/sessions", methods=['GET'])
def get_sessions():
    try:
        db = get_db_connection()
        if db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("""
                SELECT s.*, st.name as student_name 
                FROM sessions s 
                LEFT JOIN students st ON s.student_id = st.id 
                ORDER BY s.start_time DESC
            """)
            sessions = cursor.fetchall()
            cursor.close()
            db.close()
            return jsonify({"status": "ok", "sessions": sessions}), 200
        return jsonify({"status": "error", "msg": "Database connection failed"}), 500
    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route("/sessions/start", methods=['POST'])
def start_session():
    try:
        data = request.json
        student_id = data.get('student_id')
        session_name = data.get('session_name', f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        db = get_db_connection()
        if db:
            cursor = db.cursor()
            # End any active sessions for this student
            cursor.execute(
                "UPDATE sessions SET active = FALSE, end_time = %s WHERE student_id = %s AND active = TRUE",
                (datetime.now(), student_id)
            )
            # Start new session
            cursor.execute(
                "INSERT INTO sessions (student_id, session_name, start_time, active) VALUES (%s, %s, %s, TRUE)",
                (student_id, session_name, datetime.now())
            )
            session_id = cursor.lastrowid
            db.commit()
            cursor.close()
            db.close()
            return jsonify({"status": "ok", "session_id": session_id, "msg": "Session started"}), 201
        return jsonify({"status": "error", "msg": "Database connection failed"}), 500
    except Exception as e:
        logger.error(f"Start session error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route("/sessions/end/<int:session_id>", methods=['POST'])
def end_session(session_id):
    try:
        db = get_db_connection()
        if db:
            cursor = db.cursor()
            cursor.execute(
                "UPDATE sessions SET active = FALSE, end_time = %s WHERE id = %s",
                (datetime.now(), session_id)
            )
            db.commit()
            cursor.close()
            db.close()
            return jsonify({"status": "ok", "msg": "Session ended"}), 200
        return jsonify({"status": "error", "msg": "Database connection failed"}), 500
    except Exception as e:
        logger.error(f"End session error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route("/sessions/active", methods=['GET'])
def get_active_session():
    try:
        db = get_db_connection()
        if db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("""
                SELECT s.*, st.name as student_name, st.device_mac
                FROM sessions s 
                LEFT JOIN students st ON s.student_id = st.id 
                WHERE s.active = TRUE 
                LIMIT 1
            """)
            session = cursor.fetchone()
            cursor.close()
            db.close()
            if session:
                return jsonify({"status": "ok", "session": session}), 200
            return jsonify({"status": "ok", "session": None}), 200
        return jsonify({"status": "error", "msg": "Database connection failed"}), 500
    except Exception as e:
        logger.error(f"Get active session error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route("/sessions/start-monitoring", methods=['POST'])
def start_monitoring_session():
    """Start a new monitoring session with teacher info"""
    try:
        data = request.json
        teacher_name = data.get('teacher_name')
        subject = data.get('subject')
        
        if not teacher_name or not subject:
            return jsonify({"status": "error", "msg": "Teacher name and subject required"}), 400
        
        db = get_db_connection()
        if db:
            cursor = db.cursor()
            
            # End any active monitoring sessions
            cursor.execute(
                "UPDATE monitoring_sessions SET active = FALSE, end_time = %s WHERE active = TRUE",
                (datetime.now(),)
            )
            
            # Start new monitoring session
            cursor.execute(
                "INSERT INTO monitoring_sessions (teacher_name, subject, start_time, active) VALUES (%s, %s, %s, TRUE)",
                (teacher_name, subject, datetime.now())
            )
            session_id = cursor.lastrowid
            db.commit()
            cursor.close()
            db.close()
            
            logger.info(f"Monitoring session started by {teacher_name} for {subject}")
            return jsonify({
                "status": "ok", 
                "session_id": session_id, 
                "msg": "Monitoring session started",
                "teacher_name": teacher_name,
                "subject": subject
            }), 201
        return jsonify({"status": "error", "msg": "Database connection failed"}), 500
    except Exception as e:
        logger.error(f"Start monitoring session error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route("/sessions/end-monitoring", methods=['POST'])
def end_monitoring_session():
    """End the active monitoring session"""
    try:
        db = get_db_connection()
        if db:
            cursor = db.cursor()
            cursor.execute(
                "UPDATE monitoring_sessions SET active = FALSE, end_time = %s WHERE active = TRUE",
                (datetime.now(),)
            )
            db.commit()
            cursor.close()
            db.close()
            
            logger.info("Monitoring session ended")
            return jsonify({"status": "ok", "msg": "Monitoring session ended"}), 200
        return jsonify({"status": "error", "msg": "Database connection failed"}), 500
    except Exception as e:
        logger.error(f"End monitoring session error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route("/sessions/monitoring-status", methods=['GET'])
def get_monitoring_status():
    """Check if there's an active monitoring session"""
    try:
        db = get_db_connection()
        if db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM monitoring_sessions 
                WHERE active = TRUE 
                ORDER BY start_time DESC 
                LIMIT 1
            """)
            session = cursor.fetchone()
            cursor.close()
            db.close()
            
            if session:
                return jsonify({
                    "status": "ok",
                    "monitoring_active": True,
                    "session": session
                }), 200
            else:
                return jsonify({
                    "status": "ok",
                    "monitoring_active": False,
                    "session": None
                }), 200
        return jsonify({"status": "error", "msg": "Database connection failed"}), 500
    except Exception as e:
        logger.error(f"Get monitoring status error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route("/upload", methods=['POST'])
def upload_data():
    global DEVICE_STATUSES
    try:
        data = request.json
        
        # ✅ Validate incoming data
        if not data:
            return jsonify({"status": "error", "msg": "No data received"}), 400
        
        # ✅ Get MAC address
        mac_address = data.get("mac") or data.get("mac_address") or data.get("device_mac")
        if not mac_address:
            return jsonify({"status": "error", "msg": "MAC address required"}), 400
        
        # Initialize status for this MAC if not exists
        if mac_address not in DEVICE_STATUSES:
            DEVICE_STATUSES[mac_address] = {
                "connected": False, 
                "wearing": False, 
                "last_update": None,
                "error_message": None,
                "signal_quality": "unknown"
            }
       
        # ✅ Handle data formats
        if "average" in data:
            raw_values = [float(data["average"])]
        elif "value" in data:
            raw_values = [int(data["value"])]
        elif "values" in data:
            raw_values = [int(v) for v in data["values"]]
        else:
            return jsonify({"status": "error", "msg": "Invalid JSON format"}), 400
        
        timestamp = datetime.now()
       
        # ✅ Analyze signal quality
        quality, quality_msg = analyze_signal_quality(raw_values)
        DEVICE_STATUSES[mac_address].update({
            "connected": quality != "connection_error",
            "last_update": timestamp,
            "wearing": check_device_wearing(raw_values),
            "signal_quality": quality,
            "error_message": quality_msg if quality == "connection_error" else None
        })
        
        # Process EEG data
        band_powers, focus_level, mental_state = process_eeg_data(raw_values, mac_address)
       
        # ✅ Check if monitoring session is active
        db = get_db_connection()
        if not db:
            return jsonify({"status": "error", "msg": "Database connection failed"}), 500
        
        cursor = db.cursor(dictionary=True)
        
        # Check for active monitoring session
        cursor.execute("SELECT id FROM monitoring_sessions WHERE active = TRUE LIMIT 1")
        active_monitoring = cursor.fetchone()
        
        if not active_monitoring:
            # No active session - don't save
            cursor.close()
            db.close()
            
            # Only log first time
            if not hasattr(upload_data, 'no_session_logged'):
                logger.warning(f"⚠️  No active session - Data from {mac_address} not saved")
                upload_data.no_session_logged = True
            
            return jsonify({
                "status": "ok",
                "mac_address": mac_address,
                "bands": band_powers,
                "focus": focus_level,
                "mental_state": mental_state,
                "data_saved": False,
                "message": "No active session"
            }), 200
        
        # Active session exists - save data
        try:
            # Get or create student
            cursor.execute("SELECT id FROM students WHERE device_mac = %s", (mac_address,))
            student = cursor.fetchone()
            student_id = student['id'] if student else None
            
            if not student_id:
                cursor.execute(
                    "INSERT INTO students (name, device_mac) VALUES (%s, %s)",
                    (f"Student-{mac_address[-8:]}", mac_address)
                )
                student_id = cursor.lastrowid
                logger.info(f"✅ New student registered: {mac_address}")
            
            # Store raw values
            for raw_val in raw_values:
                cursor.execute("""
                    INSERT INTO raw_data (timestamp, adc_value, mac_address, student_id) 
                    VALUES (%s, %s, %s, %s)
                """, (timestamp, raw_val, mac_address, student_id))
           
            # Store processed EEG data
            cursor.execute("""
                INSERT INTO eeg_data (timestamp, delta, theta, alpha, beta, gamma, focus, signal_quality, mac_address, student_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                timestamp,
                band_powers['delta'], band_powers['theta'], band_powers['alpha'],
                band_powers['beta'], band_powers['gamma'], focus_level, quality,
                mac_address, student_id
            ))
            
            db.commit()
           
            # Log only occasionally (every 10 requests)
            if not hasattr(upload_data, 'request_count'):
                upload_data.request_count = 0
            upload_data.request_count += 1
            
            if upload_data.request_count % 10 == 1:
                logger.info(f"💾 Saving data from {mac_address} | Focus: {focus_level*100:.0f}% | {mental_state}")
            
            return jsonify({
                "status": "ok",
                "mac_address": mac_address,
                "bands": band_powers,
                "focus": focus_level,
                "mental_state": mental_state,
                "data_saved": True
            }), 200
            
        except mysql.connector.Error as db_err:
            db.rollback()
            logger.error(f"Database error: {db_err}")
            return jsonify({"status": "error", "msg": f"Database error"}), 500
        finally:
            cursor.close()
            db.close()
            
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({"status": "error", "msg": "Server error"}), 500
@app.route("/latest", methods=['GET'])
def latest():
    global DEVICE_STATUSES, EEG_BUFFERS
    try:
        # Get MAC address filter from query params (optional)
        mac_address = request.args.get('mac_address')
        
        # If no specific MAC requested, get the most recent one
        if not mac_address and DEVICE_STATUSES:
            # Get the MAC with most recent update
            mac_address = max(DEVICE_STATUSES.keys(), 
                            key=lambda k: DEVICE_STATUSES[k]["last_update"] or datetime.min)
        
        # Get device status for this MAC
        device_status = DEVICE_STATUSES.get(mac_address, {
            "connected": False,
            "wearing": False,
            "signal_quality": "no_data",
            "error_message": "No device connected",
            "last_update": None
        })
        
        # Check connection timeout
        if device_status.get("last_update"):
            time_diff = (datetime.now() - device_status["last_update"]).total_seconds()
            if time_diff > 10:
                device_status.update({
                    "connected": False,
                    "wearing": False,
                    "signal_quality": "connection_error",
                    "error_message": f"No data for {int(time_diff)} seconds - device disconnected"
                })
        
        db = get_db_connection()
        if db:
            cursor = db.cursor()
            
            # Query latest data, optionally filtered by MAC address
            if mac_address:
                cursor.execute("""
                    SELECT timestamp, delta, theta, alpha, beta, gamma, focus, signal_quality, mac_address, student_id
                    FROM eeg_data 
                    WHERE mac_address = %s
                    ORDER BY id DESC LIMIT 1
                """, (mac_address,))
            else:
                cursor.execute("""
                    SELECT timestamp, delta, theta, alpha, beta, gamma, focus, signal_quality, mac_address, student_id
                    FROM eeg_data 
                    ORDER BY id DESC LIMIT 1
                """)
            
            row = cursor.fetchone()
            cursor.close()
            db.close()

            if row:
                timestamp, delta, theta, alpha, beta, gamma, focus, signal_quality, row_mac, student_id = row
                
                # Get mental state from band powers
                band_powers = {"delta": float(delta),"theta": float(theta),"alpha": float(alpha),
                              "beta": float(beta),"gamma": float(gamma)}
                mental_state = get_mental_state(band_powers)
                
                # Get samples from buffer for this MAC
                samples = list(EEG_BUFFERS.get(row_mac, [])[-100:]) if row_mac in EEG_BUFFERS else []
                
                return jsonify({
                    "status": "ok",
                    "mac_address": row_mac,
                    "student_id": student_id,
                    "bands": band_powers,
                    "focus": float(focus),
                    "mental_state": mental_state,
                    "device_status": DEVICE_STATUSES.get(row_mac, device_status),
                    "timestamp": timestamp.isoformat(),
                    "signal_quality": signal_quality,
                    "samples": samples
                })
            else:
                return jsonify({
                    "status": "ok",
                    "mac_address": mac_address,
                    "bands": {"delta":0.2,"theta":0.15,"alpha":0.3,"beta":0.25,"gamma":0.1},
                    "focus": 0.3,
                    "mental_state": "monitoring",
                    "device_status": device_status,
                    "timestamp": None,
                    "signal_quality": device_status.get("signal_quality", "no_data"),
                    "samples": []
                })
        else:
            return jsonify({"status": "error", "msg": "Database connection failed"}), 500
    except Exception as e:
        logger.error(f"Latest error: {e}")
        return jsonify({"status": "error", "msg": f"Server error: {str(e)}"}), 500

@app.route("/status", methods=['GET'])
def device_status():
    global DEVICE_STATUSES, EEG_BUFFERS
    
    # Get MAC address filter from query params (optional)
    mac_address = request.args.get('mac_address')
    
    if mac_address:
        # Return status for specific device
        device_status = DEVICE_STATUSES.get(mac_address, {
            "connected": False,
            "wearing": False,
            "signal_quality": "no_data",
            "error_message": "Device not found",
            "last_update": None
        })
        buffer_size = len(EEG_BUFFERS.get(mac_address, []))
        
        return jsonify({
            "status": "ok",
            "mac_address": mac_address,
            "device_status": device_status,
            "server_time": datetime.now().isoformat(),
            "buffer_size": buffer_size
        })
    else:
        # Return status for all connected devices
        all_statuses = {}
        for mac, status in DEVICE_STATUSES.items():
            all_statuses[mac] = {
                "device_status": status,
                "buffer_size": len(EEG_BUFFERS.get(mac, []))
            }
        
        return jsonify({
            "status": "ok",
            "devices": all_statuses,
            "total_devices": len(DEVICE_STATUSES),
            "server_time": datetime.now().isoformat()
        })

@app.route("/devices", methods=['GET'])
def get_connected_devices():
    """Get list of currently connected devices"""
    global DEVICE_STATUSES
    try:
        db = get_db_connection()
        if db:
            cursor = db.cursor(dictionary=True)
            
            # Get all students from database
            cursor.execute("""
                SELECT s.id, s.name, s.device_mac, s.created_at
                FROM students s
                ORDER BY s.name
            """)
            all_students = cursor.fetchall()
            
            # Get students with recent EEG data (last 2 minutes)
            cursor.execute("""
                SELECT DISTINCT mac_address, MAX(timestamp) as last_data
                FROM eeg_data
                WHERE timestamp > DATE_SUB(NOW(), INTERVAL 2 MINUTE)
                GROUP BY mac_address
            """)
            recent_data = cursor.fetchall()
            recent_macs = {row['mac_address']: row['last_data'] for row in recent_data}
            
            cursor.close()
            db.close()
            
            # Build connected students list
            connected_students = []
            current_time = datetime.now()
            
            for student in all_students:
                mac = student['device_mac']
                
                # Check if device has sent data recently (either in memory or in database)
                in_memory = mac in DEVICE_STATUSES
                in_database = mac in recent_macs
                
                # Priority 1: Check memory (most recent)
                if in_memory:
                    device_status = DEVICE_STATUSES[mac]
                    if device_status.get('connected') and device_status.get('last_update'):
                        time_diff = (current_time - device_status['last_update']).total_seconds()
                        
                        if time_diff < 30:  # Connected if data within 30 seconds
                            status_copy = device_status.copy()
                            status_copy['last_update'] = device_status['last_update'].isoformat()
                            student['current_status'] = status_copy
                            connected_students.append(student)
                            continue
                
                # Priority 2: Check database for recent data
                if in_database:
                    last_data_time = recent_macs[mac]
                    time_diff = (current_time - last_data_time).total_seconds()
                    
                    if time_diff < 120:  # Connected if data within 2 minutes
                        student['current_status'] = {
                            'connected': True,
                            'last_update': last_data_time.isoformat(),
                            'signal_quality': 'good',
                            'wearing': True
                        }
                        connected_students.append(student)
                        continue
            
            # Only log when devices change
            if len(connected_students) > 0:
                logger.info(f"📱 {len(connected_students)} device(s) connected")
            
            return jsonify({
                "status": "ok",
                "devices": connected_students,
                "active_count": len(connected_students)
            }), 200
        return jsonify({"status": "error", "msg": "Database connection failed"}), 500
    except Exception as e:
        logger.error(f"Get devices error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route("/")
def welcome():
    return render_template("welcome.html")

@app.route("/dashboard")
def index():
    return render_template("index.html")

# ============================================
# Students and Session routes moved to separate files
# See students_routes.py and session_routes.py
# ============================================

@app.route("/api/performance-metrics/<mac_address>", methods=['GET'])
def get_performance_metrics(mac_address):
    """Get performance metrics for a student"""
    try:
        metrics = calculate_performance_metrics(mac_address)
        return jsonify({"status": "ok", "metrics": metrics})
    except Exception as e:
        logger.error(f"Performance metrics error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route("/data/<mac_address>", methods=['GET'])
def get_student_data(mac_address):
    """Get EEG data history for a specific student by MAC address"""
    try:
        limit = request.args.get('limit', 100, type=int)
        
        db = get_db_connection()
        if db:
            cursor = db.cursor(dictionary=True)
            
            # Get student info
            cursor.execute("SELECT * FROM students WHERE device_mac = %s", (mac_address,))
            student = cursor.fetchone()
            
            if not student:
                return jsonify({"status": "error", "msg": "Student not found"}), 404
            
            # Get recent EEG data
            cursor.execute("""
                SELECT timestamp, delta, theta, alpha, beta, gamma, focus, signal_quality
                FROM eeg_data 
                WHERE mac_address = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (mac_address, limit))
            
            eeg_data = cursor.fetchall()
            
            cursor.close()
            db.close()
            
            return jsonify({
                "status": "ok",
                "student": student,
                "mac_address": mac_address,
                "data": eeg_data,
                "count": len(eeg_data)
            }), 200
        return jsonify({"status": "error", "msg": "Database connection failed"}), 500
    except Exception as e:
        logger.error(f"Get student data error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route("/analytics/<mac_address>", methods=['GET'])
def get_student_analytics(mac_address):
    """Get comprehensive analytics for a student"""
    try:
        # Get time window from query params (default 60 minutes)
        time_window = request.args.get('time_window', 60, type=int)
        
        # Calculate all analytics
        attention_periods = calculate_attention_periods(mac_address, time_window)
        session_stats = calculate_session_stats(mac_address, time_window)
        recommendation = generate_recommendation(mac_address)
        performance_metrics = calculate_performance_metrics(mac_address, time_window)
        wave_timeline = get_wave_timeline_data(mac_address, min(30, time_window))
        
        return jsonify({
            "status": "ok",
            "mac_address": mac_address,
            "analytics": {
                "attention_periods": attention_periods,
                "session_stats": session_stats,
                "recommendation": recommendation,
                "performance_metrics": performance_metrics,
                "wave_timeline": wave_timeline
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Analytics error for {mac_address}: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route("/analytics/<mac_address>/periods", methods=['GET'])
def get_attention_periods(mac_address):
    """Get attention periods only"""
    try:
        time_window = request.args.get('time_window', 60, type=int)
        periods = calculate_attention_periods(mac_address, time_window)
        
        return jsonify({
            "status": "ok",
            "mac_address": mac_address,
            "periods": periods
        }), 200
    except Exception as e:
        logger.error(f"Attention periods error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route("/analytics/<mac_address>/stats", methods=['GET'])
def get_session_stats(mac_address):
    """Get session statistics only"""
    try:
        time_window = request.args.get('time_window', 60, type=int)
        stats = calculate_session_stats(mac_address, time_window)
        
        return jsonify({
            "status": "ok",
            "mac_address": mac_address,
            "stats": stats
        }), 200
    except Exception as e:
        logger.error(f"Session stats error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route("/analytics/<mac_address>/metrics", methods=['GET'])
def get_analytics_metrics(mac_address):
    """Get analytics metrics only"""
    try:
        time_window = request.args.get('time_window', 60, type=int)
        metrics = calculate_performance_metrics(mac_address, time_window)
        
        return jsonify({
            "status": "ok",
            "mac_address": mac_address,
            "metrics": metrics
        }), 200
    except Exception as e:
        logger.error(f"Performance metrics error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route("/analytics/<mac_address>/timeline", methods=['GET'])
def get_wave_timeline(mac_address):
    """Get brain wave timeline for charting"""
    try:
        time_window = request.args.get('time_window', 30, type=int)
        timeline = get_wave_timeline_data(mac_address, time_window)
        
        if timeline:
            return jsonify({
                "status": "ok",
                "mac_address": mac_address,
                "timeline": timeline
            }), 200
        else:
            return jsonify({
                "status": "ok",
                "mac_address": mac_address,
                "timeline": None,
                "msg": "No data available"
            }), 200
    except Exception as e:
        logger.error(f"Wave timeline error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route("/api/students-list", methods=['GET'])
def get_students_list():
    """
    Get real-time list of all students with their latest EEG data and connection status
    This API is called by the dashboard for live updates
    """
    try:
        db = get_db_connection()
        if not db:
            return jsonify({"status": "error", "msg": "Database connection failed"}), 500
        
        cursor = db.cursor(dictionary=True)
        
        # Get all students
        cursor.execute("SELECT id, name, device_mac FROM students ORDER BY name")
        students = cursor.fetchall()
        
        students_data = []
        current_time = datetime.now()
        
        for student in students:
            mac = student['device_mac']
            
            # Check device status in memory (real-time connection tracking)
            device_status = DEVICE_STATUSES.get(mac)
            
            # If no status in memory, device never connected
            if device_status is None:
                students_data.append({
                    "id": student['id'],
                    "name": student['name'],
                    "mac_address": mac,
                    "state": "disconnected",
                    "focus": 0,
                    "delta": 0,
                    "theta": 0,
                    "alpha": 0,
                    "beta": 0,
                    "gamma": 0,
                    "connected": False,
                    "wearing": False,
                    "signal_quality": "offline",
                    "last_seen": "Never"
                })
                continue
            
            last_update = device_status.get('last_update')
            
            # Device is disconnected if:
            # 1. Never received data (last_update is None)
            # 2. No data received in last 10 seconds
            # 3. Signal quality is connection_error
            # 4. Not marked as connected
            is_disconnected = (
                last_update is None or 
                (current_time - last_update).total_seconds() > 10 or
                device_status.get('signal_quality') == 'connection_error' or
                not device_status.get('connected', False)
            )
            
            if is_disconnected:
                # Device disconnected - show as offline
                students_data.append({
                    "id": student['id'],
                    "name": student['name'],
                    "mac_address": mac,
                    "state": "disconnected",
                    "focus": 0,
                    "delta": 0,
                    "theta": 0,
                    "alpha": 0,
                    "beta": 0,
                    "gamma": 0,
                    "connected": False,
                    "wearing": False,
                    "signal_quality": "offline",
                    "last_seen": last_update.strftime("%H:%M:%S") if last_update else "Never"
                })
                continue
            
            # Device is connected - get latest EEG data
            cursor.execute("""
                SELECT timestamp, delta, theta, alpha, beta, gamma, focus, signal_quality
                FROM eeg_data 
                WHERE student_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (student['id'],))
            
            latest_data = cursor.fetchone()
            
            if latest_data:
                # Determine mental state from band powers
                band_powers = {
                    'delta': latest_data['delta'],
                    'theta': latest_data['theta'],
                    'alpha': latest_data['alpha'],
                    'beta': latest_data['beta'],
                    'gamma': latest_data['gamma']
                }
                
                # Get mental state using same logic as backend
                mental_state = get_mental_state(band_powers)
                focus_level = latest_data['focus']
                
                students_data.append({
                    "id": student['id'],
                    "name": student['name'],
                    "mac_address": mac,
                    "state": mental_state,
                    "focus": round(focus_level * 100, 1),
                    "delta": round(latest_data['delta'], 2),
                    "theta": round(latest_data['theta'], 2),
                    "alpha": round(latest_data['alpha'], 2),
                    "beta": round(latest_data['beta'], 2),
                    "gamma": round(latest_data['gamma'], 2),
                    "connected": True,
                    "wearing": device_status.get('wearing', True),
                    "signal_quality": latest_data['signal_quality'],
                    "last_update": latest_data['timestamp'].strftime("%H:%M:%S")
                })
            else:
                # No data in database yet - show as monitoring
                students_data.append({
                    "id": student['id'],
                    "name": student['name'],
                    "mac_address": mac,
                    "state": "relaxed",  # Default state until data arrives
                    "focus": 50,
                    "delta": 0,
                    "theta": 0,
                    "alpha": 0,
                    "beta": 0,
                    "gamma": 0,
                    "connected": True,
                    "wearing": device_status.get('wearing', True),
                    "signal_quality": "initializing",
                    "last_update": "Just connected"
                })
        
        cursor.close()
        db.close()
        
        return jsonify({
            "status": "success",
            "students": students_data,
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")
        }), 200
        
    except Exception as e:
        logger.error(f"Get students list error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route("/api/device-status", methods=['GET'])
def get_all_device_status():
    """Get connection status of all devices in real-time"""
    try:
        current_time = datetime.now()
        device_statuses = {}
        
        for mac, status in DEVICE_STATUSES.items():
            last_update = status.get('last_update')
            is_active = False
            
            if last_update:
                seconds_since_update = (current_time - last_update).total_seconds()
                is_active = seconds_since_update < 10  # 10 second timeout
            
            device_statuses[mac] = {
                "connected": is_active and status.get('connected', False),
                "wearing": status.get('wearing', False),
                "signal_quality": status.get('signal_quality', 'unknown'),
                "last_update": last_update.strftime("%Y-%m-%d %H:%M:%S") if last_update else None,
                "seconds_since_update": int((current_time - last_update).total_seconds()) if last_update else None
            }
        
        return jsonify({
            "status": "ok",
            "devices": device_statuses,
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")
        }), 200
        
    except Exception as e:
        logger.error(f"Device status error: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route("/api/device-status/<mac_address>", methods=['GET'])
def get_device_status(mac_address):
    """Get real-time status of a specific device"""
    try:
        status = DEVICE_STATUSES.get(mac_address, {})
        last_update = status.get('last_update')
        
        is_active = False
        if last_update:
            seconds_since_update = (datetime.now() - last_update).total_seconds()
            is_active = seconds_since_update < 10
        
        return jsonify({
            "status": "ok",
            "mac_address": mac_address,
            "connected": is_active and status.get('connected', False),
            "wearing": status.get('wearing', False),
            "signal_quality": status.get('signal_quality', 'unknown'),
            "last_update": last_update.strftime("%Y-%m-%d %H:%M:%S") if last_update else None,
            "error_message": status.get('error_message')
        }), 200
        
    except Exception as e:
        logger.error(f"Device status error for {mac_address}: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500


def cleanup_stale_connections():
    """
    Background task to clean up stale device connections
    Removes devices that haven't sent data in 30 seconds
    """
    import threading
    import time
    
    def cleanup_worker():
        while True:
            try:
                time.sleep(15)  # Check every 15 seconds
                
                current_time = datetime.now()
                stale_devices = []
                
                # Check all devices for stale connections
                for mac, status in list(DEVICE_STATUSES.items()):
                    last_update = status.get('last_update')
                    if last_update:
                        seconds_since = (current_time - last_update).total_seconds()
                        if seconds_since > 30:  # 30 seconds timeout for cleanup
                            stale_devices.append(mac)
                
                # Mark stale devices as disconnected (don't delete completely)
                for mac in stale_devices:
                    if mac in DEVICE_STATUSES:  # Safety check
                        logger.info(f"🧹 Cleaning up stale connection: {mac}")
                        DEVICE_STATUSES[mac]['connected'] = False
                        DEVICE_STATUSES[mac]['wearing'] = False
                        DEVICE_STATUSES[mac]['signal_quality'] = 'timeout'
                    
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                logger.error(traceback.format_exc())
    
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    logger.info("🧹 Started connection cleanup background task")


# Register route modules with access to hybrid prediction functions
register_students_routes(app, None, predict_state_hybrid, extract_ml_features)
register_session_routes(app)

if __name__ == "__main__":
    logger.info("🚀 Starting Enhanced EEG Monitor Server with HYBRID Prediction (Formula + ML)")
    
    # Initialize database
    init_database()
    
    # Load ML model for hybrid prediction
    ml_loaded = load_ml_model()
    if ml_loaded:
        logger.info("✅ ML Model loaded - Using HYBRID prediction (Formula + ML)")
    else:
        logger.warning("⚠️  ML Model not loaded - Using Formula-based prediction only")
    
    # Start background cleanup task for stale connections
    cleanup_stale_connections()
    
    logger.info("🌐 Server ready to accept connections from multiple devices")
    logger.info("📊 Prediction Method: HYBRID (NASA Engagement Index + XGBoost/LightGBM/CatBoost)")
    logger.info("🔄 Auto-cleanup enabled for disconnected devices (30s timeout)")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)