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
                "approximate" in text_content or
                "first" in text_content.lower() or
                "removed due to" in text_content.lower()):
                text.remove()  # テキストを完全に削除
    
    # フィギュアレベルでのテキスト削除も試行
    if hasattr(fig, 'texts'):
        fig_texts = fig.texts[:]  # フィギュアのテキストリストのコピーを作成
        for text in fig_texts:
            text_content = text.get_text()
            if ("Note:" in text_content or
                "observations were removed" in text_content or
                "diffuse initialization" in text_content or
                "approximate" in text_content or
                "first" in text_content.lower() or
                "removed due to" in text_content.lower()):
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
    # 日付をYYYY/MM/DD形式に変換
    try:
        output_df['日付'] = pd.to_datetime(output_df['日付']).dt.strftime('%Y/%m/%d')
    except Exception as e:
        # 日付変換に失敗した場合は文字列として出力
        output_df['日付'] = output_df['日付'].astype(str)

    # 1行目: 日本語名, 2行目: 英字名, 3行目以降: データ
    import io, base64
    csv_buffer = io.StringIO()
    # ヘッダー2行
    csv_buffer.write(','.join(jp_names) + '\n')
    csv_buffer.write(','.join(en_names) + '\n')
    # データ
    output_df.to_csv(csv_buffer, index=False, header=False, encoding='utf-8-sig')
    # 注釈を末尾に追加
    csv_buffer.write('\n※I～O列の累積値は、介入期間のみ出力しています（介入期間外はゼロまたは空欄）。\n')
    csv_string = csv_buffer.getvalue()
    csv_base64 = base64.b64encode(csv_string.encode('utf-8-sig')).decode()
    filename = f"causal_impact_detail_{treatment_name}_{post_start.strftime('%Y%m%d')}_{post_end.strftime('%Y%m%d')}.csv"
    href = f'data:text/csv;charset=utf-8-sig;base64,{csv_base64}'
    return href, filename

def build_unified_summary_table(ci, confidence_level=95):
    """
    CausalImpactのsummary()出力を直接使用して統一した分析結果テーブルを生成する関数
    詳細レポート、分析結果概要、CSV出力で同じ数値を使用して一貫性を保つ
    
    Parameters:
    -----------
    ci : CausalImpact
        分析結果オブジェクト
    confidence_level : int
        信頼水準（%）、デフォルト95%
        
    Returns:
    --------
    pandas.DataFrame
        整形された分析結果テーブル（詳細レポートと同じ数値）
    """
    try:
        import pandas as pd
        import numpy as np
        import re
        
        # CausalImpactのsummary()を取得
        summary_text = str(ci.summary())
        lines = [l for l in summary_text.split('\n') if l.strip()]
        
        results_data = []
        
        # p値を抽出
        p_value = None
        for line in lines:
            if 'Posterior tail-area probability p:' in line:
                p_match = re.search(r'p:\s+([0-9.]+)', line)
                if p_match:
                    p_value = float(p_match.group(1))
                    break
        
        # サマリーデータを解析（詳細レポートと同じ方法）
        for line in lines[1:]:  # ヘッダー行をスキップ
            parts = re.split(r'\s{2,}', line.strip())
            if len(parts) == 3:
                item_name = parts[0]
                avg_value = parts[1]
                cum_value = parts[2]
                
                # 項目名を日本語化（より厳密なパターンマッチング）
                jp_name = item_name  # デフォルトは元の名前
                
                if 'Actual' in item_name or 'actual' in item_name.lower():
                    jp_name = '実測値'
                elif 'Predicted' in item_name or 'predicted' in item_name.lower():
                    # 信頼区間行かどうかをチェック
                    if '95% CI' in line or 'CI' in item_name:
                        jp_name = f'予測値 {confidence_level}% 信頼区間'
                    else:
                        jp_name = '予測値 (標準偏差)'
                elif 'AbsEffect' in item_name or 'abs' in item_name.lower():
                    # 信頼区間行かどうかをチェック  
                    if '95% CI' in line or 'CI' in item_name:
                        jp_name = f'絶対効果 {confidence_level}% 信頼区間'
                    else:
                        jp_name = '絶対効果 (標準偏差)'
                elif 'RelEffect' in item_name or 'rel' in item_name.lower():
                    # 信頼区間行かどうかをチェック
                    if '95% CI' in line or 'CI' in item_name:
                        jp_name = f'相対効果 {confidence_level}% 信頼区間'
                    else:
                        jp_name = '相対効果 (標準偏差)'
                
                # 相対効果の場合は%表記に変換し、平均値・累積値を同じにする
                if 'RelEffect' in item_name or 'rel' in item_name.lower():
                    try:
                        # パーセンテージ変換
                        if '[' in avg_value and ']' in avg_value:
                            # 信頼区間の場合
                            if not '%' in avg_value:
                                # %が含まれていない場合は変換
                                matches = re.findall(r'[-+]?[0-9]*\.?[0-9]+', avg_value)
                                if len(matches) >= 2:
                                    lower = float(matches[0]) * 100
                                    upper = float(matches[1]) * 100
                                    avg_value = f"[{lower:.1f}%, {upper:.1f}%]"
                        else:
                            # 単一値の場合
                            try:
                                if not '%' in avg_value:
                                    rel_val = float(avg_value) * 100
                                    avg_value = f"{rel_val:.1f}%"
                            except:
                                if not '%' in avg_value:
                                    avg_value += '%'
                        
                        # 累積値は平均値と同じにする（相対効果の場合）
                        cum_value = avg_value
                    except:
                        pass
                
                results_data.append([jp_name, avg_value, cum_value])
        
        # p値を追加
        if p_value is not None:
            results_data.append(['p値（事後確率）', f"{p_value:.4f}", f"{p_value:.4f}"])
        
        # DataFrameを作成
        df_result = pd.DataFrame(results_data, columns=['指標', '分析期間の平均値', '分析期間の累積値'])
        
        return df_result
        
    except Exception as e:
        print(f"Error in build_unified_summary_table: {e}")
        # エラーの場合は元の関数にフォールバック
        return build_enhanced_summary_table(ci, confidence_level)

