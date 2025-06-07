# インラインHTMLスタイル定数
# メインアプリケーションで使用されるインラインHTMLスタイルを管理

# セクションタイトル用スタイル
SECTION_TITLE_HTML = '<div class="section-title">{}</div>'

# サブタイトル用スタイル  
SUBSECTION_TITLE_HTML = '<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">{}</div>'

# ファイル選択表示用スタイル
FILE_SELECTED_HTML = '<div style="color:#1976d2;font-size:0.9em;">{}</div>'

# 説明テキスト用スタイル
HELP_TEXT_HTML = '<div style="color:#555555;font-size:0.9em;margin-top:-5px;margin-bottom:15px;padding-left:5px;">{}</div>'

# マージン調整用スタイル
MARGIN_TOP_25_HTML = '<div style="margin-top:25px;"></div>'
MARGIN_TOP_15_HTML = '<div style="margin-top:15px;margin-bottom:10px;"></div>'

# 分析結果表示用スタイル
ANALYSIS_INFO_HTML = '<div style="margin-bottom:0.8em;"><span style="font-weight:bold;font-size:1.05em;">{label}：</span><span style="color:#424242;">{value}</span></div>'

# 分析手法説明用スタイル
ANALYSIS_METHOD_HTML = '<div style="margin-bottom:1em;font-size:1.05em;"><span style="font-weight:bold;">{method}：</span><span style="font-weight:normal;">{description}</span></div>'

# サイドバー関連スタイル
SIDEBAR_STEP_ACTIVE_HTML = """
<div style="margin-top:0.5em;">
    <div class="{step1_class}">STEP 1：データ取り込み／可視化</div>
    <div class="{step2_class}">STEP 2：分析期間／パラメータ設定</div>
    <div class="{step3_class}">STEP 3：分析実行／結果確認</div>
</div>
<div class="separator-line"></div>
"""

# 終了メッセージHTML
END_MESSAGE_HTML = '</div>' 