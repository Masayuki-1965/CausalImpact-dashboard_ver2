import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import io
from datetime import datetime
import base64
import tempfile
from PIL import Image
import plotly.io as pio
import plotly.figure_factory as ff
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as ReportLabImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# 外部モジュールimport
from causal_impact_translator import translate_causal_impact_report
from utils_step1 import get_csv_files, load_and_clean_csv, make_period_key, aggregate_df, create_full_period_range, format_stats_with_japanese
from utils_step2 import get_period_defaults, validate_periods, calc_period_days, build_analysis_params
from utils_step3 import run_causal_impact_analysis, build_summary_dataframe, get_summary_csv_download_link, get_figure_pdf_download_link, get_detail_csv_download_link

# 処置群のみ分析用モジュール
from utils_step3_single_group import (
    run_single_group_causal_impact_analysis, 
    validate_single_group_data, 
    suggest_intervention_point,
    build_single_group_summary_dataframe,
    get_single_group_interpretation
)

# リファクタリング後の外部モジュール
from config.constants import PAGE_CONFIG, CUSTOM_CSS_PATH
from config.help_texts import (
    DATA_FORMAT_GUIDE_HTML, FAQ_CAUSAL_IMPACT, FAQ_STATE_SPACE_MODEL,
    HEADER_CARD_HTML, STEP1_CARD_HTML, STEP2_CARD_HTML, STEP3_CARD_HTML,
    RESET_GUIDE_HTML, SIDEBAR_FLOW_DESCRIPTION
)
from utils_common import load_css, initialize_session_state, reset_session_state, get_step_status

# --- 初期化 ---
initialize_session_state()

# セッション状態に分析タイプを追加
if 'analysis_type' not in st.session_state:
    st.session_state.analysis_type = "標準分析（処置群 + 対照群）"

# --- 画面幅を最大化 ---
st.set_page_config(**PAGE_CONFIG)

# --- カスタムCSS読み込み ---
load_css(CUSTOM_CSS_PATH)

# --- サイドバー ---
with st.sidebar:
    st.markdown('<div class="sidebar-title">分析フロー</div>', unsafe_allow_html=True)
    st.markdown(SIDEBAR_FLOW_DESCRIPTION, unsafe_allow_html=True)
    
    # STEPのアクティブ状態を取得
    step_status = get_step_status()
    
    st.markdown(f"""
    <div style="margin-top:0.5em;">
        <div class="{'sidebar-step-active' if step_status['step1'] else 'sidebar-step-inactive'}">STEP 1：データ取り込み／可視化</div>
        <div class="{'sidebar-step-active' if step_status['step2'] else 'sidebar-step-inactive'}">STEP 2：分析期間／パラメータ設定</div>
        <div class="{'sidebar-step-active' if step_status['step3'] else 'sidebar-step-inactive'}">STEP 3：分析実行／結果確認</div>
    </div>
    <div class="separator-line"></div>
    """, unsafe_allow_html=True)
    
    # 最初からやり直す案内文
    st.markdown('<div style="margin-top:15px;margin-bottom:10px;"></div>', unsafe_allow_html=True)
    st.markdown(RESET_GUIDE_HTML, unsafe_allow_html=True)

    with st.expander("Causal Impactとは？", expanded=False):
        st.markdown(FAQ_CAUSAL_IMPACT, unsafe_allow_html=True)
    with st.expander("状態空間モデルとは？", expanded=False):
        st.markdown(FAQ_STATE_SPACE_MODEL, unsafe_allow_html=True)

# --- メインコンテンツ ---
st.markdown(HEADER_CARD_HTML, unsafe_allow_html=True)

st.markdown(STEP1_CARD_HTML, unsafe_allow_html=True)

# --- データ形式ガイド ---
with st.expander("データ形式ガイド", expanded=False):
    st.markdown(DATA_FORMAT_GUIDE_HTML, unsafe_allow_html=True)

# --- ファイル選択UIの代わりにファイルアップロード機能 ---
st.markdown('<div class="section-title">分析対象ファイルのアップロード</div>', unsafe_allow_html=True)

# 分析タイプの選択
st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">分析タイプの選択</div>', unsafe_allow_html=True)
analysis_type = st.radio(
    "分析タイプ選択",
    options=["二群比較（処置群＋対照群を使用）", "単群推定（処置群のみを使用）"],
    index=0,
    label_visibility="collapsed",
    help="二群比較は処置群と対照群の両方を比較します。単群推定は処置群のみで介入前後のトレンド変化を分析します。"
)

# 分析タイプをセッション状態に保存
st.session_state.analysis_type = analysis_type

# 分析タイプによって説明を表示
if analysis_type == "単群推定（処置群のみを使用）":
    st.info("単群推定では、介入前のデータから季節性やトレンドを学習し、介入後の予測値（反事実シナリオ）と実測値を比較して効果を測定します。")
else:
    st.info("二群比較では、介入の影響を受けた処置群と、影響を受けていない対照群の関係性をもとに、介入後の予測値と実測値を比較して効果を測定します。")

# アップロード方法切り替えのラジオボタン
st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;margin-top:1em;">アップロード方法の選択</div>', unsafe_allow_html=True)
upload_method = st.radio(
    "アップロード方法選択",
    options=["ファイルアップロード（※日本語ファイル名は非対応／英数字のみ使用可）", "CSVテキスト直接入力"],
    index=0,
    label_visibility="collapsed",
    help="CSVデータを直接入力する方法と、ファイルをアップロードする方法があります。"
)

# 変数の初期化（エラー防止）
treatment_file = None
control_file = None
treatment_csv = ""
control_csv = ""
treatment_name = "処置群"
control_name = "対照群"
read_btn_upload = False
read_btn_text = False
read_btn_single_upload = False
read_btn_single_text = False

