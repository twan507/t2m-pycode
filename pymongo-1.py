import pandas as pd
from sqlalchemy import create_engine, text

username = 'twan'
password = 'chodom'
database = 't2m'
server = socket.gethostbyname(socket.gethostname())
engine = create_engine(f"mysql+pymysql://{username}:{password}@{server}/{database}")
conn = engine.connect()

query = text('SELECT * FROM table')
df = pd.read_sql_query(query, conn)