def build_enhanced_summary_table(ci, confidence_level=95):
    """
    CausalImpactの分析結果を見やすい表形式で整理する関数
    統一関数を優先使用し、確実に日本語表記で表示
    
    Parameters:
    -----------
    ci : CausalImpact
        分析結果オブジェクト
    confidence_level : int
        信頼水準（%）、デフォルト95%
        
    Returns:
    --------
    pandas.DataFrame
        整形された分析結果テーブル（日本語表記）
    """
    try:
        # 統一関数を使用（日本語表記保証）
        unified_result = build_unified_summary_table(ci, confidence_level)
        if unified_result is not None and not unified_result.empty:
            return unified_result
    except Exception as e:
        print(f"Unified function error: {e}")
    
    # 統一関数が失敗した場合でも日本語表記を保証する独自実装
    try:
        import pandas as pd
        import numpy as np
        
        # CSVと同じデータソースを使用：ci.inferencesから直接計算
        if hasattr(ci, 'inferences') and ci.inferences is not None:
            df = ci.inferences.copy().reset_index()
        elif hasattr(ci, 'data'):
            df = ci.data.copy().reset_index()
        else:
            # 最後の手段として空のDataFrameを返す（英語表記を避ける）
            return pd.DataFrame(columns=['指標', '分析期間の平均値', '分析期間の累積値'])
        
        # 日付列を統一
        if 'index' in df.columns:
            df = df.rename(columns={'index': 'date'})
        elif df.index.name:
            df = df.reset_index().rename(columns={df.index.name: 'date'})
        
        # 日付列が存在しない場合の対処
        if 'date' not in df.columns:
            if len(df.columns) > 0:
                df = df.rename(columns={df.columns[0]: 'date'})
            else:
                return pd.DataFrame(columns=['指標', '分析期間の平均値', '分析期間の累積値'])
        
        # 列名マッピング（CSVと同じ）
        column_mapping = {
            'predicted': 'preds',
            'predicted_lower': 'preds_lower', 
            'predicted_upper': 'preds_upper',
            'point_effects': 'point_effects',
            'point_effects_lower': 'point_effects_lower',
            'point_effects_upper': 'point_effects_upper'
        }
        
        # 列名を統一
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # 実測値（y）の算出（予測値＋効果）
        if 'y' not in df.columns:
            if 'preds' in df.columns and 'point_effects' in df.columns:
                df['y'] = df['preds'] + df['point_effects']
            else:
                # データが不足している場合は空のDataFrameを返す
                return pd.DataFrame(columns=['指標', '分析期間の平均値', '分析期間の累積値'])
        
        # 介入期間のデータのみを抽出（累積値用）
        analysis_period = None
        try:
            import streamlit as st
            if hasattr(st, 'session_state') and 'analysis_period' in st.session_state:
                analysis_period = st.session_state['analysis_period']
        except:
            pass
        
        if analysis_period and 'post_start' in analysis_period and 'post_end' in analysis_period:
            post_start = pd.to_datetime(analysis_period['post_start'])
            post_end = pd.to_datetime(analysis_period['post_end'])
            mask_post = (pd.to_datetime(df['date']) >= post_start) & (pd.to_datetime(df['date']) <= post_end)
            post_data = df[mask_post].copy()
        else:
            # 期間情報が取得できない場合は全データを使用
            post_data = df.copy()
        
        if len(post_data) == 0:
            return pd.DataFrame(columns=['指標', '分析期間の平均値', '分析期間の累積値'])
        
        # 各指標の平均値と累積値を計算（日本語表記で統一）
        results_data = []
        
        # 実測値
        if 'y' in post_data.columns:
            actual_avg = post_data['y'].mean()
            actual_cum = post_data['y'].sum()
            results_data.append(['実測値', f"{actual_avg:.1f}", f"{actual_cum:,.1f}"])
        
        # 予測値（標準偏差）
        if 'preds' in post_data.columns:
            pred_avg = post_data['preds'].mean()
            pred_cumsum = post_data['preds'].cumsum()
            pred_cum = pred_cumsum.iloc[-1] if len(pred_cumsum) > 0 else 0
            
            # 標準偏差の計算
            pred_std = post_data['preds'].std()
            results_data.append(['予測値（標準偏差）', f"{pred_avg:.1f} ({pred_std:.1f})", f"{pred_cum:,.1f} ({pred_std:.1f})"])
        
        # 予測値信頼区間（動的%表示）
        if 'preds_lower' in post_data.columns and 'preds_upper' in post_data.columns:
            pred_lower_avg = post_data['preds_lower'].mean()
            pred_upper_avg = post_data['preds_upper'].mean()
            pred_lower_cumsum = post_data['preds_lower'].cumsum()
            pred_upper_cumsum = post_data['preds_upper'].cumsum()
            pred_lower_cum = pred_lower_cumsum.iloc[-1] if len(pred_lower_cumsum) > 0 else 0
            pred_upper_cum = pred_upper_cumsum.iloc[-1] if len(pred_upper_cumsum) > 0 else 0
            
            avg_ci_str = f"[{pred_lower_avg:.1f}, {pred_upper_avg:.1f}]"
            cum_ci_str = f"[{pred_lower_cum:,.1f}, {pred_upper_cum:,.1f}]"
            results_data.append([f'予測値 {confidence_level}% 信頼区間', avg_ci_str, cum_ci_str])
        
        # 絶対効果（標準偏差）
        if 'point_effects' in post_data.columns:
            abs_avg = post_data['point_effects'].mean()
            abs_cumsum = post_data['point_effects'].cumsum()
            abs_cum = abs_cumsum.iloc[-1] if len(abs_cumsum) > 0 else 0
            
            # 標準偏差の計算
            abs_std = post_data['point_effects'].std()
            results_data.append(['絶対効果（標準偏差）', f"{abs_avg:.1f} ({abs_std:.1f})", f"{abs_cum:,.1f} ({abs_std:.1f})"])
        
        # 絶対効果信頼区間（動的%表示）
        if 'point_effects_lower' in post_data.columns and 'point_effects_upper' in post_data.columns:
            abs_lower_avg = post_data['point_effects_lower'].mean()
            abs_upper_avg = post_data['point_effects_upper'].mean()
            abs_lower_cumsum = post_data['point_effects_lower'].cumsum()
            abs_upper_cumsum = post_data['point_effects_upper'].cumsum()
            abs_lower_cum = abs_lower_cumsum.iloc[-1] if len(abs_lower_cumsum) > 0 else 0
            abs_upper_cum = abs_upper_cumsum.iloc[-1] if len(abs_upper_cumsum) > 0 else 0
            
            avg_ci_str = f"[{abs_lower_avg:.1f}, {abs_upper_avg:.1f}]"
            cum_ci_str = f"[{abs_lower_cum:,.1f}, {abs_upper_cum:,.1f}]"
            results_data.append([f'絶対効果 {confidence_level}% 信頼区間', avg_ci_str, cum_ci_str])
        
        # 相対効果（標準偏差）
        if 'point_effects' in post_data.columns and 'preds' in post_data.columns:
            total_abs_effect = post_data['point_effects'].sum()
            total_pred = post_data['preds'].sum()
            rel_unified = (total_abs_effect / total_pred * 100) if total_pred != 0 else 0
            
            # 標準偏差の計算（相対効果の）
            rel_effects_pct = (post_data['point_effects'] / post_data['preds'] * 100).replace([np.inf, -np.inf], np.nan).dropna()
            rel_std = rel_effects_pct.std() if len(rel_effects_pct) > 0 else 0
            
            results_data.append(['相対効果（標準偏差）', f"{rel_unified:.1f}% ({rel_std:.1f}%)", f"{rel_unified:.1f}% ({rel_std:.1f}%)"])
        
        # 相対効果信頼区間（動的%表示）
        if ('point_effects_lower' in post_data.columns and 'point_effects_upper' in post_data.columns and 
            'preds' in post_data.columns):
            total_abs_lower = post_data['point_effects_lower'].sum()
            total_abs_upper = post_data['point_effects_upper'].sum()
            total_pred = post_data['preds'].sum()
            rel_lower_unified = (total_abs_lower / total_pred * 100) if total_pred != 0 else 0
            rel_upper_unified = (total_abs_upper / total_pred * 100) if total_pred != 0 else 0
            
            rel_ci_unified_str = f"[{rel_lower_unified:.1f}%, {rel_upper_unified:.1f}%]"
            results_data.append([f'相対効果 {confidence_level}% 信頼区間', rel_ci_unified_str, rel_ci_unified_str])
        
        # p値（事後確率）
        if hasattr(ci, 'p_value') and ci.p_value is not None:
            p_value = ci.p_value
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
        
        # DataFrameを作成（日本語表記で統一）
        df_result = pd.DataFrame(results_data, columns=['指標', '分析期間の平均値', '分析期間の累積値'])
        
        return df_result
        
    except Exception as e:
        print(f"Error in build_enhanced_summary_table: {e}")
        # 最終的なエラーの場合でも日本語表記の空テーブルを返す
        return pd.DataFrame(columns=['指標', '分析期間の平均値', '分析期間の累積値'])

