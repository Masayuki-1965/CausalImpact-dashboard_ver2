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
    
    # グラフを作成（単群推定と同じサイズに統一）
    fig = ci.plot(figsize=(11, 7))
    if fig is None:
        fig = plt.gcf()
    
    # グラフタイトルを日本語に設定
    axes = fig.get_axes()
    if len(axes) >= 3:
        axes[0].set_title('実測値 vs 予測値', fontsize=12, weight='normal')
        axes[1].set_title('時点効果', fontsize=12, weight='normal')
        axes[2].set_title('累積効果', fontsize=12, weight='normal')
    
    # 下部の注釈メッセージを非表示にする
    for ax in axes:
        texts = ax.texts[:]  # テキストリストのコピーを作成
        for text in texts:
            text_content = text.get_text()
            if ("Note:" in text_content or 
                "observations were removed" in text_content or
                "diffuse initialization" in text_content or
                "approximate" in text_content):
                text.remove()  # テキストを完全に削除
    
    # 図全体のタイトルを削除
    fig.suptitle('')
    
    # レイアウトを調整（単群推定と同様）
    plt.tight_layout()
    
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
    
    # 相対効果と相対効果の信頼区間行を確実に適切な値に設定
    for idx in df_summary.index:
        if '相対効果' in idx:
            # 視認性向上のため、平均値欄の内容を累積値欄にもコピー
            avg_value = df_summary.at[idx, '分析期間の平均値']
            df_summary.at[idx, '分析期間の累積値'] = avg_value
            print(f"相対効果関連の行を修正: {idx} → 累積値: {avg_value}")
    
    # p値がある場合は新しい行として追加
    if p_value is not None:
        # 小数点以下4桁までの文字列にフォーマット
        p_value_str = f"{p_value:.4f}"
        # 視認性向上のため、両欄に同じ値を表示
        df_summary.loc['p値 (事後確率)'] = [p_value_str, p_value_str]
        print(f"p値を追加: 平均値: {p_value_str}, 累積値: {p_value_str}")
    
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

