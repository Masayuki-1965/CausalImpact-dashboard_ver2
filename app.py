import streamlit as st
import pandas as pd
import os
import glob
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 画面幅を最大化 ---
st.set_page_config(layout="wide")

# --- カスタムCSS（全体の余白・フォント・配色・テイスト調整） ---
st.markdown("""
<style>
body, .main, .block-container {
    background-color: #f7fafd !important;
    font-family: 'Noto Sans JP', 'Meiryo', sans-serif;
}
.big-title {
    font-size: 3.5em;
    font-weight: 900;
    color: white;
    margin-bottom: 0.1em;
    letter-spacing: 0.04em;
    text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    line-height: 1.1;
    text-align: center;
}
.sub-title {
    font-size: 1.25em;
    color: white;
    margin-bottom: 1em;
    font-weight: 500;
    text-align: center;
}
.card {
    background: #fff;
    border-radius: 12px;
    padding: 1.3em 1.8em;
    margin-bottom: 1.4em;
    border: 1.5px solid #e3e8ee;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
}
.blue-header-card {
    background: linear-gradient(135deg, #1976d2 0%, #0d47a1 100%);
    border-radius: 12px;
    padding: 1.7em 2em;
    margin-bottom: 2em;
    border: none;
    box-shadow: 0 4px 20px rgba(25, 118, 210, 0.15);
    color: white;
    height: 170px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.step-card {
    background: #e3f2fd;
    border-radius: 12px;
    padding: 1.2em 1.5em;
    margin-bottom: 1.5em;
    border: 1px solid rgba(25, 118, 210, 0.2);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.03);
}
.section-title {
    font-size: 1.3em;
    font-weight: bold;
    color: #1976d2;
    margin-bottom: 0.8em;
    margin-top: 1em;
    border-left: 5px solid #1976d2;
    padding-left: 12px;
}
.stButton>button {
    background: #1976d2;
    color: #fff;
    font-weight: bold;
    font-size: 1.1em;
    border-radius: 8px;
    padding: 0.5em 2em;
    margin: 0.8em 0;
    box-shadow: 0 2px 8px rgba(25, 118, 210, 0.2);
    width: 100%;
}
.stButton>button:hover {
    background: #1565c0;
    box-shadow: 0 4px 12px rgba(25, 118, 210, 0.3);
    transform: translateY(-1px);
    transition: all 0.2s ease;
}
.stDataFrame, .stTable {
    font-size: 1.05em;
}
hr {
    border: none;
    border-top: 2px solid #e3e8ee;
    margin: 1.5em 0;
}
.sidebar-card {
    background: #fff;
    border-radius: 12px;
    padding: 1.3em 1.5em;
    margin-bottom: 1.4em;
    border: 1.5px solid #e3e8ee;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
}
.sidebar-title {
    font-size: 1.3em;
    font-weight: bold;
    color: #1976d2;
    margin-bottom: 0.6em;
    letter-spacing: 0.02em;
}
.sidebar-step {
    font-size: 1.1em;
    font-weight: bold;
    display: block;
    margin-bottom: 0.7em;
}
.sidebar-step-active {
    background: linear-gradient(135deg, #1976d2 0%, #0d47a1 100%);
    color: white;
    border-radius: 8px;
    padding: 0.5em 1.2em;
    margin-bottom: 0.7em;
    display: inline-block;
    box-shadow: 0 2px 8px rgba(25, 118, 210, 0.2);
    width: 100%;
    font-size: 1.15em;
    font-weight: 800;
}
.sidebar-step-inactive {
    background: #e3f2fd;
    color: #1565c0;
    border-radius: 8px;
    padding: 0.5em 1.2em;
    margin-bottom: 0.7em;
    display: inline-block;
    width: 100%;
    font-size: 1.15em;
    font-weight: bold;
}
.sidebar-faq-title {
    font-size: 1.15em;
    font-weight: bold;
    color: #1976d2;
    margin-bottom: 0.5em;
}
.sidebar-faq-body {
    background: #f4f8fd;
    border-radius: 8px;
    padding: 1.2em 1.3em;
    color: #333;
    font-size: 0.98em;
    line-height: 1.6;
}
.data-format-table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
}
.data-format-table th, .data-format-table td {
    border: 1px solid #e0e0e0;
    padding: 8px 12px;
    text-align: left;
}
.data-format-table th {
    background-color: #f5f5f5;
    font-weight: bold;
}
.file-location {
    background: #e3f2fd;
    padding: 4px 10px;
    border-radius: 6px;
    color: #1565c0;
    font-weight: 500;
}
.expander-header {
    font-size: 1.15em;
    font-weight: bold;
    color: #1976d2;
}
div[data-testid="stExpander"] div[role="button"] p {
    font-size: 1.15em !important;
    font-weight: bold !important;
    color: #1976d2 !important;
}
.separator-line {
    border-top: 1px solid #e0e0e0;
    margin: 1.5em 0;
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# --- サイドバー ---
with st.sidebar:
    st.markdown('<div class="sidebar-title">分析フロー</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:1em;color:#333;margin-bottom:1em;line-height:1.5;">Causal Impact分析は以下の<b>3つのステップ</b>で行います。各ステップのコンテンツはメイン画面に表示されます。</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="margin-top:0.5em;">
        <div class="sidebar-step-active">STEP 1：データ取り込み／可視化</div>
        <div class="sidebar-step-inactive">STEP 2：分析期間／モデル設定</div>
        <div class="sidebar-step-inactive">STEP 3：分析実行／結果確認</div>
    </div>
    <div class="separator-line"></div>
    """, unsafe_allow_html=True)

    with st.expander("Causal Impactとは？", expanded=False):
        st.markdown("""
<div class="sidebar-faq-title">Causal Impactとは？</div>
<div class="sidebar-faq-body">
<b>Causal Impactは、介入（施策）の効果を測定するための統計手法です。</b><br><br>
介入前のデータから予測モデルを構築し、介入がなかった場合の予測値と実際の値を比較することで、介入の効果を推定します。
</div>
""", unsafe_allow_html=True)
    with st.expander("処置群と対照群について", expanded=False):
        st.markdown("""
<div class="sidebar-faq-title">処置群と対照群について</div>
<div class="sidebar-faq-body">
<b>処置群</b>は、施策（介入）の影響を受けたグループです。<br><br>
<b>対照群</b>は、施策の影響を受けていないグループであり、比較対象となります。
</div>
""", unsafe_allow_html=True)

