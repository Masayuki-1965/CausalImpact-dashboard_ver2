# グラフタイトル・ラベル多言語対応設定
# matplotlib/plotlyグラフの環境依存文字化け対策

import platform
import matplotlib
import matplotlib.pyplot as plt


def get_graph_labels(use_japanese=True):
    """
    グラフ用ラベル・タイトルを取得
    
    Parameters:
    -----------
    use_japanese : bool
        日本語ラベルを使用する場合True
        
    Returns:
    --------
    dict: グラフラベル辞書
    """
    
    if use_japanese:
        return {
            # メインタイトル
            'actual_vs_predicted': '実測値 vs 予測値',
            'point_effects': '時点効果', 
            'cumulative_effects': '累積効果',
            
            # 軸ラベル
            'date_axis': '日付',
            'value_axis': '値',
            'effect_axis': '効果',
            
            # 凡例
            'actual': '実測値',
            'predicted': '予測値',
            'confidence_interval': '信頼区間',
            'intervention_line': '介入時点',
            
            # グラフ説明
            'graph_note_two_group': '実測データ（黒線）と対照群から推定した予測データ（青線）の比較により純粋な介入効果を評価。影の部分は予測の不確実性を示す信頼区間。対照群により外部要因の影響を除去。',
            'graph_note_single_group': '実測データ（黒線）と予測データ（青線）の比較により介入効果を評価。影の部分は予測の不確実性を示す信頼区間。対照群がないため、外部要因の影響に注意が必要。'
        }
    else:
        return {
            # メインタイトル
            'actual_vs_predicted': 'Actual vs Predicted',
            'point_effects': 'Point Effects',
            'cumulative_effects': 'Cumulative Effects',
            
            # 軸ラベル
            'date_axis': 'Date',
            'value_axis': 'Value', 
            'effect_axis': 'Effect',
            
            # 凡例
            'actual': 'Actual',
            'predicted': 'Predicted',
            'confidence_interval': 'Confidence Interval',
            'intervention_line': 'Intervention Point',
            
            # グラフ説明
            'graph_note_two_group': 'Evaluate pure intervention effects by comparing actual data (black line) with predicted data (blue line) estimated from control group. Shaded area shows confidence interval indicating prediction uncertainty. External factors are eliminated by control group.',
            'graph_note_single_group': 'Evaluate intervention effects by comparing actual data (black line) with predicted data (blue line). Shaded area shows confidence interval indicating prediction uncertainty. Attention needed for external factors due to absence of control group.'
        }


def is_japanese_font_available_for_graphs():
    """
    グラフ表示用の日本語フォントが利用可能かどうかを判定
    
    Returns:
    --------
    bool: 日本語フォントが利用可能な場合True
    """
    system = platform.system()
    
    # Windows・macOSの場合
    if system in ["Windows", "Darwin"]:
        try:
            # japanize-matplotlibが正常に動作するかテスト
            import japanize_matplotlib
            return True
        except ImportError:
            # japanize-matplotlibがない場合はシステムフォントをテスト
            try:
                # フォントマネージャーから日本語フォントを検索
                from matplotlib import font_manager
                fonts = font_manager.findSystemFonts()
                japanese_fonts = [f for f in fonts if any(keyword in f.lower() 
                                 for keyword in ['gothic', 'mincho', 'hiragino', 'yu'])]
                return len(japanese_fonts) > 0
            except:
                return False
    
    # Linux（Streamlit Cloud）の場合は利用不可とみなす
    else:
        return False


def setup_matplotlib_japanese_font():
    """
    matplotlib用の日本語フォント設定を実行
    
    Returns:
    --------
    bool: 日本語フォント設定が成功した場合True
    """
    try:
        # japanize-matplotlib を使用して日本語フォント設定
        import japanize_matplotlib
        print("japanize-matplotlib による日本語フォント設定完了")
        return True
    except ImportError:
        try:
            # 手動での日本語フォント設定（Windows）
            if platform.system() == "Windows":
                matplotlib.rcParams['font.family'] = ['MS Gothic', 'DejaVu Sans']
                print("Windows用日本語フォント設定完了")
                return True
            # 手動での日本語フォント設定（macOS）
            elif platform.system() == "Darwin":
                matplotlib.rcParams['font.family'] = ['Hiragino Sans', 'DejaVu Sans']
                print("macOS用日本語フォント設定完了") 
                return True
            else:
                # Linux環境では英語フォントのみ
                matplotlib.rcParams['font.family'] = ['DejaVu Sans']
                print("英語フォント設定完了（Linux環境）")
                return False
        except Exception as e:
            print(f"フォント設定エラー: {e}")
            return False


def get_graph_config():
    """
    現在の環境に最適なグラフ設定を取得
    
    Returns:
    --------
    tuple: (use_japanese, labels)
        日本語使用可否とラベル辞書
    """
    
    # 日本語フォント利用可能性を判定
    use_japanese = is_japanese_font_available_for_graphs()
    
    # matplotlib日本語フォント設定
    if use_japanese:
        font_setup_success = setup_matplotlib_japanese_font()
        if not font_setup_success:
            use_japanese = False
    
    # ラベル取得
    labels = get_graph_labels(use_japanese)
    
    print(f"グラフ設定: {'日本語' if use_japanese else '英語'}モード")
    
    return use_japanese, labels


def apply_graph_style():
    """
    グラフスタイルを環境に応じて適用
    """
    use_japanese, _ = get_graph_config()
    
    if not use_japanese:
        # 英語環境用のスタイル設定
        plt.style.use('default')
        matplotlib.rcParams.update({
            'font.size': 10,
            'axes.titlesize': 12,
            'axes.labelsize': 10,
            'xtick.labelsize': 9,
            'ytick.labelsize': 9,
            'legend.fontsize': 9,
            'font.family': ['DejaVu Sans', 'sans-serif']
        })
    else:
        # 日本語環境用のスタイル設定（japanize-matplotlib使用）
        matplotlib.rcParams.update({
            'font.size': 10,
            'axes.titlesize': 12,
            'axes.labelsize': 10,
            'xtick.labelsize': 9,
            'ytick.labelsize': 9,
            'legend.fontsize': 9
        }) 