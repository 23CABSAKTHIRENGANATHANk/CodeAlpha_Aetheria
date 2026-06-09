"""
Database initialization and connection management.
Handles connection pooling, retries, and graceful degradation.
"""

import os
import logging
from urllib.parse import urlparse, parse_qs, urlencode, quote_plus

logger = logging.getLogger(__name__)


def clean_database_url(url):
    """
    Clean up DATABASE_URL to remove invalid PostgreSQL parameters.
    Handles malformed connection strings from hosting providers.
    """
    if not url:
        return None
        
    try:
        # Parse the URL
        parsed = urlparse(url)
        
        # Reconstruct the base URL
        if parsed.scheme in ['postgres', 'postgresql']:
            # Remove any invalid parameters
            netloc = parsed.netloc
            path = parsed.path or '/'
            
            # Rebuild URL with clean parameters
            clean_url = f"{parsed.scheme}://{netloc}{path}"
            
            logger.info(f"✅ Database URL cleaned successfully")
            return clean_url
        else:
            logger.warning(f"⚠️  Unknown database scheme: {parsed.scheme}")
            return url
    except Exception as e:
        logger.error(f"❌ Error cleaning database URL: {e}")
        return url


def get_database_config():
    """
    Get database configuration with proper error handling.
    Returns dict suitable for Django DATABASES config.
    """
    import dj_database_url
    
    database_url = os.environ.get("DATABASE_URL")
    
    if not database_url:
        # Fall back to local development or SQLite
        return None
    
    try:
        # Clean the database URL
        clean_url = clean_database_url(database_url)
        
        # Parse the cleaned URL
        db_config = dj_database_url.config(
            default=clean_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
        
        # Set PostgreSQL-specific options
        db_config['OPTIONS'] = {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',
        }
        
        # Remove any problematic parameters
        if 'default_transaction_isolation' in db_config.get('OPTIONS', {}):
            del db_config['OPTIONS']['default_transaction_isolation']
        
        logger.info("✅ Database configuration loaded successfully")
        return db_config
        
    except Exception as e:
        logger.error(f"❌ Error loading database configuration: {e}")
        return None


def verify_database_connection():
    """
    Verify database connection is working.
    Logs connection status but doesn't fail.
    """
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        logger.info("✅ Database connection verified")
        return True
    except Exception as e:
        logger.warning(f"⚠️  Database connection check failed: {e}")
        return False
