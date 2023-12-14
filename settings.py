import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR_NAME = 'templates'
INCLUDES_DIR_NAME = 'includes'
LOGS_DIR_NAME = 'logs'
DB_DIR_NAME = 'db'
DB_NAME = 'db.sqlite'
DB_PATH = os.path.join(DB_DIR_NAME, DB_NAME)
