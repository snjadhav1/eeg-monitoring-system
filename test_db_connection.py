"""
Test Database Connection to Clever Cloud MySQL
Run this script to verify your database credentials are correct
"""

import os
import mysql.connector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("🔍 TESTING CLEVER CLOUD DATABASE CONNECTION")
print("=" * 60)

# Get credentials from .env
db_host = os.getenv('MYSQL_HOST')
db_port = os.getenv('MYSQL_PORT', '3306')
db_user = os.getenv('MYSQL_USER')
db_password = os.getenv('MYSQL_PASSWORD')
db_name = os.getenv('MYSQL_DATABASE')

print("\n📋 Configuration Check:")
print(f"   Host: {db_host}")
print(f"   Port: {db_port}")
print(f"   User: {db_user}")
print(f"   Password: {'*' * len(db_password) if db_password else 'NOT SET'}")
print(f"   Database: {db_name}")

# Check if all required variables are set
missing = []
if not db_host or db_host == 'your-mysql-host.services.clever-cloud.com':
    missing.append('MYSQL_HOST')
if not db_user or db_user == 'your-mysql-user':
    missing.append('MYSQL_USER')
if not db_password or db_password == 'your-mysql-password':
    missing.append('MYSQL_PASSWORD')
if not db_name or db_name == 'your-database-name':
    missing.append('MYSQL_DATABASE')

if missing:
    print("\n❌ ERROR: Missing or incorrect environment variables!")
    print(f"   Please update these in your .env file: {', '.join(missing)}")
    print("\n📝 Instructions:")
    print("   1. Open .env file")
    print("   2. Go to Clever Cloud dashboard → Your MySQL add-on")
    print("   3. Click 'Environment Variables'")
    print("   4. Copy the correct values to your .env file")
    print("   5. Save and run this script again")
    exit(1)

print("\n🔌 Attempting to connect to database...")

try:
    # Try to connect
    connection = mysql.connector.connect(
        host=db_host,
        port=int(db_port),
        user=db_user,
        password=db_password,
        database=db_name,
        connection_timeout=30
    )
    
    print("✅ Connection successful!")
    
    # Test query
    cursor = connection.cursor()
    cursor.execute("SELECT VERSION()")
    version = cursor.fetchone()
    print(f"✅ MySQL Version: {version[0]}")
    
    # Show existing tables
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    
    if tables:
        print(f"\n📊 Existing tables in database:")
        for table in tables:
            print(f"   - {table[0]}")
    else:
        print("\n📊 No tables found. Creating tables...")
        
        # Create tables
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            device_mac VARCHAR(50) UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
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
        
        connection.commit()
        print("✅ Tables created successfully!")
    
    cursor.close()
    connection.close()
    
    print("\n" + "=" * 60)
    print("✨ SUCCESS! Your database is ready to use!")
    print("=" * 60)
    print("\n🚀 Next steps:")
    print("   1. Run your Flask app: python app.py")
    print("   2. Open browser: http://localhost:5000")
    print("   3. Your app will now save data to Clever Cloud!")
    print("\n")
    
except mysql.connector.Error as err:
    print(f"\n❌ Connection failed!")
    print(f"   Error: {err}")
    print("\n🔧 Troubleshooting:")
    print("   1. Check your .env file has correct credentials")
    print("   2. Verify MySQL add-on is running in Clever Cloud")
    print("   3. Check your internet connection")
    print("   4. Make sure no firewall is blocking the connection")
    print("\n")
    exit(1)

except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    print("\n")
    exit(1)