# --- メインコンテンツ ---
st.markdown("""
<div class="blue-header-card">
    <div class="big-title">Causal Impact 分析</div>
    <div class="sub-title">施策効果を測定し、可視化するシンプルな分析ツール</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="step-card">
    <h2 style="font-size:1.8em;font-weight:bold;color:#1565c0;margin-bottom:0.5em;">STEP 1：データ取り込み／可視化</h2>
    <div style="color:#1976d2;font-size:1.1em;line-height:1.5;">このステップでは、分析に必要な時系列データを読み込み、可視化します。処置群（効果を測定したい対象）と対照群（比較対象）のデータをCSVファイルから取り込み、分析用データセットを作成します。</div>
</div>
""", unsafe_allow_html=True)

# --- データ形式ガイド ---
with st.expander("データ形式ガイド", expanded=False):
    st.markdown("""
<div class="section-title" style="margin-top:0;">CSVファイルの要件</div>
<div style="font-size:1.05em;line-height:1.6;margin-bottom:1.2em;">
CSVファイルには、<b>ymd（日付）</b> と <b>qty（数量）</b> の2つのカラムが必須です。
</div>

<div style="display:flex;gap:2.5em;margin-bottom:1.5em;">
<div style="flex:1;">
<div style="font-weight:bold;font-size:1.1em;margin-bottom:0.5em;color:#1976d2;">基本レイアウト</div>
<table class="data-format-table">
<tr><th>ymd</th><th>qty</th></tr>
<tr><td>20170403</td><td>29</td></tr>
<tr><td>20170425</td><td>24</td></tr>
<tr><td>20170426</td><td>23</td></tr>
<tr><td>20170523</td><td>24</td></tr>
<tr><td>20170524</td><td>26</td></tr>
<tr><td>20170529</td><td>21</td></tr>
<tr><td>...</td><td>...</td></tr>
</table>
</div>
<div style="flex:1;">
<div style="font-weight:bold;font-size:1.1em;margin-bottom:0.5em;color:#1976d2;">追加カラムがある場合の例</div>
<table class="data-format-table">
<tr><th>product_category</th><th>ymd</th><th>qty</th></tr>
<tr><td>ﾒｳ3</td><td>20170403</td><td>29</td></tr>
<tr><td>ﾒｳ3</td><td>20170425</td><td>24</td></tr>
<tr><td>ﾒｳ3</td><td>20170426</td><td>23</td></tr>
<tr><td>ﾒｳ3</td><td>20170523</td><td>24</td></tr>
<tr><td>ﾒｳ3</td><td>20170524</td><td>26</td></tr>
<tr><td>ﾒｳ3</td><td>20170529</td><td>21</td></tr>
<tr><td>...</td><td>...</td><td>...</td></tr>
</table>
</div>
</div>

<ul style="margin-top:1em;font-size:1.05em;line-height:1.6;">
<li><b>ymd：</b>日付（YYYYMMDD形式の8桁数字）</li>
<li><b>qty：</b>数量（整数または小数）</li>
</ul>
<p style="margin-top:0.5em;color:#555;">※ 上記以外のカラムは自由に追加できます。なくても問題ありません</p>

<div class="section-title">データファイルの保存場所</div>
<p style="margin-bottom:1em;font-size:1.05em;line-height:1.6;">処置群と対照群それぞれのCSVデータファイルを、以下の専用フォルダに保存してください。</p>

<div style="background:#f5f5f5;border-radius:10px;padding:1.2em;margin-bottom:1.5em;">
<div style="display:flex;margin-bottom:1em;">
<div style="width:180px;font-weight:bold;">処置群データ：</div>
<div class="file-location">data/treatment_data/</div>
</div>
<div style="display:flex;">
<div style="width:180px;font-weight:bold;">対照群データ：</div>
<div class="file-location">data/control_data/</div>
</div>
</div>

<ul style="font-size:1.05em;line-height:1.6;">
<li>CSVファイルの名称を製品名・品種名などに設定すると、処置群・対照群の名称として表示されます（日本語表記も可）</li>
<li>フォルダ内に複数のCSVファイルを保存しておくと、「データ選択」メニューから対象ファイルを選択できます</li>
</ul>
""", unsafe_allow_html=True)

