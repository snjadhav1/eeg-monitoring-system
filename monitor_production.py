"""
Real-Time Model Performance Monitor
Tracks model predictions in production and validates accuracy
"""

import mysql.connector
from datetime import datetime, timedelta
import numpy as np
from collections import Counter
import sys
import os

sys.path.append(os.path.dirname(__file__))

from app import get_db_connection, get_mental_state, calculate_focus

def analyze_recent_predictions(minutes=60):
    """Analyze predictions from last N minutes"""
    print(f"\n{'='*70}")
    print(f"ANALYZING LAST {minutes} MINUTES OF PREDICTIONS")
    print("="*70)
    
    db = get_db_connection()
    if not db:
        print("❌ Database connection failed")
        return
    
    cursor = db.cursor(dictionary=True)
    
    # Get data from last N minutes
    cursor.execute("""
        SELECT 
            timestamp,
            delta, theta, alpha, beta, gamma,
            focus,
            mac_address,
            student_id
        FROM eeg_data
        WHERE timestamp > DATE_SUB(NOW(), INTERVAL %s MINUTE)
        ORDER BY timestamp DESC
    """, (minutes,))
    
    records = cursor.fetchall()
    cursor.close()
    db.close()
    
    if not records:
        print(f"⚠️ No data found in last {minutes} minutes")
        return
    
    print(f"\n✅ Found {len(records)} records")
    
    # Analyze predictions
    states = []
    focus_levels = []
    band_stats = {
        'delta': [], 'theta': [], 'alpha': [], 'beta': [], 'gamma': []
    }
    
    conflicts = 0
    
    for record in records:
        # Reconstruct band powers
        bands = {
            'delta': record['delta'],
            'theta': record['theta'],
            'alpha': record['alpha'],
            'beta': record['beta'],
            'gamma': record['gamma']
        }
        
        # Re-calculate state using current formula
        calculated_state = get_mental_state(bands)
        calculated_focus = calculate_focus(bands)
        stored_focus = record['focus']
        
        states.append(calculated_state)
        focus_levels.append(stored_focus)
        
        for band, value in bands.items():
            band_stats[band].append(value)
        
        # Check for conflicts (high focus but distracted state)
        if stored_focus > 0.7 and calculated_state == 'distracted':
            conflicts += 1
        elif stored_focus < 0.3 and calculated_state == 'focused':
            conflicts += 1
    
    # Statistics
    print("\n" + "="*70)
    print("STATE DISTRIBUTION")
    print("="*70)
    
    state_counts = Counter(states)
    total = len(states)
    
    for state, count in state_counts.most_common():
        percentage = (count / total) * 100
        bar = "█" * int(percentage / 2)
        print(f"{state:12s}: {count:4d} ({percentage:5.1f}%) {bar}")
    
    # Focus statistics
    print("\n" + "="*70)
    print("FOCUS LEVEL STATISTICS")
    print("="*70)
    
    avg_focus = np.mean(focus_levels) * 100
    min_focus = np.min(focus_levels) * 100
    max_focus = np.max(focus_levels) * 100
    std_focus = np.std(focus_levels) * 100
    
    print(f"Average Focus: {avg_focus:.1f}%")
    print(f"Min Focus:     {min_focus:.1f}%")
    print(f"Max Focus:     {max_focus:.1f}%")
    print(f"Std Dev:       {std_focus:.1f}%")
    
    # Band power statistics
    print("\n" + "="*70)
    print("AVERAGE BAND POWERS")
    print("="*70)
    
    for band, values in band_stats.items():
        avg = np.mean(values)
        print(f"{band.capitalize():8s}: {avg:.4f}")
    
    # Conflict analysis
    print("\n" + "="*70)
    print("PREDICTION QUALITY")
    print("="*70)
    
    conflict_rate = (conflicts / total) * 100
    
    print(f"Total Predictions:     {total}")
    print(f"Conflicting:           {conflicts} ({conflict_rate:.1f}%)")
    print(f"Consistent:            {total - conflicts} ({100 - conflict_rate:.1f}%)")
    
    if conflict_rate < 5:
        print("\n✅ EXCELLENT: Very few conflicts")
    elif conflict_rate < 15:
        print("\n✅ GOOD: Acceptable conflict rate")
    elif conflict_rate < 25:
        print("\n⚠️ WARNING: High conflict rate")
    else:
        print("\n❌ CRITICAL: Too many conflicts")
    
    return conflict_rate