def get_detail_csv_download_link(ci, period, treatment_name):
    """
    CausalImpactの詳細データ（予測値・実測値・効果・累積値など）をCSVとしてダウンロードするためのリンクを生成する関数
    
    Parameters:
    -----------
    ci : CausalImpactオブジェクト
    period : dict
        'pre_start', 'pre_end', 'post_start', 'post_end' を含む分析期間情報
    treatment_name : str
        分析対象の名称
    
    Returns:
    --------
    href, filename : str, str
        ダウンロードリンクのHTML, ファイル名
    """
    import numpy as np
    df = ci.inferences.copy()
    df = df.reset_index()
    # 日付列名を統一
    if 'index' in df.columns:
        df = df.rename(columns={'index': '日付'})
    elif 'date' in df.columns:
        df = df.rename(columns={'date': '日付'})
    else:
        df = df.rename(columns={df.columns[0]: '日付'})

    # 変数名マッピング
    col_map = {
        'preds': ['preds', 'predicted', 'predicted_mean', 'prediction', 'pred_mean', 'preds', 'pred'],
        'preds_lower': ['preds_lower', 'predicted_lower', 'prediction_lower', 'pred_lower', 'lower'],
        'preds_upper': ['preds_upper', 'predicted_upper', 'prediction_upper', 'pred_upper', 'upper'],
        'point_effects': ['point_effects', 'point_effect', 'effect', 'effects'],
        'point_effects_lower': ['point_effects_lower', 'effect_lower', 'point_effect_lower', 'effects_lower'],
        'point_effects_upper': ['point_effects_upper', 'effect_upper', 'point_effect_upper', 'effects_upper'],
        'post_cum_y': ['post_cum_y', 'cumulative_actual', 'cum_actual', 'actual_cum', 'cumsum_actual'],
        'post_cum_pred': ['post_cum_pred', 'cumulative_predicted', 'cum_predicted', 'predicted_cum', 'cumsum_predicted'],
        'post_cum_pred_lower': ['post_cum_pred_lower', 'cumulative_predicted_lower', 'cum_predicted_lower', 'predicted_cum_lower', 'cumsum_predicted_lower'],
        'post_cum_pred_upper': ['post_cum_pred_upper', 'cumulative_predicted_upper', 'cum_predicted_upper', 'predicted_cum_upper', 'cumsum_predicted_upper'],
        'post_cum_effects': ['post_cum_effects', 'cumulative_effect', 'cum_effect', 'effect_cum', 'cumsum_effect'],
        'post_cum_effects_lower': ['post_cum_effects_lower', 'cumulative_effect_lower', 'cum_effect_lower', 'effect_cum_lower', 'cumsum_effect_lower'],
        'post_cum_effects_upper': ['post_cum_effects_upper', 'cumulative_effect_upper', 'cum_effect_upper', 'effect_cum_upper', 'cumsum_effect_upper'],
    }
    # 15列の日本語名・英字名
    jp_names = [
        '日付',
        '実測値',
        '予測値',
        '予測値下限',
        '予測値上限',
        '効果',
        '効果下限',
        '効果上限',
        '累積実測値',
        '累積予測値',
        '累積予測値下限',
        '累積予測値上限',
        '累積効果',
        '累積効果下限',
        '累積効果上限',
    ]
    en_names = [
        'date',
        'y',
        'preds',
        'preds_lower',
        'preds_upper',
        'point_effects',
        'point_effects_lower',
        'point_effects_upper',
        'post_cum_y',
        'post_cum_pred',
        'post_cum_pred_lower',
        'post_cum_pred_upper',
        'post_cum_effects',
        'post_cum_effects_lower',
        'post_cum_effects_upper',
    ]
    # 変数名→出力名の対応
    var2en = dict(zip(jp_names, en_names))
    var2out = {
        'preds': '予測値',
        'preds_lower': '予測値下限',
        'preds_upper': '予測値上限',
        'point_effects': '効果',
        'point_effects_lower': '効果下限',
        'point_effects_upper': '効果上限',
        'post_cum_y': '累積実測値',
        'post_cum_pred': '累積予測値',
        'post_cum_pred_lower': '累積予測値下限',
        'post_cum_pred_upper': '累積予測値上限',
        'post_cum_effects': '累積効果',
        'post_cum_effects_lower': '累積効果下限',
        'post_cum_effects_upper': '累積効果上限',
    }
    # 各列をDataFrameに追加
    for var, candidates in col_map.items():
        found = False
        for cand in candidates:
            if cand in df.columns:
                df[var2out[var]] = df[cand]
                found = True
                break
        if not found:
            df[var2out[var]] = np.nan

    # 実測値（y）: 予測値＋効果
    df['実測値'] = df['予測値'] + df['効果']

    # 期間情報
    post_start = pd.to_datetime(period['post_start'])
    post_end = pd.to_datetime(period['post_end'])
    mask_post = (df['日付'] >= post_start) & (df['日付'] <= post_end)

    # 累積値（I～O列）は介入期間のみ出力、それ以外は空欄
    for col in jp_names[8:]:
        if col in df.columns:
            df.loc[~mask_post, col] = np.nan

    # 列順を指定
    for col in jp_names:
        if col not in df.columns:
            df[col] = np.nan
    output_df = df[jp_names].copy()
    # 日付を文字列に
    output_df['日付'] = pd.to_datetime(output_df['日付']).dt.strftime('%Y/%m/%d')

    # 1行目: 日本語名, 2行目: 英字名, 3行目以降: データ
    import io, base64
    csv_buffer = io.StringIO()
    # ヘッダー2行
    csv_buffer.write(','.join(jp_names) + '\n')
    csv_buffer.write(','.join(en_names) + '\n')
    # データ
    output_df.to_csv(csv_buffer, index=False, header=False, encoding='utf-8-sig')
    # 注釈を末尾に追加
    csv_buffer.write('\n※I～O列の累積値は、介入期間のみ出力しています（介入期間外は空欄）。\n')
    csv_string = csv_buffer.getvalue()
    csv_base64 = base64.b64encode(csv_string.encode('utf-8-sig')).decode()
    filename = f"causal_impact_detail_{treatment_name}_{post_start.strftime('%Y%m%d')}_{post_end.strftime('%Y%m%d')}.csv"
    href = f'data:text/csv;charset=utf-8-sig;base64,{csv_base64}'
    return href, filename

