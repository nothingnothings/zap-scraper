#!/usr/bin/env python
# coding: utf-8
"""
Centralized database configuration for the Zap Scraper project.

Credentials are read from the `.env` file (same file used by `zap.py`).
If a variable is missing, a sensible default matching the bundled
`docker/docker-compose.yml` is used.

Export:
    get_db_params() -> dict   The parameters to pass to pymysql.connect()
"""

import os


def get_db_params():
    """
    Return a dict of MySQL connection parameters.

    Values come from environment variables (see .env.example / docker-compose)
    and fall back to the defaults used by the bundled docker-compose.

    The .env file is loaded lazily so that importing this module (e.g. for
    offline testing) does not require python-dotenv to be installed.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "myuser"),
        "password": os.getenv("DB_PASSWORD", "mypassword"),
        "database": os.getenv("DB_NAME", "mydatabase"),
        "charset": "utf8mb4",
    }