# 分析タイプに応じてUIを切り替え
if analysis_type == "二群比較（処置群＋対照群を使用）":
    # 既存の標準分析UI
    if upload_method == "ファイルアップロード（※日本語ファイル名は非対応／英数字のみ使用可）":
        # 処置群と対照群の名称入力欄（ファイルアップロード・CSVテキスト共通）
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群データ</div>', unsafe_allow_html=True)
            
            treatment_file = st.file_uploader(
                "処置群のCSVファイルをアップロード", 
                type=['csv'], 
                key="treatment_upload", 
                help="処置群（効果を測定したい対象）のCSVファイルをアップロードしてください。",
                accept_multiple_files=False,
                label_visibility="collapsed"
            )
            
            if treatment_file:
                file_basename = os.path.splitext(treatment_file.name)[0]
                treatment_name = file_basename
                selected_treat = f"選択：{treatment_file.name}（処置群）"
                st.markdown(f'<div style="color:#1976d2;font-size:0.9em;">{selected_treat}</div>', unsafe_allow_html=True)
            else:
                treatment_name = "処置群"
                
            treatment_name = st.text_input("処置群の名称を入力", value=treatment_name, key="treatment_name_upload", help="処置群の名称を入力してください（例：商品A、店舗B など）")
            
        with col2:
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">対照群データ</div>', unsafe_allow_html=True)
            
            control_file = st.file_uploader(
                "対照群のCSVファイルをアップロード", 
                type=['csv'], 
                key="control_upload", 
                help="対照群（比較対象）のCSVファイルをアップロードしてください。",
                accept_multiple_files=False,
                label_visibility="collapsed"
            )
            
            if control_file:
                file_basename = os.path.splitext(control_file.name)[0]
                control_name = file_basename
                selected_ctrl = f"選択：{control_file.name}（対照群）"
                st.markdown(f'<div style="color:#1976d2;font-size:0.9em;">{selected_ctrl}</div>', unsafe_allow_html=True)
            else:
                control_name = "対照群"
                
            control_name = st.text_input("対照群の名称を入力", value=control_name, key="control_name_upload", help="対照群の名称を入力してください（例：商品B、店舗C など）")
        
        # データ読み込みボタン（標準分析・ファイルアップロード用）
        st.markdown('<div style="margin-top:25px;"></div>', unsafe_allow_html=True)
        read_btn_upload = st.button("データを読み込む", key="read_upload", help="アップロードしたファイルを読み込みます。", type="primary", use_container_width=True, disabled=(not treatment_file or not control_file))

    else:
        # CSVテキスト直接入力のUI（標準分析）
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群データ</div>', unsafe_allow_html=True)
            treatment_name = st.text_input("処置群の名称を入力", value="処置群", key="treatment_name_text", help="処置群の名称を入力してください（例：商品A、店舗B など）")
            
            treatment_csv = st.text_area(
                "CSVデータを入力（カンマ・タブ・スペース区切り）",
                height=200,
                help="CSVデータを直接入力またはコピペしてください。最低限、ymd（日付）とqty（数量）の列が必要です。",
                placeholder="ymd,qty\n20170403,29\n20170425,24\n20170426,23\n20170523,24\n20170524,26"
            )
            st.markdown('<div style="color:#555555;font-size:0.9em;margin-top:-5px;margin-bottom:15px;padding-left:5px;">（上の入力欄にCSVデータをコピペしてください）</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">対照群データ</div>', unsafe_allow_html=True)
            control_name = st.text_input("対照群の名称を入力", value="対照群", key="control_name_text", help="対照群の名称を入力してください（例：商品B、店舗C など）")
            
            control_csv = st.text_area(
                "CSVデータを入力（カンマ・タブ・スペース区切り）",
                height=200,
                help="CSVデータを直接入力またはコピペしてください。最低限、ymd（日付）とqty（数量）の列が必要です。",
                placeholder="ymd,qty\n20170403,35\n20170425,30\n20170426,28\n20170523,29\n20170524,31"
            )
            st.markdown('<div style="color:#555555;font-size:0.9em;margin-top:-5px;margin-bottom:15px;padding-left:5px;">（上の入力欄にCSVデータをコピペしてください）</div>', unsafe_allow_html=True)
        
        # データ読み込みボタン（標準分析・CSVテキスト直接入力用）
        st.markdown('<div style="margin-top:25px;"></div>', unsafe_allow_html=True)
        read_btn_text = st.button("データを読み込む", key="read_text", help="入力したCSVデータを読み込みます。", type="primary", use_container_width=True, disabled=(not treatment_csv or not control_csv))

else:
    # 単群推定UI
    if upload_method == "ファイルアップロード（※日本語ファイル名は非対応／英数字のみ使用可）":
        st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群データ</div>', unsafe_allow_html=True)
        
        treatment_file = st.file_uploader(
            "処置群のCSVファイルをアップロード", 
            type=['csv'], 
            key="treatment_single_upload", 
            help="処置群（効果を測定したい対象）のCSVファイルをアップロードしてください。",
            accept_multiple_files=False,
            label_visibility="collapsed"
        )
        
        if treatment_file:
            file_basename = os.path.splitext(treatment_file.name)[0]
            treatment_name = file_basename
            selected_treat = f"選択：{treatment_file.name}（単群推定）"
            st.markdown(f'<div style="color:#1976d2;font-size:0.9em;">{selected_treat}</div>', unsafe_allow_html=True)
        else:
            treatment_name = "処置群"
            
        treatment_name = st.text_input("処置群の名称を入力", value=treatment_name, key="treatment_name_single_upload", help="処置群の名称を入力してください（例：商品A、店舗B など）")
        
        # データ読み込みボタン（処置群のみ・ファイルアップロード用）
        st.markdown('<div style="margin-top:25px;"></div>', unsafe_allow_html=True)
        read_btn_single_upload = st.button("データを読み込む", key="read_single_upload", help="アップロードしたファイルを読み込みます。", type="primary", use_container_width=True, disabled=(not treatment_file))

    else:
        # CSVテキスト直接入力のUI（処置群のみ）
        st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群データ</div>', unsafe_allow_html=True)
        treatment_name = st.text_input("処置群の名称を入力", value="処置群", key="treatment_name_single_text", help="処置群の名称を入力してください（例：商品A、店舗B など）")
        
        treatment_csv = st.text_area(
            "CSVデータを入力（カンマ・タブ・スペース区切り）",
            height=300,
            help="CSVデータを直接入力またはコピペしてください。最低限、ymd（日付）とqty（数量）の列が必要です。単群推定では最低37日間のデータが推奨されます。",
            placeholder="ymd,qty\n20170403,29\n20170425,24\n20170426,23\n20170523,24\n20170524,26\n...\n（介入前後を含む十分なデータを入力）"
        )
        st.markdown('<div style="color:#555555;font-size:0.9em;margin-top:-5px;margin-bottom:15px;padding-left:5px;">（最低37日間のデータを推奨、介入前期間は全体の60%以上が必要）</div>', unsafe_allow_html=True)
        
        # データ読み込みボタン（処置群のみ・CSVテキスト直接入力用）
        st.markdown('<div style="margin-top:25px;"></div>', unsafe_allow_html=True)
        read_btn_single_text = st.button("データを読み込む", key="read_single_text", help="入力したCSVデータを読み込みます。", type="primary", use_container_width=True, disabled=(not treatment_csv))

