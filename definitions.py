import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(ROOT_DIR, 'manager/db/data.db')
TMP_DATABASE_PATH = os.path.join(ROOT_DIR, 'tests/tmp_data.db')