def check_state_transitions(minutes=30):
    """Analyze how states change over time"""
    print(f"\n{'='*70}")
    print(f"STATE TRANSITION ANALYSIS (Last {minutes} minutes)")
    print("="*70)
    
    db = get_db_connection()
    if not db:
        print("❌ Database connection failed")
        return
    
    cursor = db.cursor(dictionary=True)
    
    # Get time-series data
    cursor.execute("""
        SELECT 
            timestamp,
            delta, theta, alpha, beta, gamma,
            focus,
            mac_address
        FROM eeg_data
        WHERE timestamp > DATE_SUB(NOW(), INTERVAL %s MINUTE)
        ORDER BY mac_address, timestamp ASC
    """, (minutes,))
    
    records = cursor.fetchall()
    cursor.close()
    db.close()
    
    if len(records) < 10:
        print(f"⚠️ Not enough data for transition analysis")
        return
    
    # Group by device
    devices = {}
    for record in records:
        mac = record['mac_address']
        if mac not in devices:
            devices[mac] = []
        devices[mac].append(record)
    
    print(f"\n✅ Analyzing {len(devices)} device(s)")
    
    total_transitions = 0
    rapid_changes = 0
    
    for mac, device_records in devices.items():
        if len(device_records) < 5:
            continue
        
        print(f"\nDevice: {mac[-8:]}")
        
        prev_state = None
        prev_time = None
        state_durations = []
        
        for record in device_records:
            bands = {
                'delta': record['delta'],
                'theta': record['theta'],
                'alpha': record['alpha'],
                'beta': record['beta'],
                'gamma': record['gamma']
            }
            
            current_state = get_mental_state(bands)
            current_time = record['timestamp']
            
            if prev_state is not None:
                if current_state != prev_state:
                    # State changed
                    duration = (current_time - prev_time).total_seconds()
                    state_durations.append(duration)
                    total_transitions += 1
                    
                    if duration < 5:  # Very rapid change
                        rapid_changes += 1
                        print(f"  ⚠️ Rapid change: {prev_state} → {current_state} ({duration:.1f}s)")
                    else:
                        print(f"  ✓ {prev_state} → {current_state} ({duration:.1f}s)")
            
            prev_state = current_state
            prev_time = current_time
        
        if state_durations:
            avg_duration = np.mean(state_durations)
            print(f"  Average state duration: {avg_duration:.1f}s")
    
    print("\n" + "="*70)
    print("TRANSITION SUMMARY")
    print("="*70)
    
    print(f"Total transitions:     {total_transitions}")
    print(f"Rapid changes (<5s):   {rapid_changes}")
    
    if total_transitions > 0:
        rapid_rate = (rapid_changes / total_transitions) * 100
        print(f"Rapid change rate:     {rapid_rate:.1f}%")
        
        if rapid_rate < 10:
            print("\n✅ STABLE: States change smoothly")
        elif rapid_rate < 25:
            print("\n⚠️ MODERATE: Some instability")
        else:
            print("\n❌ UNSTABLE: Too many rapid changes")


def validate_band_power_ratios():
    """Check if band power ratios make sense"""
    print(f"\n{'='*70}")
    print("BAND POWER RATIO VALIDATION")
    print("="*70)
    
    db = get_db_connection()
    if not db:
        print("❌ Database connection failed")
        return
    
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT delta, theta, alpha, beta, gamma
        FROM eeg_data
        WHERE timestamp > DATE_SUB(NOW(), INTERVAL 30 MINUTE)
        LIMIT 100
    """)
    
    records = cursor.fetchall()
    cursor.close()
    db.close()
    
    if not records:
        print("⚠️ No recent data")
        return
    
    # Check ratios
    beta_theta_ratios = []
    beta_alpha_ratios = []
    total_powers = []
    
    for record in records:
        beta = record['beta']
        theta = record['theta']
        alpha = record['alpha']
        total = sum([record['delta'], record['theta'], record['alpha'], record['beta'], record['gamma']])
        
        if theta > 0:
            beta_theta_ratios.append(beta / theta)
        if alpha > 0:
            beta_alpha_ratios.append(beta / alpha)
        total_powers.append(total)
    
    print(f"\nBeta/Theta Ratio:")
    print(f"  Mean: {np.mean(beta_theta_ratios):.2f}")
    print(f"  Range: {np.min(beta_theta_ratios):.2f} - {np.max(beta_theta_ratios):.2f}")
    
    print(f"\nBeta/Alpha Ratio:")
    print(f"  Mean: {np.mean(beta_alpha_ratios):.2f}")
    print(f"  Range: {np.min(beta_alpha_ratios):.2f} - {np.max(beta_alpha_ratios):.2f}")
    
    print(f"\nTotal Power:")
    print(f"  Mean: {np.mean(total_powers):.4f}")
    print(f"  Range: {np.min(total_powers):.4f} - {np.max(total_powers):.4f}")
    
    # Validate ranges
    issues = []
    
    if np.mean(beta_theta_ratios) < 0.5:
        issues.append("⚠️ Low beta/theta ratio - may over-predict distraction")
    
    if np.mean(total_powers) < 0.1:
        issues.append("⚠️ Very low total power - check signal quality")
    elif np.mean(total_powers) > 10:
        issues.append("⚠️ Very high total power - check normalization")
    
    if issues:
        print("\n" + "="*70)
        print("POTENTIAL ISSUES:")
        for issue in issues:
            print(issue)
    else:
        print("\n✅ All ratios within acceptable ranges")


def main():
    """Run all monitoring tests"""
    print("="*70)
    print("REAL-TIME MODEL PERFORMANCE MONITOR")
    print("="*70)
    print(f"Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Run tests
    conflict_rate = analyze_recent_predictions(minutes=60)
    check_state_transitions(minutes=30)
    validate_band_power_ratios()
    
    print("\n" + "="*70)
    print("OVERALL ASSESSMENT")
    print("="*70)
    
    if conflict_rate is not None:
        if conflict_rate < 10:
            print("✅ Model is performing EXCELLENTLY in production")
            print("   Confidence: 95-100%")
        elif conflict_rate < 20:
            print("✅ Model is performing WELL in production")
            print("   Confidence: 85-95%")
        elif conflict_rate < 30:
            print("⚠️ Model performance is ACCEPTABLE but could improve")
            print("   Confidence: 70-85%")
        else:
            print("❌ Model performance NEEDS IMPROVEMENT")
            print("   Confidence: <70%")
    else:
        print("⚠️ Not enough data to assess model performance")
        print("   Run system for at least 30 minutes with connected devices")
    
    print(f"\nTest Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)


if __name__ == "__main__":
    main()