# --- アップロードされたファイルからデータを読み込む関数 ---
def load_and_clean_uploaded_csv(uploaded_file):
    try:
        # ファイル名をログに出力（デバッグ用）
        file_name = uploaded_file.name
        print(f"処理中のファイル: {file_name}")
        
        # バイト列を読み込み
        file_bytes = uploaded_file.getvalue()
        
        # エンコーディング検出の試行回数を増やす
        encodings = ['utf-8', 'shift-jis', 'cp932', 'euc-jp', 'iso-2022-jp', 'latin1']
        df = None
        
        # 方法1: 直接StringIOを使用
        for encoding in encodings:
            try:
                # エンコーディングを設定して読み込み試行
                content = file_bytes.decode(encoding)
                # テスト用に先頭行だけ解析
                test_df = pd.read_csv(io.StringIO(content.split('\n', 5)[0]), nrows=1)
                # 成功したらすべてを読み込む
                df = pd.read_csv(io.StringIO(content))
                print(f"正常に読み込み: エンコーディング {encoding}")
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"エラー（{encoding}）: {str(e)}")
                continue
        
        # どのエンコーディングでも読み込めなかった場合
        if df is None:
            try:
                # 方法2: BytesIOを直接使用
                df = pd.read_csv(io.BytesIO(file_bytes))
                print("BytesIOを使用して正常に読み込み")
            except Exception as e2:
                try:
                    # 方法3: tempfileを使用（ファイル名に依存しない処理）
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                        tmp_file.write(file_bytes)
                        tmp_path = tmp_file.name
                    
                    # 一時ファイルから読み込む
                    df = pd.read_csv(tmp_path)
                    # 読み込み後に一時ファイルを削除
                    os.unlink(tmp_path)
                    print("一時ファイルを使用して正常に読み込み")
                except Exception as e3:
                    print(f"全ての読み込み方法が失敗: {str(e2)}, {str(e3)}")
                    st.error(f"ファイルの読み込みに失敗しました。")
                    return None
        
        # カラム名の確認とクリーニング
        df.columns = [col.strip() for col in df.columns]
        
        # 必須カラムが含まれているか確認
        required_columns = ['ymd', 'qty']
        if not all(col in df.columns for col in required_columns):
            # カスタムカラムの場合は、最初の2つのカラムがymdとqtyと仮定
            if len(df.columns) >= 2:
                rename_dict = {df.columns[0]: 'ymd', df.columns[1]: 'qty'}
                df = df.rename(columns=rename_dict)
                st.info(f"カラム名を自動設定しました: {df.columns[0]} → ymd, {df.columns[1]} → qty")
            else:
                st.error(f"必須カラム 'ymd' と 'qty' が見つかりません。")
                return None
        
        # 日付の処理
        df['ymd'] = df['ymd'].astype(str).str.zfill(8)
        try:
            # まず%Y%m%d形式で変換を試行
            df['ymd'] = pd.to_datetime(df['ymd'], format='%Y%m%d', errors='coerce')
        except:
            try:
                # 失敗した場合は自動推定で変換
                df['ymd'] = pd.to_datetime(df['ymd'], errors='coerce')
            except:
                st.error("日付列の変換に失敗しました。YYYYMMDD形式で入力してください。")
                return None
        
        # 無効な日付をチェック
        invalid_dates = df[df['ymd'].isna()]
        if not invalid_dates.empty:
            st.warning(f"{len(invalid_dates)}行の日付が無効なため除外されました。YYYYMMDD形式（例：20240101）で入力してください。")
            df = df.dropna(subset=['ymd'])
        
        # 欠損値を除外
        original_len = len(df)
        df = df.dropna(subset=['ymd'])
            
        # qty列の数値変換確認
        try:
            df['qty'] = pd.to_numeric(df['qty'], errors='coerce')
            if df['qty'].isna().any():
                st.warning(f"{df['qty'].isna().sum()}行の数量(qty)が数値に変換できないため除外されました。")
                df = df.dropna(subset=['qty'])
        except Exception as e:
            st.error(f"数量(qty)の処理中にエラーが発生しました。")
            return None
        
        if len(df) == 0:
            st.error("処理後のデータが0行になりました。データを確認してください。")
            return None
            
        return df
    except Exception as e:
        st.error(f"ファイルの処理中にエラーが発生しました: {str(e)}")
        return None

# --- テキスト入力からCSVデータを読み込む関数 ---
def load_and_clean_csv_text(csv_text, source_name):
    try:
        # 空のテキストチェック
        if not csv_text.strip():
            st.error(f"{source_name}のCSVデータが入力されていません。")
            return None
        
        # 入力テキストの前処理（改行と区切り文字の正規化）
        csv_text = csv_text.strip()
        # 最初の行を取得してヘッダー行を分析
        lines = csv_text.split('\n')
        if len(lines) == 0:
            st.error(f"{source_name}の入力データに行がありません。")
            return None
            
        # データ形式のチェック（タブ区切り、カンマ区切り、スペース区切りに対応）
        header = lines[0]
        sep = None
        
        # 区切り文字の検出（タブ、カンマ、スペースの順で試す）
        if '\t' in header:
            sep = '\t'
        elif ',' in header:
            sep = ','
        elif ' ' in header and len(header.split()) > 1:
            sep = '\\s+'  # 正規表現によるスペース区切り
        else:
            # 区切り文字が見つからない場合は、カンマ区切りと仮定
            sep = ','
        
        try:
            # 区切り文字を指定してCSVをパース
            if sep == '\\s+':
                # 正規表現のスペース区切りの場合
                df = pd.read_csv(io.StringIO(csv_text), sep=sep, engine='python')
            else:
                df = pd.read_csv(io.StringIO(csv_text), sep=sep)
        except Exception as e:
            st.error(f"{source_name}のCSVデータ形式が不正です。")
            # タブ区切りでもカンマ区切りでも失敗した場合、スペース区切りを試す
            try:
                df = pd.read_csv(io.StringIO(csv_text), delim_whitespace=True)
            except Exception as e2:
                st.error(f"{source_name}のデータ読み込みに失敗しました。")
                return None
        
        # カラム名の確認とクリーニング（空白を除去）
        df.columns = [col.strip() for col in df.columns]
        
        # 必須カラムが含まれているか確認
        required_columns = ['ymd', 'qty']
        if not all(col in df.columns for col in required_columns):
            # カスタムカラムの場合は、最初の2つのカラムがymdとqtyと仮定
            if len(df.columns) >= 2:
                rename_dict = {df.columns[0]: 'ymd', df.columns[1]: 'qty'}
                df = df.rename(columns=rename_dict)
            else:
                st.error(f"{source_name}の必須カラム 'ymd' と 'qty' が見つかりません。")
                return None
        
        # 日付の処理
        df['ymd'] = df['ymd'].astype(str).str.zfill(8)
        try:
            # まず%Y%m%d形式で変換を試行
            df['ymd'] = pd.to_datetime(df['ymd'], format='%Y%m%d', errors='coerce')
        except:
            try:
                # 失敗した場合は自動推定で変換
                df['ymd'] = pd.to_datetime(df['ymd'], errors='coerce')
            except:
                st.error("日付列の変換に失敗しました。YYYYMMDD形式で入力してください。")
                return None
        
        # 無効な日付をチェック
        invalid_dates = df[df['ymd'].isna()]
        if not invalid_dates.empty:
            st.warning(f"{len(invalid_dates)}行の日付が無効なため除外されました。YYYYMMDD形式（例：20240101）で入力してください。")
            df = df.dropna(subset=['ymd'])
        
        # 欠損値を除外
        original_len = len(df)
        df = df.dropna(subset=['ymd'])
            
        # qty列の数値変換確認
        try:
            df['qty'] = pd.to_numeric(df['qty'], errors='coerce')
            if df['qty'].isna().any():
                df = df.dropna(subset=['qty'])
        except Exception as e:
            st.error(f"{source_name}の数量(qty)の処理中にエラーが発生しました。")
            return None
        
        # カラムがすべて揃っていることを確認
        if 'ymd' not in df.columns or 'qty' not in df.columns:
            st.error(f"{source_name}のデータにymdまたはqtyカラムがありません。")
            return None
        
        # データが空でないことを確認
        if df.empty:
            st.error(f"{source_name}の有効なデータがありません。")
            return None
            
        return df
    except Exception as e:
        st.error(f"{source_name}のデータ処理中にエラーが発生しました。")
        return None

