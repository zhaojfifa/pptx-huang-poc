"""
MySQL skill - thin wrapper around mysql-connector-python.
Primary data access is in database/db.py.
"""

from config.settings import MYSQL_DB, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT, MYSQL_USER
from database.db import get_connection

__all__ = ["get_connection", "MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DB"]