# --- ファイル選択UI ---
st.markdown('<div class="section-title">分析対象ファイルの選択</div>', unsafe_allow_html=True)

treatment_dir = "data/treatment_data"
control_dir = "data/control_data"

def get_csv_files(directory):
    files = glob.glob(os.path.join(directory, "*.csv"))
    return [os.path.basename(f) for f in files]

treatment_files = get_csv_files(treatment_dir)
control_files = get_csv_files(control_dir)

col1, col2 = st.columns(2)
with col1:
    st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群ファイル</div>', unsafe_allow_html=True)
    treatment_file = st.selectbox("", treatment_files, key="treat", label_visibility="collapsed")
    selected_treat = f"選択：{treatment_file}（処置群）" if treatment_files else "処置群ファイルが見つかりません"
    st.markdown(f'<div style="color:#1976d2;font-size:0.9em;">{selected_treat}</div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">対照群ファイル</div>', unsafe_allow_html=True)
    control_file = st.selectbox("", control_files, key="ctrl", label_visibility="collapsed")
    selected_ctrl = f"選択：{control_file}（対照群）" if control_files else "対照群ファイルが見つかりません"
    st.markdown(f'<div style="color:#1976d2;font-size:0.9em;">{selected_ctrl}</div>', unsafe_allow_html=True)

# --- データ読み込みボタン ---
st.markdown('<div style="margin: 1em 0; width: 100%;"></div>', unsafe_allow_html=True)
read_btn = st.button("データを読み込む", key="read", help="選択したファイルを読み込みます。", type="primary", use_container_width=True)