def build_enhanced_summary_table(ci, confidence_level=95):
    """
    CausalImpactの分析結果を見やすい表形式で整理する関数
    
    Parameters:
    -----------
    ci : CausalImpact
        分析結果オブジェクト
    confidence_level : int
        信頼水準（%）、デフォルト95%
        
    Returns:
    --------
    pandas.DataFrame
        整形された分析結果テーブル
    """
    try:
        import pandas as pd
        
        # CausalImpactの summary データを取得
        # まず summary_data を試し、なければ summary を使用
        if hasattr(ci, 'summary_data') and ci.summary_data is not None:
            summary_data = ci.summary_data
        elif hasattr(ci, 'summary') and callable(ci.summary):
            # summary()メソッドの結果をDataFrameに変換
            summary_text = str(ci.summary())
            # テキストからデータを抽出（フォールバック）
            return extract_summary_from_text(summary_text, confidence_level)
        else:
            # どちらも利用できない場合は空のDataFrameを返す
            return pd.DataFrame(columns=['指標', '分析期間の平均値', '分析期間の累積値'])
        
        # 表示用のデータを準備
        results_data = []
        
        # 実測値
        if 'actual' in summary_data.index:
            actual_avg = summary_data.loc['actual', 'average']
            actual_cum = summary_data.loc['actual', 'cumulative']
            results_data.append(['実測値', f"{actual_avg:.1f}", f"{actual_cum:,.1f}"])
        
        # 予測値（標準偏差）
        if 'predicted' in summary_data.index:
            pred_avg = summary_data.loc['predicted', 'average']
            pred_cum = summary_data.loc['predicted', 'cumulative']
            
            # 標準偏差が利用可能かチェック
            if 'std' in summary_data.columns:
                pred_sd = summary_data.loc['predicted', 'std']
                avg_str = f"{pred_avg:.1f} ({pred_sd:.1f})"
                cum_str = f"{pred_cum:,.1f} ({pred_sd:.1f})"
            else:
                avg_str = f"{pred_avg:.1f}"
                cum_str = f"{pred_cum:,.1f}"
            
            results_data.append(['予測値（標準偏差）', avg_str, cum_str])
        
        # 予測値信頼区間（動的に信頼水準を反映）
        if 'predicted_lower' in summary_data.index and 'predicted_upper' in summary_data.index:
            pred_lower_avg = summary_data.loc['predicted_lower', 'average']
            pred_upper_avg = summary_data.loc['predicted_upper', 'average']
            pred_lower_cum = summary_data.loc['predicted_lower', 'cumulative']
            pred_upper_cum = summary_data.loc['predicted_upper', 'cumulative']
            
            avg_ci_str = f"[{pred_lower_avg:.1f}, {pred_upper_avg:.1f}]"
            cum_ci_str = f"[{pred_lower_cum:,.1f}, {pred_upper_cum:,.1f}]"
            results_data.append([f'予測値 {confidence_level}% 信頼区間', avg_ci_str, cum_ci_str])
        
        # 絶対効果（標準偏差）
        if 'abs_effect' in summary_data.index:
            abs_avg = summary_data.loc['abs_effect', 'average']
            abs_cum = summary_data.loc['abs_effect', 'cumulative']
            
            # 標準偏差が利用可能かチェック
            if 'std' in summary_data.columns:
                abs_sd = summary_data.loc['abs_effect', 'std']
                avg_str = f"{abs_avg:.1f} ({abs_sd:.1f})"
                cum_str = f"{abs_cum:,.1f} ({abs_sd:.1f})"
            else:
                avg_str = f"{abs_avg:.1f}"
                cum_str = f"{abs_cum:,.1f}"
            
            results_data.append(['絶対効果（標準偏差）', avg_str, cum_str])
        
        # 絶対効果信頼区間（動的に信頼水準を反映）
        if 'abs_effect_lower' in summary_data.index and 'abs_effect_upper' in summary_data.index:
            abs_lower_avg = summary_data.loc['abs_effect_lower', 'average']
            abs_upper_avg = summary_data.loc['abs_effect_upper', 'average']
            abs_lower_cum = summary_data.loc['abs_effect_lower', 'cumulative']
            abs_upper_cum = summary_data.loc['abs_effect_upper', 'cumulative']
            
            avg_ci_str = f"[{abs_lower_avg:.1f}, {abs_upper_avg:.1f}]"
            cum_ci_str = f"[{abs_lower_cum:,.1f}, {abs_upper_cum:,.1f}]"
            results_data.append([f'絶対効果 {confidence_level}% 信頼区間', avg_ci_str, cum_ci_str])
        
        # 相対効果（標準偏差）
        if 'rel_effect' in summary_data.index:
            rel_avg = summary_data.loc['rel_effect', 'average']
            
            # 標準偏差が利用可能かチェック
            if 'std' in summary_data.columns:
                rel_sd = summary_data.loc['rel_effect', 'std']
                rel_str = f"{rel_avg*100:.1f}% ({rel_sd*100:.1f}%)"
            else:
                rel_str = f"{rel_avg*100:.1f}%"
            
            # 視認性向上のため、両欄に同じ値を表示
            results_data.append(['相対効果（標準偏差）', rel_str, rel_str])
        
        # 相対効果信頼区間（動的に信頼水準を反映）
        if 'rel_effect_lower' in summary_data.index and 'rel_effect_upper' in summary_data.index:
            rel_lower_avg = summary_data.loc['rel_effect_lower', 'average']
            rel_upper_avg = summary_data.loc['rel_effect_upper', 'average']
            
            rel_ci_str = f"[{rel_lower_avg*100:.1f}%, {rel_upper_avg*100:.1f}%]"
            # 視認性向上のため、両欄に同じ値を表示
            results_data.append([f'相対効果 {confidence_level}% 信頼区間', rel_ci_str, rel_ci_str])
        
        # p値（事後確率）
        if hasattr(ci, 'p_value') and ci.p_value is not None:
            p_value = ci.p_value
            # 視認性向上のため、両欄に同じ値を表示
            results_data.append(['p値（事後確率）', f"{p_value:.4f}", f"{p_value:.4f}"])
        elif hasattr(ci, 'summary_data') and 'Posterior tail-area probability p:' in ci.summary_data.index:
            # 代替的なp値取得方法
            p_value = ci.summary_data.loc['Posterior tail-area probability p:', 'Posterior tail-area probability p:']
            results_data.append(['p値（事後確率）', f"{p_value:.4f}", f"{p_value:.4f}"])
        else:
            # テキストサマリーからp値を抽出
            try:
                import re
                summary_text = str(ci.summary())
                p_match = re.search(r'Posterior tail-area probability p:\s+([0-9.]+)', summary_text)
                if p_match:
                    p_value = float(p_match.group(1))
                    results_data.append(['p値（事後確率）', f"{p_value:.4f}", f"{p_value:.4f}"])
            except:
                pass  # p値が取得できない場合はスキップ
        
        # DataFrameを作成
        df = pd.DataFrame(results_data, columns=['指標', '分析期間の平均値', '分析期間の累積値'])
        
        return df
        
    except Exception as e:
        print(f"Error in build_enhanced_summary_table: {e}")
        # エラーの場合は空のDataFrameを返す
        import pandas as pd
        return pd.DataFrame(columns=['指標', '分析期間の平均値', '分析期間の累積値'])

