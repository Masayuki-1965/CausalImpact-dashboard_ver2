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
"""

# === FAQ テキスト ===
FAQ_CAUSAL_IMPACT = """
<div class="sidebar-faq-body">
<b>Causal Impact</b>は、Googleが開発した統計的手法で、キャンペーンなどの施策（＝介入）がもたらした効果を測定するために用いられます。<br><br>
施策の影響を受けた<b>"処置群"</b>と、影響を受けていない<b>"対照群"</b>の関係性をもとに、状態空間モデルを用いて「介入がなかった場合の処置群の予測値」を算出し、これを実際の観測値と比較することで、施策による因果的な影響を明らかにします。
</div>
"""

FAQ_STATE_SPACE_MODEL = """
<div class="sidebar-faq-body">
<b>状態空間モデル</b>は、時系列データの変化の傾向や構造を捉える統計手法で、観測データの背後にある"見えない状態"を推定しながら将来の動きを予測します。<br><br>
Causal Impactでは、このモデルを用いて「施策がなかった場合の自然な推移」を予測します。
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