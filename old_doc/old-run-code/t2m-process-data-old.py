def run_data():
    import copy
    import datetime as dt
    import os
    import warnings
    from datetime import timedelta

    import numpy as np
    import pandas as pd

    warnings.filterwarnings("ignore")
    warnings.simplefilter("ignore", category=FutureWarning)
    pd.options.mode.chained_assignment = None

    # Đọc name map để chuyển đỏi các tên thành dạng full
    name_map = pd.read_excel(
        "data/t2m_classification.xlsx", sheet_name="name_map"
    ).drop(columns=["group", "order"], axis=1)
    name_map_dict = name_map.set_index("code")["full_name"].to_dict()

    order_map = pd.read_excel(
        "data/t2m_classification.xlsx", sheet_name="name_map"
    ).drop(columns=["group", "full_name"], axis=1)
    order_map_dict = order_map.set_index("code")["order"].to_dict()

    group_map = pd.read_excel(
        "data/t2m_classification.xlsx", sheet_name="name_map"
    ).drop(columns=["order", "full_name"], axis=1)
    group_map_dict = group_map.set_index("code")["group"].to_dict()

    # Đọc toàn bộ các file csv được xuất ra từ ami eod
    eod_item_dict = {}
    folder_path = "D:\\t2m-project\\ami-data\\ami_eod_data"
    for filename in os.listdir(folder_path):
        if filename.endswith(".csv"):
            key = os.path.splitext(filename)[0]
            eod_item_dict[key] = (
                pd.read_csv(os.path.join(folder_path, filename))
                .sort_values("date", ascending=False)
                .reset_index(drop=True)
            )

    for item, df in eod_item_dict.items():
        df["date"] = pd.to_datetime(df["date"].astype(str), format="%y%m%d")
        eod_item_dict[item] = df

    # Tạo bảng tổng hớp tất cả các item
    eod_item_df = pd.DataFrame(list(eod_item_dict.keys())).rename(columns={0: "item"})
    eod_item_df["len"] = eod_item_df["item"].apply(lambda x: len(x))
    eod_item_df["last_2chars"] = eod_item_df["item"].str[-2:]
    eod_item_df["first_4chars"] = eod_item_df["item"].str[:4]

    # Lọc ra danh sách tên các cổ phiếu và index
    stock_name_df = (
        eod_item_df[eod_item_df["len"] == 3]
        .reset_index(drop=True)
        .drop(["len", "last_2chars", "first_4chars"], axis=1)
    )
    index_name_df = (
        eod_item_df[
            (eod_item_df["len"] > 3)
            & (eod_item_df["len"] != 6)
            & (eod_item_df["len"] < 10)
            & (eod_item_df["item"] != "0001")
        ]
        .reset_index(drop=True)
        .drop(["len", "last_2chars", "first_4chars"], axis=1)
    )

    eod_stock_dict = {
        k: v.drop(["option"], axis=1)
        for k, v in eod_item_dict.items()
        if k in stock_name_df["item"].tolist()
    }
    eod_index_dict = {
        k: v.rename(columns={"option": "value"}).drop("cap", axis=1)
        for k, v in eod_item_dict.items()
        if k in index_name_df["item"].tolist()
    }

    # Lọc ra danh sách tên các cổ phiếu, index giao dịch tự doanh và nước ngoài
    stock_name_td_df = (
        eod_item_df[(eod_item_df["len"] == 6) & (eod_item_df["last_2chars"] == "TD")]
        .reset_index(drop=True)
        .drop(["len", "last_2chars", "first_4chars"], axis=1)
    )
    stock_name_nn_df = (
        eod_item_df[(eod_item_df["len"] == 6) & (eod_item_df["last_2chars"] == "NN")]
        .reset_index(drop=True)
        .drop(["len", "last_2chars", "first_4chars"], axis=1)
    )
    index_td_nn_df = (
        eod_item_df[
            (eod_item_df["len"] >= 10)
            & (eod_item_df["first_4chars"] != "VN30")
            & (
                (eod_item_df["last_2chars"] == "NN")
                | (eod_item_df["last_2chars"] == "TD")
            )
        ]
        .reset_index(drop=True)
        .drop(["len", "last_2chars", "first_4chars"], axis=1)
    )

    stock_td_dict = {
        k: v.drop(["high", "low", "cap"], axis=1).rename(
            columns={
                "open": "sell_volume",
                "close": "buy_volume",
                "volume": "sell_value",
                "option": "buy_value",
            }
        )
        for k, v in eod_item_dict.items()
        if k in stock_name_td_df["item"].tolist()
    }
    stock_nn_dict = {
        k: v.drop(["high", "low", "cap"], axis=1).rename(
            columns={
                "open": "sell_volume",
                "close": "buy_volume",
                "volume": "sell_value",
                "option": "buy_value",
            }
        )
        for k, v in eod_item_dict.items()
        if k in stock_name_nn_df["item"].tolist()
    }
    index_td_nn_dict = {
        k: v.drop(["high", "low", "cap", "stock"], axis=1).rename(
            columns={
                "open": "sell_volume",
                "close": "buy_volume",
                "volume": "sell_value",
                "option": "buy_value",
            }
        )
        for k, v in eod_item_dict.items()
        if k in index_td_nn_df["item"].tolist()
    }

    # Điều chỉnh đơn vị của các bảng NN và TD
    for df in index_td_nn_dict.values():
        df["buy_volume"] = df["buy_volume"] / 1000
        df["sell_volume"] = -df["sell_volume"] / 1000
        df["buy_value"] = df["buy_value"] / 1000000000
        df["sell_value"] = -df["sell_value"] / 1000000000
        df["net_volume"] = df["buy_volume"] + df["sell_volume"]
        df["net_value"] = df["buy_value"] + df["sell_value"]

    # Tạo một date_series bao gồm khoảng ngày tính toán eod
    date_series = pd.DataFrame(eod_index_dict["VNINDEX"]["date"]).rename(
        columns={0: "date"}
    )

    # Tạo một time_series bao gồm khoảng ngày tính toán itd (tính thừa 1 ngày để trừ dần đi)
    time_series_list = []
    for day in date_series["date"].iloc[:1].tolist():
        time_series_list.extend(
            pd.date_range(start=f"{day} 09:00:00", end=f"{day} 11:25:00", freq="5T")
        )
        time_series_list.extend(
            pd.date_range(start=f"{day} 13:00:00", end=f"{day} 14:55:00", freq="5T")
        )
    time_series = pd.DataFrame(time_series_list).rename(columns={0: "date"})

    # Tạo 1 khung thời gian trong ngày từ 9h15 tới hết giờ
    itd_series = pd.DataFrame(time_series_list[3:]).rename(columns={0: "date"})

    # Đọc toàn bộ các file csv được xuất ra từ ami itd
    itd_item_dict = {}
    folder_path = "D:\\t2m-project\\ami-data\\ami_itd_data"
    for filename in os.listdir(folder_path):
        if filename.endswith(".csv"):
            key = os.path.splitext(filename)[0]
            itd_item_dict[key] = (
                pd.read_csv(os.path.join(folder_path, filename))
                .sort_values("date", ascending=False)
                .reset_index(drop=True)
            )

    # Lấy thời gian hiện tại của dữ liệu được xuất ra
    current_time = pd.to_datetime(
        itd_item_dict["HNXINDEX"]["date"].iloc[0], format="%y%m%d %H%M%S"
    )

    # Điều chỉnh lại timeseries cho khớp với khung thời gian dữ liệu, bỏ đi các hàng chưa có dữ liệu
    time_series = (
        time_series.loc[time_series["date"] <= current_time]
        .sort_values("date", ascending=False)
        .reset_index(drop=True)
    )

    for item, df in itd_item_dict.items():

        df["date"] = pd.to_datetime(df["date"].astype(str), format="%y%m%d %H%M%S")

        # Fill dữ liệu vào các khoảng thời gian trống
        df = time_series.merge(df, on="date", how="left").sort_values(
            "date", ascending=False
        )
        df[["open", "high", "low", "close"]] = df[
            ["open", "high", "low", "close"]
        ].fillna(method="bfill")
        df["volume"] = df["volume"].fillna(0)
        df["stock"] = item

        itd_item_dict[item] = df

    # Tạo bảng tổng hợp tất cả các item
    itd_item_df = pd.DataFrame(list(itd_item_dict.keys())).rename(columns={0: "item"})
    itd_item_df["len"] = itd_item_df["item"].apply(lambda x: len(x))
    itd_item_df["last_2chars"] = itd_item_df["item"].str[-2:]
    itd_item_df["third_last_char"] = itd_item_df["item"].str[-3:-2]
    itd_item_df["first_4chars"] = itd_item_df["item"].str[:4]

    # Lọc ra danh sách tên các cổ phiếu và index
    stock_name_df = (
        itd_item_df[itd_item_df["len"] == 3]
        .reset_index(drop=True)
        .drop(["len", "last_2chars", "third_last_char", "first_4chars"], axis=1)
    )
    index_name_df = (
        itd_item_df[
            (itd_item_df["len"] > 3)
            & (itd_item_df["len"] != 6)
            & (itd_item_df["len"] < 10)
            & (itd_item_df["item"] != "0001")
        ]
        .reset_index(drop=True)
        .drop(["len", "last_2chars", "third_last_char", "first_4chars"], axis=1)
    )

    itd_stock_dict = {
        k: v for k, v in itd_item_dict.items() if k in stock_name_df["item"].tolist()
    }
    itd_index_dict = {
        k: v.rename(columns={"option": "value"})
        for k, v in itd_item_dict.items()
        if k in index_name_df["item"].tolist()
    }

    def calculate_time_percent(time):
        start_time_am = dt.time(9, 00)
        end_time_am = dt.time(11, 30)
        start_time_pm = dt.time(13, 00)
        end_time_pm = dt.time(15, 00)

        def time_difference_in_minutes(time1, time2):
            delta1 = dt.timedelta(
                hours=time1.hour, minutes=time1.minute, seconds=time1.second
            )
            delta2 = dt.timedelta(
                hours=time2.hour, minutes=time2.minute, seconds=time2.second
            )
            diff = delta2 - delta1
            return diff.seconds // 60

        time = (time + timedelta(minutes=5)).time()
        full_time_range = time_difference_in_minutes(
            start_time_am, end_time_am
        ) + time_difference_in_minutes(start_time_pm, end_time_pm)

        if time <= end_time_am:
            time_range = time_difference_in_minutes(start_time_am, time)
        elif time >= start_time_pm:
            time_range = time_difference_in_minutes(
                start_time_am, time
            ) - time_difference_in_minutes(end_time_am, start_time_pm)

        return time_range / full_time_range

    # Điều chỉnh lại time_series bỏ đi các hàng thời gian chưa có dữ liệu
    time_series = (
        time_series.loc[time_series["date"] <= current_time]
        .sort_values("date", ascending=False)
        .reset_index(drop=True)
    )

    # Tính thêm time percent
    time_percent = time_series.copy()
    time_percent["percent"] = time_percent["date"].apply(calculate_time_percent)
    time_percent["percent"] = time_percent["percent"].apply(lambda x: x if x < 1 else 1)
    current_time_percent = time_percent["percent"].iloc[0]

    # Tạo bảng thời gian update
    def get_update_time(start_time_am, end_time_am, start_time_pm, end_time_pm):
        if (dt.datetime.now()).weekday() <= 4:
            current_time = dt.datetime.now().time()
            if current_time < start_time_am:
                current_time = end_time_pm
            elif (current_time >= start_time_am) & (current_time < end_time_am):
                current_time = current_time
            elif (current_time >= end_time_am) & (current_time < start_time_pm):
                current_time = end_time_am
            elif (current_time >= start_time_pm) & (current_time < end_time_pm):
                current_time = current_time
            elif current_time >= end_time_pm:
                current_time = end_time_pm
            return current_time
        if (dt.datetime.now()).weekday() > 4:
            return end_time_pm

    time_update = get_update_time(
        dt.time(9, 00), dt.time(11, 30), dt.time(13, 00), dt.time(15, 00)
    )
    date_time_update = dt.datetime.combine(current_time.date(), time_update)
    update_time = pd.DataFrame(
        [f"Cập nhât: {date_time_update.strftime('%d/%m/%Y %H:%M:%S')}"]
    ).rename(columns={0: "date"})

    # #### Đường trung bình
    # Tính toán các đường trung bình và các đường MA
    eod_stock_dict = {
        k: v.sort_values(by=["date"], ascending=True).reset_index(drop=True)
        for k, v in eod_stock_dict.items()
    }

    eod_stock_dict = {
        key: df.assign(
            high5=df["high"].rolling(window=5, min_periods=1).max(),
            low5=df["low"].rolling(window=5, min_periods=1).min(),
            high20=df["high"].rolling(window=20, min_periods=1).max(),
            low20=df["low"].rolling(window=20, min_periods=1).min(),
            high60=df["high"].rolling(window=60, min_periods=1).max(),
            low60=df["low"].rolling(window=60, min_periods=1).min(),
            high120=df["high"].rolling(window=120, min_periods=1).max(),
            low120=df["low"].rolling(window=120, min_periods=1).min(),
            high240=df["high"].rolling(window=240, min_periods=1).max(),
            low240=df["low"].rolling(window=240, min_periods=1).min(),
            high480=df["high"].rolling(window=480, min_periods=1).max(),
            low480=df["low"].rolling(window=480, min_periods=1).min(),
            ma5_V=df["volume"].rolling(window=5, min_periods=1).mean().shift(1),
            ma20_V=df["volume"].rolling(window=20, min_periods=1).mean().shift(1),
            ma60_V=df["volume"].rolling(window=60, min_periods=1).mean().shift(1),
            ma120_V=df["volume"].rolling(window=120, min_periods=1).mean().shift(1),
            ma5=df["close"].rolling(window=5, min_periods=1).mean(),
            ma20=df["close"].rolling(window=20, min_periods=1).mean(),
            ma60=df["close"].rolling(window=60, min_periods=1).mean(),
            ma120=df["close"].rolling(window=120, min_periods=1).mean(),
            ma240=df["close"].rolling(window=240, min_periods=1).mean(),
            ma480=df["close"].rolling(window=480, min_periods=1).mean(),
        )
        for key, df in eod_stock_dict.items()
    }

    eod_stock_dict = {
        key: df.assign(
            trend_5p=(df["close"] > ((df["high5"] + df["low5"]) / 2).shift(1)).astype(
                int
            ),
            trend_20p=(
                df["close"] > ((df["high20"] + df["low20"]) / 2).shift(1)
            ).astype(int),
            trend_60p=(
                df["close"] > ((df["high60"] + df["low60"]) / 2).shift(1)
            ).astype(int),
            trend_120p=(
                df["close"] > ((df["high120"] + df["low120"]) / 2).shift(1)
            ).astype(int),
            trend_240p=(
                df["close"] > ((df["high240"] + df["low240"]) / 2).shift(1)
            ).astype(int),
            trend_480p=(
                df["close"] > ((df["high480"] + df["low480"]) / 2).shift(1)
            ).astype(int),
        )
        for key, df in eod_stock_dict.items()
    }
    eod_stock_dict = {
        k: v.sort_values(by=["date"], ascending=False).reset_index(drop=True)
        for k, v in eod_stock_dict.items()
    }

    # Gán các đường trung bình và MA sang bảng dữ liệu ITD
    for stock, df in itd_stock_dict.items():
        temp_data = eod_stock_dict[stock][
            [
                "high5",
                "low5",
                "high20",
                "low20",
                "high60",
                "low60",
                "high120",
                "low120",
                "high240",
                "low240",
                "high480",
                "low480",
            ]
        ].iloc[0]
        itd_stock_dict[stock] = df.assign(**temp_data)

    itd_stock_dict = {
        k: v.sort_values(by=["date"], ascending=True).reset_index(drop=True)
        for k, v in itd_stock_dict.items()
    }
    itd_stock_dict = {
        key: df.assign(
            trend_5p=(df["close"] > ((df["high5"] + df["low5"]) / 2).shift(1)).astype(
                int
            ),
            trend_20p=(
                df["close"] > ((df["high20"] + df["low20"]) / 2).shift(1)
            ).astype(int),
            trend_60p=(
                df["close"] > ((df["high60"] + df["low60"]) / 2).shift(1)
            ).astype(int),
            trend_120p=(
                df["close"] > ((df["high120"] + df["low120"]) / 2).shift(1)
            ).astype(int),
            trend_240p=(
                df["close"] > ((df["high240"] + df["low240"]) / 2).shift(1)
            ).astype(int),
            trend_480p=(
                df["close"] > ((df["high480"] + df["low480"]) / 2).shift(1)
            ).astype(int),
        )
        for key, df in itd_stock_dict.items()
    }
    itd_stock_dict = {
        k: v.sort_values(by=["date"], ascending=False).reset_index(drop=True)
        for k, v in itd_stock_dict.items()
    }

    # Xoá các cổ phiếu chưa có giao dịch trong ngày
    delete_stock = []
    for stock, df in eod_stock_dict.items():
        if date_series["date"].iloc[0] != df["date"].iloc[0]:
            delete_stock.append(stock)
    for stock in delete_stock:
        try:
            itd_stock_dict.pop(stock)
            eod_stock_dict.pop(stock)
        except:
            eod_stock_dict.pop(stock)

    # Xoá các cổ phiếu có giá bị lỗi bằng 0
    delete_stock = []
    for stock, df in eod_stock_dict.items():
        if df["close"].min() == 0:
            delete_stock.append(stock)
    for stock in delete_stock:
        try:
            itd_stock_dict.pop(stock)
            eod_stock_dict.pop(stock)
        except:
            eod_stock_dict.pop(stock)

    # Tính hệ số thanh khoản và đổi lại cap của cổ phiếu thành cap trung bình trong 20 phiên
    for df in eod_stock_dict.values():
        df["liquid_ratio"] = df["volume"] / (df["ma5_V"])
        df["liquid_ratio"].iloc[0] = df["volume"].iloc[0] / (
            (df["ma5_V"]).iloc[0] * current_time_percent
        )
        df["cap"] = df["cap"][::-1].rolling(window=20).mean()[::-1]

    # #### Phân nhóm cổ phiếu

    stock_classification = pd.read_excel("data/t2m_classification.xlsx")
    stock_classification = stock_classification[
        stock_classification["stock"].isin(list(eod_stock_dict.keys()))
    ]

    # Tạo ngày đầu tiên của tháng hiện tại
    first_day_of_month = date_series[
        date_series["date"]
        > pd.Timestamp(
            date_series["date"].iloc[0].year, date_series["date"].iloc[0].month, 1
        )
    ]["date"].iloc[-1]

    # Tạo các mảng dữ liệu vốn hoá và giá của phiên đầu tiên hàng tháng
    price_arr = []
    cap_arr = []
    for stock, df in eod_stock_dict.items():
        if len(df[df["date"] == first_day_of_month]) > 0:
            price_arr.append(df[df["date"] == first_day_of_month]["close"].item())
            cap_arr.append(df[df["date"] == first_day_of_month]["cap"].iloc[0].item())
        else:
            price_arr.append(df["close"].iloc[0].item())
            cap_arr.append(df["cap"].iloc[0].item())

    # Tạo bảng chia nhóm vốn hoá
    vonhoa_classification_df = stock_classification.copy()
    vonhoa_classification_df["price"] = price_arr
    vonhoa_classification_df["cap"] = cap_arr

    cap_coef = sum(cap_arr) / 10000
    vonhoa_classification_df["marketcap_group"] = vonhoa_classification_df.apply(
        lambda x: (
            "small"
            if ((x["cap"] > cap_coef) & (x["cap"] < 10 * cap_coef))
            | (
                (x["cap"] >= 10 * cap_coef)
                & (x["cap"] < 20 * cap_coef)
                & (x["price"] < 10)
            )
            else (
                "mid"
                if (
                    (x["cap"] >= 10 * cap_coef)
                    & (x["cap"] < 20 * cap_coef)
                    & (x["price"] >= 10)
                )
                | ((x["cap"] >= 20 * cap_coef) & (x["cap"] < 100 * cap_coef))
                else ("large" if x["cap"] >= 100 * cap_coef else "penny")
            )
        ),
        axis=1,
    )

    stock_classification = pd.concat(
        [stock_classification, vonhoa_classification_df["marketcap_group"]], axis=1
    )

    # Convert DataFrame columns to dictionaries for quick access
    stock_by_industry = stock_classification.set_index("stock")[
        "industry_name"
    ].to_dict()
    stock_by_perform = stock_classification.set_index("stock")[
        "industry_perform"
    ].to_dict()
    stock_by_marketcap = stock_classification.set_index("stock")[
        "marketcap_group"
    ].to_dict()

    # Initialize dictionaries
    eod_all_stock = {}
    itd_all_stock = {}
    eod_industry_name = {}
    itd_industry_name = {}
    eod_industry_perform = {}
    itd_industry_perform = {}
    eod_marketcap_group = {}
    itd_marketcap_group = {}

    # Function to create mappings based on category
    def create_mapping(stock_dict, category_dict):
        category_map = {}
        for category, stocks in category_dict.items():
            category_map[category] = {
                stock: stock_dict[stock] for stock in stocks if stock in stock_dict
            }
        return category_map

    # Precompute unique categories and relevant stocks
    unique_industries = np.unique(list(stock_by_industry.values()))
    unique_performs = np.unique(list(stock_by_perform.values()))
    unique_marketcaps = ["large", "mid", "small", "penny"]

    # Mapping for all_stock
    itd_all_stock["all_stock"] = {key: value for key, value in itd_stock_dict.items()}
    eod_all_stock["all_stock"] = {key: value for key, value in eod_stock_dict.items()}

    # Mapping for industry
    for industry in unique_industries:
        relevant_stocks = [
            stock for stock, ind in stock_by_industry.items() if ind == industry
        ]
        eod_industry_name[industry] = {
            stock: eod_stock_dict[stock]
            for stock in relevant_stocks
            if stock in eod_stock_dict
        }
        itd_industry_name[industry] = {
            stock: itd_stock_dict[stock]
            for stock in relevant_stocks
            if stock in itd_stock_dict
        }

    # Mapping for performance
    for performance in unique_performs:
        relevant_stocks = [
            stock for stock, perf in stock_by_perform.items() if perf == performance
        ]
        eod_industry_perform[performance] = {
            stock: eod_stock_dict[stock]
            for stock in relevant_stocks
            if stock in eod_stock_dict
        }
        itd_industry_perform[performance] = {
            stock: itd_stock_dict[stock]
            for stock in relevant_stocks
            if stock in itd_stock_dict
        }

    # Mapping for marketcap
    for marketcap in unique_marketcaps:
        relevant_stocks = [
            stock for stock, mcap in stock_by_marketcap.items() if mcap == marketcap
        ]
        eod_marketcap_group[marketcap] = {
            stock: eod_stock_dict[stock]
            for stock in relevant_stocks
            if stock in eod_stock_dict
        }
        itd_marketcap_group[marketcap] = {
            stock: itd_stock_dict[stock]
            for stock in relevant_stocks
            if stock in itd_stock_dict
        }

    group_stock_list = (
        ["all_stock"]
        + stock_classification["industry_name"].unique().tolist()
        + stock_classification["industry_perform"].unique().tolist()
        + stock_classification["marketcap_group"].unique().tolist()
    )

    # Tạo bảng để slicer các nhóm cổ phiếu
    group_slicer_df = pd.DataFrame(group_stock_list).rename(columns={0: "name"})
    group_slicer_df["order"] = group_slicer_df["name"].map(order_map_dict)
    group_slicer_df["group"] = group_slicer_df["name"].map(group_map_dict)
    group_slicer_df["name"] = group_slicer_df["name"].map(name_map_dict)

    # #### Biểu đồ cấu trúc sóng

    import pandas as pd

    def transform_ms(stock_group):
        stock_dict = copy.deepcopy(stock_group)

        # Prepare a base date DataFrame from date_series
        dates_df = pd.DataFrame(date_series["date"].tolist(), columns=["date"])

        for group_name, stocks in stock_dict.items():
            # Initialize a DataFrame for group trends
            group_trends = dates_df.copy()

            # Compute trends across stocks
            for trend in [
                "trend_5p",
                "trend_20p",
                "trend_60p",
                "trend_120p",
                "trend_240p",
                "trend_480p",
            ]:
                # Concatenate all trend data for current trend across all stocks
                trend_data = pd.concat(
                    [stocks[stock][trend] for stock in stocks], axis=1
                )
                trend_data.fillna(0, inplace=True)

                # Calculate the sum and percent for the trend
                sum_trend = trend_data.sum(axis=1)
                percent_trend = sum_trend / len(stocks)

                # Add to group trends DataFrame
                group_trends[f"{trend}"] = percent_trend

            # Sort the DataFrame by date and limit to the last 60 entries
            stock_dict[group_name] = group_trends.sort_values(
                "date", ascending=False
            ).iloc[:60]

        return stock_dict

    # Tính toán các biểu đồ MS cho các nhóm cổ phiếu
    all_stock_ms = transform_ms(eod_all_stock)
    industry_name_ms = transform_ms(eod_industry_name)
    industry_perform_ms = transform_ms(eod_industry_perform)
    marketcap_group_ms = transform_ms(eod_marketcap_group)

    # Gộp tất cả biểu đồ MS vào 1 bảng
    market_ms = pd.DataFrame()
    for item in [
        all_stock_ms,
        industry_name_ms,
        industry_perform_ms,
        marketcap_group_ms,
    ]:
        for group, df in item.items():
            df["name"] = group
            market_ms = pd.concat([market_ms, df], axis=0)

    market_ms["name"] = market_ms["name"].map(name_map_dict)

    # #### Điểm dòng tiền từng cổ phiếu

    # - Điểm dòng tiền EOD

    eod_stock_dict = {
        k: v.iloc[:60].reset_index(drop=True) for k, v in eod_stock_dict.items()
    }
    date_series = date_series.iloc[:60]

    def score_calculation(df):
        try:
            result = (
                ((df["close"] - df["low"]) - (df["high"] - df["close"]))
                / (df["high"] - df["low"])
                * abs((df["close"] - df["close_prev"]))
                / df["close_prev"]
                * (df["volume"] * df["close"])
                / (df["ma5_prev"] * df["ma5_V"])
            ) * 100 + (
                (df["volume"] * df["close"]) / (df["ma5_prev"] * df["ma5_V"])
            ) / 100
            result.fillna(0, inplace=True)
            return result
        except ZeroDivisionError:
            # return 0
            return ((df["volume"] * df["close"]) / (df["ma5_prev"] * df["ma5_V"])) / 100

    # Tính toán các cột cần thiết để lọc danh sách cổ phiếu dòng tiền
    raw_eod_score_dict = {}
    for stock in eod_stock_dict.keys():
        raw_eod_score_dict[stock] = eod_stock_dict[stock]
        [
            [
                "stock",
                "date",
                "high",
                "low",
                "close",
                "volume",
                "liquid_ratio",
                "cap",
                "ma5_V",
                "ma20_V",
                "ma60_V",
                "ma120_V",
                "ma5",
            ]
        ]

        raw_eod_score_dict[stock]["ma5_prev"] = raw_eod_score_dict[stock]["ma5"].shift(
            -1
        )
        raw_eod_score_dict[stock]["close_prev"] = raw_eod_score_dict[stock][
            "close"
        ].shift(-1)

        raw_eod_score_dict[stock]["raw_score"] = score_calculation(
            raw_eod_score_dict[stock]
        )
        raw_eod_score_dict[stock]["raw_score"].iloc[0] = (
            raw_eod_score_dict[stock]["raw_score"].iloc[0].item() / current_time_percent
        )

        raw_eod_score_dict[stock]["highest_price"] = (
            raw_eod_score_dict[stock]["close"][::-1]
            .rolling(window=40, min_periods=1)
            .max()[::-1]
        )
        raw_eod_score_dict[stock]["lowest_volume60"] = (
            raw_eod_score_dict[stock]["volume"][::-1]
            .rolling(window=60, min_periods=1)
            .min()
            .shift(1)[::-1]
        )
        raw_eod_score_dict[stock]["mean_volume20"] = (
            raw_eod_score_dict[stock]["volume"][::-1]
            .rolling(window=20, min_periods=1)
            .mean()
            .shift(1)[::-1]
        )

    # Lọc danh sách cổ phiếu dòng tiền
    eod_score_dict = {
        stock: df[
            [
                "stock",
                "date",
                "close",
                "low",
                "high",
                "volume",
                "liquid_ratio",
                "raw_score",
                "cap",
            ]
        ]
        for stock, df in raw_eod_score_dict.items()
        if all(
            [
                df["ma5_V"][0] >= 50000,
                df["ma20_V"][0] >= 50000,
                df["ma60_V"][0] >= 50000,
                df["ma120_V"][0] >= 50000,
                df["lowest_volume60"][0] > 0,
                df["mean_volume20"][0] >= 50000,
                df["close"][0] > df["highest_price"][0] * 0.382,
            ]
        )
    }

    stock_classification_filtered = stock_classification[
        stock_classification["stock"].isin(eod_score_dict.keys())
    ].reset_index(drop=True)

    for stock in eod_score_dict.keys():
        nganh = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["industry_name"].item()
        marketcap = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["marketcap_group"].item()

        eod_score_dict[stock]["t0_score"] = eod_score_dict[stock]["raw_score"]

        eod_score_dict[stock].sort_values("date", ascending=True, inplace=True)
        eod_score_dict[stock]["t5_score"] = (
            eod_score_dict[stock]["t0_score"].rolling(window=5, min_periods=1).mean()
        )
        eod_score_dict[stock].sort_values("date", ascending=False, inplace=True)

        eod_score_dict[stock]["industry_name"] = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["industry_name"].item()
        eod_score_dict[stock]["industry_perform"] = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["industry_perform"].item()
        eod_score_dict[stock]["stock_perform"] = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["stock_perform"].item()
        eod_score_dict[stock]["marketcap_group"] = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["marketcap_group"].item()
        eod_score_dict[stock]["t2m_select"] = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["t2m_select"].item()

    group_score = date_series.copy()
    ranking_group = date_series.copy()

    # Xếp hạng T5
    for stock in eod_score_dict.keys():
        group_score[stock] = eod_score_dict[stock]["t5_score"]
        group_score.fillna(0, inplace=True)
        ranking_group[stock] = 0
    ranking_group = group_score.iloc[:, 1:].rank(ascending=False, method="min", axis=1)

    for stock, df in eod_score_dict.items():
        df["price_change"] = df["close"][::-1].pct_change()[::-1]
        df["value_change"] = df["close"][::-1].diff()[::-1]
        df["rank"] = ranking_group[stock]
        df["rank_prev"] = df["rank"].shift(-1)
        df["rank_change"] = df["rank_prev"] - df["rank"]

    # Xếp hạng T0
    for stock in eod_score_dict.keys():
        group_score[stock] = eod_score_dict[stock]["t0_score"]
        group_score.fillna(0, inplace=True)
        ranking_group[stock] = 0
    ranking_group = group_score.iloc[:, 1:].rank(ascending=False, method="min", axis=1)

    for stock, df in eod_score_dict.items():
        df["rank_t0"] = ranking_group[stock]
        df["rank_t0_prev"] = df["rank_t0"].shift(-1)

    # Check xem xếp hạng T0 nằm trong top 10% hay không
    for stock, df in eod_score_dict.items():
        df["top_check"] = df["rank_t0"].apply(
            lambda x: 1 if x <= len(stock_classification_filtered) * 0.1 else 0
        )
        df["top_count"] = df["top_check"][::-1].rolling(window=20).sum()[::-1]

    eod_score_dict = {
        k: v.drop(columns=["raw_score", "rank_t0_prev", "rank_prev", "top_check"])
        for k, v in eod_score_dict.items()
    }

    # Tạo bảng tổng hợp điểm t0 của tất cả cổ phiếu
    eod_score_df = pd.DataFrame(stock_classification_filtered["stock"])

    score_list = []
    for stock, df in eod_score_dict.items():
        score_list.append(df.iloc[0])

    eod_score_df = (
        pd.DataFrame(score_list)
        .sort_values("t0_score", ascending=False)
        .reset_index(drop=True)
    )
    eod_score_df = eod_score_df.fillna("")

    eod_score_df["filter_t0"] = eod_score_df["t0_score"].apply(
        lambda x: "Tiền vào" if x >= 0 else "Tiền ra"
    )
    eod_score_df["filter_t5"] = eod_score_df["t5_score"].apply(
        lambda x: "Tiền vào" if x >= 0 else "Tiền ra"
    )
    eod_score_df["filter_liquid"] = eod_score_df["liquid_ratio"].apply(
        lambda x: (
            "<50%"
            if x < 0.6
            else (
                "50%-100%"
                if (x >= 0.5) & (x < 1)
                else (
                    "100%-150%"
                    if (x >= 1) & (x < 1.5)
                    else ("150%-200%" if (x >= 1.5) & (x < 2) else ">200%")
                )
            )
        )
    )
    eod_score_df["order_filter_liquid"] = eod_score_df["filter_liquid"].apply(
        lambda x: (
            1
            if x == "<50%"
            else (
                2
                if x == "50%-100%"
                else (3 if x == "100%-150%" else (4 if x == "150%-200%" else 5))
            )
        )
    )
    eod_score_df["filter_rank"] = eod_score_df["rank"].apply(
        lambda x: (
            "1-50"
            if x <= 50
            else (
                "51-150"
                if (x > 50) & (x <= 150)
                else ("151-250" if (x > 150) & (x <= 250) else ">250")
            )
        )
    )
    eod_score_df["order_filter_rank"] = eod_score_df["filter_rank"].apply(
        lambda x: (
            1 if x == "1-50" else (2 if x == "51-150" else (3 if x == "151-250" else 4))
        )
    )

    eod_score_df["industry_name"] = eod_score_df["industry_name"].map(name_map_dict)
    eod_score_df["industry_perform"] = eod_score_df["industry_perform"].map(
        name_map_dict
    )
    eod_score_df["marketcap_group"] = eod_score_df["marketcap_group"].map(name_map_dict)

    # - Điểm dòng tiền ITD

    # Giả định date_series và itd_stock_dict đã được định nghĩa
    hsx_itd_start = pd.Timestamp(
        date_series["date"].iloc[0].replace(hour=9, minute=15, second=0, microsecond=0)
    )

    # Danh sách stock từ stock_classification_filtered và danh sách HSX stocks
    filtered_stocks = stock_classification_filtered["stock"].tolist()
    hsx_stocks = stock_classification[stock_classification["exchange"] == "HSX"][
        "stock"
    ].tolist()

    # Lọc và cập nhật itd_score_dict trong một bước
    itd_score_dict = {
        k: v.loc[
            v["date"]
            >= (hsx_itd_start if k in hsx_stocks else date_series["date"].iloc[0])
        ]
        for k, v in copy.deepcopy(itd_stock_dict).items()
        if k in filtered_stocks
    }

    for stock, df in itd_score_dict.items():

        df["ma5_V"] = time_percent["percent"] * (
            raw_eod_score_dict[stock]["ma5_V"].iloc[0]
        )
        df["ma5_prev"] = raw_eod_score_dict[stock]["ma5_prev"].iloc[0]
        df["close_prev"] = raw_eod_score_dict[stock]["close_prev"].iloc[0]
        df["cap"] = raw_eod_score_dict[stock]["cap"].iloc[0]

        df["high"] = df["high"][::-1].cummax()[::-1]
        df["low"] = df["low"][::-1].cummin()[::-1]
        df["volume"] = df["volume"][::-1].cumsum()[::-1]
        df["liquid_ratio"] = df["volume"] / df["ma5_V"]

        df.loc[0, "volume"] = raw_eod_score_dict[stock]["volume"].iloc[0]
        df.loc[0, "close"] = raw_eod_score_dict[stock]["close"].iloc[0]
        df.loc[0, "low"] = raw_eod_score_dict[stock]["low"].iloc[0]
        df.loc[0, "high"] = raw_eod_score_dict[stock]["high"].iloc[0]

        df["raw_score"] = score_calculation(df)

    for stock in itd_score_dict.keys():
        nganh = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["industry_name"].item()
        marketcap = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["marketcap_group"].item()

        itd_score_dict[stock]["t0_score"] = itd_score_dict[stock]["raw_score"]

        itd_score_dict[stock]["price_change"] = (
            itd_score_dict[stock]["close"] - eod_stock_dict[stock]["open"].iloc[0]
        ) / eod_stock_dict[stock]["open"].iloc[0]
        itd_score_dict[stock]["industry_name"] = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["industry_name"].item()
        itd_score_dict[stock]["industry_perform"] = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["industry_perform"].item()
        itd_score_dict[stock]["stock_perform"] = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["stock_perform"].item()
        itd_score_dict[stock]["marketcap_group"] = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["marketcap_group"].item()
        itd_score_dict[stock]["t2m_select"] = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["t2m_select"].item()

    itd_score_dict = {
        k: v[
            [
                "stock",
                "date",
                "close",
                "volume",
                "t0_score",
                "liquid_ratio",
                "industry_name",
                "industry_perform",
                "stock_perform",
                "marketcap_group",
                "t2m_select",
                "price_change",
            ]
        ]
        for k, v in itd_score_dict.items()
    }

    # #### Điểm dòng tiền nhóm cổ phiếu

    # - Các hàm tính toán

    # Chỉnh sửa lại điểm dòng tiền t0 cho từng cổ phiếu với tác động của độ rộng từng nhóm
    def adjust_score_by_breath(t0_score, ratio_column):
        adjusted_score = []
        for score, ratio in zip(t0_score, ratio_column):
            if score >= 0:
                adjusted_score.append(score * ratio)
            else:
                adjusted_score.append(score * (1 - ratio))
        return adjusted_score

    # Hàm điều chỉnh điểm dòng tiền của cổ phiếu tránh sự đột biến khi đóng góp vào nhóm chung
    def adjust_score_for_smooth(row, column_name, max_percent, mark):
        origin_score = row[column_name]

        if abs(origin_score) > row["total"] * max_percent:

            sum_abs = row["total"] - abs(row[column_name])
            fixed_score = sum_abs / (1 - max_percent) - sum_abs

            if origin_score >= 0:
                return fixed_score
            else:
                return -fixed_score
        else:
            mark[0] = 0
            return origin_score

    # Áp dụng hàm điều chỉnh điểm phía trên vào các nhóm cổ phiếu, việc này lặp lại nhiều lần cho tới khi triệt tiêu sự đột biến
    def apply_smooth_score(group_stock, group_name, type_name):
        if type_name == "itd":
            initial_score_df = time_series.copy()
            score_dict = itd_score_dict
        elif type_name == "eod":
            score_dict = eod_score_dict
            initial_score_df = date_series.copy()

        for key in group_stock.keys():

            score_df = initial_score_df.copy()
            current_stock_list = list(score_dict.keys())

            if group_name == "all_stock":
                temp_stock_list_full = stock_classification_filtered["stock"].tolist()
                temp_stock_list = list(
                    set(temp_stock_list_full) & set(current_stock_list)
                )
            else:
                temp_stock_list_full = stock_classification_filtered[
                    stock_classification_filtered[f"{group_name}"] == key
                ]["stock"].tolist()
                temp_stock_list = list(
                    set(temp_stock_list_full) & set(current_stock_list)
                )

            for stock in temp_stock_list:
                try:
                    score_df[stock] = score_dict[stock][f"t0_score"]
                except:
                    pass

            max_percent = max(0.1, min(5 * (1 / len(temp_stock_list)), 0.5))
            score_df["total"] = score_df.iloc[:, 1:].abs().sum(axis=1)

            mark = [1]
            while True:
                if mark[0] == 1:
                    for stock in temp_stock_list:
                        score_df[stock] = score_df.iloc[:, 1:].apply(
                            adjust_score_for_smooth,
                            axis=1,
                            args=(stock, max_percent, mark),
                        )
                if mark[0] == 0:
                    break

            for stock in temp_stock_list:
                try:
                    score_dict[stock][f"t0_{group_name}"] = score_df[stock]
                except:
                    pass

    # - Dòng tiền vào nhóm cổ phiếu EOD

    # Loại bỏ các giá trị điểm đột biến của các cổ phiếu khi đóng góp vào điểm dòng tiền ngành
    apply_smooth_score(eod_industry_name, "industry_name", "eod")
    apply_smooth_score(eod_industry_perform, "industry_perform", "eod")
    apply_smooth_score(eod_marketcap_group, "marketcap_group", "eod")
    apply_smooth_score(eod_all_stock, "all_stock", "eod")

    # Tính độ rộng cho từng phiên phục vụ cho việc điều chỉnh điểm dòng tiền
    temp_df = date_series.copy()
    for stock, df in eod_score_dict.items():
        temp_df[stock] = eod_score_dict[stock]["t0_score"]
    temp_df.iloc[:, 1:] = temp_df.iloc[:, 1:].applymap(lambda x: 1 if x > 0 else 0)

    eod_market_breath = date_series.copy()

    industry_name_breadth_dict = {}
    for key in eod_industry_name.keys():
        stock_list = stock_classification_filtered[
            stock_classification_filtered["industry_name"] == key
        ]["stock"].tolist()
        industry_name_breadth_dict[key] = temp_df[
            ["date"] + [columns for columns in stock_list]
        ]
        eod_market_breath[key] = industry_name_breadth_dict[key].iloc[:, 1:].sum(
            axis=1
        ) / len(stock_list)

    industry_perform_breadth_dict = {}
    for key in eod_industry_perform.keys():
        stock_list = stock_classification_filtered[
            stock_classification_filtered["industry_perform"] == key
        ]["stock"].tolist()
        industry_perform_breadth_dict[key] = temp_df[
            ["date"] + [columns for columns in stock_list]
        ]
        eod_market_breath[key] = industry_perform_breadth_dict[key].iloc[:, 1:].sum(
            axis=1
        ) / len(stock_list)

    marketcap_group_breadth_dict = {}
    for key in eod_marketcap_group.keys():
        stock_list = stock_classification_filtered[
            stock_classification_filtered["marketcap_group"] == key
        ]["stock"].tolist()
        marketcap_group_breadth_dict[key] = temp_df[
            ["date"] + [columns for columns in stock_list]
        ]
        eod_market_breath[key] = marketcap_group_breadth_dict[key].iloc[:, 1:].sum(
            axis=1
        ) / len(stock_list)

    all_stock_breadth_dict = {}
    for key in eod_all_stock.keys():
        stock_list = stock_classification_filtered["stock"].tolist()
        all_stock_breadth_dict[key] = temp_df[
            ["date"] + [columns for columns in stock_list]
        ]
        eod_market_breath[key] = all_stock_breadth_dict[key].iloc[:, 1:].sum(
            axis=1
        ) / len(stock_list)

    # Chỉnh sửa lại điểm dòng tiền t0 cho từng cổ phiếu với tác động của độ rộng từng nhóm
    for stock, df in eod_score_dict.items():
        name_of_industry_name = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["industry_name"].item()
        name_of_industry_perform = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["industry_perform"].item()
        name_of_marketcap_group = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["marketcap_group"].item()

        df[f"t0_industry_name"] = adjust_score_by_breath(
            df["t0_industry_name"], eod_market_breath[name_of_industry_name]
        )
        df[f"t0_industry_perform"] = adjust_score_by_breath(
            df["t0_industry_perform"], eod_market_breath[name_of_industry_perform]
        )
        df[f"t0_marketcap_group"] = adjust_score_by_breath(
            df["t0_marketcap_group"], eod_market_breath[name_of_marketcap_group]
        )
        df[f"t0_all_stock"] = adjust_score_by_breath(
            df["t0_all_stock"], eod_market_breath["all_stock"]
        )

    # Tạo bảng dữ liệu điểm dòng tiền cho các nhóm cổ phiếu
    eod_group_score_df = date_series.copy()

    # Thêm cột điểm dòng tiền toàn bộ cổ phiếu
    for nganh in eod_all_stock.keys():
        score_df = date_series.copy()
        for stock in stock_classification_filtered["stock"]:
            score_df[stock] = eod_score_dict[stock]["t0_all_stock"]
        score_df["total"] = score_df.iloc[:, 1:].mean(axis=1)
        eod_group_score_df[nganh] = score_df["total"]

    # Thêm các cột điểm dòng tiền ngành
    eod_industry_name_score_df = date_series.copy()
    for nganh in eod_industry_name.keys():
        score_df = date_series.copy()
        for stock in stock_classification_filtered[
            stock_classification_filtered["industry_name"] == nganh
        ]["stock"]:
            score_df[stock] = eod_score_dict[stock]["t0_industry_name"]
        score_df["total"] = score_df.iloc[:, 1:].mean(axis=1)
        eod_group_score_df[nganh] = score_df["total"]

    # Thêm các cột điểm dòng tiền nhóm hiệu suất
    eod_industry_perform_score_df = date_series.copy()
    for group in eod_industry_perform.keys():
        score_df = date_series.copy()
        for stock in stock_classification_filtered[
            stock_classification_filtered["industry_perform"] == group
        ]["stock"]:
            score_df[stock] = eod_score_dict[stock]["t0_industry_perform"]
        score_df["total"] = score_df.iloc[:, 1:].mean(axis=1)
        eod_group_score_df[group] = score_df["total"]

    # Thêm các cột điểm dòng tiền nhóm vốn hoá
    eod_marketcap_group_score_df = date_series.copy()
    for marketcap in eod_marketcap_group.keys():
        score_df = date_series.copy()
        for stock in stock_classification_filtered[
            stock_classification_filtered["marketcap_group"] == marketcap
        ]["stock"]:
            score_df[stock] = eod_score_dict[stock]["t0_marketcap_group"]
        score_df["total"] = score_df.iloc[:, 1:].mean(axis=1)
        eod_group_score_df[marketcap] = score_df["total"]

    eod_group_score_df["week"] = eod_group_score_df["date"].dt.strftime("%U-%Y")
    eod_group_score_df["month"] = eod_group_score_df["date"].dt.strftime("%m-%Y")
    eod_group_score_df["week_day"] = eod_group_score_df["date"].dt.day_name()
    eod_group_score_df["day_num"] = eod_group_score_df["date"].dt.day

    # - Dòng tiền vào nhóm cổ phiếu ITD

    # Loại bỏ các giá trị điểm đột biến của cá cổ phiếu khi đóng góp vào điểm dòng tiền ngành
    apply_smooth_score(itd_industry_name, "industry_name", "itd")
    apply_smooth_score(itd_industry_perform, "industry_perform", "itd")
    apply_smooth_score(itd_marketcap_group, "marketcap_group", "itd")
    apply_smooth_score(itd_all_stock, "all_stock", "itd")

    # Tính độ rộng cho từng phiên phục vụ cho việc điều chỉnh điểm dòng tiền
    temp_df = time_series.copy()
    for stock, df in itd_score_dict.items():
        temp_df[stock] = itd_score_dict[stock]["t0_score"]
    temp_df.iloc[:, 1:] = temp_df.iloc[:, 1:].applymap(lambda x: 1 if x > 0 else 0)

    itd_market_breath = time_series.copy()
    current_stock_list = list(itd_score_dict.keys())

    industry_name_breadth_dict = {}
    for key in itd_industry_name.keys():
        temp_stock_list_full = stock_classification_filtered[
            stock_classification_filtered["industry_name"] == key
        ]["stock"].tolist()
        stock_list = list(set(temp_stock_list_full) & set(current_stock_list))

        industry_name_breadth_dict[key] = temp_df[
            ["date"] + [columns for columns in stock_list]
        ]
        itd_market_breath[key] = industry_name_breadth_dict[key].iloc[:, 1:].sum(
            axis=1
        ) / len(stock_list)

    industry_perform_breadth_dict = {}
    for key in itd_industry_perform.keys():
        temp_stock_list_full = stock_classification_filtered[
            stock_classification_filtered["industry_perform"] == key
        ]["stock"].tolist()
        stock_list = list(set(temp_stock_list_full) & set(current_stock_list))

        industry_perform_breadth_dict[key] = temp_df[
            ["date"] + [columns for columns in stock_list]
        ]
        itd_market_breath[key] = industry_perform_breadth_dict[key].iloc[:, 1:].sum(
            axis=1
        ) / len(stock_list)

    marketcap_group_breadth_dict = {}
    for key in itd_marketcap_group.keys():
        temp_stock_list_full = stock_classification_filtered[
            stock_classification_filtered["marketcap_group"] == key
        ]["stock"].tolist()
        stock_list = list(set(temp_stock_list_full) & set(current_stock_list))

        marketcap_group_breadth_dict[key] = temp_df[
            ["date"] + [columns for columns in stock_list]
        ]
        itd_market_breath[key] = marketcap_group_breadth_dict[key].iloc[:, 1:].sum(
            axis=1
        ) / len(stock_list)

    all_stock_breadth_dict = {}
    for key in itd_all_stock.keys():
        temp_stock_list_full = stock_classification_filtered["stock"].tolist()
        stock_list = list(set(temp_stock_list_full) & set(current_stock_list))

        all_stock_breadth_dict[key] = temp_df[
            ["date"] + [columns for columns in stock_list]
        ]
        itd_market_breath[key] = all_stock_breadth_dict[key].iloc[:, 1:].sum(
            axis=1
        ) / len(stock_list)

    # Chỉnh sửa lại điểm dòng tiền t0 cho từng cổ phiếu với tác động của độ rộng từng nhóm

    for stock, df in itd_score_dict.items():

        name_of_industry_name = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["industry_name"].item()
        name_of_industry_perform = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["industry_perform"].item()
        name_of_marketcap_group = stock_classification_filtered[
            stock_classification_filtered["stock"] == stock
        ]["marketcap_group"].item()

        df["t0_industry_name"] = adjust_score_by_breath(
            df["t0_industry_name"], itd_market_breath[name_of_industry_name]
        )
        df["t0_industry_perform"] = adjust_score_by_breath(
            df["t0_industry_perform"], itd_market_breath[name_of_industry_perform]
        )
        df["t0_marketcap_group"] = adjust_score_by_breath(
            df["t0_marketcap_group"], itd_market_breath[name_of_marketcap_group]
        )
        df["t0_all_stock"] = adjust_score_by_breath(
            df["t0_all_stock"], itd_market_breath["all_stock"]
        )

    # Tạo bảng dữ liệu điểm dòng tiền cho các nhóm cổ phiếu
    itd_group_score_df = time_series.copy()
    current_stock_list = list(itd_score_dict.keys())

    # Thêm cột điểm dòng tiền toàn bộ cổ phiếu
    for nganh in itd_all_stock.keys():
        score_df = time_series.copy()
        temp_stock_list_full = stock_classification_filtered["stock"].tolist()
        stock_list = list(set(temp_stock_list_full) & set(current_stock_list))

        for stock in stock_list:
            score_df[stock] = itd_score_dict[stock]["t0_all_stock"]
        score_df["total"] = score_df.iloc[:, 1:].mean(axis=1)
        itd_group_score_df[nganh] = score_df["total"]

    # Thêm các cột điểm dòng tiền ngành
    itd_industry_name_score_df = time_series.copy()
    for nganh in itd_industry_name.keys():
        score_df = time_series.copy()
        temp_stock_list_full = stock_classification_filtered[
            stock_classification_filtered["industry_name"] == nganh
        ]["stock"].tolist()
        stock_list = list(set(temp_stock_list_full) & set(current_stock_list))

        for stock in stock_list:
            score_df[stock] = itd_score_dict[stock]["t0_industry_name"]
        score_df["total"] = score_df.iloc[:, 1:].mean(axis=1)
        itd_group_score_df[nganh] = score_df["total"]

    # Thêm các cột điểm dòng tiền nhóm hiệu suất
    itd_industry_perform_score_df = time_series.copy()
    for group in itd_industry_perform.keys():
        score_df = time_series.copy()
        temp_stock_list_full = stock_classification_filtered[
            stock_classification_filtered["industry_perform"] == group
        ]["stock"].tolist()
        stock_list = list(set(temp_stock_list_full) & set(current_stock_list))

        for stock in stock_list:
            score_df[stock] = itd_score_dict[stock]["t0_industry_perform"]
        score_df["total"] = score_df.iloc[:, 1:].mean(axis=1)
        itd_group_score_df[group] = score_df["total"]

    # Thêm các cột điểm dòng tiền nhóm vốn hoá
    itd_marketcap_group_score_df = time_series.copy()
    for marketcap in itd_marketcap_group.keys():
        score_df = time_series.copy()
        temp_stock_list_full = stock_classification_filtered[
            stock_classification_filtered["marketcap_group"] == marketcap
        ]["stock"].tolist()
        stock_list = list(set(temp_stock_list_full) & set(current_stock_list))

        for stock in stock_list:
            score_df[stock] = itd_score_dict[stock]["t0_marketcap_group"]
        score_df["total"] = score_df.iloc[:, 1:].mean(axis=1)
        itd_group_score_df[marketcap] = score_df["total"]

    # #### Hệ số thanh khoản cho nhóm cổ phiếu

    # - Hệ số thanh khoản nhóm cổ phiếu EOD

    eod_group_liquidity_df = date_series.copy()

    for name in eod_all_stock.keys():
        temp_volume_df = date_series.copy()
        for stock, df in eod_all_stock[name].items():
            temp_volume_df[stock] = df["volume"]
        temp_volume_df["volume"] = temp_volume_df.iloc[:, 1:].sum(axis=1)
        temp_volume_df["ma5_V"] = (
            temp_volume_df["volume"][::-1].shift(1).rolling(window=5).mean()[::-1]
        )
        temp_volume_df.loc[0, "ma5_V"] = (
            temp_volume_df["ma5_V"].iloc[0] * current_time_percent
        )
        temp_volume_df["ratio"] = temp_volume_df["volume"] / temp_volume_df["ma5_V"]
        eod_group_liquidity_df[name] = temp_volume_df["ratio"]

    for name in eod_industry_name.keys():
        temp_volume_df = date_series.copy()
        for stock, df in eod_industry_name[name].items():
            temp_volume_df[stock] = df["volume"]
        temp_volume_df["volume"] = temp_volume_df.iloc[:, 1:].sum(axis=1)
        temp_volume_df["ma5_V"] = (
            temp_volume_df["volume"][::-1].shift(1).rolling(window=5).mean()[::-1]
        )
        temp_volume_df.loc[0, "ma5_V"] = (
            temp_volume_df["ma5_V"].iloc[0] * current_time_percent
        )
        temp_volume_df["ratio"] = temp_volume_df["volume"] / temp_volume_df["ma5_V"]
        eod_group_liquidity_df[name] = temp_volume_df["ratio"]

    for name in eod_industry_perform.keys():
        temp_volume_df = date_series.copy()
        for stock, df in eod_industry_perform[name].items():
            temp_volume_df[stock] = df["volume"]
        temp_volume_df["volume"] = temp_volume_df.iloc[:, 1:].sum(axis=1)
        temp_volume_df["ma5_V"] = (
            temp_volume_df["volume"][::-1].shift(1).rolling(window=5).mean()[::-1]
        )
        temp_volume_df.loc[0, "ma5_V"] = (
            temp_volume_df["ma5_V"].iloc[0] * current_time_percent
        )
        temp_volume_df["ratio"] = temp_volume_df["volume"] / temp_volume_df["ma5_V"]
        eod_group_liquidity_df[name] = temp_volume_df["ratio"]

    for name in eod_marketcap_group.keys():
        temp_volume_df = date_series.copy()
        for stock, df in eod_marketcap_group[name].items():
            temp_volume_df[stock] = df["volume"]
        temp_volume_df["volume"] = temp_volume_df.iloc[:, 1:].sum(axis=1)
        temp_volume_df["ma5_V"] = (
            temp_volume_df["volume"][::-1].shift(1).rolling(window=5).mean()[::-1]
        )
        temp_volume_df.loc[0, "ma5_V"] = (
            temp_volume_df["ma5_V"].iloc[0] * current_time_percent
        )
        temp_volume_df["ratio"] = temp_volume_df["volume"] / temp_volume_df["ma5_V"]
        eod_group_liquidity_df[name] = temp_volume_df["ratio"]

    eod_group_liquidity_df = eod_group_liquidity_df.iloc[:20]

    # - Hệ số thanh khoản nhóm cổ phiếu ITD

    itd_group_liquidity_df = (
        time_series.copy().sort_values("date").reset_index(drop=True)
    )

    # Thêm cột toàn bộ cổ phiếu
    for name in itd_all_stock.keys():
        liquidity_t0 = (
            time_percent[time_percent["date"] >= date_series["date"].iloc[0]]
            .sort_values("date")
            .reset_index(drop=True)
        )
        liquidity_month_ma5 = 0

        for stock, df in itd_all_stock[name].items():
            liquidity_t0[stock] = (
                df[df["date"] >= date_series["date"].iloc[0]]
                .sort_values("date")["volume"]
                .reset_index(drop=True)
            )
            liquidity_month_ma5 += eod_stock_dict[stock].iloc[0]["ma5_V"]
        for column in liquidity_t0.columns[2:]:
            liquidity_t0[column] = liquidity_t0[column].cumsum()

        liquidity_t0["volume_t0"] = liquidity_t0.iloc[:, 2:].sum(axis=1)
        liquidity_t0["volume_month_ma5"] = liquidity_month_ma5 * liquidity_t0["percent"]
        liquidity_t0["ratio"] = (
            liquidity_t0["volume_t0"] / liquidity_t0["volume_month_ma5"]
        )
        liquidity_t0.loc[0, "ratio"] = 0

        itd_group_liquidity_df[name] = liquidity_t0["ratio"]

    # Thêm các cột cho các ngành
    for name in itd_industry_name.keys():
        liquidity_t0 = (
            time_percent[time_percent["date"] >= date_series["date"].iloc[0]]
            .sort_values("date")
            .reset_index(drop=True)
        )
        liquidity_month_ma5 = 0

        for stock, df in itd_industry_name[name].items():
            liquidity_t0[stock] = (
                df[df["date"] >= date_series["date"].iloc[0]]
                .sort_values("date")["volume"]
                .reset_index(drop=True)
            )
            liquidity_month_ma5 += eod_stock_dict[stock].iloc[0]["ma5_V"]
        for column in liquidity_t0.columns[2:]:
            liquidity_t0[column] = liquidity_t0[column].cumsum()

        liquidity_t0["volume_t0"] = liquidity_t0.iloc[:, 2:].sum(axis=1)
        liquidity_t0["volume_month_ma5"] = liquidity_month_ma5 * liquidity_t0["percent"]
        liquidity_t0["ratio"] = (
            liquidity_t0["volume_t0"] / liquidity_t0["volume_month_ma5"]
        )
        liquidity_t0.loc[0, "ratio"] = 0

        itd_group_liquidity_df[name] = liquidity_t0["ratio"]

    # Thêm các cột cho các nhóm hiệu suất
    for name in itd_industry_perform.keys():
        liquidity_t0 = (
            time_percent[time_percent["date"] >= date_series["date"].iloc[0]]
            .sort_values("date")
            .reset_index(drop=True)
        )
        liquidity_month_ma5 = 0

        for stock, df in itd_industry_perform[name].items():
            liquidity_t0[stock] = (
                df[df["date"] >= date_series["date"].iloc[0]]
                .sort_values("date")["volume"]
                .reset_index(drop=True)
            )
            liquidity_month_ma5 += eod_stock_dict[stock].iloc[0]["ma5_V"]
        for column in liquidity_t0.columns[2:]:
            liquidity_t0[column] = liquidity_t0[column].cumsum()

        liquidity_t0["volume_t0"] = liquidity_t0.iloc[:, 2:].sum(axis=1)
        liquidity_t0["volume_month_ma5"] = liquidity_month_ma5 * liquidity_t0["percent"]
        liquidity_t0["ratio"] = (
            liquidity_t0["volume_t0"] / liquidity_t0["volume_month_ma5"]
        )
        liquidity_t0.loc[0, "ratio"] = 0

        itd_group_liquidity_df[name] = liquidity_t0["ratio"]

    # Thêm các cột cho các nhóm vốn hoá
    for name in itd_marketcap_group.keys():
        liquidity_t0 = (
            time_percent[time_percent["date"] >= date_series["date"].iloc[0]]
            .sort_values("date")
            .reset_index(drop=True)
        )
        liquidity_month_ma5 = 0

        for stock, df in itd_marketcap_group[name].items():
            liquidity_t0[stock] = (
                df[df["date"] >= date_series["date"].iloc[0]]
                .sort_values("date")["volume"]
                .reset_index(drop=True)
            )
            liquidity_month_ma5 += eod_stock_dict[stock].iloc[0]["ma5_V"]
        for column in liquidity_t0.columns[2:]:
            liquidity_t0[column] = liquidity_t0[column].cumsum()

        liquidity_t0["volume_t0"] = liquidity_t0.iloc[:, 2:].sum(axis=1)
        liquidity_t0["volume_month_ma5"] = liquidity_month_ma5 * liquidity_t0["percent"]
        liquidity_t0["ratio"] = (
            liquidity_t0["volume_t0"] / liquidity_t0["volume_month_ma5"]
        )
        liquidity_t0.loc[0, "ratio"] = 0

        itd_group_liquidity_df[name] = liquidity_t0["ratio"]

    itd_group_liquidity_df = itd_group_liquidity_df.sort_values(
        "date", ascending=False
    ).reset_index(drop=True)

    # #### Xếp hạng các nhóm cổ phiếu

    # Tạo bảng xếp hạng cho các nhóm cổ phiếu
    def create_ranking_df(score_df):
        socre_dict = {}
        for group in score_df.columns[1:]:
            socre_dict[group] = date_series.copy()
            socre_dict[group]["t0_score"] = score_df[group]
            socre_dict[group]["t5_score"] = (
                socre_dict[group]["t0_score"][::-1].rolling(window=5).mean()[::-1]
            )

        ranking_score = date_series.copy()
        for group in socre_dict.keys():
            ranking_score[group] = socre_dict[group]["t5_score"]
            ranking_score.fillna(0, inplace=True)

        ranking_df = date_series.copy()
        for group in socre_dict.keys():
            ranking_df[group] = 0

        for i in range(len(date_series.copy())):
            ranking_df.iloc[i, 1:] = ranking_score.iloc[i, 1:].rank(
                ascending=False, method="min"
            )

        ranking_df = ranking_df.head(20)

        return ranking_df

    industry_name_ranking = create_ranking_df(
        eod_group_score_df[
            [
                "date",
                "ban_le",
                "bao_hiem",
                "bds",
                "bds_kcn",
                "chung_khoan",
                "cong_nghe",
                "cong_nghiep",
                "dau_khi",
                "det_may",
                "dulich_dv",
                "dv_hatang",
                "hoa_chat",
                "htd",
                "khoang_san",
                "ngan_hang",
                "tai_chinh",
                "thep",
                "thuc_pham",
                "thuy_san",
                "van_tai",
                "vlxd",
                "xd",
                "y_te",
            ]
        ]
    )
    industry_perform_ranking = create_ranking_df(
        eod_group_score_df[["date", "A", "B", "C", "D"]]
    )
    marketcap_group_ranking = create_ranking_df(
        eod_group_score_df[["date", "large", "mid", "small", "penny"]]
    )

    group_score_ranking = industry_name_ranking.merge(
        industry_perform_ranking, on="date", how="left"
    ).merge(marketcap_group_ranking, on="date", how="left")

    group_score_ranking_melted = pd.DataFrame()
    for column in group_score_ranking.columns[1:]:
        temp_df = group_score_ranking[["date", column]]
        temp_df.columns = [["date", "rank"]]
        temp_df["name"] = column
        group_score_ranking_melted = pd.concat(
            [group_score_ranking_melted, temp_df], axis=0
        )

    group_score_ranking_melted.columns = ["date", "rank", "name"]
    group_score_ranking_melted["name"] = group_score_ranking_melted["name"].map(
        name_map_dict
    )

    # #### Gộp thanh khoản và dòng tiền các nhóm cổ phiếu

    # - Gộp bảng hệ số thanh khoản và dòng tiền của các nhóm cổ phiếu EOD

    # Gộp bảng hệ số thanh khoản và dòng tiền của các nhóm cổ phiếu EOD
    eod_score_liquidity_df = date_series.copy()
    for column in eod_group_liquidity_df.columns[1:]:
        eod_score_liquidity_df[f"liquid_{column}"] = eod_group_liquidity_df[column]
    for column in eod_group_score_df.columns[1:]:
        eod_score_liquidity_df[f"score_{column}"] = eod_group_score_df[column]

    eod_score_liquidity_df = eod_score_liquidity_df.iloc[:20]

    eod_group_liquidity_melted = eod_group_liquidity_df.iloc[:20].melt(
        id_vars=["date"], var_name="group_name", value_name="value"
    )
    eod_group_liquidity_melted = eod_group_liquidity_melted.rename(
        columns={"value": "liquidity"}
    )
    eod_group_score_melted = eod_group_score_df.iloc[:20, :-4].melt(
        id_vars=["date"], var_name="group_name", value_name="value"
    )
    eod_group_score_melted = eod_group_score_melted.rename(columns={"value": "score"})

    eod_score_liquidity_melted = eod_group_liquidity_melted.merge(
        eod_group_score_melted, on=["date", "group_name"], how="inner"
    )

    eod_score_liquidity_melted["group_name"] = eod_score_liquidity_melted[
        "group_name"
    ].map(name_map_dict)

    # - Gộp bảng hệ số thanh khoản và dòng tiền của các nhóm cổ phiếu ITD

    # Gộp bảng hệ số thanh khoản và dòng tiền của các nhóm cổ phiếu ITD
    itd_score_liquidity_df = time_series.copy().reset_index(drop=True)
    for column in itd_group_liquidity_df.columns[1:]:
        itd_score_liquidity_df[f"liquid_{column}"] = itd_group_liquidity_df[column]
    for column in itd_group_score_df.columns[1:]:
        itd_score_liquidity_df[f"score_{column}"] = itd_group_score_df[column]

    itd_score_liquidity_df.iloc[0, 1:] = eod_score_liquidity_df.iloc[0, 1:-4]

    # Hiệu chỉnh lại theo khung thời gian ITD
    itd_score_liquidity_df = itd_series.merge(
        itd_score_liquidity_df, on="date", how="left"
    )

    # Gộp thành bảng dọc để dùng slicer
    itd_group_liquidity_df = itd_series.merge(
        itd_group_liquidity_df, on="date", how="left"
    )
    itd_group_liquidity_melted = itd_group_liquidity_df.melt(
        id_vars=["date"], var_name="group_name", value_name="value"
    )
    itd_group_liquidity_melted = itd_group_liquidity_melted.rename(
        columns={"value": "liquidity"}
    )

    itd_group_score_df = itd_series.merge(itd_group_score_df, on="date", how="left")
    itd_group_score_melted = itd_group_score_df.melt(
        id_vars=["date"], var_name="group_name", value_name="value"
    )
    itd_group_score_melted = itd_group_score_melted.rename(columns={"value": "score"})

    itd_score_liquidity_melted = itd_group_liquidity_melted.merge(
        itd_group_score_melted, on=["date", "group_name"], how="inner"
    )

    itd_score_liquidity_melted["group_name"] = itd_score_liquidity_melted[
        "group_name"
    ].map(name_map_dict)

    # Tạo bảng giá trị cuối của dòng tiền và thanh khoản
    itd_score_liquidity_last = pd.concat(
        [
            eod_group_liquidity_df.iloc[0, 1:],
            eod_group_score_df.iloc[0, 1:-4],
            eod_group_score_df.iloc[:5, 1:-4].mean(axis=0),
            group_score_ranking.iloc[0].iloc[1:],
        ],
        axis=1,
    ).reset_index()
    itd_score_liquidity_last.columns = [
        "name",
        "liquidity",
        "score",
        "score_t5",
        "rank",
    ]
    itd_score_liquidity_last["liquid_state"] = itd_score_liquidity_last[
        "liquidity"
    ].apply(
        lambda x: (
            "Rất thấp"
            if x < 0.5
            else (
                "Thấp"
                if (x >= 0.5) & (x < 0.8)
                else (
                    "Trung bình"
                    if (x >= 0.8) & (x < 1.2)
                    else ("Cao" if (x >= 1.2) & (x < 1.5) else "Rất cao")
                )
            )
        )
    )

    itd_score_liquidity_last["order"] = itd_score_liquidity_last["name"].map(
        order_map_dict
    )
    itd_score_liquidity_last["group"] = itd_score_liquidity_last["name"].map(
        group_map_dict
    )
    itd_score_liquidity_last["name"] = itd_score_liquidity_last["name"].map(
        name_map_dict
    )

    # #### Dòng tiền trong tuần và trong tháng

    def fill_month_flow(series):
        new_series = series.copy()
        for i in range(len(series) - 1):
            if i == 0:
                fill_value = 0
                new_series[i] = fill_value
            else:
                fill_value = new_series[i - 1]
                if pd.isna(series[i]):
                    if not series[i:-1].isna().all():
                        new_series[i] = fill_value
        return new_series

    # - Tính toán cho từng cổ phiếu

    stock_score_df = date_series.copy()
    all_stock_list = stock_classification_filtered["stock"].tolist()

    for stock, df in eod_score_dict.items():
        stock_score_df[stock] = eod_score_dict[stock]["t0_score"]

    stock_score_df["week"] = stock_score_df["date"].dt.strftime("%U-%Y")
    stock_score_df["month"] = stock_score_df["date"].dt.strftime("%m-%Y")
    stock_score_df["week_day"] = stock_score_df["date"].dt.day_name()
    stock_score_df["day_num"] = stock_score_df["date"].dt.day

    # Tạo bảng dữ liệu theo tuần
    week_day_index = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }
    week_day_dict = {
        "Monday": "Thứ 2",
        "Tuesday": "Thứ 3",
        "Wednesday": "Thứ 4",
        "Thursday": "Thứ 5",
        "Friday": "Thứ 6",
    }
    week_score_dict = {}
    for i in range(2):
        week_score_dict[f"week_{i+1}"] = (
            stock_score_df[stock_score_df["week"] == stock_score_df["week"].unique()[i]]
            .drop(columns=["date", "week", "month", "day_num"])
            .set_index("week_day")
        )

        temp_df = (
            pd.DataFrame(["Monday", "Tuesday", "Wednesday", "Friday", "Thursday"])
            .rename(columns={0: "week_day"})
            .set_index("week_day")
        )
        week_score_dict[f"week_{i+1}"] = pd.concat(
            [temp_df, week_score_dict[f"week_{i+1}"]], axis=1
        ).reset_index()

        columns_list = week_score_dict[f"week_{i+1}"].columns
        week_score_dict[f"week_{i+1}"]["id"] = f"w{i+1}"

        week_score_dict[f"week_{i+1}"] = week_score_dict[f"week_{i+1}"].melt(
            id_vars=["week_day", "id"],
            value_vars=all_stock_list,
            var_name="stock",
            value_name="value",
        )
        week_score_dict[f"week_{i+1}"] = (
            week_score_dict[f"week_{i+1}"]
            .pivot_table(
                index=["week_day", "stock"],
                columns="id",
                values="value",
                aggfunc="first",
            )
            .reset_index()
        )

    # Bảng so sánh 2 tuần
    stock_score_week = week_score_dict["week_1"].merge(
        week_score_dict["week_2"], on=["week_day", "stock"], how="outer"
    )
    stock_score_week["day_index"] = stock_score_week["week_day"].map(week_day_index)
    stock_score_week["week_day"] = stock_score_week["week_day"].map(week_day_dict)
    stock_score_week = stock_score_week.sort_values("day_index")

    # Tạo bảng dữ liệu theo tháng
    month_score_dict = {}
    for i in range(2):
        month_score_dict[f"month_{i+1}"] = (
            stock_score_df[
                stock_score_df["month"] == stock_score_df["month"].unique()[i]
            ]
            .drop(columns=["date", "week", "month", "week_day"])
            .set_index("day_num")
        )

        temp_df = (
            pd.DataFrame(list(range(0, 32)))
            .rename(columns={0: "day_num"})
            .set_index("day_num")
        )
        month_score_dict[f"month_{i+1}"] = pd.concat(
            [temp_df, month_score_dict[f"month_{i+1}"]], axis=1
        ).reset_index()
        columns_list = month_score_dict[f"month_{i+1}"].columns

        for column in columns_list[1:]:
            month_score_dict[f"month_{i+1}"][column] = month_score_dict[f"month_{i+1}"][
                column
            ].cumsum()
            month_score_dict[f"month_{i+1}"][column].iloc[
                month_score_dict[f"month_{i+1}"][column].first_valid_index() - 1
            ] = 0
            month_score_dict[f"month_{i+1}"][column] = fill_month_flow(
                month_score_dict[f"month_{i+1}"][column]
            )

        month_score_dict[f"month_{i+1}"]["id"] = f"m{i+1}"

        month_score_dict[f"month_{i+1}"] = month_score_dict[f"month_{i+1}"].melt(
            id_vars=["day_num", "id"],
            value_vars=all_stock_list,
            var_name="stock",
            value_name="value",
        )
        month_score_dict[f"month_{i+1}"] = (
            month_score_dict[f"month_{i+1}"]
            .pivot_table(
                index=["day_num", "stock"],
                columns="id",
                values="value",
                aggfunc="first",
            )
            .reset_index()
        )

    # Bảng so sánh các 2 tháng
    stock_score_month = month_score_dict["month_1"].merge(
        month_score_dict["month_2"], on=["day_num", "stock"], how="outer"
    )

    # - Tính toán cho các nhóm cổ phiếu

    # Tạo bảng dữ liệu theo tuần
    week_day_index = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }
    week_day_dict = {
        "Monday": "Thứ 2",
        "Tuesday": "Thứ 3",
        "Wednesday": "Thứ 4",
        "Thursday": "Thứ 5",
        "Friday": "Thứ 6",
    }
    week_score_dict = {}
    for i in range(2):
        week_score_dict[f"week_{i+1}"] = (
            eod_group_score_df[
                eod_group_score_df["week"] == eod_group_score_df["week"].unique()[i]
            ]
            .drop(columns=["date", "week", "month", "day_num"])
            .set_index("week_day")
        )

        temp_df = (
            pd.DataFrame(["Monday", "Tuesday", "Wednesday", "Friday", "Thursday"])
            .rename(columns={0: "week_day"})
            .set_index("week_day")
        )
        week_score_dict[f"week_{i+1}"] = pd.concat(
            [temp_df, week_score_dict[f"week_{i+1}"]], axis=1
        ).reset_index()

        columns_list = week_score_dict[f"week_{i+1}"].columns
        week_score_dict[f"week_{i+1}"]["id"] = f"w{i+1}"

        week_score_dict[f"week_{i+1}"] = week_score_dict[f"week_{i+1}"].melt(
            id_vars=["week_day", "id"],
            value_vars=group_stock_list,
            var_name="group_name",
            value_name="value",
        )
        week_score_dict[f"week_{i+1}"] = (
            week_score_dict[f"week_{i+1}"]
            .pivot_table(
                index=["week_day", "group_name"],
                columns="id",
                values="value",
                aggfunc="first",
            )
            .reset_index()
        )

    # Bảng so sánh 2 tuần
    group_score_week = week_score_dict["week_1"].merge(
        week_score_dict["week_2"], on=["week_day", "group_name"], how="outer"
    )
    group_score_week["day_index"] = group_score_week["week_day"].map(week_day_index)
    group_score_week["group_name"] = group_score_week["group_name"].map(name_map_dict)
    group_score_week["week_day"] = group_score_week["week_day"].map(week_day_dict)
    group_score_week = group_score_week.sort_values("day_index")

    # Tạo bảng dữ liệu theo tháng
    month_score_dict = {}
    for i in range(2):
        month_score_dict[f"month_{i+1}"] = (
            eod_group_score_df[
                eod_group_score_df["month"] == eod_group_score_df["month"].unique()[i]
            ]
            .drop(columns=["date", "week", "month", "week_day"])
            .set_index("day_num")
        )

        temp_df = (
            pd.DataFrame(list(range(0, 32)))
            .rename(columns={0: "day_num"})
            .set_index("day_num")
        )
        month_score_dict[f"month_{i+1}"] = pd.concat(
            [temp_df, month_score_dict[f"month_{i+1}"]], axis=1
        ).reset_index()
        columns_list = month_score_dict[f"month_{i+1}"].columns

        for column in columns_list[1:]:
            month_score_dict[f"month_{i+1}"][column] = month_score_dict[f"month_{i+1}"][
                column
            ].cumsum()
            month_score_dict[f"month_{i+1}"][column].iloc[
                month_score_dict[f"month_{i+1}"][column].first_valid_index() - 1
            ] = 0
            month_score_dict[f"month_{i+1}"][column] = fill_month_flow(
                month_score_dict[f"month_{i+1}"][column]
            )

        month_score_dict[f"month_{i+1}"]["id"] = f"m{i+1}"

        month_score_dict[f"month_{i+1}"] = month_score_dict[f"month_{i+1}"].melt(
            id_vars=["day_num", "id"],
            value_vars=group_stock_list,
            var_name="group_name",
            value_name="value",
        )
        month_score_dict[f"month_{i+1}"] = (
            month_score_dict[f"month_{i+1}"]
            .pivot_table(
                index=["day_num", "group_name"],
                columns="id",
                values="value",
                aggfunc="first",
            )
            .reset_index()
        )

    # Bảng so sánh các 2 tháng
    group_score_month = month_score_dict["month_1"].merge(
        month_score_dict["month_2"], on=["day_num", "group_name"], how="outer"
    )
    group_score_month["group_name"] = group_score_month["group_name"].map(name_map_dict)

    # #### Chỉ số kĩ thuật

    def calculate_ta_df(price_df):
        ta_df = price_df[
            ["stock", "date", "open", "high", "low", "close", "volume"]
        ].copy()
        ta_df["week"] = ta_df["date"].dt.strftime("%Y-%U")
        ta_df["month"] = ta_df["date"].dt.to_period("M")
        ta_df["quarter"] = ta_df["date"].dt.to_period("Q")
        ta_df["year"] = ta_df["date"].dt.to_period("Y")
        return ta_df

    def calculate_candle_ta_df(ta_df, input_type):
        ta_df_copy = ta_df.copy()
        # Define unique time frames up front to avoid recalculating them multiple times
        unique_weeks = ta_df["week"].unique()
        unique_months = ta_df_copy["month"].unique()
        unique_quarters = ta_df_copy["quarter"].unique()
        unique_years = ta_df_copy["year"].unique()

        # Define filters for reuse
        filter_week_1 = (
            ta_df_copy["week"] == unique_weeks[1] if len(unique_weeks) > 1 else None
        )
        filter_week_0 = (
            ta_df_copy["week"] == unique_weeks[0] if len(unique_weeks) > 0 else None
        )
        filter_month_1 = (
            ta_df_copy["month"] == unique_months[1] if len(unique_months) > 1 else None
        )
        filter_month_0 = (
            ta_df_copy["month"] == unique_months[0] if len(unique_months) > 0 else None
        )
        filter_quarter_1 = (
            ta_df_copy["quarter"] == unique_quarters[1]
            if len(unique_quarters) > 1
            else None
        )
        filter_quarter_0 = (
            ta_df_copy["quarter"] == unique_quarters[0]
            if len(unique_quarters) > 0
            else None
        )
        filter_year_1 = (
            ta_df_copy["year"] == unique_years[1] if len(unique_years) > 1 else None
        )
        filter_year_0 = (
            ta_df_copy["year"] == unique_years[0] if len(unique_years) > 0 else None
        )

        # Apply filters and calculate needed values
        if filter_week_1 is not None:
            ta_df_copy["week_last_low"] = ta_df_copy.loc[filter_week_1, "low"].min()
            ta_df_copy["week_last_high"] = ta_df_copy.loc[filter_week_1, "high"].max()
        if filter_week_0 is not None:
            ta_df_copy["week_open"] = ta_df_copy.loc[filter_week_0, "open"].iloc[-1]

        if filter_month_1 is not None:
            ta_df_copy["month_last_low"] = ta_df_copy.loc[filter_month_1, "low"].min()
            ta_df_copy["month_last_high"] = ta_df_copy.loc[filter_month_1, "high"].max()
        if filter_month_0 is not None:
            ta_df_copy["month_open"] = ta_df_copy.loc[filter_month_0, "open"].iloc[-1]

        if filter_quarter_1 is not None:
            ta_df_copy["quarter_last_low"] = ta_df_copy.loc[
                filter_quarter_1, "low"
            ].min()
            ta_df_copy["quarter_last_high"] = ta_df_copy.loc[
                filter_quarter_1, "high"
            ].max()
        if filter_quarter_0 is not None:
            ta_df_copy["quarter_open"] = ta_df_copy.loc[filter_quarter_0, "open"].iloc[
                -1
            ]

        if filter_year_1 is not None:
            ta_df_copy["year_last_low"] = ta_df_copy.loc[filter_year_1, "low"].min()
            ta_df_copy["year_last_high"] = ta_df_copy.loc[filter_year_1, "high"].max()
        if filter_year_0 is not None:
            ta_df_copy["year_open"] = ta_df_copy.loc[filter_year_0, "open"].iloc[-1]

        # Compute 'from' values for stock or index
        columns_to_compute = ["week", "month", "quarter", "year"]
        for frame in columns_to_compute:
            suffix = ["last_high", "last_low", "open"]
            for suf in suffix:
                column_name = f"{frame}_{suf}"
                if column_name in ta_df_copy.columns:
                    if input_type == "stock":
                        ta_df_copy[f"from_{frame}_{suf}"] = (
                            ta_df_copy["close"] - ta_df_copy[column_name]
                        ) / ta_df_copy[column_name]
                    elif input_type == "index":
                        ta_df_copy[f"from_{frame}_{suf}"] = (
                            ta_df_copy["close"] - ta_df_copy[column_name]
                        )

        return ta_df_copy

    def calculate_fibo_ta_df(ta_df, input_type):
        ta_df_copy = ta_df.copy()

        ta_df_copy["month_high"] = ta_df_copy[
            ta_df_copy["month"].isin(ta_df_copy["month"].unique()[:2].tolist())
        ]["high"].max()
        ta_df_copy["quarter_high"] = ta_df_copy[
            ta_df_copy["quarter"].isin(ta_df_copy["quarter"].unique()[:2].tolist())
        ]["high"].max()
        ta_df_copy["year_high"] = ta_df_copy[
            ta_df_copy["year"].isin(ta_df_copy["year"].unique()[:2].tolist())
        ]["high"].max()

        ta_df_copy["month_low"] = ta_df_copy[
            ta_df_copy["month"].isin(ta_df_copy["month"].unique()[:2].tolist())
        ]["low"].min()
        ta_df_copy["quarter_low"] = ta_df_copy[
            ta_df_copy["quarter"].isin(ta_df_copy["quarter"].unique()[:2].tolist())
        ]["low"].min()
        ta_df_copy["year_low"] = ta_df_copy[
            ta_df_copy["year"].isin(ta_df_copy["year"].unique()[:2].tolist())
        ]["low"].min()

        ta_df_copy["month_fibo_382"] = (
            ta_df_copy["month_high"]
            - (ta_df_copy["month_high"] - ta_df_copy["month_low"]) * 0.382
        )
        ta_df_copy["month_fibo_500"] = (
            ta_df_copy["month_high"]
            - (ta_df_copy["month_high"] - ta_df_copy["month_low"]) * 0.5
        )
        ta_df_copy["month_fibo_618"] = (
            ta_df_copy["month_high"]
            - (ta_df_copy["month_high"] - ta_df_copy["month_low"]) * 0.618
        )

        ta_df_copy["quarter_fibo_382"] = (
            ta_df_copy["quarter_high"]
            - (ta_df_copy["quarter_high"] - ta_df_copy["quarter_low"]) * 0.382
        )
        ta_df_copy["quarter_fibo_500"] = (
            ta_df_copy["quarter_high"]
            - (ta_df_copy["quarter_high"] - ta_df_copy["quarter_low"]) * 0.5
        )
        ta_df_copy["quarter_fibo_618"] = (
            ta_df_copy["quarter_high"]
            - (ta_df_copy["quarter_high"] - ta_df_copy["quarter_low"]) * 0.618
        )

        ta_df_copy["year_fibo_382"] = (
            ta_df_copy["year_high"]
            - (ta_df_copy["year_high"] - ta_df_copy["year_low"]) * 0.382
        )
        ta_df_copy["year_fibo_500"] = (
            ta_df_copy["year_high"]
            - (ta_df_copy["year_high"] - ta_df_copy["year_low"]) * 0.5
        )
        ta_df_copy["year_fibo_618"] = (
            ta_df_copy["year_high"]
            - (ta_df_copy["year_high"] - ta_df_copy["year_low"]) * 0.618
        )

        if input_type == "stock":

            ta_df_copy["from_month_fibo_382"] = (
                ta_df_copy["close"] - ta_df_copy["month_fibo_382"]
            ) / abs(ta_df_copy["month_fibo_382"])
            ta_df_copy["from_month_fibo_500"] = (
                ta_df_copy["close"] - ta_df_copy["month_fibo_500"]
            ) / abs(ta_df_copy["month_fibo_500"])
            ta_df_copy["from_month_fibo_618"] = (
                ta_df_copy["close"] - ta_df_copy["month_fibo_618"]
            ) / abs(ta_df_copy["month_fibo_618"])

            ta_df_copy["from_quarter_fibo_382"] = (
                ta_df_copy["close"] - ta_df_copy["quarter_fibo_382"]
            ) / abs(ta_df_copy["quarter_fibo_382"])
            ta_df_copy["from_quarter_fibo_500"] = (
                ta_df_copy["close"] - ta_df_copy["quarter_fibo_500"]
            ) / abs(ta_df_copy["quarter_fibo_500"])
            ta_df_copy["from_quarter_fibo_618"] = (
                ta_df_copy["close"] - ta_df_copy["quarter_fibo_618"]
            ) / abs(ta_df_copy["quarter_fibo_618"])

            ta_df_copy["from_year_fibo_382"] = (
                ta_df_copy["close"] - ta_df_copy["year_fibo_382"]
            ) / abs(ta_df_copy["year_fibo_382"])
            ta_df_copy["from_year_fibo_500"] = (
                ta_df_copy["close"] - ta_df_copy["year_fibo_500"]
            ) / abs(ta_df_copy["year_fibo_500"])
            ta_df_copy["from_year_fibo_618"] = (
                ta_df_copy["close"] - ta_df_copy["year_fibo_618"]
            ) / abs(ta_df_copy["year_fibo_618"])

        if input_type == "index":

            ta_df_copy["from_month_fibo_382"] = (
                ta_df_copy["close"] - ta_df_copy["month_fibo_382"]
            )
            ta_df_copy["from_month_fibo_500"] = (
                ta_df_copy["close"] - ta_df_copy["month_fibo_500"]
            )
            ta_df_copy["from_month_fibo_618"] = (
                ta_df_copy["close"] - ta_df_copy["month_fibo_618"]
            )

            ta_df_copy["from_quarter_fibo_382"] = (
                ta_df_copy["close"] - ta_df_copy["quarter_fibo_382"]
            )
            ta_df_copy["from_quarter_fibo_500"] = (
                ta_df_copy["close"] - ta_df_copy["quarter_fibo_500"]
            )
            ta_df_copy["from_quarter_fibo_618"] = (
                ta_df_copy["close"] - ta_df_copy["quarter_fibo_618"]
            )

            ta_df_copy["from_year_fibo_382"] = (
                ta_df_copy["close"] - ta_df_copy["year_fibo_382"]
            )
            ta_df_copy["from_year_fibo_500"] = (
                ta_df_copy["close"] - ta_df_copy["year_fibo_500"]
            )
            ta_df_copy["from_year_fibo_618"] = (
                ta_df_copy["close"] - ta_df_copy["year_fibo_618"]
            )

        return ta_df_copy

    def calculate_pivot_ta_df(ta_df, input_type):
        ta_df_copy = ta_df.copy()

        try:
            ta_df_copy["month_high"] = ta_df_copy[
                ta_df_copy["month"] == ta_df_copy["month"].unique()[1]
            ]["high"].max()
        except:
            ta_df_copy["month_high"] = None
        try:
            ta_df_copy["quarter_high"] = ta_df_copy[
                ta_df_copy["quarter"] == ta_df_copy["quarter"].unique()[1]
            ]["high"].max()
        except:
            ta_df_copy["quarter_high"] = None
        try:
            ta_df_copy["year_high"] = ta_df_copy[
                ta_df_copy["year"] == ta_df_copy["year"].unique()[1]
            ]["high"].max()
        except:
            ta_df_copy["year_high"] = None

        try:
            ta_df_copy["month_low"] = ta_df_copy[
                ta_df_copy["month"] == ta_df_copy["month"].unique()[1]
            ]["low"].min()
        except:
            ta_df_copy["month_low"] = None
        try:
            ta_df_copy["quarter_low"] = ta_df_copy[
                ta_df_copy["quarter"] == ta_df_copy["quarter"].unique()[1]
            ]["low"].min()
        except:
            ta_df_copy["quarter_low"] = None
        try:
            ta_df_copy["year_low"] = ta_df_copy[
                ta_df_copy["year"] == ta_df_copy["year"].unique()[1]
            ]["low"].min()
        except:
            ta_df_copy["year_low"] = None

        try:
            ta_df_copy["month_close"] = ta_df_copy[
                ta_df_copy["month"] == ta_df_copy["month"].unique()[1]
            ]["close"].iloc[0]
        except:
            ta_df_copy["month_close"] = None
        try:
            ta_df_copy["quarter_close"] = ta_df_copy[
                ta_df_copy["quarter"] == ta_df_copy["quarter"].unique()[1]
            ]["close"].iloc[0]
        except:
            ta_df_copy["quarter_close"] = None
        try:
            ta_df_copy["year_close"] = ta_df_copy[
                ta_df_copy["year"] == ta_df_copy["year"].unique()[1]
            ]["close"].iloc[0]
        except:
            ta_df_copy["year_close"] = None

        ta_df_copy["month_pivot"] = (
            ta_df_copy["month_high"]
            + ta_df_copy["month_low"]
            + ta_df_copy["month_close"]
        ) / 3
        ta_df_copy["quarter_pivot"] = (
            ta_df_copy["quarter_high"]
            + ta_df_copy["quarter_low"]
            + ta_df_copy["quarter_close"]
        ) / 3
        ta_df_copy["year_pivot"] = (
            ta_df_copy["year_high"] + ta_df_copy["year_low"] + ta_df_copy["year_close"]
        ) / 3

        if input_type == "index":
            ta_df_copy["from_month_pivot"] = (
                ta_df_copy["close"] - ta_df_copy["month_pivot"]
            )
            ta_df_copy["from_quarter_pivot"] = (
                ta_df_copy["close"] - ta_df_copy["quarter_pivot"]
            )
            ta_df_copy["from_year_pivot"] = (
                ta_df_copy["close"] - ta_df_copy["year_pivot"]
            )

        if input_type == "stock":
            ta_df_copy["from_month_pivot"] = (
                ta_df_copy["close"] - ta_df_copy["month_pivot"]
            ) / abs(ta_df_copy["month_pivot"])
            ta_df_copy["from_quarter_pivot"] = (
                ta_df_copy["close"] - ta_df_copy["quarter_pivot"]
            ) / abs(ta_df_copy["quarter_pivot"])
            ta_df_copy["from_year_pivot"] = (
                ta_df_copy["close"] - ta_df_copy["year_pivot"]
            ) / abs(ta_df_copy["year_pivot"])

        return ta_df_copy

    def calculate_ma_ta_df(ta_df, input_type):
        ta_df_copy = ta_df.copy()

        ta_df_copy["ma5"] = (
            ta_df_copy["close"][::-1].rolling(window=5, min_periods=1).mean()[::-1]
        )
        ta_df_copy["ma20"] = (
            ta_df_copy["close"][::-1].rolling(window=20, min_periods=1).mean()[::-1]
        )
        ta_df_copy["ma60"] = (
            ta_df_copy["close"][::-1].rolling(window=60, min_periods=1).mean()[::-1]
        )
        ta_df_copy["ma120"] = (
            ta_df_copy["close"][::-1].rolling(window=120, min_periods=1).mean()[::-1]
        )
        ta_df_copy["ma240"] = (
            ta_df_copy["close"][::-1].rolling(window=240, min_periods=1).mean()[::-1]
        )
        ta_df_copy["ma480"] = (
            ta_df_copy["close"][::-1].rolling(window=480, min_periods=1).mean()[::-1]
        )

        if input_type == "stock":

            ta_df_copy["from_month_ma5"] = (
                ta_df_copy["close"] - ta_df_copy["ma5"]
            ) / ta_df_copy["ma5"]
            ta_df_copy["from_month_ma20"] = (
                ta_df_copy["close"] - ta_df_copy["ma20"]
            ) / ta_df_copy["ma20"]
            ta_df_copy["from_quarter_ma60"] = (
                ta_df_copy["close"] - ta_df_copy["ma60"]
            ) / ta_df_copy["ma60"]
            ta_df_copy["from_quarter_ma120"] = (
                ta_df_copy["close"] - ta_df_copy["ma120"]
            ) / ta_df_copy["ma120"]
            ta_df_copy["from_year_ma240"] = (
                ta_df_copy["close"] - ta_df_copy["ma240"]
            ) / ta_df_copy["ma240"]
            ta_df_copy["from_year_ma480"] = (
                ta_df_copy["close"] - ta_df_copy["ma480"]
            ) / ta_df_copy["ma480"]

        if input_type == "index":

            ta_df_copy["from_month_ma5"] = ta_df_copy["close"] - ta_df_copy["ma5"]
            ta_df_copy["from_month_ma20"] = ta_df_copy["close"] - ta_df_copy["ma20"]
            ta_df_copy["from_quarter_ma60"] = ta_df_copy["close"] - ta_df_copy["ma60"]
            ta_df_copy["from_quarter_ma120"] = ta_df_copy["close"] - ta_df_copy["ma120"]
            ta_df_copy["from_year_ma240"] = ta_df_copy["close"] - ta_df_copy["ma240"]
            ta_df_copy["from_year_ma480"] = ta_df_copy["close"] - ta_df_copy["ma480"]

        return ta_df_copy

    def transform_ta_df(ta_df, ta_name):
        df_list = []
        for time_frame in ["month", "quarter", "year"]:
            if ta_name == "candle":
                df = ta_df[
                    [
                        "stock",
                        f"{time_frame}_open",
                        f"{time_frame}_last_high",
                        f"{time_frame}_last_low",
                        f"from_{time_frame}_open",
                        f"from_{time_frame}_last_high",
                        f"from_{time_frame}_last_low",
                    ]
                ].iloc[:1]
                df_name = ["Open", "Last High", "Last Low"]
                coef = 4
            elif ta_name == "fibo":
                df = ta_df[
                    [
                        "stock",
                        f"{time_frame}_fibo_382",
                        f"{time_frame}_fibo_500",
                        f"{time_frame}_fibo_618",
                        f"from_{time_frame}_fibo_382",
                        f"from_{time_frame}_fibo_500",
                        f"from_{time_frame}_fibo_618",
                    ]
                ].iloc[:1]
                df_name = ["Fibo 0.382", "Fibo 0.500", "Fibo 0.618"]
                coef = 4
            elif ta_name == "pivot":
                df = ta_df[
                    ["stock", f"{time_frame}_pivot", f"from_{time_frame}_pivot"]
                ].iloc[:1]
                df_name = ["Pivot"]
                coef = 2
            elif ta_name == "ma":
                if time_frame == "month":
                    df = ta_df[
                        ["stock", "ma5", "ma20", "from_month_ma5", "from_month_ma20"]
                    ].iloc[:1]
                    df_name = ["MA5", "MA20"]
                elif time_frame == "quarter":
                    df = ta_df[
                        [
                            "stock",
                            "ma60",
                            "ma120",
                            "from_quarter_ma60",
                            "from_quarter_ma120",
                        ]
                    ].iloc[:1]
                    df_name = ["MA60", "MA120"]
                elif time_frame == "year":
                    df = ta_df[
                        [
                            "stock",
                            "ma240",
                            "ma480",
                            "from_year_ma240",
                            "from_year_ma480",
                        ]
                    ].iloc[:1]
                    df_name = ["MA240", "MA480"]
                coef = 3
            df_value = df.iloc[0, 1:coef].tolist()
            df_from = df.iloc[0, coef:].tolist()

            if ta_name == "pivot":
                df_order = 3
            else:
                df_order = [i for i in range(1, len(df_name) + 1)]

            df = pd.DataFrame(
                {
                    "stock": df["stock"].item(),
                    "name": df_name,
                    "value": df_value,
                    "from": df_from,
                    "order": df_order,
                }
            )
            df["id"] = time_frame
            df["ta_name"] = ta_name
            df["value"] = df["value"].apply(
                lambda x: "{:.2f}".format(x) if isinstance(x, (int, float)) else x
            )
            df_list.append(df)
        concat_df = pd.concat(df_list, axis=0)
        return concat_df

    def concat_ta_df(df, input_type):
        ta_df = calculate_ta_df(df)

        df_candle_raw = calculate_candle_ta_df(ta_df, input_type)
        df_pivot_raw = calculate_pivot_ta_df(ta_df, input_type)
        df_ma_raw = calculate_ma_ta_df(ta_df, input_type)
        df_fibo_raw = calculate_fibo_ta_df(ta_df, input_type)

        df_candle = transform_ta_df(df_candle_raw, "candle")
        df_pivot = transform_ta_df(df_pivot_raw, "pivot")
        df_ma = transform_ta_df(df_ma_raw, "ma")
        df_fibo = transform_ta_df(df_fibo_raw, "fibo")

        concat_ta_df = pd.concat([df_candle, df_fibo, df_pivot, df_ma], axis=0)

        ta_dict = {
            "concat_ta_df": concat_ta_df,
            "ta_dict": {
                "df_candle": df_candle_raw,
                "df_pivot": df_pivot_raw,
                "df_ma": df_ma_raw,
                "df_fibo": df_fibo_raw,
            },
        }
        return ta_dict

    # - Tính toán chỉ số kĩ thuật cho index

    ta_index_df = pd.DataFrame()
    for index, df in eod_index_dict.items():
        temp_ta_dict = concat_ta_df(df, "index")

        temp_ta_index_df = temp_ta_dict["concat_ta_df"]
        ta_index_df = pd.concat([ta_index_df, temp_ta_index_df], axis=0)

    # - Tính toán chỉ số kĩ thuật cho cổ phiếu

    ta_stock_df = pd.DataFrame()
    ta_stock_dict = {}

    for stock, df in eod_all_stock["all_stock"].items():
        df_copy = df.copy()
        temp_ta_dict = concat_ta_df(df_copy, "stock")

        temp_ta_stock_df = temp_ta_dict["concat_ta_df"]
        ta_stock_df = pd.concat([ta_stock_df, temp_ta_stock_df], axis=0)

        ta_stock_dict[stock] = temp_ta_dict["ta_dict"]

    # #### Page 1: Tổng quan thị trường

    # - Bảng hiển thị 5 chỉ số dạng Card

    index_card_dict = {}
    for index, df in eod_index_dict.items():
        df["change_value"] = df["close"][::-1].diff()[::-1]
        df["change_percent"] = (df["close"][::-1].pct_change()[::-1]).round(4)

        index_card_dict[index] = df.iloc[0]

    index_card_df = (
        pd.DataFrame(index_card_dict)
        .transpose()
        .drop(["open", "high", "low"], axis=1)
        .reset_index(drop=True)
    )

    # - Dữ liệu cho bảng thông tin chung

    # Hàm tính độ rộng thị trường
    up_count, up_value, up_volume = 0, 0, 0
    down_count, down_value, down_volume = 0, 0, 0
    unchange_count, unchange_value, unchange_volume = 0, 0, 0

    for stock, df in eod_stock_dict.items():
        open_price = df["open"].iloc[0].item()
        current_price = df["close"].iloc[0].item()
        price_change = current_price - open_price
        if price_change > 0:
            up_count += 1
            up_volume += df["volume"].iloc[0].item()
            up_value += df["close"].iloc[0].item() * 1000 * df["volume"].iloc[0].item()
        elif price_change < 0:
            down_count += 1
            down_volume += df["volume"].iloc[0].item()
            down_value += (
                df["close"].iloc[0].item() * 1000 * df["volume"].iloc[0].item()
            )
        else:
            unchange_count += 1
            unchange_volume += df["volume"].iloc[0].item()
            unchange_value += (
                df["close"].iloc[0].item() * 1000 * df["volume"].iloc[0].item()
            )

    market_info_df = pd.DataFrame(
        {
            "name": ["Tăng giá", "Giảm giá", "Không đổi"],
            "count": [up_count, down_count, unchange_count],
            "volume": [up_volume, down_volume, unchange_volume],
            "value": [
                up_value / 1000000000,
                down_value / 1000000000,
                unchange_value / 1000000000,
            ],
        }
    )

    # - Ghép bảng vẽ biểu đồ đường cho 5 chỉ số index

    temp_df1 = pd.DataFrame(eod_index_dict["VNINDEX"]["date"])
    for index, df in eod_index_dict.items():
        temp_df1[index] = df["close"]

    temp_df1 = temp_df1.melt(
        id_vars=["date"], var_name="index_name", value_name="value"
    )

    index_price_chart_df = pd.DataFrame()
    for time_span, name in zip([20, 50, 100], ["1M", "3M", "6M"]):
        for index_name in temp_df1["index_name"].unique():
            temp_df2 = temp_df1.loc[temp_df1["index_name"] == index_name].iloc[
                :time_span
            ]
            temp_df2["time_span"] = name
            index_price_chart_df = pd.concat([index_price_chart_df, temp_df2])

    # Tính bảng chỉ số tâm lý
    market_sentiment = time_series.copy()
    total_count = 0

    for stock, df in itd_score_dict.items():
        total_count += 1
        market_sentiment[stock] = df["t0_score"]

    market_sentiment["count"] = market_sentiment.iloc[:, 1:].apply(
        lambda row: (row > 0).sum(), axis=1
    )
    market_sentiment["total"] = total_count
    market_sentiment = market_sentiment[["date", "count", "total"]]
    market_sentiment["ratio"] = market_sentiment["count"] / market_sentiment["total"]
    market_sentiment["sentiment"] = market_sentiment["ratio"].apply(
        lambda x: (
            "Sợ hãi"
            if x < 0.2
            else (
                "Tiêu cực"
                if (x >= 0.2) & (x < 0.4)
                else (
                    "Trung lập"
                    if (x >= 0.4) & (x < 0.6)
                    else ("Tích cực" if (x >= 0.6) & (x < 0.8) else "Hưng phấn")
                )
            )
        )
    )

    # Nhân 100 giá trị của cột hệ số
    market_sentiment["ratio"] = market_sentiment["ratio"] * 100

    # Thêm các cột giá trị cuối để tạp card trong power bi
    market_sentiment["last_ratio"] = market_sentiment["ratio"].iloc[0]
    market_sentiment["last_sentiment"] = market_sentiment["sentiment"].iloc[0]

    # Hiệu chỉnh lại theo khung thời gian ITD
    market_sentiment = itd_series.merge(market_sentiment, on="date", how="left")

    # - Khối ngoại và tự doanh

    # Tạo dữ liệu mua bán phiên hiện tại khối ngoại và tự doanh
    def calculate_nn_td_buy_sell(index_name):
        temp_dict_nn = {}
        temp_dict_nn["KLGD_NN"] = (
            index_td_nn_dict[f"{index_name}_NN"]
            .iloc[0][["buy_volume", "sell_volume", "net_volume"]]
            .tolist()
        )
        temp_dict_nn["GTGD_NN"] = (
            index_td_nn_dict[f"{index_name}_NN"]
            .iloc[0][["buy_value", "sell_value", "net_value"]]
            .tolist()
        )
        nn_buy_sell_df = pd.DataFrame.from_dict(
            temp_dict_nn, orient="index"
        ).reset_index()
        nn_buy_sell_df.columns = ["type", "Mua", "Bán", "Mua-Bán"]
        nn_buy_sell_df = nn_buy_sell_df.set_index("type").transpose()

        temp_dict_td = {}
        temp_dict_td["KLGD_TD"] = (
            index_td_nn_dict[f"{index_name}_TD"]
            .iloc[0][["buy_volume", "sell_volume", "net_volume"]]
            .tolist()
        )
        temp_dict_td["GTGD_TD"] = (
            index_td_nn_dict[f"{index_name}_TD"]
            .iloc[0][["buy_value", "sell_value", "net_value"]]
            .tolist()
        )
        td_buy_sell_df = pd.DataFrame.from_dict(
            temp_dict_td, orient="index"
        ).reset_index()
        td_buy_sell_df.columns = ["type", "Mua", "Bán", "Mua-Bán"]
        td_buy_sell_df = td_buy_sell_df.set_index("type").transpose()

        nn_td_buy_sell_df = pd.concat([nn_buy_sell_df, td_buy_sell_df], axis=1)
        nn_td_buy_sell_df["order"] = [1, 2, 3]

        return nn_td_buy_sell_df

    nn_td_buy_sell_hsx = calculate_nn_td_buy_sell("VNINDEX")
    nn_td_buy_sell_hsx["id"] = "HSX"
    nn_td_buy_sell_hsx["order_id"] = 1
    nn_td_buy_sell_hnx = calculate_nn_td_buy_sell("HNXINDEX")
    nn_td_buy_sell_hnx["id"] = "HNX"
    nn_td_buy_sell_hnx["order_id"] = 2
    nn_td_buy_sell_upcom = calculate_nn_td_buy_sell("UPINDEX")
    nn_td_buy_sell_upcom["id"] = "UPCOM"
    nn_td_buy_sell_upcom["order_id"] = 3

    nn_td_buy_sell_df = (
        pd.concat(
            [nn_td_buy_sell_hsx, nn_td_buy_sell_hnx, nn_td_buy_sell_upcom], axis=0
        )
        .reset_index()
        .rename(columns={"index": "type"})
    )

    # Tạo dữ liệu lịch sử 20p khối ngoại và tự doanh
    nn_20p_df_hsx = (
        index_td_nn_dict["VNINDEX_NN"][["date", "net_value"]]
        .iloc[:20]
        .rename(columns={"net_value": "nn_value"})
    )
    td_20p_df_hsx = (
        index_td_nn_dict["VNINDEX_TD"][["date", "net_value"]]
        .iloc[:20]
        .rename(columns={"net_value": "td_value"})
    )
    nn_td_20p_df_hsx = nn_20p_df_hsx.merge(td_20p_df_hsx, how="left", on="date")
    nn_td_20p_df_hsx["id"] = "HSX"

    nn_20p_df_hnx = (
        index_td_nn_dict["HNXINDEX_NN"][["date", "net_value"]]
        .iloc[:20]
        .rename(columns={"net_value": "nn_value"})
    )
    td_20p_df_hnx = (
        index_td_nn_dict["HNXINDEX_TD"][["date", "net_value"]]
        .iloc[:20]
        .rename(columns={"net_value": "td_value"})
    )
    nn_td_20p_df_hnx = nn_20p_df_hnx.merge(td_20p_df_hnx, how="left", on="date")
    nn_td_20p_df_hnx["id"] = "HNX"

    nn_20p_df_upcom = (
        index_td_nn_dict["UPINDEX_NN"][["date", "net_value"]]
        .iloc[:20]
        .rename(columns={"net_value": "nn_value"})
    )
    td_20p_df_upcom = (
        index_td_nn_dict["UPINDEX_TD"][["date", "net_value"]]
        .iloc[:20]
        .rename(columns={"net_value": "td_value"})
    )
    nn_td_20p_df_upcom = nn_20p_df_upcom.merge(td_20p_df_upcom, how="left", on="date")
    nn_td_20p_df_upcom["id"] = "UPCOM"

    nn_td_20p_df = pd.concat(
        [nn_td_20p_df_hsx, nn_td_20p_df_hnx, nn_td_20p_df_upcom], axis=0
    )

    def create_nn_td_top_stock(stock_dict):
        today = date_series["date"][0]
        yesterday = date_series["date"][1]
        the_day_before = date_series["date"][2]

        # Tạo ra top cổ phiếu mua bán của NN
        top_stock_dict = {}
        for stock, df in stock_dict.items():
            if not df.empty:
                if df["date"][0] == today:
                    top_stock_dict[stock] = df.iloc[0, 1:].tolist()
                elif df["date"][0] == yesterday:
                    top_stock_dict[stock] = df.iloc[0, 1:].tolist()
                elif df["date"][0] == the_day_before:
                    top_stock_dict[stock] = df.iloc[0, 1:].tolist()
        top_stock_df = pd.DataFrame.from_dict(
            top_stock_dict, orient="index"
        ).reset_index()
        top_stock_df.columns = df.columns
        top_stock_df["net_values"] = (
            top_stock_df["buy_value"] - top_stock_df["sell_value"]
        ) / 1000000000
        top_stock_df["stock"] = top_stock_df["stock"].apply(lambda x: x[:3])

        top_sell = (
            top_stock_df[top_stock_df["net_values"] < 0]
            .sort_values("net_values")[["stock", "date", "net_values"]]
            .rename(columns={"stock": "sell_stock", "net_values": "sell_value"})
            .reset_index(drop=True)
            .head(20)
        )
        top_buy = (
            top_stock_df[top_stock_df["net_values"] > 0]
            .sort_values("net_values", ascending=False)[["stock", "net_values"]]
            .rename(columns={"stock": "buy_stock", "net_values": "buy_value"})
            .reset_index(drop=True)
            .head(20)
        )
        top_stock_df = pd.concat([top_sell, top_buy], axis=1)

        return top_stock_df

    try:
        nn_top_stock_hsx = create_nn_td_top_stock(
            {
                k: v
                for k, v in stock_nn_dict.items()
                if k[:3]
                in stock_classification[stock_classification["exchange"] == "HSX"][
                    "stock"
                ].tolist()
            }
        )
        nn_top_stock_hsx.columns = [
            "nn_sell_stock",
            "nn_date",
            "nn_sell_value",
            "nn_buy_stock",
            "nn_buy_value",
        ]
    except:
        nn_top_stock_hnx = pd.DataFrame(
            columns=[
                "nn_sell_stock",
                "nn_date",
                "nn_sell_value",
                "nn_buy_stock",
                "nn_buy_value",
            ]
        )
    try:
        td_top_stock_hsx = create_nn_td_top_stock(
            {
                k: v
                for k, v in stock_td_dict.items()
                if k[:3]
                in stock_classification[stock_classification["exchange"] == "HSX"][
                    "stock"
                ].tolist()
            }
        )
        td_top_stock_hsx.columns = [
            "td_sell_stock",
            "td_date",
            "td_sell_value",
            "td_buy_stock",
            "td_buy_value",
        ]
    except:
        td_top_stock_hsx = pd.DataFrame(
            columns=[
                "td_sell_stock",
                "td_date",
                "td_sell_value",
                "td_buy_stock",
                "td_buy_value",
            ]
        )

    nn_td_top_stock_hsx = pd.concat([nn_top_stock_hsx, td_top_stock_hsx], axis=1)
    nn_td_top_stock_hsx["id"] = "HSX"

    try:
        nn_top_stock_hnx = create_nn_td_top_stock(
            {
                k: v
                for k, v in stock_nn_dict.items()
                if k[:3]
                in stock_classification[stock_classification["exchange"] == "HNX"][
                    "stock"
                ].tolist()
            }
        )
        nn_top_stock_hnx.columns = [
            "nn_sell_stock",
            "nn_date",
            "nn_sell_value",
            "nn_buy_stock",
            "nn_buy_value",
        ]
    except:
        nn_top_stock_hnx = pd.DataFrame(
            columns=[
                "nn_sell_stock",
                "nn_date",
                "nn_sell_value",
                "nn_buy_stock",
                "nn_buy_value",
            ]
        )

    try:
        td_top_stock_hnx = create_nn_td_top_stock(
            {
                k: v
                for k, v in stock_td_dict.items()
                if k[:3]
                in stock_classification[stock_classification["exchange"] == "HNX"][
                    "stock"
                ].tolist()
            }
        )
        td_top_stock_hnx.columns = [
            "td_sell_stock",
            "td_date",
            "td_sell_value",
            "td_buy_stock",
            "td_buy_value",
        ]
    except:
        td_top_stock_hnx = pd.DataFrame(
            columns=[
                "td_sell_stock",
                "td_date",
                "td_sell_value",
                "td_buy_stock",
                "td_buy_value",
            ]
        )

    nn_td_top_stock_hnx = pd.concat([nn_top_stock_hnx, td_top_stock_hnx], axis=1)
    nn_td_top_stock_hnx["id"] = "HNX"

    try:
        nn_top_stock_upcom = create_nn_td_top_stock(
            {
                k: v
                for k, v in stock_nn_dict.items()
                if k[:3]
                in stock_classification[stock_classification["exchange"] == "UPCOM"][
                    "stock"
                ].tolist()
            }
        )
        nn_top_stock_upcom.columns = [
            "nn_sell_stock",
            "nn_date",
            "nn_sell_value",
            "nn_buy_stock",
            "nn_buy_value",
        ]
    except:
        nn_top_stock_upcom = pd.DataFrame(
            columns=[
                "td_sell_stock",
                "td_date",
                "td_sell_value",
                "td_buy_stock",
                "td_buy_value",
            ]
        )

    try:
        td_top_stock_upcom = create_nn_td_top_stock(
            {
                k: v
                for k, v in stock_td_dict.items()
                if k[:3]
                in stock_classification[stock_classification["exchange"] == "UPCOM"][
                    "stock"
                ].tolist()
            }
        )
        td_top_stock_upcom.columns = [
            "td_sell_stock",
            "td_date",
            "td_sell_value",
            "td_buy_stock",
            "td_buy_value",
        ]
    except:
        td_top_stock_upcom = pd.DataFrame(
            columns=[
                "td_sell_stock",
                "td_date",
                "td_sell_value",
                "td_buy_stock",
                "td_buy_value",
            ]
        )

    nn_td_top_stock_upcom = pd.concat([nn_top_stock_upcom, td_top_stock_upcom], axis=1)
    nn_td_top_stock_upcom["id"] = "UPCOM"

    nn_td_top_stock = pd.concat(
        [nn_td_top_stock_hsx, nn_td_top_stock_hnx, nn_td_top_stock_upcom], axis=0
    )

    # - Dữ liệu top 10 cổ phiếu tiền vào và tiền ra

    market_top_10 = (
        eod_score_df[
            [
                "stock",
                "industry_name",
                "industry_perform",
                "marketcap_group",
                "close",
                "price_change",
                "t0_score",
                "liquid_ratio",
            ]
        ]
        .sort_values("t0_score", ascending=False)
        .iloc[:10]
    )
    market_top_10["type"] = "top"

    market_low_10 = (
        eod_score_df[
            [
                "stock",
                "industry_name",
                "industry_perform",
                "marketcap_group",
                "close",
                "price_change",
                "t0_score",
                "liquid_ratio",
            ]
        ]
        .sort_values("t0_score", ascending=True)
        .iloc[:10]
    )
    market_low_10["type"] = "low"

    market_top_stock = pd.concat([market_top_10, market_low_10], axis=0).reset_index(
        drop=True
    )

    # #### Page 2: Dòng tiền thị trường

    # - Tính toán độ rộng của tất cả nhóm cổ phiếu trong phiên T0

    # Hàm tính độ rộng thị trường
    def calculate_breadth(name, stock_list):
        up_count = 0
        down_count = 0

        for stock, df in eod_score_dict.items():
            if stock in stock_list:
                if df["t0_score"].iloc[0].item() >= 0:
                    up_count += 1
                if df["t0_score"].iloc[0].item() < 0:
                    down_count += 1

        return [name, up_count, down_count]

    # Lấy các giá trị duy nhất từng cột và chuyển thành danh sách
    industry_names = stock_classification["industry_name"].unique().tolist()
    industry_performs = stock_classification["industry_perform"].unique().tolist()
    marketcap_groups = stock_classification["marketcap_group"].unique().tolist()

    # Gộp các danh sách lại thành một
    group_stock_name_list = (
        ["all_stock"] + industry_names + industry_performs + marketcap_groups
    )

    market_breath_list = []
    for name in group_stock_name_list:
        if name == "all_stock":
            market_breath_list.append(
                calculate_breadth(name, stock_classification_filtered["stock"].tolist())
            )
        elif name in industry_names:
            market_breath_list.append(
                calculate_breadth(
                    name,
                    stock_classification_filtered[
                        stock_classification_filtered["industry_name"] == name
                    ]["stock"].tolist(),
                )
            )
        elif name in industry_performs:
            market_breath_list.append(
                calculate_breadth(
                    name,
                    stock_classification_filtered[
                        stock_classification_filtered["industry_perform"] == name
                    ]["stock"].tolist(),
                )
            )
        elif name in marketcap_groups:
            market_breath_list.append(
                calculate_breadth(
                    name,
                    stock_classification_filtered[
                        stock_classification_filtered["marketcap_group"] == name
                    ]["stock"].tolist(),
                )
            )

    market_breath_df = pd.DataFrame(
        market_breath_list, columns=["name", "in_flow", "out_flow"]
    )
    market_breath_df["group"] = market_breath_df["name"].map(group_map_dict)
    market_breath_df["order"] = market_breath_df["name"].map(order_map_dict)
    market_breath_df["name"] = market_breath_df["name"].map(name_map_dict)

    # Thêm thứ tự theo dòng tiền của các nhóm vào bảng độ rộng
    temp_df = itd_score_liquidity_last[
        itd_score_liquidity_last["group"].isin(["A", "B", "C", "D"])
    ]
    temp_df = (
        temp_df.sort_values("score", ascending=False)["name"]
        .reset_index(drop=True)
        .reset_index()
    )
    industry_breath_df = market_breath_df[
        market_breath_df["group"].isin(["A", "B", "C", "D"])
    ].drop(columns=["group", "order"])
    industry_breath_df = industry_breath_df.merge(temp_df, on="name", how="inner")

    # Thêm cột thứ tự vào bảng liquid các ngành
    itd_score_liquidity_last = itd_score_liquidity_last.merge(
        temp_df, on="name", how="left"
    )
    market_breath_df = market_breath_df.merge(temp_df, on="name", how="left")

    # Tạo bảng chỉ số dòng tiền T0 tới T5
    group_score_df_5p = eod_group_score_df.iloc[:5, :-4]
    group_score_df_5p["id"] = ["T-0", "T-1", "T-2", "T-3", "T-4"]
    group_score_df_5p = (
        group_score_df_5p.drop(columns=["date"], axis=1)
        .set_index("id")
        .transpose()
        .reset_index()
        .rename(columns={"index": "name"})
    )
    group_score_df_5p["score"] = group_score_df_5p[
        ["T-0", "T-1", "T-2", "T-3", "T-4"]
    ].sum(axis=1)
    group_score_df_5p["rank"] = group_score_df_5p["score"].rank()

    group_score_df_5p["group"] = group_score_df_5p["name"].map(group_map_dict)
    group_score_df_5p["order"] = group_score_df_5p["name"].map(order_map_dict)
    group_score_df_5p["name"] = group_score_df_5p["name"].map(name_map_dict)

    # - Bảng xếp hạng 23 ngành theo thứ tự từ trên xuống dưới

    full_industry_ranking = eod_group_score_df[
        [
            "date",
            "ban_le",
            "bao_hiem",
            "bds",
            "bds_kcn",
            "chung_khoan",
            "cong_nghe",
            "cong_nghiep",
            "dau_khi",
            "det_may",
            "dulich_dv",
            "dv_hatang",
            "hoa_chat",
            "htd",
            "khoang_san",
            "ngan_hang",
            "tai_chinh",
            "thep",
            "thuc_pham",
            "thuy_san",
            "van_tai",
            "vlxd",
            "xd",
            "y_te",
        ]
    ]

    for column in full_industry_ranking.columns[1:]:
        full_industry_ranking[column] = (
            full_industry_ranking[column][::-1].rolling(window=5).mean()[::-1]
        )

    full_industry_ranking = (
        pd.DataFrame(full_industry_ranking.iloc[0, 1:])
        .rename(columns={0: "score"})
        .reset_index()
    )
    full_industry_ranking.columns = ["name", "score"]
    full_industry_ranking["type"] = full_industry_ranking["score"].apply(
        lambda x: "Tiền vào" if x >= 0 else "Tiền ra"
    )
    full_industry_ranking["rank"] = full_industry_ranking["score"].rank(
        ascending=False, method="min"
    )
    full_industry_ranking["name"] = full_industry_ranking["name"].map(name_map_dict)

    # #### Page 3: Phân tích nhóm ngành

    # - Biểu đồ đường thể hiện index các nhóm cổ phiếu

    def calculate_index(stock_group, name):
        price_index_date_series_copy = copy.deepcopy(price_index_date_series)

        for stock, df in stock_group[name].items():
            price_index_date_series_copy[stock] = df["close"]
            price_index_date_series_copy[stock] = price_index_date_series_copy[stock][
                ::-1
            ].pct_change()[::-1]

        price_index_date_series_copy["total_change"] = (
            price_index_date_series_copy.iloc[:, 1:].sum(axis=1)
        )
        price_index_date_series_copy["total_change"] = (
            price_index_date_series_copy["total_change"] / len(stock_group[name])
        ) * 100
        price_index_date_series_copy["total_change"] = (
            price_index_date_series_copy["total_change"] * 10
        )
        price_index_date_series_copy["index_value"] = (
            price_index_date_series_copy["total_change"][::-1].cumsum()[::-1] + 1000
        )

        return price_index_date_series_copy["index_value"]

    # Lấy ra một date_series bao gồm năm nay và 2 năm trước
    price_index_date_series = pd.DataFrame(eod_index_dict["VNINDEX"]["date"])
    previous_year = price_index_date_series["date"].iloc[0].year - 2
    price_index_date_series = price_index_date_series.loc[
        price_index_date_series["date"]
        > pd.Timestamp(year=previous_year, month=1, day=1)
    ]

    temp_df1 = price_index_date_series.copy()

    for group, df in eod_industry_name.items():
        temp_df1[group] = calculate_index(eod_industry_name, group)

    for group, df in eod_industry_perform.items():
        temp_df1[group] = calculate_index(eod_industry_perform, group)

    for group, df in eod_marketcap_group.items():
        temp_df1[group] = calculate_index(eod_marketcap_group, group)

    # Gộp lại thành bảng dọc
    temp_df1 = temp_df1.melt(
        id_vars=["date"], var_name="group_name", value_name="value"
    )
    temp_df1["group_name"] = temp_df1["group_name"].map(name_map_dict)

    # Lặp lại thành các khung thời gian
    group_stock_price_index = pd.DataFrame()
    for time_span, name in zip([20, 50, 100], ["1M", "3M", "6M"]):
        for index_name in temp_df1["group_name"].unique():
            temp_df2 = temp_df1.loc[temp_df1["group_name"] == index_name].iloc[
                :time_span
            ]
            temp_df2["time_span"] = name
            group_stock_price_index = pd.concat([group_stock_price_index, temp_df2])

    # - Biểu đồ diễn biến xếp hạng của nhóm cổ phiếu trong 20p

    group_score_ranking_melted = group_score_ranking.iloc[:20].melt(
        id_vars=["date"], var_name="group_name", value_name="value"
    )
    group_score_ranking_melted.columns = ["date", "group_name", "rank"]
    group_score_ranking_melted["group_name"] = group_score_ranking_melted[
        "group_name"
    ].map(name_map_dict)

    # - Top cổ phiếu tích cực trong nhóm

    group_stock_top_10_df = pd.DataFrame()

    for group in group_stock_list:
        if group in stock_classification_filtered["industry_name"].unique().tolist():
            temp_group_stock_list = stock_classification_filtered[
                stock_classification_filtered["industry_name"] == group
            ]["stock"].tolist()
        elif (
            group in stock_classification_filtered["industry_perform"].unique().tolist()
        ):
            temp_group_stock_list = stock_classification_filtered[
                stock_classification_filtered["industry_perform"] == group
            ]["stock"].tolist()
        elif (
            group in stock_classification_filtered["marketcap_group"].unique().tolist()
        ):
            temp_group_stock_list = stock_classification_filtered[
                stock_classification_filtered["marketcap_group"] == group
            ]["stock"].tolist()
        else:
            temp_group_stock_list = []

        group_stock_df = eod_score_df[
            eod_score_df["stock"].isin(temp_group_stock_list)
        ][
            [
                "stock",
                "industry_name",
                "industry_perform",
                "marketcap_group",
                "close",
                "price_change",
                "t0_score",
                "t5_score",
                "liquid_ratio",
                "rank",
            ]
        ]

        group_stock_top_10 = group_stock_df.sort_values(
            "t0_score", ascending=False
        ).iloc[:10]
        group_stock_top_10["name"] = group
        group_stock_top_10_df = pd.concat(
            [group_stock_top_10_df, group_stock_top_10], axis=0
        )

    group_stock_top_10_df["name"] = group_stock_top_10_df["name"].map(name_map_dict)

    # #### Page 4: Phân tích cổ phiếu

    # - Biểu đồ giá cổ phiếu

    temp_df1 = pd.DataFrame(eod_index_dict["VNINDEX"]["date"])
    for stock in stock_classification_filtered["stock"].tolist():
        temp_df1[stock] = eod_all_stock["all_stock"][stock]["close"]

    temp_df1 = temp_df1.melt(id_vars=["date"], var_name="stock", value_name="value")

    # Pre-compute unique stocks and time spans
    unique_stocks = temp_df1["stock"].unique()
    time_spans = [20, 50]
    names = ["1M", "3M"]

    # Using groupby for efficient manipulation
    result_list = []
    for time_span, name in zip(time_spans, names):
        grouped = temp_df1.groupby("stock")
        for stock in unique_stocks:
            temp_df2 = grouped.get_group(stock).head(time_span)
            temp_df2["time_span"] = name
            result_list.append(temp_df2)

    # Concatenate all results outside the loop
    stock_price_chart_df = pd.concat(result_list, ignore_index=True)

    # - Biểu đồ dòng tiền và thanh khoản T0

    stock_liquidty_score_t0 = pd.DataFrame()
    for stock, df in itd_score_dict.items():
        temp_df = itd_series.merge(df, on="date", how="left")
        temp_df["stock"] = stock
        stock_liquidty_score_t0 = pd.concat(
            [
                stock_liquidty_score_t0,
                temp_df[["stock", "date", "t0_score", "liquid_ratio"]],
            ],
            axis=0,
        )

    # - Diễn biến xếp hạng dòng tiền cổ phiếu, tương quan dòng tiền, hệ số thanh khoản

    stock_score_power_df = pd.DataFrame()
    for stock, df in eod_score_dict.items():
        temp_df = date_series.copy().iloc[:20]
        temp_df["stock"] = stock
        temp_df["close"] = eod_score_dict[stock]["close"]
        temp_df["liquid_ratio"] = eod_score_dict[stock]["liquid_ratio"]
        temp_df["t0_score"] = eod_score_dict[stock]["t0_score"]
        temp_df["rank"] = eod_score_dict[stock]["rank"]
        temp_df["rank_t0"] = eod_score_dict[stock]["rank_t0"]
        temp_df["top_rank_check"] = temp_df["rank_t0"].apply(
            lambda x: 1 if x < temp_df["rank_t0"].max() * 0.1 else 0
        )
        temp_df["bot_rank_check"] = temp_df["rank_t0"].apply(
            lambda x: 1 if x > temp_df["rank_t0"].max() * 0.9 else 0
        )

        temp_df["score_change"] = (
            temp_df["t0_score"][::-1].cumsum()[::-1] - temp_df["t0_score"].iloc[-1]
        ) / 100
        temp_df["price_change"] = (
            temp_df["close"][::-1].pct_change()[::-1].fillna(0)[::-1].cumsum()[::-1]
        )

        stock_score_power_df = pd.concat([stock_score_power_df, temp_df], axis=0)

    # #### Page 5: Bộ lọc cổ phiếu

    stock_candle_df = pd.DataFrame(
        {
            key: df["df_candle"][
                [
                    "stock",
                    "from_week_open",
                    "from_week_last_high",
                    "from_week_last_low",
                    "from_month_open",
                    "from_month_last_high",
                    "from_month_last_low",
                    "from_quarter_open",
                    "from_quarter_last_high",
                    "from_quarter_last_low",
                    "from_year_open",
                    "from_year_last_high",
                    "from_year_last_low",
                ]
            ].iloc[0]
            for key, df in ta_stock_dict.items()
        }
    ).T.reset_index(drop=True)

    stock_pivot_df = pd.DataFrame(
        {
            key: df["df_pivot"][
                ["stock", "from_month_pivot", "from_quarter_pivot", "from_year_pivot"]
            ].iloc[0]
            for key, df in ta_stock_dict.items()
        }
    ).T.reset_index(drop=True)

    stock_ma_df = pd.DataFrame(
        {
            key: df["df_ma"][
                [
                    "stock",
                    "from_month_ma5",
                    "from_month_ma20",
                    "from_quarter_ma60",
                    "from_quarter_ma120",
                    "from_year_ma240",
                    "from_year_ma480",
                ]
            ].iloc[0]
            for key, df in ta_stock_dict.items()
        }
    ).T.reset_index(drop=True)

    stock_fibo_df = pd.DataFrame(
        {
            key: df["df_fibo"][
                [
                    "stock",
                    "from_month_fibo_382",
                    "from_month_fibo_500",
                    "from_month_fibo_618",
                    "from_quarter_fibo_382",
                    "from_quarter_fibo_500",
                    "from_quarter_fibo_618",
                    "from_year_fibo_382",
                    "from_year_fibo_500",
                    "from_year_fibo_618",
                ]
            ].iloc[0]
            for key, df in ta_stock_dict.items()
        }
    ).T.reset_index(drop=True)

    filter_stock_df = (
        eod_score_df.merge(stock_candle_df, on="stock", how="left")
        .merge(stock_pivot_df, on="stock", how="left")
        .merge(stock_ma_df, on="stock", how="left")
        .merge(stock_fibo_df, on="stock", how="left")
    )

    filter_stock_df["month_trend"] = filter_stock_df.apply(
        lambda x: (
            "Tăng mạnh"
            if (x["from_week_last_high"] >= 0) & (x["from_month_fibo_382"] >= 0)
            else (
                "Tăng"
                if (x["from_week_last_high"] < 0) & (x["from_month_fibo_382"] >= 0)
                else (
                    "Trung lập"
                    if (x["from_month_fibo_618"] >= 0) & (x["from_month_fibo_382"] < 0)
                    else (
                        "Giảm"
                        if (x["from_week_last_low"] >= 0)
                        & (x["from_month_fibo_618"] < 0)
                        else "Giảm mạnh"
                    )
                )
            )
        ),
        axis=1,
    )

    filter_stock_df["quarter_trend"] = filter_stock_df.apply(
        lambda x: (
            "Tăng mạnh"
            if (x["from_month_last_high"] >= 0) & (x["from_quarter_fibo_382"] >= 0)
            else (
                "Tăng"
                if (x["from_month_last_high"] < 0) & (x["from_quarter_fibo_382"] >= 0)
                else (
                    "Trung lập"
                    if (x["from_quarter_fibo_618"] >= 0)
                    & (x["from_quarter_fibo_382"] < 0)
                    else (
                        "Giảm"
                        if (x["from_month_last_low"] >= 0)
                        & (x["from_quarter_fibo_618"] < 0)
                        else "Giảm mạnh"
                    )
                )
            )
        ),
        axis=1,
    )

    filter_stock_df["year_trend"] = filter_stock_df.apply(
        lambda x: (
            "Tăng mạnh"
            if (x["from_quarter_last_high"] >= 0) & (x["from_year_fibo_382"] >= 0)
            else (
                "Tăng"
                if (x["from_quarter_last_high"] < 0) & (x["from_year_fibo_382"] >= 0)
                else (
                    "Trung lập"
                    if (x["from_year_fibo_618"] >= 0) & (x["from_year_fibo_382"] < 0)
                    else (
                        "Giảm"
                        if (x["from_quarter_last_low"] >= 0)
                        & (x["from_year_fibo_618"] < 0)
                        else "Giảm mạnh"
                    )
                )
            )
        ),
        axis=1,
    )

    # #### Lưu vào SQL

    from sqlalchemy import MetaData, create_engine, text

    # Thông tin kết nối cơ sở dữ liệu
    username = "twan"
    password = "chodom"
    database = "t2m"
    host = "14.225.192.30"
    port = "3306"
    engine = create_engine(
        f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
    )

    # #Xoá toàn bộ các bảng cũ
    # conn = engine.connect()
    # metadata = MetaData()
    # metadata.reflect(bind=engine)
    # for table in reversed(metadata.sorted_tables):
    #     table.drop(engine)
    # conn.close()

    # Hàm lưu dữ liệu vào sql
    def save_dataframe_to_sql(df, table_name, engine):
        temp_table_name = f"temp_{table_name}"
        if table_name == "stock_price_chart_df":
            index = False
        else:
            index = True

        df.to_sql(name=temp_table_name, con=engine, if_exists="replace", index=index)
        with engine.begin() as connection:
            connection.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
            connection.execute(
                text(f"ALTER TABLE {temp_table_name} RENAME TO {table_name}")
            )

    # Lưu DataFrame vào cơ sở dữ liệu
    save_dataframe_to_sql(update_time, "update_time", engine)
    save_dataframe_to_sql(index_card_df, "index_card_df", engine)
    save_dataframe_to_sql(market_info_df, "market_info_df", engine)
    save_dataframe_to_sql(index_price_chart_df, "index_price_chart_df", engine)
    save_dataframe_to_sql(ta_index_df, "ta_index_df", engine)
    save_dataframe_to_sql(nn_td_top_stock, "nn_td_top_stock", engine)
    save_dataframe_to_sql(nn_td_20p_df, "nn_td_20p_df", engine)
    save_dataframe_to_sql(nn_td_buy_sell_df, "nn_td_buy_sell_df", engine)
    save_dataframe_to_sql(market_sentiment, "market_sentiment", engine)
    save_dataframe_to_sql(itd_score_liquidity_df, "itd_score_liquidity_df", engine)
    save_dataframe_to_sql(itd_score_liquidity_last, "itd_score_liquidity_last", engine)
    save_dataframe_to_sql(market_ms, "market_ms", engine)
    save_dataframe_to_sql(market_top_stock, "market_top_stock", engine)
    save_dataframe_to_sql(group_score_week, "group_score_week", engine)
    save_dataframe_to_sql(group_score_month, "group_score_month", engine)
    save_dataframe_to_sql(
        eod_score_liquidity_melted, "eod_score_liquidity_melted", engine
    )
    save_dataframe_to_sql(market_breath_df, "market_breath_df", engine)
    save_dataframe_to_sql(group_score_df_5p, "group_score_df_5p", engine)
    save_dataframe_to_sql(group_score_ranking, "group_score_ranking", engine)
    save_dataframe_to_sql(eod_group_liquidity_df, "eod_group_liquidity_df", engine)
    save_dataframe_to_sql(full_industry_ranking, "full_industry_ranking", engine)
    save_dataframe_to_sql(
        group_score_ranking_melted, "group_score_ranking_melted", engine
    )
    save_dataframe_to_sql(
        itd_score_liquidity_melted, "itd_score_liquidity_melted", engine
    )
    save_dataframe_to_sql(eod_score_df, "eod_score_df", engine)
    save_dataframe_to_sql(group_stock_price_index, "group_stock_price_index", engine)
    save_dataframe_to_sql(group_stock_top_10_df, "group_stock_top_10_df", engine)
    save_dataframe_to_sql(stock_price_chart_df, "stock_price_chart_df", engine)
    save_dataframe_to_sql(ta_stock_df, "stock_ta_df", engine)
    save_dataframe_to_sql(stock_liquidty_score_t0, "stock_liquidty_score_t0", engine)
    save_dataframe_to_sql(stock_score_week, "stock_score_week", engine)
    save_dataframe_to_sql(stock_score_month, "stock_score_month", engine)
    save_dataframe_to_sql(stock_score_power_df, "stock_score_power_df", engine)
    save_dataframe_to_sql(filter_stock_df, "filter_stock_df", engine)


