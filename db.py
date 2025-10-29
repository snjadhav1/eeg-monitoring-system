"""
Database Configuration Module
Centralized database connection management for EEG Monitoring System
"""

import os
import mysql.connector
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

def print_env_credentials():
    """
    Print environment credentials for debugging
    """
    print("\n" + "="*70)
    print("DATABASE ENVIRONMENT CREDENTIALS")
    print("="*70)
    print(f"MYSQL_HOST     : {os.getenv('MYSQL_HOST', 'NOT SET')}")
    print(f"MYSQL_PORT     : {os.getenv('MYSQL_PORT', 'NOT SET')}")
    print(f"MYSQL_USER     : {os.getenv('MYSQL_USER', 'NOT SET')}")
    print(f"MYSQL_PASSWORD : {'*' * len(os.getenv('MYSQL_PASSWORD', '')) if os.getenv('MYSQL_PASSWORD') else 'NOT SET'}")
    print(f"MYSQL_DATABASE : {os.getenv('MYSQL_DATABASE', 'NOT SET')}")
    print("="*70 + "\n")

def get_db_config():
    """
    Get database configuration from environment variables
    Returns dict with MySQL connection parameters
    """
    config = {
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
    
    # Print credentials for debugging
    print(f"🔧 DB Config - Host: {config['host']}, Port: {config['port']}, User: {config['user']}, DB: {config['database']}")
    
    return config

def get_db_connection():
    """
    Create and return a MySQL database connection
    Uses environment variables for configuration
    
    Returns:
        mysql.connector.connection: Database connection object
    
    Raises:
        Exception: If connection fails
    """
    try:
        db_config = get_db_config()
        db = mysql.connector.connect(**db_config)
        logger.info(f"✅ Connected to MySQL: {db_config['host']}")
        return db
    except mysql.connector.Error as err:
        logger.error(f"❌ MySQL Connection Error: {err}")
        print("\n⚠️ Connection failed! Printing environment credentials for debugging:")
        print_env_credentials()
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error connecting to database: {e}")
        print("\n⚠️ Unexpected error! Printing environment credentials for debugging:")
        print_env_credentials()
        raise