def extract_summary_from_text(summary_text, confidence_level=95):
    """
    CausalImpactのテキストサマリーからデータを抽出する関数
    
    Parameters:
    -----------
    summary_text : str
        CausalImpactのsummary()メソッドの出力テキスト
    confidence_level : int
        信頼水準（%）、デフォルト95%
        
    Returns:
    --------
    pandas.DataFrame
        抽出されたサマリーデータ
    """
    import pandas as pd
    import re
    
    results_data = []
    lines = summary_text.split('\n')
    
    for line in lines:
        if line.strip():
            # 各行から指標とデータを抽出
            parts = re.split(r'\s{2,}', line.strip())
            if len(parts) >= 3:
                indicator = parts[0]
                avg_value = parts[1]
                cum_value = parts[2]
                
                # 指標名の日本語化（信頼水準を動的に反映）
                if 'Actual' in indicator:
                    indicator = '実測値'
                elif 'Predicted' in indicator:
                    indicator = '予測値（標準偏差）'
                elif 'AbsEffect' in indicator:
                    indicator = '絶対効果（標準偏差）'
                elif 'RelEffect' in indicator:
                    indicator = '相対効果（標準偏差）'
                    # 視認性向上のため、両欄に同じ値を表示
                    cum_value = avg_value
                elif '95% CI' in indicator or 'CI' in indicator:
                    if 'Predicted' in line:
                        indicator = f'予測値 {confidence_level}% 信頼区間'
                    elif 'AbsEffect' in line:
                        indicator = f'絶対効果 {confidence_level}% 信頼区間'
                    elif 'RelEffect' in line:
                        indicator = f'相対効果 {confidence_level}% 信頼区間'
                        # 視認性向上のため、両欄に同じ値を表示
                        cum_value = avg_value
                
                results_data.append([indicator, avg_value, cum_value])
    
    # p値を抽出
    p_match = re.search(r'Posterior tail-area probability p:\s+([0-9.]+)', summary_text)
    if p_match:
        p_value = float(p_match.group(1))
        # 視認性向上のため、両欄に同じ値を表示
        results_data.append(['p値（事後確率）', f"{p_value:.4f}", f"{p_value:.4f}"])
    
    df = pd.DataFrame(results_data, columns=['指標', '分析期間の平均値', '分析期間の累積値'])
    return df

