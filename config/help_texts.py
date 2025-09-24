# -*- coding: utf-8 -*-
"""
Causal Impact分析アプリ ヘルプテキスト定数

app.py内の長文テキスト（HTML含む）を外部化
"""

# === データ形式ガイド ===
DATA_FORMAT_GUIDE_HTML = """
<div class="section-title" style="margin-top:0;">CSVファイルの要件</div>
<div style="font-size:1.05em;line-height:1.6;margin-bottom:1.2em;">
CSVファイルには、<b>ymd（日付）</b> と <b>qty（数量）</b> の2つのカラムが必須です。
</div>

<div style="background-color:#e3f2fd;border-radius:8px;padding:15px;margin-bottom:1.5em;border-left:4px solid #1976d2;">
<div style="font-weight:bold;margin-bottom:8px;color:#1976d2;font-size:1.1em;">データ量の推奨値</div>
<ul style="margin:0;padding-left:1.2em;line-height:1.6;">
<li><b>二群比較（処置群＋対照群）：</b>介入前後を合わせて24件以上のデータを推奨<br>
<span style="color:#666;font-size:0.95em;">（月次データ：2年分、旬次データ：8ヶ月分程度）</span></li>
<li><b>単群推定（処置群のみ）：</b>季節性学習のため、36件以上のデータを強く推奨<br>
<span style="color:#666;font-size:0.95em;">（月次データ：3年分、旬次データ：1年分程度。介入前期間は全体の60%以上を推奨）</span></li>
</ul>
</div>

<div style="display:flex;gap:2.5em;margin-bottom:1.5em;">
<div style="flex:1;">
<div style="font-weight:bold;font-size:1.1em;margin-bottom:0.5em;">基本レイアウト</div>
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
<div style="font-weight:bold;font-size:1.1em;margin-bottom:0.5em;">追加カラムがある場合の例</div>
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
"""

# === FAQ テキスト ===
FAQ_CAUSAL_IMPACT = """
<div class="sidebar-faq-body">
Googleが開発した<b>因果推論手法</b>。<br>「キャンペーンの効果は本当にあったのか？」「台風で売上がどれだけ伸びたのか？」といった営業施策や天候などの外部要因（＝介入）が過去の需要に与えた影響（＝介入効果）を測定するために用いられます。
<br><br>
介入の影響を受けたグループ<b> 処置群 </b>と影響を受けていないグループ<b> 対照群 </b>の関係性をもとに、状態空間モデルを用いて「もし介入がなかったら処置群どうなっていたのか？」を予測し、その予測値と実際のデータを比較して介入効果を測定します。
</div>
"""

FAQ_STATE_SPACE_MODEL = """
<div class="sidebar-faq-body">
時系列データの変化の傾向や構造を捉える統計手法で、観測データの背後にある"見えない状態"を推定しながら将来の動きを予測します。<br><br>
Causal Impactでは、このモデルを用いて「介入がなかった場合の自然な推移」を予測します。
</div>
"""

# === ヘッダーカード ===
HEADER_CARD_HTML = """
<div class="blue-header-card">
    <div class="big-title">Causal Impact 分析</div>
    <div class="sub-title">施策効果を測定し、可視化するシンプルな分析ツール</div>
</div>
"""

# === STEPカード ===
STEP1_CARD_HTML = """
<div class="step-card">
    <h2 style="font-size:1.8em;font-weight:bold;color:#1565c0;margin-bottom:0.5em;">STEP 1：データ取り込み／可視化</h2>
    <div style="color:#1976d2;font-size:1.1em;line-height:1.5;">このステップでは、分析に必要な時系列データを読み込み、可視化します。処置群（効果を測定したい対象）と対照群（比較対象）のデータをCSVファイルから取り込み、分析用データセットを作成します。</div>
</div>
"""

STEP2_CARD_HTML = """
<div class="step-card">
    <h2 style="font-size:1.8em;font-weight:bold;color:#1565c0;margin-bottom:0.5em;">STEP 2：分析期間／パラメータ設定</h2>
    <div style="color:#1976d2;font-size:1.1em;line-height:1.5;">このステップでは、Causal Impact分析の実行に必要な期間設定とモデルパラメータを設定します。データの観測期間を「介入前期間」「介入期間」に分割し、統計分析に必要なパラメータを指定します。</div>
</div>
"""

STEP3_CARD_HTML = """
<div class="step-card">
    <h2 style="font-size:1.8em;font-weight:bold;color:#1565c0;margin-bottom:0.5em;">STEP 3：分析実行／結果確認</h2>
    <div style="color:#1976d2;font-size:1.1em;line-height:1.5;">このステップでは、設定したパラメータでCausal Impact分析を実行し、結果を確認・ダウンロードします。分析結果はタブごとに整理され、施策効果のサマリー・詳細・グラフ・レポートを表示します。</div>
</div>
"""

# === リセット案内文 ===
RESET_GUIDE_HTML = """
<div style="background-color:#ffebee;border-radius:8px;padding:12px 15px;border-left:4px solid #d32f2f;margin-bottom:15px;">
    <div style="font-weight:bold;margin-bottom:8px;color:#d32f2f;font-size:1.05em;">最初からやり直す場合：</div>
    <div style="line-height:1.5;">画面左上の<b>更新ボタン（⟳）</b>をクリックするか、<b>Ctrl + R</b>を押して、STEP１のデータの取り込みから再実行してください。</div>
</div>
"""

# === サイドバー フロー説明 ===
SIDEBAR_FLOW_DESCRIPTION = """
<div style="font-size:1em;color:#333;margin-bottom:1em;line-height:1.5;">Causal Impact分析は以下の<b>3つのステップ</b>で行います。各ステップのコンテンツはメイン画面に表示されます。</div>
""" 