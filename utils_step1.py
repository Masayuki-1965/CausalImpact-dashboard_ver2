import os
import glob
import pandas as pd
import io

def get_csv_files(directory):
    files = glob.glob(os.path.join(directory, "*.csv"))
    return [os.path.basename(f) for f in files]

def load_and_clean_csv(path):
    try:
        # ファイルを読み込み
        try:
            # 最初にUTF-8として読み込みを試みる
            df = pd.read_csv(path, usecols=lambda c: c.strip() in ['ymd', 'qty'])
        except UnicodeDecodeError:
            # 日本語のエンコーディングで試みる
            for encoding in ['shift-jis', 'cp932', 'euc-jp']:
                try:
                    df = pd.read_csv(path, usecols=lambda c: c.strip() in ['ymd', 'qty'], encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
                except Exception:
                    continue
            else:
                # すべてのエンコーディングで失敗した場合はエラーを発生させる
                raise ValueError(f"ファイル {path} のエンコーディングを認識できませんでした。UTF-8、Shift-JIS、CP932、EUC-JPでのエンコーディングを試しましたが失敗しました。")
        
        # カラムが見つからない場合のエラーハンドリング
        if 'ymd' not in df.columns and 'qty' not in df.columns:
            # カラム名のクリーニングを試みる
            df.columns = [col.strip() for col in df.columns]
            
            # それでも見つからない場合はエラー
            if 'ymd' not in df.columns or 'qty' not in df.columns:
                raise ValueError(f"必須カラム 'ymd' と 'qty' が見つかりません。現在のカラム: {list(df.columns)}")
        
        # 日付処理
        df['ymd'] = df['ymd'].astype(str).str.zfill(8)
        df['ymd'] = pd.to_datetime(df['ymd'], format='%Y%m%d', errors='coerce')
        
        # 無効な日付の処理
        invalid_dates = df[df['ymd'].isna()]
        if not invalid_dates.empty:
            print(f"{len(invalid_dates)}件の無効な日付形式のデータを除外します。")
        
        # 欠損値を除外
        df = df.dropna(subset=['ymd'])
        
        # 数値変換チェック
        try:
            df['qty'] = pd.to_numeric(df['qty'], errors='coerce')
            if df['qty'].isna().any():
                print("数量(qty)に数値に変換できない値が含まれています。これらは欠損値として除外します。")
                df = df.dropna(subset=['qty'])
        except Exception as e:
            raise ValueError(f"数量(qty)の処理中にエラーが発生しました: {str(e)}")
        
        return df
    except Exception as e:
        # 例外をキャッチしてエラーメッセージを表示
        error_msg = f"ファイル {path} の読み込み中にエラーが発生しました: {str(e)}"
        print(error_msg)
        raise ValueError(error_msg)

def make_period_key(dt, freq):
    if freq == "月次":
        return dt.strftime('%Y-%m-01')
    elif freq == "旬次":
        day = dt.day
        if day <= 10:
            return dt.strftime('%Y-%m-01')
        elif day <= 20:
            return dt.strftime('%Y-%m-11')
        else:
            return dt.strftime('%Y-%m-21')
    else:
        return dt.strftime('%Y-%m-%d')

def aggregate_df(df, freq):
    df = df.copy()
    df['period'] = df['ymd'].apply(lambda x: make_period_key(x, freq))
    agg = df.groupby('period', as_index=False)['qty'].sum()
    agg['period'] = pd.to_datetime(agg['period'])
    return agg

def create_full_period_range(df1, df2, freq):
    df1_dates = pd.to_datetime(df1['ymd'])
    df2_dates = pd.to_datetime(df2['ymd'])
    start_date = max(df1_dates.min(), df2_dates.min())
    end_date = min(df1_dates.max(), df2_dates.max())
    if freq == "月次":
        periods = pd.date_range(
            start=start_date.replace(day=1),
            end=end_date.replace(day=1),
            freq='MS'
        )
    elif freq == "旬次":
        first_month = start_date.replace(day=1)
        last_month = end_date.replace(day=1)
        months = pd.date_range(start=first_month, end=last_month, freq='MS')
        periods = []
        for month in months:
            for day in [1, 11, 21]:
                date = month.replace(day=day)
                if start_date <= date <= end_date:
                    periods.append(date)
        periods = pd.DatetimeIndex(periods)
    else:
        periods = pd.date_range(start=start_date, end=end_date, freq='D')
    return periods

def format_stats_with_japanese(df):
    stats = df.describe().reset_index()
    stats.columns = ['統計項目', '数値']
    stats['統計項目'] = stats['統計項目'].replace({
        'count': 'count（個数）',
        'mean': 'mean（平均）',
        'std': 'std（標準偏差）',
        'min': 'min（最小値）',
        '25%': '25%（第1四分位数）',
        '50%': '50%（中央値）',
        '75%': '75%（第3四分位数）',
        'max': 'max（最大値）'
    })
    for i, row in stats.iterrows():
        if row['統計項目'] != 'count（個数）':
            stats.at[i, '数値'] = round(row['数値'], 2)
    return stats 