def get_analysis_summary_message(ci, confidence_level=95):
    """
    分析結果から相対効果と統計的有意性を判定してサマリーメッセージを生成する関数
    
    Parameters:
    -----------
    ci : CausalImpact
        分析結果オブジェクト
    confidence_level : int
        信頼水準（%）、デフォルト95%
        
    Returns:
    --------
    str or None
        分析結果のサマリーメッセージ（生成できない場合はNone）
    """
    try:
        import re
        
        # 相対効果と有意性の取得
        relative_effect = None
        p_value = None
        is_significant = False
        
        # 1. CausalImpactのsummary_dataから取得を試行
        if hasattr(ci, 'summary_data') and ci.summary_data is not None:
            if 'rel_effect' in ci.summary_data.index:
                relative_effect = ci.summary_data.loc['rel_effect', 'average'] * 100
            
            # 統計的有意性の判定（信頼区間による）
            if ('abs_effect_lower' in ci.summary_data.index and 
                'abs_effect_upper' in ci.summary_data.index):
                lower_bound = ci.summary_data.loc['abs_effect_lower', 'cumulative']
                upper_bound = ci.summary_data.loc['abs_effect_upper', 'cumulative']
                if (lower_bound > 0 and upper_bound > 0) or (lower_bound < 0 and upper_bound < 0):
                    is_significant = True
        
        # 2. p値の取得
        if hasattr(ci, 'p_value') and ci.p_value is not None:
            p_value = ci.p_value
        else:
            # テキストサマリーからp値を抽出
            summary_text = str(ci.summary())
            p_match = re.search(r'Posterior tail-area probability p:\s+([0-9.]+)', summary_text)
            if p_match:
                p_value = float(p_match.group(1))
        
        # 3. フォールバック：テキストから相対効果も抽出
        if relative_effect is None:
            summary_text = str(ci.summary())
            # 相対効果の行を探す（パーセンテージ形式）
            for line in summary_text.split('\n'):
                if 'RelEffect' in line or '相対効果' in line:
                    # パーセンテージ値を抽出
                    percent_match = re.search(r'([-+]?\d+\.?\d*)%', line)
                    if percent_match:
                        relative_effect = float(percent_match.group(1))
                        break
        
        # さらなるフォールバック：DataFrame型のsummaryからの抽出
        if relative_effect is None and hasattr(ci, 'summary'):
            try:
                summary_df = ci.summary
                if hasattr(summary_df, 'loc') and 'RelEffect' in summary_df.index:
                    rel_effect_val = summary_df.loc['RelEffect', 'Average']
                    if not hasattr(rel_effect_val, '__iter__'):
                        relative_effect = rel_effect_val * 100
            except:
                pass
        
        # 4. メッセージの生成
        if relative_effect is not None and p_value is not None:
            # 統計的有意性の判定（p値による）
            is_significant_by_p = p_value < 0.05
            
            # より確実な有意性判定（信頼区間とp値の両方を考慮）
            final_significance = is_significant or is_significant_by_p
            
            if final_significance:
                return f"相対効果は {relative_effect:+.1f}% で、統計的に有意です（p = {p_value:.3f}）。詳しくは、この下の「詳細レポート」を参照ください。"
            else:
                return f"相対効果は {relative_effect:+.1f}% ですが、統計的には有意ではありません（p = {p_value:.3f}）。詳しくは、この下の「詳細レポート」を参照ください。"
        
        return None
        
    except Exception as e:
        print(f"Error in get_analysis_summary_message: {e}")
        return None

