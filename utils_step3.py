import matplotlib.pyplot as plt
import pandas as pd
import re
import io
import base64
from causalimpact import CausalImpact
import matplotlib
matplotlib.use('Agg')  # バックエンドを明示的に指定（サーバー環境対応）

def run_causal_impact_analysis(data, pre_period, post_period):
    ci = CausalImpact(data, pre_period, post_period)
    summary = ci.summary()
    report = ci.summary(output='report')
    
    # グラフを作成
    fig = ci.plot(figsize=(10, 6))
    if fig is None:
        fig = plt.gcf()
    
    # 下部の注釈メッセージを非表示にする
    # 現在のaxesを取得
    axes = plt.gcf().get_axes()
    for ax in axes:
        # 下部の注釈テキストを探して削除
        texts = ax.texts
        for text in texts:
            if "Note:" in text.get_text() or "observations were removed" in text.get_text():
                text.set_visible(False)  # テキストを非表示に
    
    return ci, summary, report, fig

def build_summary_dataframe(summary, alpha_percent):
    """
    CausalImpactの分析結果サマリーをデータフレームにまとめる関数
    相対効果と相対効果の信頼区間、p値については、平均値の欄にのみ表示し、累積値には「同左」と表示する
    """
    lines = [l for l in summary.split('\n') if l.strip()]
    data_lines = []
    
    # p値を抽出（Posterior tail-area probability p:行から）
    p_value = None
    for line in lines:
        if 'Posterior tail-area probability p:' in line:
            p_match = re.search(r'p:\s+([0-9.]+)', line)
            if p_match:
                p_value = float(p_match.group(1))
                break
    
    # サマリーデータを抽出・整形
    for line in lines[1:]:
        parts = re.split(r'\s{2,}', line.strip())
        if len(parts) == 3:
            item_name = parts[0]
            avg_value = parts[1]
            cum_value = parts[2]
            
            # 相対効果に関連する行を識別するための条件を強化
            is_relative_effect = (
                '相対効果' in item_name or 
                'relative effect' in item_name.lower() or 
                'relative' in item_name.lower() and 'effect' in item_name.lower() or
                '%' in avg_value and '%' in cum_value  # 百分率表記（%）を含む行も相対効果として処理
            )
            
            # 相対効果関連の行と認識された場合
            if is_relative_effect:
                # 平均値をそのまま表示し、累積値を「同左」に置き換え
                data_lines.append([avg_value, '同左'])
                print(f"相対効果行として処理: {item_name} → 平均値: {avg_value}, 累積値: 同左")
            else:
                data_lines.append([avg_value, cum_value])
    
    df_summary = pd.DataFrame(data_lines, columns=['分析期間の平均値','分析期間の累積値'])
    
    # インデックス名の設定（既存と同じ）
    japanese_index = [
        '実測値',
        '予測値 (標準偏差)',
        f'予測値 {alpha_percent}% 信頼区間',
        '絶対効果 (標準偏差)',
        f'絶対効果 {alpha_percent}% 信頼区間',
        '相対効果 (標準偏差)',
        f'相対効果 {alpha_percent}% 信頼区間'
    ]
    
    # インデックス名を設定（データフレームの行数に合わせて切り詰める）
    if len(df_summary) <= len(japanese_index):
        df_summary.index = japanese_index[:len(df_summary)]
    else:
        # データフレームの行数が多い場合は警告を出力
        print(f"警告: データフレームの行数({len(df_summary)})がインデックス名の数({len(japanese_index)})より多いです")
        # 不足分は元のインデックスを使用
        df_summary.index = japanese_index + [f"行{i+1}" for i in range(len(japanese_index), len(df_summary))]
    
    # 行ごとのインデックス名とデータを確認
    for idx, row in df_summary.iterrows():
        print(f"行: {idx}, 平均値: {row['分析期間の平均値']}, 累積値: {row['分析期間の累積値']}")
    
    # 相対効果と相対効果の信頼区間行を確実に「同左」に設定
    for idx in df_summary.index:
        if '相対効果' in idx:
            df_summary.at[idx, '分析期間の累積値'] = '同左'
            print(f"相対効果関連の行を修正: {idx} → 累積値: 同左")
    
    # p値がある場合は新しい行として追加
    if p_value is not None:
        # 小数点以下4桁までの文字列にフォーマット
        p_value_str = f"{p_value:.4f}"
        # 最終行の後に新しい行を追加し、平均値の列に値を表示し、累積値の列は「同左」と表示
        df_summary.loc['p値 (事後確率)'] = [p_value_str, '同左']
        print(f"p値を追加: 平均値: {p_value_str}, 累積値: 同左")
    
    # データフレームを戻す前に最終的な形を確認
    print("最終的なデータフレーム:")
    print(df_summary)
    
    return df_summary