def build_enhanced_summary_table_fallback(ci, confidence_level=95):
    """
    CausalImpactの分析結果を見やすい表形式で整理する関数
    CSVダウンロードと同じデータソース（ci.inferences）を使用して一貫性を保つ
    
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
        import numpy as np
        
        # CSVと同じデータソースを使用：ci.inferencesから直接計算
        if hasattr(ci, 'inferences') and ci.inferences is not None:
            df = ci.inferences.copy().reset_index()
        elif hasattr(ci, 'data'):
            df = ci.data.copy().reset_index()
        else:
            # フォールバック：既存の方法
            return build_enhanced_summary_table_fallback(ci, confidence_level)
        
        # 日付列を統一
        if 'index' in df.columns:
            df = df.rename(columns={'index': 'date'})
        elif df.index.name:
            df = df.reset_index().rename(columns={df.index.name: 'date'})
        
        # 日付列が存在しない場合の対処
        if 'date' not in df.columns:
            if len(df.columns) > 0:
                df = df.rename(columns={df.columns[0]: 'date'})
            else:
                return pd.DataFrame(columns=['指標', '分析期間の平均値', '分析期間の累積値'])
        
        # 列名マッピング（CSVと同じ）
        column_mapping = {
            'predicted': 'preds',
            'predicted_lower': 'preds_lower', 
            'predicted_upper': 'preds_upper',
            'point_effects': 'point_effects',
            'point_effects_lower': 'point_effects_lower',
            'point_effects_upper': 'point_effects_upper'
        }
        
        # 列名を統一
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # 実測値（y）の算出（予測値＋効果）
        if 'y' not in df.columns:
            if 'preds' in df.columns and 'point_effects' in df.columns:
                df['y'] = df['preds'] + df['point_effects']
            else:
                # データが不足している場合はフォールバック
                return build_enhanced_summary_table_fallback(ci, confidence_level)
        
        # 介入期間のデータのみを抽出（累積値用）
        # セッション状態から期間情報を取得
        analysis_period = None
        try:
            import streamlit as st
            if hasattr(st, 'session_state') and 'analysis_period' in st.session_state:
                analysis_period = st.session_state['analysis_period']
        except:
            pass
        
        if analysis_period and 'post_start' in analysis_period and 'post_end' in analysis_period:
            post_start = pd.to_datetime(analysis_period['post_start'])
            post_end = pd.to_datetime(analysis_period['post_end'])
            mask_post = (pd.to_datetime(df['date']) >= post_start) & (pd.to_datetime(df['date']) <= post_end)
            post_data = df[mask_post].copy()
        else:
            # 期間情報が取得できない場合は全データを使用
            post_data = df.copy()
        
        if len(post_data) == 0:
            return build_enhanced_summary_table_fallback(ci, confidence_level)
        
        # 各指標の平均値と累積値を計算
        results_data = []
        
        # 実測値
        if 'y' in post_data.columns:
            actual_avg = post_data['y'].mean()
            actual_cum = post_data['y'].sum()  # 実測値は期間合計
            results_data.append(['実測値', f"{actual_avg:.1f}", f"{actual_cum:,.1f}"])
        
        # 予測値（標準偏差を削除）
        if 'preds' in post_data.columns:
            pred_avg = post_data['preds'].mean()
            # CSVと同じ累積計算：各日の累積値の最終値
            pred_cumsum = post_data['preds'].cumsum()
            pred_cum = pred_cumsum.iloc[-1] if len(pred_cumsum) > 0 else 0
            
            results_data.append(['予測値', f"{pred_avg:.1f}", f"{pred_cum:,.1f}"])
        
        # 予測値信頼区間
        if 'preds_lower' in post_data.columns and 'preds_upper' in post_data.columns:
            pred_lower_avg = post_data['preds_lower'].mean()
            pred_upper_avg = post_data['preds_upper'].mean()
            # CSVと同じ累積計算
            pred_lower_cumsum = post_data['preds_lower'].cumsum()
            pred_upper_cumsum = post_data['preds_upper'].cumsum()
            pred_lower_cum = pred_lower_cumsum.iloc[-1] if len(pred_lower_cumsum) > 0 else 0
            pred_upper_cum = pred_upper_cumsum.iloc[-1] if len(pred_upper_cumsum) > 0 else 0
            
            avg_ci_str = f"[{pred_lower_avg:.1f}, {pred_upper_avg:.1f}]"
            cum_ci_str = f"[{pred_lower_cum:,.1f}, {pred_upper_cum:,.1f}]"
            results_data.append([f'予測値 {confidence_level}% 信頼区間', avg_ci_str, cum_ci_str])
        
        # 絶対効果（標準偏差を削除）
        if 'point_effects' in post_data.columns:
            abs_avg = post_data['point_effects'].mean()
            # CSVと同じ累積計算
            abs_cumsum = post_data['point_effects'].cumsum()
            abs_cum = abs_cumsum.iloc[-1] if len(abs_cumsum) > 0 else 0
            
            results_data.append(['絶対効果', f"{abs_avg:.1f}", f"{abs_cum:,.1f}"])
        
        # 絶対効果信頼区間
        if 'point_effects_lower' in post_data.columns and 'point_effects_upper' in post_data.columns:
            abs_lower_avg = post_data['point_effects_lower'].mean()
            abs_upper_avg = post_data['point_effects_upper'].mean()
            # CSVと同じ累積計算
            abs_lower_cumsum = post_data['point_effects_lower'].cumsum()
            abs_upper_cumsum = post_data['point_effects_upper'].cumsum()
            abs_lower_cum = abs_lower_cumsum.iloc[-1] if len(abs_lower_cumsum) > 0 else 0
            abs_upper_cum = abs_upper_cumsum.iloc[-1] if len(abs_upper_cumsum) > 0 else 0
            
            avg_ci_str = f"[{abs_lower_avg:.1f}, {abs_upper_avg:.1f}]"
            cum_ci_str = f"[{abs_lower_cum:,.1f}, {abs_upper_cum:,.1f}]"
            results_data.append([f'絶対効果 {confidence_level}% 信頼区間', avg_ci_str, cum_ci_str])
        
        # 相対効果（標準偏差を削除、明示的数値表示）
        if 'point_effects' in post_data.columns and 'preds' in post_data.columns:
            # 相対効果を統一した計算方法で算出：累積値ベース（総効果/総予測値）
            total_abs_effect = post_data['point_effects'].sum()
            total_pred = post_data['preds'].sum()
            rel_unified = (total_abs_effect / total_pred * 100) if total_pred != 0 else 0
            
            # 平均値・累積値ともに同じ値を使用
            results_data.append(['相対効果', f"{rel_unified:.1f}%", f"{rel_unified:.1f}%"])
        
        # 相対効果信頼区間（明示的数値表示）
        if ('point_effects_lower' in post_data.columns and 'point_effects_upper' in post_data.columns and 
            'preds' in post_data.columns):
            # 累積値ベースで統一した計算
            total_abs_lower = post_data['point_effects_lower'].sum()
            total_abs_upper = post_data['point_effects_upper'].sum()
            total_pred = post_data['preds'].sum()
            rel_lower_unified = (total_abs_lower / total_pred * 100) if total_pred != 0 else 0
            rel_upper_unified = (total_abs_upper / total_pred * 100) if total_pred != 0 else 0
            
            # 平均値・累積値ともに同じ値を使用
            rel_ci_unified_str = f"[{rel_lower_unified:.1f}%, {rel_upper_unified:.1f}%]"
            results_data.append([f'相対効果 {confidence_level}% 信頼区間', rel_ci_unified_str, rel_ci_unified_str])
        
        # p値（事後確率）（明示的数値表示）
        if hasattr(ci, 'p_value') and ci.p_value is not None:
            p_value = ci.p_value
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
        df_result = pd.DataFrame(results_data, columns=['指標', '分析期間の平均値', '分析期間の累積値'])
        
        return df_result
        
    except Exception as e:
        print(f"Error in build_enhanced_summary_table_fallback: {e}")
        # エラーの場合は空のDataFrameを返す
        return pd.DataFrame(columns=['指標', '分析期間の平均値', '分析期間の累積値'])

def get_analysis_summary_message(ci, confidence_level=95):
    """
    分析結果から相対効果と統計的有意性を判定してサマリーメッセージを生成する関数
    build_enhanced_summary_tableと同じデータソースと計算方法を使用して一貫性を保つ
    
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
        import pandas as pd
        import numpy as np
        import re
        
        # build_enhanced_summary_tableと同じデータソースを使用
        if hasattr(ci, 'inferences') and ci.inferences is not None:
            df = ci.inferences.copy().reset_index()
        elif hasattr(ci, 'data'):
            df = ci.data.copy().reset_index()
        else:
            # フォールバック：既存の方法
            return get_analysis_summary_message_fallback(ci, confidence_level)
        
        # 日付列を統一
        if 'index' in df.columns:
            df = df.rename(columns={'index': 'date'})
        elif df.index.name:
            df = df.reset_index().rename(columns={df.index.name: 'date'})
        
        if 'date' not in df.columns:
            if len(df.columns) > 0:
                df = df.rename(columns={df.columns[0]: 'date'})
            else:
                return get_analysis_summary_message_fallback(ci, confidence_level)
        
        # 列名マッピング（build_enhanced_summary_tableと同じ）
        column_mapping = {
            'predicted': 'preds',
            'predicted_lower': 'preds_lower', 
            'predicted_upper': 'preds_upper',
            'point_effects': 'point_effects',
            'point_effects_lower': 'point_effects_lower',
            'point_effects_upper': 'point_effects_upper'
        }
        
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # 実測値（y）の算出
        if 'y' not in df.columns:
            if 'preds' in df.columns and 'point_effects' in df.columns:
                df['y'] = df['preds'] + df['point_effects']
            else:
                return get_analysis_summary_message_fallback(ci, confidence_level)
        
        # 介入期間のデータのみを抽出
        analysis_period = None
        try:
            import streamlit as st
            if hasattr(st, 'session_state') and 'analysis_period' in st.session_state:
                analysis_period = st.session_state['analysis_period']
        except:
            pass
        
        if analysis_period and 'post_start' in analysis_period and 'post_end' in analysis_period:
            post_start = pd.to_datetime(analysis_period['post_start'])
            post_end = pd.to_datetime(analysis_period['post_end'])
            mask_post = (pd.to_datetime(df['date']) >= post_start) & (pd.to_datetime(df['date']) <= post_end)
            post_data = df[mask_post].copy()
        else:
            post_data = df.copy()
        
        if len(post_data) == 0:
            return get_analysis_summary_message_fallback(ci, confidence_level)
        
        # build_enhanced_summary_tableと同じ方法で相対効果を計算（累積値を使用）
        relative_effect = None
        p_value = None
        
        if 'point_effects' in post_data.columns and 'preds' in post_data.columns:
            # 統一した累積値ベースの計算（アプリ表示と完全に同じ方法）
            total_abs_effect = post_data['point_effects'].sum()
            total_pred = post_data['preds'].sum()
            relative_effect = (total_abs_effect / total_pred * 100) if total_pred != 0 else 0
        
        # p値の取得
        if hasattr(ci, 'p_value') and ci.p_value is not None:
            p_value = ci.p_value
        else:
            # テキストサマリーからp値を抽出
            try:
                summary_text = str(ci.summary())
                p_match = re.search(r'Posterior tail-area probability p:\s+([0-9.]+)', summary_text)
                if p_match:
                    p_value = float(p_match.group(1))
            except:
                pass
        
        # 統計的有意性の判定（信頼区間による）
        is_significant = False
        if ('point_effects_lower' in post_data.columns and 'point_effects_upper' in post_data.columns):
            # 累積効果の信頼区間で判定
            abs_lower_cumsum = post_data['point_effects_lower'].cumsum()
            abs_upper_cumsum = post_data['point_effects_upper'].cumsum()
            lower_bound = abs_lower_cumsum.iloc[-1] if len(abs_lower_cumsum) > 0 else 0
            upper_bound = abs_upper_cumsum.iloc[-1] if len(abs_upper_cumsum) > 0 else 0
            if (lower_bound > 0 and upper_bound > 0) or (lower_bound < 0 and upper_bound < 0):
                is_significant = True
        
        # メッセージの生成
        if relative_effect is not None and p_value is not None:
            # 統計的有意性の判定（p値による）
            is_significant_by_p = p_value < 0.05
            
            # より確実な有意性判定（信頼区間とp値の両方を考慮）
            final_significance = is_significant or is_significant_by_p
            
            if final_significance:
                return f"相対効果は {relative_effect:+.1f}% で、統計的に有意です（p = {p_value:.3f}）。詳しくは、この下の「詳細レポート」を参照ください。"
            else:
                return f"相対効果は {relative_effect:+.1f}% ですが、統計的には有意ではありません（p = {p_value:.3f}）。詳しくは、この下の「詳細レポート」を参照ください。"
        
        return get_analysis_summary_message_fallback(ci, confidence_level)
        
    except Exception as e:
        print(f"Error in get_analysis_summary_message: {e}")
        return get_analysis_summary_message_fallback(ci, confidence_level)