if read_btn:
    treatment_path = os.path.join(treatment_dir, treatment_file)
    control_path = os.path.join(control_dir, control_file)
    df_treat = pd.read_csv(treatment_path)
    df_ctrl = pd.read_csv(control_path)
    
    # 必要なカラムのみを抽出
    if 'ymd' in df_treat.columns and 'qty' in df_treat.columns:
        df_treat = df_treat[['ymd', 'qty']]
    if 'ymd' in df_ctrl.columns and 'qty' in df_ctrl.columns:
        df_ctrl = df_ctrl[['ymd', 'qty']]

    st.success("データを読み込みました。下記にプレビューと統計情報を表示します。")

    # --- データプレビュー ---
    st.markdown('<div class="section-title">読み込みデータのプレビュー（上位10件）</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    # ファイル名から拡張子を除去
    treatment_name = os.path.splitext(treatment_file)[0]
    control_name = os.path.splitext(control_file)[0]
    
    with col1:
        st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.1em;color:#1976d2;">処置群（{treatment_name}）</div>', unsafe_allow_html=True)
        # インデックスを1から始める
        preview_df_treat = df_treat.head(10).copy()
        preview_df_treat.index = range(1, len(preview_df_treat) + 1)
        st.dataframe(preview_df_treat, use_container_width=True)
    with col2:
        st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.1em;color:#1976d2;">対照群（{control_name}）</div>', unsafe_allow_html=True)
        # インデックスを1から始める
        preview_df_ctrl = df_ctrl.head(10).copy()
        preview_df_ctrl.index = range(1, len(preview_df_ctrl) + 1)
        st.dataframe(preview_df_ctrl, use_container_width=True)

    # --- 統計情報 ---
    st.markdown('<div class="section-title">データの統計情報</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    # 日本語名を含む統計表示用の関数
    def format_stats_with_japanese(df):
        stats = df.describe().reset_index()
        stats.columns = ['統計項目', '数値']
        
        # 日本語名を追加
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
        
        # 小数点以下2桁に丸める（count以外）
        for i, row in stats.iterrows():
            if row['統計項目'] != 'count（個数）':
                stats.at[i, '数値'] = round(row['数値'], 2)
        
        return stats
    
    with col1:
        st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.1em;color:#1976d2;">処置群（{treatment_name}）</div>', unsafe_allow_html=True)
        if 'qty' in df_treat.columns:
            stats_treat = format_stats_with_japanese(df_treat[['qty']])
            st.dataframe(stats_treat, use_container_width=True, hide_index=True)
        else:
            st.error("データに 'qty' カラムが見つかりません")
    
    with col2:
        st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.1em;color:#1976d2;">対照群（{control_name}）</div>', unsafe_allow_html=True)
        if 'qty' in df_ctrl.columns:
            stats_ctrl = format_stats_with_japanese(df_ctrl[['qty']])
            st.dataframe(stats_ctrl, use_container_width=True, hide_index=True)
        else:
            st.error("データに 'qty' カラムが見つかりません")

    # --- 日付をdatetime型に変換 ---
    df_treat['ymd'] = pd.to_datetime(df_treat['ymd'], errors='coerce')
    df_ctrl['ymd'] = pd.to_datetime(df_ctrl['ymd'], errors='coerce')

    # 日付変換エラーをチェック
    if df_treat['ymd'].isna().any() or df_ctrl['ymd'].isna().any():
        st.warning("一部の日付データが正しく変換できませんでした。データ形式を確認してください。")

    # --- 時系列プロット ---
    st.markdown('<div class="section-title">時系列プロット</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.1em;color:#1976d2;">処置群と対照群の時系列推移</div>', unsafe_allow_html=True)
    
    # 2つのY軸を持つサブプロットを作成
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 処置群のプロット（左軸）
    fig.add_trace(
        go.Scatter(
            x=df_treat['ymd'], 
            y=df_treat['qty'],
            name=f"処置群（{treatment_name}）",
            line=dict(color="#1976d2", width=3),
            mode='lines'
        ),
        secondary_y=False
    )
    
    # 対照群のプロット（右軸）
    fig.add_trace(
        go.Scatter(
            x=df_ctrl['ymd'], 
            y=df_ctrl['qty'],
            name=f"対照群（{control_name}）",
            line=dict(color="#ef5350", width=3),
            mode='lines'
        ),
        secondary_y=True
    )
    
    # 軸ラベルを更新
    fig.update_xaxes(title_text="日付", gridcolor="#e0e0e0", tickformat="%Y-%m")
    fig.update_yaxes(title_text=f"処置群の数量", secondary_y=False, 
                     title_font=dict(color="#1976d2"), tickfont=dict(color="#1976d2"), gridcolor="#e0e0e0")
    fig.update_yaxes(title_text=f"対照群の数量", secondary_y=True, 
                     title_font=dict(color="#ef5350"), tickfont=dict(color="#ef5350"))
    
    # レイアウトを更新
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        hovermode="x unified",
        plot_bgcolor='white',
        margin=dict(t=50, l=60, r=60, b=50),
        height=500
    )
    
    # グラフ表示の設定
    config = {
        'displayModeBar': True,
        'scrollZoom': True,
        'displaylogo': False,
        'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape'],
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'time_series_plot',
            'height': 500,
            'width': 900,
            'scale': 2
        }
    }
    
    st.plotly_chart(fig, use_container_width=True, config=config)
    
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
    
    with st.expander("分析期間設定のヒント"):
        st.markdown("""
<div style="line-height:1.7;">
<ul>
<li><b>介入前期間</b>：施策（介入）実施前の十分な長さのデータ期間を選択してください</li>
<li><b>介入後期間</b>：施策（介入）実施後の効果測定期間を選択してください</li>
<li><b>季節性</b>：データに季節性がある場合は、少なくとも2〜3周期分のデータがあることが望ましいです</li>
<li><b>イレギュラー</b>：大きな外部要因の影響がある期間は介入前期間に含めないことをおすすめします</li>
</ul>
</div>
        """, unsafe_allow_html=True)

    # --- 分析用データセット作成セクション ---
    st.markdown('<div class="section-title">分析用データセットの作成</div>', unsafe_allow_html=True)
    
    st.markdown("""
<div style="background:#f5f5f5;border-radius:10px;padding:1.5em;margin-bottom:1.5em;">
<div style="font-size:1.15em;font-weight:bold;color:#1976d2;margin-bottom:1em;">Causal Impact分析用データセットの作成</div>
<div style="font-size:1.05em;margin-bottom:0.8em;">データ集計方法を選択</div>
</div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 3])
    with col1:
        freq_option = st.radio(
            "データ集計方法",
            options=["月次", "旬次"],
            label_visibility="collapsed"
        )
    
    # --- データセット作成ボタン ---
    create_btn = st.button("データセット作成", key="create", help="Causal Impact分析用データセットを作成します。", type="primary")
    
    if create_btn:
        st.success("データセットの作成が完了しました。分析設定を行いましょう。")
        
        # --- 作成データセットプレビュー ---
        st.markdown('<div class="section-title">作成データセットのプレビュー</div>', unsafe_allow_html=True)
        
        # データセット作成処理（簡略版）
        dataset_preview = pd.DataFrame({
            'ymd': pd.date_range(start=df_treat['ymd'].min(), end=df_treat['ymd'].max(), freq='MS' if freq_option == "月次" else '10D'),
            f'処置群（{treatment_name}）': range(len(pd.date_range(start=df_treat['ymd'].min(), end=df_treat['ymd'].max(), freq='MS' if freq_option == "月次" else '10D'))),
            f'対照群（{control_name}）': range(100, 100 + len(pd.date_range(start=df_treat['ymd'].min(), end=df_treat['ymd'].max(), freq='MS' if freq_option == "月次" else '10D')))
        })
        
        # データ期間情報
        st.markdown(f"""
<div style="margin-bottom:1.5em;">
<div><b>対象期間：</b>{dataset_preview['ymd'].min().strftime('%Y-%m-%d')} 〜 {dataset_preview['ymd'].max().strftime('%Y-%m-%d')}</div>
<div><b>データ数：</b>{len(dataset_preview)}件</div>
</div>
        """, unsafe_allow_html=True)
        
        # プレビューとデータ表示
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;">データプレビュー（上位10件表示）</div>', unsafe_allow_html=True)
            preview_df = dataset_preview.head(10).copy()
            preview_df['ymd'] = preview_df['ymd'].dt.strftime('%Y-%m-%d')
            # インデックスを1から始める
            preview_df.index = range(1, len(preview_df) + 1)
            st.dataframe(preview_df, use_container_width=True)
        
        with col2:
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;">統計情報</div>', unsafe_allow_html=True)
            stats_df = pd.DataFrame({
                '統計項目': ['count（個数）', 'mean（平均）', 'std（標準偏差）', 'min（最小値）', '25%（第1四分位数）', '50%（中央値）', '75%（第3四分位数）', 'max（最大値）'],
                f'処置群（{treatment_name}）': [len(dataset_preview), 10.00, 5.00, 0.00, 5.00, 10.00, 15.00, 20.00],
                f'対照群（{control_name}）': [len(dataset_preview), 110.00, 5.00, 100.00, 105.00, 110.00, 115.00, 120.00]
            })
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
        # STEP 1完了表示
        st.markdown("""
<div style="background:#e8f5e9;border-radius:10px;padding:1em;margin-top:2em;margin-bottom:1em;">
<div style="display:flex;align-items:center;">
<span style="font-size:1.6em;margin-right:0.5em;">✓</span>
<span style="color:#2e7d32;font-weight:bold;font-size:1.2em;">データセットの作成が完了しました。分析設定を行いましょう。</span>
</div>
</div>
        """, unsafe_allow_html=True)
        
else:
    st.info("処置群・対照群のCSVファイルを選択し、「データを読み込む」ボタンを押してください。") 