def get_summary_csv_download_link(df_summary, treatment_name, period_start, period_end, alpha_percent):
    """
    分析結果サマリーをCSVとしてダウンロードするためのリンクを生成する関数
    
    Parameters:
    -----------
    df_summary : pandas.DataFrame
        build_summary_dataframe関数で生成した分析結果サマリーのデータフレーム
    treatment_name : str
        分析対象の名称
    period_start : datetime.date
        分析期間の開始日
    period_end : datetime.date
        分析期間の終了日
    alpha_percent : int
        信頼水準（%）
        
    Returns:
    --------
    str
        ダウンロードリンクのHTML
    """
    # CSVに追加するヘッダー情報（メタデータ）を作成
    header_info = pd.DataFrame([
        ['分析対象', treatment_name],
        ['分析期間', f"{period_start.strftime('%Y-%m-%d')} ～ {period_end.strftime('%Y-%m-%d')}"],
        ['信頼水準', f"{alpha_percent}%"],
    ], columns=['項目', '値'])
    
    # メタデータとサマリーを結合
    # サマリーデータフレームをリセットしてインデックスを列に変換
    df_summary_reset = df_summary.reset_index()
    df_summary_reset.columns = ['指標', '分析期間の平均値', '分析期間の累積値']
    
    # バッファを使ってCSVを生成
    csv_buffer = io.StringIO()
    
    # メタデータを書き込み
    header_info.to_csv(csv_buffer, index=False, encoding='utf-8-sig')  # UTF-8 with BOMで文字化け対策
    
    # 改行を追加
    csv_buffer.write('\n')
    
    # サマリーを書き込み（ヘッダーは既に書き込み済みなので書き込まない）
    df_summary_reset.to_csv(csv_buffer, index=False, encoding='utf-8-sig', mode='a')
    
    # バッファの内容をbase64エンコード
    csv_string = csv_buffer.getvalue()
    csv_base64 = base64.b64encode(csv_string.encode('utf-8-sig')).decode()
    
    # ファイル名の設定
    filename = f"causal_impact_summary_{treatment_name}_{period_start.strftime('%Y%m%d')}_{period_end.strftime('%Y%m%d')}.csv"
    
    # ダウンロードリンクの生成
    href = f'data:text/csv;charset=utf-8-sig;base64,{csv_base64}'
    
    return href, filename

def get_figure_pdf_download_link(fig, treatment_name, period_start, period_end):
    """
    分析結果グラフをPDFとしてダウンロードするためのリンクを生成する関数
    
    Parameters:
    -----------
    fig : matplotlib.figure.Figure
        run_causal_impact_analysis関数で生成した分析結果グラフ
    treatment_name : str
        分析対象の名称
    period_start : datetime.date
        分析期間の開始日
    period_end : datetime.date
        分析期間の終了日
        
    Returns:
    --------
    str
        ダウンロードリンクのHTML
    """
    # PDFのバッファを用意
    pdf_buffer = io.BytesIO()
    
    # タイトルを追加（文字化け防止のため削除）
    # fig.suptitle(f"分析対象: {treatment_name}\n分析期間: {period_start.strftime('%Y-%m-%d')} ～ {period_end.strftime('%Y-%m-%d')}")
    
    # PDFとして保存
    fig.savefig(pdf_buffer, format='pdf', bbox_inches='tight')
    pdf_buffer.seek(0)
    
    # Base64エンコード
    pdf_base64 = base64.b64encode(pdf_buffer.read()).decode()
    
    # ファイル名の設定
    filename = f"causal_impact_graph_{treatment_name}_{period_start.strftime('%Y%m%d')}_{period_end.strftime('%Y%m%d')}.pdf"
    
    # ダウンロードリンクの生成
    href = f'data:application/pdf;base64,{pdf_base64}'
    
    return href, filename 