def get_current_time(start_time_am, end_time_am, start_time_pm, end_time_pm):
    if (dt.datetime.now()).weekday() <= 4:
        current_time = dt.datetime.now().time()
        if current_time < start_time_am:
            current_time = 0
        elif (current_time >= start_time_am) & (current_time < end_time_am):
            current_time = current_time
        elif (current_time >= end_time_am) & (current_time < start_time_pm):
            current_time = end_time_am
        elif (current_time >= start_time_pm) & (current_time < end_time_pm):
            current_time = current_time
        elif current_time >= end_time_pm:
            current_time = 1
        return current_time
    if (dt.datetime.now()).weekday() > 4:
        return None


# --------------------------------------------------------------------------------------------------------------
import datetime as dt
import time
from datetime import datetime

import pandas as pd

print("Dữ liệu đang được xử lý ...")

while True:
    try:
        start_time = time.time()
        current_time = get_current_time(
            dt.time(9, 00), dt.time(11, 30), dt.time(13, 00), dt.time(15, 10)
        )

        if current_time == 0:
            print(
                "Chưa tới thời gian giao dịch: ",
                dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            )
            time.sleep(60)
            continue
        elif current_time == 1:
            print(
                "Đã hết thời gian giao dịch: ",
                dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            )
            time.sleep(64000)
            continue
        elif current_time == None:
            print(
                "Ngày nghỉ không giao dịch: ",
                dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            )
            time.sleep(86400)
            continue

        date_series = pd.read_csv(
            "D:\\t2m-project\\ami-data\\ami_eod_data\\VNINDEX.csv"
        ).iloc[-1]
        date_series["date"] = pd.to_datetime(
            date_series["date"].astype(str), format="%y%m%d"
        )

        run_data()
        end_time = time.time()

        print(
            f"Updated: {datetime.combine(date_series['date'].date(), current_time).strftime('%d/%m/%Y %H:%M:%S')}, Completed in: {int(end_time - start_time)}s"
        )

    except Exception as e:
        print(f"Error: {type(e).__name__}")