def get_analysis_summary_message_fallback(ci, confidence_level=95):
    """
    フォールバック用の分析結果サマリーメッセージ生成関数
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
        print(f"Error in get_analysis_summary_message_fallback: {e}")
        return None

def get_metrics_explanation_table():
    """
    分析結果の各指標の説明をテーブル形式で返す関数（簡潔版）
    
    Returns:
    --------
    str
        HTML形式の説明テーブル
    """
    return """
<div style="line-height:1.6;">
<table style="width:100%;border-collapse:collapse;font-size:0.9em;">
<thead>
<tr style="background-color:#f8f9fa;">
<th style="border:1px solid #dee2e6;padding:6px;text-align:left;font-weight:bold;width:30%;">指標名</th>
<th style="border:1px solid #dee2e6;padding:6px;text-align:left;font-weight:bold;width:70%;">意味</th>
</tr>
</thead>
<tbody>
<tr>
<td style="border:1px solid #dee2e6;padding:6px;">実測値</td>
<td style="border:1px solid #dee2e6;padding:6px;">介入期間中に実際に観測された値です。</td>
</tr>
<tr>
<td style="border:1px solid #dee2e6;padding:6px;">予測値 (標準偏差)</td>
<td style="border:1px solid #dee2e6;padding:6px;">介入がなかった場合の予測値を表しています。カッコ内の値は標準偏差です。</td>
</tr>
<tr>
<td style="border:1px solid #dee2e6;padding:6px;">絶対効果 (標準偏差)</td>
<td style="border:1px solid #dee2e6;padding:6px;">実測値から予測値を差し引いた値で、介入による変化量を表しています。カッコ内の値は標準偏差です。</td>
</tr>
<tr>
<td style="border:1px solid #dee2e6;padding:6px;">相対効果 (標準偏差)</td>
<td style="border:1px solid #dee2e6;padding:6px;">絶対効果を予測値で割った値で、変化率をパーセンテージで表しています。カッコ内の値は標準偏差です。</td>
</tr>
<tr>
<td style="border:1px solid #dee2e6;padding:6px;">信頼区間</td>
<td style="border:1px solid #dee2e6;padding:6px;">効果の推定範囲を示しています。0を含まない場合は統計的に有意な効果があると判断されます。</td>
</tr>
<tr>
<td style="border:1px solid #dee2e6;padding:6px;">p値</td>
<td style="border:1px solid #dee2e6;padding:6px;">効果が偶然による確率を表しています。0.05未満の場合は統計的に有意な効果があると判断されます。</td>
</tr>
</tbody>
</table>
</div>