# --- 処置群のみ分析用データセット作成関数 ---
def create_single_group_dataset(df_treat, treatment_name, freq_option):
    """
    処置群のみのデータからデータセットを作成する関数
    """
    try:
        # データフレームの集計
        agg_treat = aggregate_df(df_treat, freq_option)
        
        # 全期間の範囲を生成（処置群のみの場合）
        # 処置群のデータから開始日と終了日を取得
        df_dates = pd.to_datetime(df_treat['ymd'])
        start_date = df_dates.min()
        end_date = df_dates.max()
        
        if freq_option == "月次":
            # 月の初日のシーケンスを生成
            all_periods = pd.date_range(
                start=start_date.replace(day=1),
                end=end_date.replace(day=1),
                freq='MS'  # Month Start
            )
        elif freq_option == "旬次":
            # 旬区切りの日付リストを作成（utils_step1.pyと同じロジック）
            first_month = start_date.replace(day=1)
            last_month = end_date.replace(day=1)
            months = pd.date_range(start=first_month, end=last_month, freq='MS')
            
            periods = []
            for month in months:
                # 各月の1日、11日、21日を追加（範囲内の場合のみ）
                for day in [1, 11, 21]:
                    date = month.replace(day=day)
                    if start_date <= date <= end_date:
                        periods.append(date)
            all_periods = pd.DatetimeIndex(periods)
        else:  # 日次
            all_periods = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 全期間のインデックスを作成し、データをゼロ埋め
        all_periods_df = pd.DataFrame(index=all_periods)
        all_periods_df.index.name = 'period'
        
        # データフレームとマージしてゼロ埋め
        agg_treat_full = pd.merge(
            all_periods_df, 
            agg_treat.set_index('period'), 
            how='left', 
            left_index=True, 
            right_index=True
        ).fillna(0)
        
        # 最終データセット作成（処置群のみ）
        dataset = pd.DataFrame({
            'ymd': all_periods,
            f'処置群（{treatment_name}）': agg_treat_full['qty'].values
        })
        
        return dataset
        
    except Exception as e:
        st.error(f"処置群のみデータセット作成でエラーが発生しました: {str(e)}")
        return None

# --- 二群比較のファイルアップロード後のデータ読み込み ---
if analysis_type == "二群比較（処置群＋対照群を使用）":
    if upload_method == "ファイルアップロード（※日本語ファイル名は非対応／英数字のみ使用可）" and read_btn_upload and treatment_file and control_file:
        with st.spinner("データ読み込み中..."):
            try:
                # Streamlit Cloud環境かどうかを確認（環境変数などで判定可能）
                is_cloud_env = os.environ.get('STREAMLIT_SHARING_MODE') == 'streamlit_sharing'
                
                # セーフティチェック - ファイルサイズの確認
                if treatment_file.size > 5 * 1024 * 1024 or control_file.size > 5 * 1024 * 1024:
                    st.error("ファイルサイズが大きすぎます。5MB以下のファイルを使用してください。")
                    df_treat = None
                    df_ctrl = None
                else:
                    # ファイルのシーク位置をリセット（複数回読み込む可能性があるため）
                    treatment_file.seek(0)
                    
                    # 日本語ファイル名チェック
                    if any(ord(c) > 127 for c in treatment_file.name) and is_cloud_env:
                        st.error(f"Streamlit Cloud環境では日本語を含むファイル名（{treatment_file.name}）はサポートされていません。英数字のファイル名に変更してください。")
                        df_treat = None
                    else:
                        # 処置群ファイルの読み込み試行
                        df_treat = load_and_clean_uploaded_csv(treatment_file)
                    
                    # 処置群ファイルが読み込めた場合のみ対照群ファイルを読み込む
                    if df_treat is not None:
                        # ファイルのシーク位置をリセット
                        control_file.seek(0)
                        
                        # 日本語ファイル名チェック
                        if any(ord(c) > 127 for c in control_file.name) and is_cloud_env:
                            st.error(f"Streamlit Cloud環境では日本語を含むファイル名（{control_file.name}）はサポートされていません。英数字のファイル名に変更してください。")
                            df_ctrl = None
                        else:
                            # 対照群ファイルの読み込み試行
                            df_ctrl = load_and_clean_uploaded_csv(control_file)
                    else:
                        df_ctrl = None
                        st.error("処置群ファイルの読み込みに失敗したため、対照群ファイルの読み込みをスキップします。")
                
                if df_treat is not None and df_ctrl is not None and not df_treat.empty and not df_ctrl.empty:
                    # セッションに保存（ユーザーが入力した名称を使用）
                    st.session_state['df_treat'] = df_treat
                    st.session_state['df_ctrl'] = df_ctrl
                    # 名前が空でなければユーザー入力値を使用、空なら処理名をデフォルト値に
                    treatment_name = treatment_name.strip() if treatment_name and treatment_name.strip() else "処置群"
                    control_name = control_name.strip() if control_name and control_name.strip() else "対照群"
                    st.session_state['treatment_name'] = treatment_name
                    st.session_state['control_name'] = control_name
                    st.session_state['data_loaded'] = True
                    st.success("データを読み込みました。下記にプレビューと統計情報を表示します。")
                else:
                    st.error("データの読み込みに失敗しました。CSVファイルの形式を確認してください。")
                    if df_treat is None:
                        st.error("処置群ファイルの読み込みに失敗しました。")
                    elif df_treat.empty:
                        st.error("処置群ファイルに有効なデータがありません。")
                    if df_ctrl is None:
                        st.error("対照群ファイルの読み込みに失敗しました。")
                    elif df_ctrl is not None and df_ctrl.empty:
                        st.error("対照群ファイルに有効なデータがありません。")
                    st.session_state['data_loaded'] = False
                    
                    # 代替入力方法の提案
                    st.info("CSVテキスト直接入力をご利用ください。以下は入力例です：\n\nymd,qty\n20170403,29\n20170425,24\n...")
            except Exception as e:
                st.error(f"データ読み込み中に予期しないエラーが発生しました: {str(e)}")
                st.session_state['data_loaded'] = False
                
                # 代替入力方法の提案
                st.info("CSVテキスト直接入力をご利用ください。以下は入力例です：\n\nymd,qty\n20170403,29\n20170425,24\n...")

    # --- 二群比較のテキスト入力からのデータ読み込み ---
    elif upload_method == "CSVテキスト直接入力" and read_btn_text:
        with st.spinner("データ読み込み中..."):
            df_treat = load_and_clean_csv_text(treatment_csv, "処置群")
            df_ctrl = load_and_clean_csv_text(control_csv, "対照群")
            
            if df_treat is not None and df_ctrl is not None and not df_treat.empty and not df_ctrl.empty:
                # セッションに保存（ユーザーが入力した名称を使用）
                st.session_state['df_treat'] = df_treat
                st.session_state['df_ctrl'] = df_ctrl
                # 名前が空でなければユーザー入力値を使用、空なら処理名をデフォルト値に
                treatment_name = treatment_name.strip() if treatment_name and treatment_name.strip() else "処置群"
                control_name = control_name.strip() if control_name and control_name.strip() else "対照群"
                st.session_state['treatment_name'] = treatment_name
                st.session_state['control_name'] = control_name
                st.session_state['data_loaded'] = True
                st.success("データを読み込みました。下記にプレビューと統計情報を表示します。")
            else:
                st.error("データの読み込みに失敗しました。入力したCSVデータの形式を確認してください。")
                if df_treat is None:
                    st.error("処置群データの読み込みに失敗しました。")
                if df_ctrl is None:
                    st.error("対照群データの読み込みに失敗しました。")
                st.session_state['data_loaded'] = False

