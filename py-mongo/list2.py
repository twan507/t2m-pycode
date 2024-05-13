import socket
import time
import pandas as pd
import numpy as np
from pymongo import MongoClient
from sqlalchemy import create_engine, text

list1 = ['index_card_df','itd_score_liquidity_last','market_info_df','market_sentiment','update_time']
list2 = ['itd_score_liquidity_df','eod_score_liquidity_melted','eod_group_liquidity_df','industry_breath_df','market_breath_df']
list3 = ['nn_td_20p_df','nn_td_buy_sell_df','nn_td_top_stock','ta_index_df','market_top_stock','group_slicer_df','group_score_ranking','group_score_df_5p']
list4 = ['full_industry_ranking', 'group_score_month','group_score_ranking_melted','group_score_week','group_stock_top_10_df','itd_score_liquidity_melted',
         'stock_ta_df','stock_score_power_df','eod_score_df',
         'stock_liquidty_score_t0','stock_score_month','stock_score_week',
         'filter_stock_accumulation', 'filter_stock_support', 'filter_stock_breakout']
list5 = ['stock_price_chart_df','index_price_chart_df','group_stock_price_index','market_ms',]

start_time = time.time()

#Đọc dữ liệu từ mysql
username = 'twan'
password = 'chodom'
database = 't2m'
server = socket.gethostbyname(socket.gethostname())
engine = create_engine(f"mysql+pymysql://{username}:{password}@{server}/{database}")
conn = engine.connect()

#Truy cập Mongo
conn_string = "mongodb+srv://t2minvest:b1RbCLkeYZyKPmMM@t2m.ev6enbf.mongodb.net/"
client = MongoClient(conn_string)
db = client['stockdata']

for table_name in list2:
        
    df = pd.read_sql_query(text(f'SELECT * FROM {table_name}'), conn)
    df = df.replace({np.nan: None, pd.NaT: None})

    #Xoá bảng trong Mongo nếu đã tồn tại
    collections = db.list_collection_names()
    if table_name in collections:
        db[table_name].drop()

    #Lưu lại bảng df vào db
    collection = db[table_name]
    collection.insert_many(df.to_dict("records")) 

client.close()
engine.dispose()


end_time = time.time()
print(f"✔ list 2, Completed in: {int(end_time - start_time)}s")