<div style="margin-top:1em;font-size:0.85em;color:#666;">
<p><strong>平均値：</strong>介入期間中の1件あたりの平均値を表しています　<strong>累積値：</strong>介入期間全体での合計値を表しています</p>
</div>
"""

def get_comprehensive_pdf_download_link(ci, analysis_info, summary_df, fig, confidence_level=95):
    """
    分析結果の包括的PDFレポートを生成してダウンロードリンクを返す関数
    統一関数による数値でサマリーテーブルを更新し、詳細レポートとの一貫性を保つ
    
    Parameters:
    -----------
    ci : CausalImpact
        CausalImpactオブジェクト
    analysis_info : dict
        分析情報辞書
    summary_df : pandas.DataFrame
        分析結果概要テーブル
    fig : matplotlib.figure.Figure
        分析結果グラフ
    confidence_level : int
        信頼水準（95等）
        
    Returns:
    --------
    href, filename : str, str
        ダウンロードリンクのbase64データとファイル名
    """
    try:
        # 統一関数によるサマリーテーブルで更新
        try:
            unified_summary_df = build_unified_summary_table(ci, confidence_level)
            # インデックスをリセットして統一
            unified_summary_df = unified_summary_df.reset_index(drop=True)
            summary_df = unified_summary_df
        except Exception as e:
            print(f"統一サマリーテーブル生成でエラー、元のサマリーを使用: {e}")
            pass
    except:
        pass
    
    import pandas as pd
    import numpy as np
    import io
    import base64
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from datetime import datetime

    # メモリ上でPDFを作成
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    
    # スタイル設定
    styles = getSampleStyleSheet()
    
    # フォント設定（日本語対応のためフォールバック）
    try:
        # Windowsの場合
        font_path = "C:/Windows/Fonts/NotoSansCJK-Regular.ttc"
        pdfmetrics.registerFont(TTFont('NotoSansCJK', font_path))
        font_name = 'NotoSansCJK'
    except:
        try:
            # 代替フォント
            font_path = "C:/Windows/Fonts/msgothic.ttc"
            pdfmetrics.registerFont(TTFont('MSGothic', font_path))
            font_name = 'MSGothic'
        except:
            # フォールバック：英語フォント
            font_name = 'Helvetica'
    
    # カスタムスタイル
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontName=font_name,
        fontSize=16,
        alignment=1,  # 中央揃え
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=12,
        spaceAfter=10
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=10,
        spaceAfter=8
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        spaceAfter=6
    )
    
    # PDF内容を構築
    story = []
    
    # タイトル
    story.append(Paragraph('Causal Impact分析レポート', title_style))
    story.append(Spacer(1, 12))
    
    # 分析条件
    if font_name == 'Helvetica':
        story.append(Paragraph("Analysis Conditions", subtitle_style))
    else:
        story.append(Paragraph("分析条件", subtitle_style))
    
    # analysis_info辞書から必要な情報を取得
    treatment_name = analysis_info.get('treatment_name', '分析対象')
    control_name = analysis_info.get('control_name', '')
    period_start = analysis_info.get('period_start')
    period_end = analysis_info.get('period_end')
    analysis_type = analysis_info.get('analysis_type', '二群比較')
    
    conditions_text = []
    if font_name == 'Helvetica':
        conditions_text.append(f"Analysis Target: {treatment_name}")
        if control_name:
            conditions_text.append(f"vs {control_name}")
        conditions_text.append(f"Analysis Period: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}")
        conditions_text.append(f"Method: {analysis_type}")
        conditions_text.append(f"Confidence Level: {confidence_level}%")
    else:
        conditions_text.append(f"分析対象：{treatment_name}")
        if control_name:
            conditions_text.append(f"（vs {control_name}）")
        conditions_text.append(f"分析期間：{period_start.strftime('%Y年%m月%d日')} ～ {period_end.strftime('%Y年%m月%d日')}")
        conditions_text.append(f"分析手法：{analysis_type}")
        conditions_text.append(f"信頼水準：{confidence_level}%")
    
    for text in conditions_text:
        story.append(Paragraph(text, normal_style))
    story.append(Spacer(1, 12))
    
    # 分析結果概要テーブル
    story.append(Paragraph('分析結果概要', heading_style))
    
    # サマリーテーブルをPDF用に変換
    table_data = []
    for index, row in summary_df.iterrows():
        table_data.append([str(row[col]) for col in summary_df.columns])
    
    # ヘッダーを追加
    headers = [str(col) for col in summary_df.columns]
    table_data.insert(0, headers)
    
    # テーブル作成
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    story.append(Spacer(1, 12))
    
    # 分析レポートまとめメッセージ
    summary_message = get_analysis_summary_message(ci, confidence_level)
    story.append(Paragraph(summary_message, normal_style))
    story.append(Spacer(1, 20))
    
    # グラフを画像として挿入
    story.append(Paragraph('分析結果グラフ', heading_style))
    
    # グラフタイトル
    if analysis_type == "単群推定（処置群のみを使用）":
        graph_title = f"{treatment_name}"
        graph_subtitle = "単群推定分析：介入前トレンドからの予測との比較"
    else:
        graph_title = f"{treatment_name}（vs {control_name}）"
        graph_subtitle = "二群比較分析：対照群との関係性による予測との比較"
    
    story.append(Paragraph(graph_title, normal_style))
    story.append(Paragraph(graph_subtitle, normal_style))
    story.append(Spacer(1, 6))
    
    # MatplotlibのグラフをPDFに変換
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    img_buffer.seek(0)
    
    # 画像をPDFに挿入
    img = Image(img_buffer, width=450, height=300)  # サイズ調整
    story.append(img)
    story.append(Spacer(1, 12))
    
    # グラフの見方
    if analysis_type == "単群推定（処置群のみを使用）":
        graph_explanation = "実測データ（黒線）と介入前トレンドから推定した予測データ（青線）の比較により介入効果を評価。影の部分は予測の不確実性を示す信頼区間。"
    else:
        graph_explanation = "実測データ（黒線）と対照群から推定した予測データ（青線）の比較により純粋な介入効果を評価。影の部分は予測の不確実性を示す信頼区間。対照群により外部要因の影響を除去。"
    
    story.append(Paragraph(f"グラフの見方：{graph_explanation}", normal_style))
    
    # PDFを構築
    doc.build(story)
    pdf_buffer.seek(0)
    
    # Base64エンコード
    pdf_base64 = base64.b64encode(pdf_buffer.read()).decode()
    
    # ファイル名生成
    analysis_type_short = "SingleGroup" if "単群推定" in analysis_type else "TwoGroup"
    filename = f"causal_impact_report_{treatment_name}_{period_start.strftime('%Y%m%d')}_{period_end.strftime('%Y%m%d')}_{analysis_type_short}.pdf"
    
    # ダウンロードリンク生成
    href = f'data:application/pdf;base64,{pdf_base64}'
    
    return href, filename

def get_comprehensive_csv_download_link(ci, analysis_info, confidence_level=95):
    """
    予測値・実測値の詳細データをロングフォーマットCSVとしてダウンロードするリンクを生成する関数
    （二群比較・単群推定の両分析タイプに対応）
    信頼区間の数値不一致を避けるため、ユーザー向けには8列のクリーンなフォーマットで提供
    
    Parameters:
    -----------
    ci : CausalImpact
        CausalImpactオブジェクト
    analysis_info : dict
        分析情報（treatment_name, analysis_type, period_start, period_end等）
    confidence_level : int
        信頼水準（95等）
        
    Returns:
    --------
    href, filename : str, str
        ダウンロードリンクのbase64データとファイル名
    """
    import pandas as pd
    import numpy as np
    import io
    import base64
    
    # CausalImpactの結果データを取得
    if hasattr(ci, 'inferences') and ci.inferences is not None:
        df = ci.inferences.copy().reset_index()
    elif hasattr(ci, 'data'):
        # データがあるがinferencesがない場合の処理
        df = ci.data.copy().reset_index()
    else:
        raise ValueError("CausalImpactオブジェクトから分析結果を取得できません")
    
    # 日付列を統一
    if 'index' in df.columns:
        df = df.rename(columns={'index': 'date'})
    elif df.index.name:
        df = df.reset_index().rename(columns={df.index.name: 'date'})
    
    # 日付列が存在しない場合の対処
    if 'date' not in df.columns:
        # 最初の列を日付列として使用
        if len(df.columns) > 0:
            df = df.rename(columns={df.columns[0]: 'date'})
        else:
            # データフレームが空の場合は空のDataFrameを返す
            raise ValueError("データフレームに列が存在しません")
    
    # 8列の簡潔なフォーマット（信頼区間列を除去）
    jp_names = [
        '日付', '実測値', '予測値', '効果',
        '累積実測値', '累積予測値', '累積効果', '介入期間フラグ'
    ]
    
    en_names = [
        'date', 'y', 'preds', 'point_effects',
        'post_cum_y', 'post_cum_pred', 'post_cum_effects', 'post_period'
    ]
    
    # データフレームの列名マッピング（pycausalimpactの出力に対応）
    column_mapping = {
        'predicted': 'preds',
        'point_effects': 'point_effects'
    }
    
    # 列名を統一
    for old_name, new_name in column_mapping.items():
        if old_name in df.columns:
            df = df.rename(columns={old_name: new_name})
    
    # 期間情報
    period_start = analysis_info.get('period_start')
    period_end = analysis_info.get('period_end')
    
    # 実測値（y）の算出（予測値＋効果）
    if 'y' not in df.columns:
        if 'preds' in df.columns and 'point_effects' in df.columns:
            df['y'] = df['preds'] + df['point_effects']
        else:
            df['y'] = np.nan
    
    # 介入期間フラグを追加
    if period_start and period_end:
        post_start = pd.to_datetime(period_start)
        post_end = pd.to_datetime(period_end)
        mask_post = (pd.to_datetime(df['date']) >= post_start) & (pd.to_datetime(df['date']) <= post_end)
        df['post_period'] = mask_post.astype(int)  # 1が介入期間、0が介入前期間
        
        # 介入期間のデータのみで累積値を計算
        post_data = df[mask_post].copy()
        if len(post_data) > 0:
            # 累積値を正しく計算（各行で累積されていく）
            post_data = post_data.reset_index(drop=True)
            post_data['post_cum_y'] = post_data['y'].cumsum()
            post_data['post_cum_pred'] = post_data['preds'].cumsum() if 'preds' in post_data.columns else np.nan
            post_data['post_cum_effects'] = post_data['point_effects'].cumsum() if 'point_effects' in post_data.columns else np.nan
            
            # 元のデータフレームの該当箇所に累積値をセット
            post_indices = df[mask_post].index
            for i, idx in enumerate(post_indices):
                if i < len(post_data):
                    df.loc[idx, 'post_cum_y'] = post_data.iloc[i]['post_cum_y']
                    df.loc[idx, 'post_cum_pred'] = post_data.iloc[i]['post_cum_pred']
                    df.loc[idx, 'post_cum_effects'] = post_data.iloc[i]['post_cum_effects']
    else:
        df['post_period'] = 0
    
    # 不足している列を追加（NaNで初期化）
    for en_name in en_names:
        if en_name not in df.columns:
            df[en_name] = np.nan
    
    # 出力用データフレームを作成（8列のみ）
    output_df = df[en_names].copy()
    
    # 日付をYYYY/MM/DD形式に変換
    try:
        output_df['date'] = pd.to_datetime(output_df['date']).dt.strftime('%Y/%m/%d')
    except Exception as e:
        # 日付変換に失敗した場合は文字列として出力
        output_df['date'] = output_df['date'].astype(str)
    
    # CSVバッファを作成
    csv_buffer = io.StringIO()
    
    # 1行目：日本語項目名
    csv_buffer.write(','.join(jp_names) + '\n')
    
    # 2行目：英字変数名
    csv_buffer.write(','.join(en_names) + '\n')
    
    # 3行目以降：実データ
    output_df.to_csv(csv_buffer, index=False, header=False)
    
    # 注釈を追加（信頼区間の不一致について説明）
    csv_buffer.write('\n')
    csv_buffer.write('【CSV出力データについて】\n')
    csv_buffer.write('※ 累積値は介入期間のみ出力されます（介入前期間はゼロまたは空欄になります）。\n')
    csv_buffer.write('　 介入期間フラグ：1＝介入期間、0＝介入前期間\n')
    csv_buffer.write('※ 統計的判断に必要な信頼区間の情報は、「詳細レポート」および「サマリー表」でご確認ください。\n')

    # Base64エンコード
    csv_string = csv_buffer.getvalue()
    csv_base64 = base64.b64encode(csv_string.encode('utf-8-sig')).decode()
    
    # ファイル名生成
    treatment_name = analysis_info.get('treatment_name', '分析対象')
    analysis_type = analysis_info.get('analysis_type', '')
    analysis_type_short = "SingleGroup" if "単群推定" in analysis_type else "TwoGroup"
    
    filename = f"causal_impact_detail_{treatment_name}_{period_start.strftime('%Y%m%d')}_{period_end.strftime('%Y%m%d')}_{analysis_type_short}.csv"
    
    # ダウンロードリンク生成
    href = f'data:text/csv;charset=utf-8-sig;base64,{csv_base64}'
    
    return href, filename