# --- 単群推定のデータ読み込み ---
else:  # analysis_type == "単群推定（処置群のみを使用）"
    if upload_method == "ファイルアップロード（※日本語ファイル名は非対応／英数字のみ使用可）" and read_btn_single_upload and treatment_file:
        with st.spinner("処置群のみデータ読み込み中..."):
            try:
                # Streamlit Cloud環境かどうかを確認
                is_cloud_env = os.environ.get('STREAMLIT_SHARING_MODE') == 'streamlit_sharing'
                
                # セーフティチェック - ファイルサイズの確認
                if treatment_file.size > 5 * 1024 * 1024:
                    st.error("ファイルサイズが大きすぎます。5MB以下のファイルを使用してください。")
                    df_treat = None
                else:
                    # ファイルのシーク位置をリセット
                    treatment_file.seek(0)
                    
                    # 日本語ファイル名チェック
                    if any(ord(c) > 127 for c in treatment_file.name) and is_cloud_env:
                        st.error(f"Streamlit Cloud環境では日本語を含むファイル名（{treatment_file.name}）はサポートされていません。英数字のファイル名に変更してください。")
                        df_treat = None
                    else:
                        # 処置群ファイルの読み込み試行
                        df_treat = load_and_clean_uploaded_csv(treatment_file)
                
                if df_treat is not None and not df_treat.empty:
                    # 処置群のみ分析用データ検証
                    is_valid, error_msg = validate_single_group_data(df_treat)
                    
                    if is_valid:
                        # セッションに保存（処置群のみ）
                        st.session_state['df_treat'] = df_treat
                        st.session_state['df_ctrl'] = None  # 対照群なし
                        treatment_name = treatment_name.strip() if treatment_name and treatment_name.strip() else "処置群"
                        st.session_state['treatment_name'] = treatment_name
                        st.session_state['control_name'] = None
                        st.session_state['data_loaded'] = True
                        st.session_state['analysis_type'] = "単群推定（処置群のみを使用）"  # 分析タイプを明示的に保存
                        st.success("処置群のみデータを読み込みました。下記にプレビューと統計情報を表示します。")
                    else:
                        st.error(f"データ検証エラー: {error_msg}")
                        st.session_state['data_loaded'] = False
                else:
                    st.error("処置群ファイルの読み込みに失敗しました。CSVファイルの形式を確認してください。")
                    st.session_state['data_loaded'] = False
                
            except Exception as e:
                st.error(f"処置群のみデータ読み込み中に予期しないエラーが発生しました: {str(e)}")
                st.session_state['data_loaded'] = False

    elif upload_method == "CSVテキスト直接入力" and read_btn_single_text:
        with st.spinner("処置群のみデータ読み込み中..."):
            df_treat = load_and_clean_csv_text(treatment_csv, "処置群")
            
            if df_treat is not None and not df_treat.empty:
                # 処置群のみ分析用データ検証
                is_valid, error_msg = validate_single_group_data(df_treat)
                
                if is_valid:
                    # セッションに保存（処置群のみ）
                    st.session_state['df_treat'] = df_treat
                    st.session_state['df_ctrl'] = None  # 対照群なし
                    treatment_name = treatment_name.strip() if treatment_name and treatment_name.strip() else "処置群"
                    st.session_state['treatment_name'] = treatment_name
                    st.session_state['control_name'] = None
                    st.session_state['data_loaded'] = True
                    st.session_state['analysis_type'] = "単群推定（処置群のみを使用）"  # 分析タイプを明示的に保存
                    st.success("処置群のみデータを読み込みました。下記にプレビューと統計情報を表示します。")
                else:
                    st.error(f"データ検証エラー: {error_msg}")
                    st.session_state['data_loaded'] = False
            else:
                st.error("処置群データの読み込みに失敗しました。入力したCSVデータの形式を確認してください。")
                st.session_state['data_loaded'] = False