def get_metrics_explanation_table():
    """
    分析結果の各指標の説明をテーブル形式で返す関数
    結果の解釈ガイドの内容も統合して表示
    
    Returns:
    --------
    str
        HTML形式の説明テーブル
    """
    return """
<div style="line-height:1.7;">
<table style="width:100%;border-collapse:collapse;font-size:0.9em;">
<thead>
<tr style="background-color:#f8f9fa;">
<th style="border:1px solid #dee2e6;padding:8px;text-align:left;font-weight:bold;width:25%;">指標名</th>
<th style="border:1px solid #dee2e6;padding:8px;text-align:left;font-weight:bold;width:75%;">意味</th>
</tr>
</thead>
<tbody>
<tr>
<td style="border:1px solid #dee2e6;padding:8px;white-space:nowrap;">実測値</td>
<td style="border:1px solid #dee2e6;padding:8px;">介入期間中に実際に観測された応答変数の値です。対象となる処置群の実際の測定値を表します。</td>
</tr>
<tr>
<td style="border:1px solid #dee2e6;padding:8px;white-space:nowrap;">予測値（標準偏差）</td>
<td style="border:1px solid #dee2e6;padding:8px;">介入が行われなかった場合に予測される応答値です。括弧内の数値は予測の不確実性を示す標準偏差です。</td>
</tr>
<tr>
<td style="border:1px solid #dee2e6;padding:8px;white-space:nowrap;">予測値 XX% 信頼区間</td>
<td style="border:1px solid #dee2e6;padding:8px;">予測値の信頼区間を示します。実際の効果がこの範囲内に収まる確率がXX%であることを意味します。区間は[下限値, 上限値]として表示されます。</td>
</tr>
<tr>
<td style="border:1px solid #dee2e6;padding:8px;white-space:nowrap;">絶対効果（標準偏差）</td>
<td style="border:1px solid #dee2e6;padding:8px;">実測値から予測値を引いた差分で、介入による効果の絶対値を示します。プラスの値は正の効果、マイナスの値は負の効果を意味します。括弧内の数値は標準偏差です。</td>
</tr>
<tr>
<td style="border:1px solid #dee2e6;padding:8px;white-space:nowrap;">絶対効果 XX% 信頼区間</td>
<td style="border:1px solid #dee2e6;padding:8px;">絶対効果の信頼区間です。この範囲に0が含まれていない場合、効果は統計的に有意と判断できます。区間は[下限値, 上限値]として表示されます。</td>
</tr>
<tr>
<td style="border:1px solid #dee2e6;padding:8px;white-space:nowrap;">相対効果（標準偏差）</td>
<td style="border:1px solid #dee2e6;padding:8px;">絶対効果を予測値で割った比率で、効果のパーセンテージを示します。予測値に対して何%の変化があったかを表します。相対効果については、分析期間の平均値の欄に表示しています。</td>
</tr>
<tr>
<td style="border:1px solid #dee2e6;padding:8px;white-space:nowrap;">相対効果 XX% 信頼区間</td>
<td style="border:1px solid #dee2e6;padding:8px;">相対効果の信頼区間です。この範囲に0%が含まれていない場合、相対効果は統計的に有意と判断できます。相対効果の信頼区間についても、分析期間の平均値の欄に表示しています。</td>
</tr>
<tr>
<td style="border:1px solid #dee2e6;padding:8px;white-space:nowrap;">p値（事後確率）</td>
<td style="border:1px solid #dee2e6;padding:8px;">観測された効果（または、より極端な効果）が単なる偶然で生じる確率です。一般的に0.05未満の場合、効果は統計的に有意と判断されます。数値が小さいほど、効果が偶然ではなく介入によるものである可能性が高いことを示します。p値については、分析期間の平均値の欄に表示しています。</td>
</tr>
</tbody>
</table>
</div>

<div style="margin-top:1.5em;padding:12px;background-color:#f8f9fa;border-radius:4px;font-size:0.9em;">
<h4 style="margin:0 0 8px 0;color:#333;">結果の解釈ガイド</h4>
<p style="margin-bottom:8px;"><strong>分析手法の特徴：</strong>介入前のトレンドと季節性から「介入がなかった場合」の予測値を推定し、実測値と比較。対照群がある場合は外部要因の影響を適切に除去し、より信頼性の高い因果効果を推定します。</p>
<p style="margin-bottom:8px;"><strong>有意性の判断：</strong>信頼区間が0を含まない場合に統計的に有意。p値が0.05未満（一般的基準）の場合も有意と判断されます。実用的な効果サイズと統計的有意性の両方を併せて判断することが重要です。</p>
<p style="margin:0;"><strong>注意事項：</strong>単群推定（対照群なし）の場合、外部要因の影響も効果として計測される可能性があるため、結果の解釈には注意が必要です。二群比較の場合は、対照群により外部要因の影響を除去できるため、より信頼性が高くなります。</p>
</div>

<div style="margin-top:1em;font-size:0.9em;color:#666;">
<p><strong>分析期間の平均値：</strong> 介入期間中の1件あたりの平均値を示します。</p>
<p><strong>分析期間の累積値：</strong> 介入期間全体での合計値を示します。</p>
<p style="margin-top:1em;">※相対効果、相対効果の信頼区間、およびp値については、分析期間の平均値の欄に集約して表示しています。</p>
</div>
""" 