# --- データ読み込み済みなら表示（セッションから取得） ---
if st.session_state.get('data_loaded', False):
    df_treat = st.session_state['df_treat']
    df_ctrl = st.session_state.get('df_ctrl', None)  # 処置群のみ分析では None
    treatment_name = st.session_state['treatment_name']
    control_name = st.session_state.get('control_name', None)
    current_analysis_type = st.session_state.get('analysis_type', analysis_type)
    
    # --- データプレビュー ---
    st.markdown('<div class="section-title">読み込みデータのプレビュー（上位10件表示）</div>', unsafe_allow_html=True)
    
    if current_analysis_type == "二群比較（処置群＋対照群を使用）" and df_ctrl is not None:
        # 二群比較の場合（処置群 + 対照群）
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群（{treatment_name}）</div>', unsafe_allow_html=True)
            preview_df_treat = df_treat[['ymd', 'qty']].head(10).copy()
            preview_df_treat['ymd'] = preview_df_treat['ymd'].dt.strftime('%Y-%m-%d')
            preview_df_treat.index = range(1, len(preview_df_treat) + 1)
            st.dataframe(preview_df_treat, use_container_width=True)
        with col2:
            st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">対照群（{control_name}）</div>', unsafe_allow_html=True)
            preview_df_ctrl = df_ctrl[['ymd', 'qty']].head(10).copy()
            preview_df_ctrl['ymd'] = preview_df_ctrl['ymd'].dt.strftime('%Y-%m-%d')
            preview_df_ctrl.index = range(1, len(preview_df_ctrl) + 1)
            st.dataframe(preview_df_ctrl, use_container_width=True)
    else:
        # 単群推定の場合
        # データ要件チェックを独立したセクションとして表示
        st.markdown('<div class="section-title">データ要件チェック</div>', unsafe_allow_html=True)
        
        try:
            suggested_date, pre_days, post_days = suggest_intervention_point(df_treat)
            total_days = len(df_treat)
            
            # データ要件情報を整列表示
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("総データ日数", f"{total_days}日")
            with col2:
                # suggested_dateが日付型かどうかを確認して適切に表示
                if isinstance(suggested_date, str):
                    date_str = suggested_date
                else:
                    try:
                        if hasattr(suggested_date, 'strftime'):
                            date_str = suggested_date.strftime('%Y-%m-%d')
                        else:
                            date_str = str(suggested_date)
                    except Exception:
                        date_str = str(suggested_date)
                st.metric("推奨介入日", date_str)
            with col3:
                st.metric("介入前期間", f"{pre_days}日")
            with col4:
                st.metric("介入後期間", f"{post_days}日")
            
            # データ量充足状況
            if total_days >= 37:
                st.success("十分なデータ量が確保されており、信頼性の高い分析が可能です。")
            else:
                st.warning("データ量が不足しています。より信頼性の高い分析のため、37日以上のデータを推奨します。")
                
        except Exception as e:
            total_days = len(df_treat)
            st.metric("総データ日数", f"{total_days}日")
            st.warning(f"推奨介入日の計算でエラーが発生しました: {str(e)}")
            
            if total_days >= 37:
                st.success("十分なデータ量が確保されており、信頼性の高い分析が可能です。")
            else:
                st.warning("データ量が不足しています。より信頼性の高い分析のため、37日以上のデータを推奨します。")
        
        # データプレビューと統計情報を横並びで表示
        st.markdown('<div class="section-title">読み込みデータのプレビュー（上位10件表示）と統計情報</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">データプレビュー（上位10件表示）</div>', unsafe_allow_html=True)
            preview_df_treat = df_treat[['ymd', 'qty']].head(10).copy()
            preview_df_treat['ymd'] = preview_df_treat['ymd'].dt.strftime('%Y-%m-%d')
            preview_df_treat.index = range(1, len(preview_df_treat) + 1)
            st.dataframe(preview_df_treat, use_container_width=True)
        with col2:
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">統計情報</div>', unsafe_allow_html=True)
            if 'qty' in df_treat.columns:
                stats_treat = format_stats_with_japanese(df_treat[['qty']])
                st.dataframe(stats_treat, use_container_width=True, hide_index=True)
            else:
                st.error("データに 'qty' カラムが見つかりません")

    # --- 統計情報（二群比較のみ） ---
    if current_analysis_type == "二群比較（処置群＋対照群を使用）" and df_ctrl is not None:
        st.markdown('<div class="section-title">データの統計情報</div>', unsafe_allow_html=True)
        # 二群比較の統計情報表示
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群（{treatment_name}）</div>', unsafe_allow_html=True)
            if 'qty' in df_treat.columns:
                stats_treat = format_stats_with_japanese(df_treat[['qty']])
                st.dataframe(stats_treat, use_container_width=True, hide_index=True)
            else:
                st.error("データに 'qty' カラムが見つかりません")
        with col2:
            st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">対照群（{control_name}）</div>', unsafe_allow_html=True)
            if 'qty' in df_ctrl.columns:
                stats_ctrl = format_stats_with_japanese(df_ctrl[['qty']])
                st.dataframe(stats_ctrl, use_container_width=True, hide_index=True)
            else:
                st.error("データに 'qty' カラムが見つかりません")

    # --- 分析用データセット作成セクション ---
    st.markdown('<div class="section-title">分析用データセットの作成</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">分析データ集計方法の選択</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 3])
    with col1:
        freq_option = st.radio(
            "データ集計方法",
            options=["月次", "旬次"],
            label_visibility="collapsed"
        )
    with col2:
        if freq_option == "月次":
            st.markdown("""
<div style="font-size:0.98em;margin-top:0.1em;padding-left:0;">
<span style="font-weight:bold;">月次集計：</span>月単位で集計し、日付はその月の1日になります<br>
<span style="font-weight:normal;color:#666;">旬次集計：</span>月を上旬・中旬・下旬に3分割して集計し、日付はそれぞれ1日（上旬）、11日（中旬）、21日（下旬）になります<br>
<div style="color:#1976d2;font-size:0.9em;margin-top:0.3em;padding-left:0;">※欠損値は自動的に0で埋められます。</div>
</div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
<div style="font-size:0.98em;margin-top:0.1em;padding-left:0;">
<span style="font-weight:normal;color:#666;">月次集計：</span>月単位で集計し、日付はその月の1日になります<br>
<span style="font-weight:bold;">旬次集計：</span>月を上旬・中旬・下旬に3分割して集計し、日付はそれぞれ1日（上旬）、11日（中旬）、21日（下旬）になります<br>
<div style="color:#1976d2;font-size:0.9em;margin-top:0.3em;padding-left:0;">※欠損値は自動的に0で埋められます。</div>
</div>
            """, unsafe_allow_html=True)
    
    # 「データセットを作成する」ボタンの上に余白を追加
    st.markdown('<div style="margin-top:25px;"></div>', unsafe_allow_html=True)
    create_btn = st.button("データセットを作成する", key="create", help="Causal Impact分析用データセットを作成します。", type="primary", use_container_width=True)
    
    if create_btn or ('dataset_created' in st.session_state and st.session_state['dataset_created']):
        if create_btn:  # 新しくデータセットを作成する場合のみ実行
            if current_analysis_type == "二群比較（処置群＋対照群を使用）" and df_ctrl is not None:
                # 二群比較のデータセット作成（既存ロジック）
                # データフレームの集計
                agg_treat = aggregate_df(df_treat, freq_option)
                agg_ctrl = aggregate_df(df_ctrl, freq_option)
                
                # 共通期間の全日付範囲を生成（両群の開始日の遅い方から終了日の早い方まで）
                all_periods = create_full_period_range(df_treat, df_ctrl, freq_option)
                
                # 全期間のインデックスを作成し、データをゼロ埋め
                all_periods_df = pd.DataFrame(index=all_periods)
                all_periods_df.index.name = 'period'
                
                # 各データフレームとマージしてゼロ埋め
                agg_treat_full = pd.merge(
                    all_periods_df, 
                    agg_treat.set_index('period'), 
                    how='left', 
                    left_index=True, 
                    right_index=True
                ).fillna(0)
                
                agg_ctrl_full = pd.merge(
                    all_periods_df, 
                    agg_ctrl.set_index('period'), 
                    how='left', 
                    left_index=True, 
                    right_index=True
                ).fillna(0)
                
                # 最終データセット作成
                dataset = pd.DataFrame({
                    'ymd': all_periods,
                    f'処置群（{treatment_name}）': agg_treat_full['qty'].values,
                    f'対照群（{control_name}）': agg_ctrl_full['qty'].values
                })
                
                # データ期間情報を保存（表示用）
                treat_period = f"{df_treat['ymd'].min().strftime('%Y/%m/%d')} ～ {df_treat['ymd'].max().strftime('%Y/%m/%d')}"
                ctrl_period = f"{df_ctrl['ymd'].min().strftime('%Y/%m/%d')} ～ {df_ctrl['ymd'].max().strftime('%Y/%m/%d')}"
                common_period = f"{all_periods.min().strftime('%Y/%m/%d')} ～ {all_periods.max().strftime('%Y/%m/%d')}"
                st.session_state['period_info'] = {
                    'treat_period': treat_period,
                    'ctrl_period': ctrl_period,
                    'common_period': common_period
                }
            else:
                # 処置群のみ分析のデータセット作成
                dataset = create_single_group_dataset(df_treat, treatment_name, freq_option)
                
                if dataset is not None:
                    # データ期間情報を保存（処置群のみ）
                    treat_period = f"{df_treat['ymd'].min().strftime('%Y/%m/%d')} ～ {df_treat['ymd'].max().strftime('%Y/%m/%d')}"
                    st.session_state['period_info'] = {
                        'treat_period': treat_period,
                        'ctrl_period': None,  # 処置群のみ分析では対照群なし
                        'common_period': treat_period  # 処置群のみの期間
                    }
                else:
                    st.error("単群推定用データセットの作成に失敗しました。")
                    dataset = None
            
            if dataset is not None:
                # セッションに保存
                st.session_state['dataset'] = dataset
                st.session_state['dataset_created'] = True
                
                # 分析期間のデフォルト値を設定
                dataset_min_date = dataset['ymd'].min().date()
                dataset_max_date = dataset['ymd'].max().date()
                
                # データセットの前半部分を介入前期間、後半部分を介入期間としてデフォルト設定
                mid_point_idx = len(dataset) // 2
                default_pre_end = dataset.iloc[mid_point_idx-1]['ymd'].date()
                default_post_start = dataset.iloc[mid_point_idx]['ymd'].date()
                
                # 単群推定の場合は推奨介入ポイントを使用
                if current_analysis_type == "単群推定（処置群のみを使用）":
                    try:
                        suggested_date, _, _ = suggest_intervention_point(df_treat)
                        # suggested_dateが日付型かどうかを確認
                        if hasattr(suggested_date, 'date'):
                            suggested_date_obj = suggested_date.date() if hasattr(suggested_date, 'date') else suggested_date
                        elif isinstance(suggested_date, str) and suggested_date != "エラー：推奨日計算失敗":
                            try:
                                suggested_date_obj = pd.to_datetime(suggested_date).date()
                            except:
                                suggested_date_obj = None
                        else:
                            suggested_date_obj = None
                        
                        if suggested_date_obj is not None:
                            # データセット内で推奨日に最も近い日付を見つける
                            dataset_dates = dataset['ymd'].dt.date
                            closest_idx = (dataset_dates - suggested_date_obj).abs().idxmin()
                            suggested_dataset_date = dataset.iloc[closest_idx]['ymd'].date()
                            
                            # 推奨日を基準に期間を設定
                            if closest_idx > 0:
                                default_pre_end = dataset.iloc[closest_idx-1]['ymd'].date()
                                default_post_start = suggested_dataset_date
                    except Exception as e:
                        # エラーが発生した場合はデフォルトの中点を使用
                        pass
                
                st.session_state['period_defaults'] = {
                    'pre_start': dataset_min_date,
                    'pre_end': default_pre_end,
                    'post_start': default_post_start,
                    'post_end': dataset_max_date
                }
        else:
            # データセットが既に作成済みの場合、セッションから取得
            dataset = st.session_state['dataset']
        
        if dataset is not None:
            # データセット情報の表示（新規作成・既存問わず）
            period_info = st.session_state.get('period_info', {})
            common_period = period_info.get('common_period', f"{dataset['ymd'].min().strftime('%Y/%m/%d')} ～ {dataset['ymd'].max().strftime('%Y/%m/%d')}")
            
            st.markdown(f"""
<div style="margin-bottom:1.5em;">
<div style="display:flex;align-items:center;margin-bottom:0.5em;">
  <div style="font-weight:bold;font-size:1.05em;margin-right:0.5em;">対象期間：</div>
<div>{dataset['ymd'].min().strftime('%Y/%m/%d')} ～ {dataset['ymd'].max().strftime('%Y/%m/%d')}</div>
  <div style="color:#1976d2;font-size:0.9em;margin-left:2em;">　※{current_analysis_type}に基づいてデータセットを作成しています。</div>
</div>
<div style="display:flex;align-items:center;margin-bottom:0.5em;">
  <div style="font-weight:bold;font-size:1.05em;margin-right:0.5em;">データ数：</div>
<div>{len(dataset)} 件</div>
</div>
</div>
            """, unsafe_allow_html=True)
            
            # 元データの期間情報がある場合は詳細を表示
            if 'period_info' in st.session_state:
                with st.expander("元データの期間情報", expanded=False):
                    period_info = st.session_state['period_info']
                    if current_analysis_type == "二群比較（処置群＋対照群を使用）":
                        st.markdown(f"""
<div style="margin-top:0.5em;">
<p><b>処置群期間：</b>{period_info['treat_period']}</p>
<p><b>対照群期間：</b>{period_info['ctrl_period']}</p>
<p><b>共通期間：</b>{period_info['common_period']}</p>
<p style="margin-top:1em;font-size:0.9em;color:#666;">※共通期間は「処置群と対照群の開始日のうち遅い方」から「終了日のうち早い方」までとして計算しています。<br>※欠損値はすべてゼロ埋めされています。</p>
</div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
<div style="margin-top:0.5em;">
<p><b>処置群期間：</b>{period_info['treat_period']}</p>
<p style="margin-top:1em;font-size:0.9em;color:#666;">※単群推定では、処置群のデータ期間全体を対象としています。<br>※欠損値はすべてゼロ埋めされています。</p>
</div>
                        """, unsafe_allow_html=True)

            # データプレビューと統計情報の表示
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">データプレビュー（上位10件表示）</div>', unsafe_allow_html=True)
                preview_df = dataset.head(10).copy()
                preview_df['ymd'] = preview_df['ymd'].dt.strftime('%Y-%m-%d')
                preview_df.index = range(1, len(preview_df) + 1)
                st.dataframe(preview_df, use_container_width=True)
            with col2:
                st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">統計情報</div>', unsafe_allow_html=True)
                
                # 統計情報の列名を動的に取得
                numeric_columns = [col for col in dataset.columns if col != 'ymd']
                
                stats_data = []
                for col in numeric_columns:
                    stats_data.append([
                        len(dataset),
                        round(dataset[col].mean(), 2),
                        round(dataset[col].std(), 2),
                        dataset[col].min(),
                        dataset[col].quantile(0.25),
                        dataset[col].quantile(0.5),
                        dataset[col].quantile(0.75),
                        dataset[col].max()
                    ])
                
                stats_df = pd.DataFrame(stats_data).T
                stats_df.columns = numeric_columns
                stats_df.index = ['count（個数）', 'mean（平均）', 'std（標準偏差）', 'min（最小値）', '25%（第1四分位数）', '50%（中央値）', '75%（第3四分位数）', 'max（最大値）']
                stats_df.insert(0, '統計項目', stats_df.index)
                st.dataframe(stats_df, use_container_width=True, hide_index=True)

            # --- 時系列可視化セクション ---
            st.markdown('<div class="section-title">時系列プロット</div>', unsafe_allow_html=True)
            
            if current_analysis_type == "二群比較（処置群＋対照群を使用）" and len(dataset.columns) >= 3:
                # 二群比較の時系列可視化（処置群 + 対照群）
                # 列名を動的に取得
                treatment_col = [col for col in dataset.columns if col != 'ymd' and '処置群' in col][0]
                control_col = [col for col in dataset.columns if col != 'ymd' and '対照群' in col][0]
                
                # プロットの作成
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                # 処置群のトレース追加
                fig.add_trace(
                    go.Scatter(
                        x=dataset['ymd'], 
                        y=dataset[treatment_col], 
                        name=treatment_col, 
                        line=dict(color="#1976d2", width=2), 
                        mode='lines+markers', 
                        marker=dict(size=4),
                        hovertemplate='日付: %{x|%Y-%m-%d}<br>数量: %{y}<extra></extra>'
                    ),
                    secondary_y=False
                )
                
                # 対照群のトレース追加
                fig.add_trace(
                    go.Scatter(
                        x=dataset['ymd'], 
                        y=dataset[control_col], 
                        name=control_col, 
                        line=dict(color="#ef5350", width=2), 
                        mode='lines+markers', 
                        marker=dict(size=4),
                        hovertemplate='日付: %{x|%Y-%m-%d}<br>数量: %{y}<extra></extra>'
                    ),
                    secondary_y=True
                )
                
                # X軸の設定
                fig.update_xaxes(
                    title_text="日付", 
                    type="date", 
                    tickformat="%Y-%m", 
                    showgrid=True, 
                    tickangle=-30
                )
                
                # 左Y軸の設定（処置群）
                fig.update_yaxes(
                    title_text="処置群の数量", 
                    secondary_y=False, 
                    title_font=dict(color="#1976d2"), 
                    tickfont=dict(color="#1976d2")
                )
                
                # 右Y軸の設定（対照群）
                fig.update_yaxes(
                    title_text="対照群の数量", 
                    secondary_y=True, 
                    title_font=dict(color="#ef5350"), 
                    tickfont=dict(color="#ef5350")
                )
                
                # レイアウトの設定（凡例を中央に配置、range sliderを追加）
                fig.update_layout(
                    title="処置群と対照群の時系列推移",
                    height=500,
                    hovermode='x unified',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5
                    ),
                    xaxis_rangeslider_visible=True,
                    dragmode="zoom"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                # 単群推定の時系列可視化
                # 列名を動的に取得
                treatment_col = [col for col in dataset.columns if col != 'ymd'][0]
                
                # プロットの作成
                fig = go.Figure()
                
                # 処置群のトレース追加（凡例を明示）
                fig.add_trace(
                    go.Scatter(
                        x=dataset['ymd'], 
                        y=dataset[treatment_col], 
                        name=f"処置群（{treatment_name}）", 
                        line=dict(color="#1976d2", width=2), 
                        mode='lines', 
                        hovertemplate='日付: %{x|%Y-%m-%d}<br>数量: %{y}<extra></extra>'
                    )
                )
                
                # レイアウトの設定（凡例表示、range slider追加）
                fig.update_layout(
                    title="処置群の時系列推移",
                    legend=dict(
                        orientation="h", 
                        yanchor="bottom", 
                        y=1.02, 
                        xanchor="center", 
                        x=0.5
                    ),
                    hovermode="x unified",
                    plot_bgcolor='white',
                    margin=dict(t=50, l=60, r=60, b=60),
                    height=500,
                    autosize=True,
                    xaxis_rangeslider_visible=True,
                    dragmode="zoom"
                )
                
                # X軸の設定
                fig.update_xaxes(
                    title_text="日付", 
                    type="date", 
                    tickformat="%Y-%m", 
                    showgrid=True, 
                    tickangle=-30
                )
                
                # Y軸の設定（左軸ラベルを青文字で明示）
                fig.update_yaxes(
                    title_text="処置群の数量",
                    title_font=dict(color="#1976d2"),
                    tickfont=dict(color="#1976d2"),
                    showgrid=True
                )
                
                st.plotly_chart(fig, use_container_width=True)

            # --- Plotlyインタラクティブグラフの使い方ガイド ---
            with st.expander("Plotlyインタラクティブグラフの使い方ガイド"):
                st.markdown("""
<div style="line-height:1.7;">
<ul>
<li><b>データ確認</b>：グラフ上の線やポイントにマウスを置くと、詳細値がポップアップ表示されます</li>
<li><b>拡大表示</b>：見たい期間をドラッグして範囲選択すると拡大表示されます</li>
<li><b>表示移動</b>：拡大後、右クリックドラッグで表示位置を調整できます</li>
<li><b>初期表示</b>：ダブルクリックすると全期間表示に戻ります</li>
<li><b>系列表示切替</b>：凡例をクリックすると系列の表示/非表示を切り替えできます</li>
</ul>
</div>
                """, unsafe_allow_html=True)
            
            # --- 分析期間設定のヒント ---
            with st.expander("分析期間設定のヒント"):
                if current_analysis_type == "二群比較（処置群＋対照群を使用）":
                    st.markdown("""
<div style="line-height:1.7;">
<ul>
  <li><b>介入期間</b>：処置群（青線）において、施策（介入）実施後の効果を測定したい期間を設定してください</li>
  <li><b>介入前期間</b>：施策（介入）実施前の期間として、十分な長さのデータを含めて設定してください
    <ul>
      <li><b>季節性</b>：介入前期間に季節性がある場合は、少なくとも2〜3周期分のデータを含めるのが望ましいです</li>
      <li><b>イレギュラー要因</b>：外部要因による大きな影響がある期間は、介入前期間に含めないことをおすすめします</li>
    </ul>
  </li>
</ul>
</div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
<div style="line-height:1.7;">
<ul>
  <li><b>介入期間</b>：処置群において、施策（介入）実施後の効果を測定したい期間を設定してください</li>
  <li><b>介入前期間</b>：施策（介入）実施前の期間として、十分な長さのデータを含めて設定してください
    <ul>
      <li><b>季節性</b>：介入前期間に季節性がある場合は、少なくとも2〜3周期分のデータを含めるのが望ましいです</li>
      <li><b>イレギュラー要因</b>：外部要因による大きな影響がある期間は、介入前期間に含めないことをおすすめします</li>
      <li><b>単群推定</b>：対照群がないため、介入前のトレンドと季節性パターンから反事実シナリオを構築します</li>
    </ul>
  </li>
</ul>
</div>
                    """, unsafe_allow_html=True)

            # STEP 1完了メッセージと次のSTEPへのボタンを表示
            st.success("データセットの作成が完了しました。次のステップで分析期間とパラメータの設定を行います。")
            
            # 分析期間とパラメータを設定するボタンを追加
            next_step_btn = st.button("分析期間とパラメータを設定する", key="next_step", help="次のステップ（分析期間とパラメータ設定）に進みます。", type="primary", use_container_width=True)
            
            # STEP2への遷移処理（今後実装予定）
            if next_step_btn:
                st.session_state['show_step2'] = True
                st.info("🚧 STEP2の実装は現在進行中です。単群推定に対応した期間設定機能を実装予定です。")

st.markdown("---")
st.markdown("### 🚧 開発中")
st.markdown("**単群推定機能**は現在開発中です。既存の二群比較機能をベースに、以下の拡張を実装予定：")
st.markdown("""
- ✅ 処置群のみデータの取り込み機能
- 🔄 介入ポイント自動推奨機能  
- 🔄 季節性パラメータ最適化
- 🔄 結果解釈の強化（対照群なし分析特有の注意事項）
""") 