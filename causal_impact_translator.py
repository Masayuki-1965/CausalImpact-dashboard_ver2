import re

class CausalImpactTranslator:
    """
    CausalImpactの分析レポートを日本語に翻訳するクラス
    
    英語の原文パターンを正規表現で検出し、対応する日本語訳に変換します。
    新しいパターンを追加する場合は、translate_report メソッド内のパターンリストに追加してください。
    """
    
    def __init__(self):
        pass
        
    def translate_report(self, report, alpha=0.95):
        """
        CausalImpactレポートを日本語に翻訳する
        
        Parameters:
        -----------
        report : str
            原文の英語レポート文字列
        alpha : float, optional (default=0.95)
            信頼区間の値（0〜1の間）
            
        Returns:
        --------
        str
            翻訳された日本語レポート
        """
        # 信頼区間をパーセント表示に変換（例：0.95 → 95%）
        alpha_percent = int(alpha * 100)
        
        # 翻訳処理開始（元のレポートを複製して変換処理）
        report_jp = report
        
        # 先頭の「Analysis report {CausalImpact}」を置換
        report_jp = report_jp.replace("Analysis report {CausalImpact}", "分析レポート {CausalImpact}")
        
        # パターン1: 最初の段落（介入期間と予測値の比較）
        first_para_match = re.search(r"During the post-intervention period.*?see below\.", report_jp, re.DOTALL)
        if first_para_match:
            # 数値をキャプチャ
            avg_value = re.search(r"average value of approx. ([0-9.]+)", first_para_match.group(0))
            exp_response = re.search(r"expected an average response of ([0-9.]+)", first_para_match.group(0))
            interval_pred = re.search(r"prediction is \[([0-9., -]+)\]", first_para_match.group(0))
            effect = re.search(r"This effect is ([0-9.+\-]+) with", first_para_match.group(0))
            effect_interval = re.search(r"95% interval of\s+\[([0-9., -]+)\]", first_para_match.group(0))
            
            if avg_value and exp_response and interval_pred and effect and effect_interval:
                # 数値を保持して日本語化 - 信頼区間を動的に反映
                first_para_jp = f"""介入期間中、応答変数は平均値が約{avg_value.group(1)}でした。もし介入がなかった場合、予測される平均応答値は{exp_response.group(1)}でした。この反事実予測の{alpha_percent}%信頼区間は[{interval_pred.group(1)}]です。この予測値を観測値から引くことで、介入が応答変数に与えた因果効果の推定値が得られます。この効果は{effect.group(1)}であり、{alpha_percent}%信頼区間は[{effect_interval.group(1)}]です。この効果の有意性については以下を参照してください。"""
                
                # 元のテキストを置換
                report_jp = report_jp.replace(first_para_match.group(0), first_para_jp)
        
        # パターン1b: 最初の段落の別パターン（"By contrast"を含む負の効果の場合）
        alt_first_para_match = re.search(r"During the post-intervention period.*?By contrast.*?see below\.", report_jp, re.DOTALL)
        if alt_first_para_match:
            # 数値をキャプチャ
            avg_value = re.search(r"average value of approx. ([0-9.]+)", alt_first_para_match.group(0))
            exp_response = re.search(r"expected an average response of ([0-9.]+)", alt_first_para_match.group(0))
            interval_pred = re.search(r"prediction is \[([0-9., -]+)\]", alt_first_para_match.group(0))
            effect = re.search(r"This effect is (-[0-9.]+) with", alt_first_para_match.group(0))
            effect_interval = re.search(r"95% interval of\s+\[([0-9., -]+)\]", alt_first_para_match.group(0))
            
            if avg_value and exp_response and interval_pred and effect and effect_interval:
                # 数値を保持して日本語化 - 信頼区間を動的に反映
                alt_first_para_jp = f"""介入期間中、応答変数は平均値が約{avg_value.group(1)}でした。対照的に、介入がなかった場合には、予測される平均応答値は{exp_response.group(1)}でした。この反事実予測の{alpha_percent}%信頼区間は[{interval_pred.group(1)}]です。この予測値を観測値から引くことで、介入が応答変数に与えた因果効果の推定値が得られます。この効果は{effect.group(1)}であり、{alpha_percent}%信頼区間は[{effect_interval.group(1)}]です。この効果の有意性については以下を参照してください。"""
                
                # 元のテキストを置換
                report_jp = report_jp.replace(alt_first_para_match.group(0), alt_first_para_jp)
        
        # パターン2: 二番目の "Summing up the individual data points..." 段落
        second_para_match = re.search(r"Summing up the individual data points.*?this prediction is \[[0-9., -]+\].", report_jp, re.DOTALL)
        if second_para_match:
            # 数値をキャプチャ
            overall_value = re.search(r"overall value of ([0-9.]+)", second_para_match.group(0))
            sum_expected = re.search(r"expected\s+a sum of ([0-9.]+)", second_para_match.group(0))
            sum_interval = re.search(r"prediction is \[([0-9., -]+)\]", second_para_match.group(0))
            
            if overall_value and sum_expected and sum_interval:
                # 数値を保持して日本語化 - 信頼区間を動的に反映
                second_para_jp = f"""介入期間中の個々のデータポイントを合計すると（これが意味を持つ場合のみ）、応答変数の全体値は{overall_value.group(1)}でした。介入がなかった場合、予測される合計値は{sum_expected.group(1)}でした。この予測の{alpha_percent}%信頼区間は[{sum_interval.group(1)}]です。"""
                
                # 元のテキストを置換
                report_jp = report_jp.replace(second_para_match.group(0), second_para_jp)
        
        # パターン3: 三番目の "The above results are given in terms of absolute numbers..." 段落（増加の場合）
        third_para_match = re.search(r"The above results are given in terms of absolute numbers.*?this percentage is \[[0-9.%, -]+\].", report_jp, re.DOTALL)
        if third_para_match:
            # 数値をキャプチャ
            increase = re.search(r"increase of \+?([0-9.%]+)", third_para_match.group(0))
            percentage_interval = re.search(r"percentage is \[([0-9.%, -]+)\]", third_para_match.group(0))
            
            if increase and percentage_interval:
                # 数値を保持して日本語化 - 信頼区間を動的に反映
                third_para_jp = f"""上記の結果は絶対値で示されています。相対的には、応答変数は{increase.group(1)}の増加を示しました。この割合の{alpha_percent}%信頼区間は[{percentage_interval.group(1)}]です。"""
                
                # 元のテキストを置換
                report_jp = report_jp.replace(third_para_match.group(0), third_para_jp)
        
        # パターン3b: 三番目の段落の別パターン（"decrease"を含む場合 - 負の効果）
        alt_third_para_match = re.search(r"The above results are given in terms of absolute numbers.*?decrease of -[0-9.]+%.*?this percentage is \[[0-9.%, -]+\].", report_jp, re.DOTALL)
        if alt_third_para_match:
            # 数値をキャプチャ
            decrease = re.search(r"decrease of (-[0-9.]+%)", alt_third_para_match.group(0))
            percentage_interval = re.search(r"percentage is \[([0-9.%, -]+)\]", alt_third_para_match.group(0))
            
            if decrease and percentage_interval:
                # 数値を保持して日本語化 - 信頼区間を動的に反映
                alt_third_para_jp = f"""上記の結果は絶対値で示されています。相対的には、応答変数は{decrease.group(1)}の減少を示しました。この割合の{alpha_percent}%信頼区間は[{percentage_interval.group(1)}]です。"""
                
                # 元のテキストを置換
                report_jp = report_jp.replace(alt_third_para_match.group(0), alt_third_para_jp)
        
        # パターン4: 四番目の "This means that, although the intervention appears..." 段落
        fourth_para_match = re.search(r"This means that, although the intervention appears.*?was above zero.", report_jp, re.DOTALL)
        if fourth_para_match:
            fourth_para_jp = """これは、介入が正の効果をもたらしたように見えるものの、介入期間全体を考慮するとこの効果は統計的に有意ではないことを意味します。介入期間内の個々の日や短い期間については（効果の時系列グラフの下限が0より上にある場合に示されるように）依然として有意な効果があった可能性があります。"""
            report_jp = report_jp.replace(fourth_para_match.group(0), fourth_para_jp)
        
        # パターン4b: 統計的に有意な場合の代替パターン（正の効果があり、統計的に有意である場合）
        alt_fourth_para_match = re.search(r"This means that the positive effect observed during the intervention.*?of the underlying intervention\.", report_jp, re.DOTALL)
        if alt_fourth_para_match:
            # 効果値を抽出
            effect_value = re.search(r"absolute effect \(([0-9.]+)\)", alt_fourth_para_match.group(0))
            effect_str = effect_value.group(1) if effect_value else "X"
            alt_fourth_para_jp = f"""これは、介入期間中に観察された正の効果が統計的に有意であり、ランダムな変動に起因する可能性が低いことを意味します。ただし、この増加が実質的な意味を持つかどうかという問題は、絶対効果（{effect_str}）を介入の本来の目標と比較することによってのみ答えることができることに注意すべきです。"""
            report_jp = report_jp.replace(alt_fourth_para_match.group(0), alt_fourth_para_jp)
        
        # パターン4c: 統計的に有意な負の効果を持つ場合のパターン
        negative_fourth_para_match = re.search(r"This means that the negative effect observed during the intervention.*?in the absence of the intervention\.", report_jp, re.DOTALL)
        if negative_fourth_para_match:
            negative_fourth_para_jp = """これは、介入期間中に観察された負の効果が統計的に有意であることを意味します。実験者が正の効果を期待していた場合は、制御変数の異常が、介入がない場合に応答変数で起こるはずだったことについて過度に楽観的な期待を引き起こした可能性があるかどうかを再確認することをお勧めします。"""
            report_jp = report_jp.replace(negative_fourth_para_match.group(0), negative_fourth_para_jp)
        
        # パターン4d: 「It may look as though...」のパターン（統計的に有意でない負の効果）
        alt_negative_para_match = re.search(r"This means that, although it may look as though the intervention has.*?meaningfully interpreted\.", report_jp, re.DOTALL)
        if alt_negative_para_match:
            alt_negative_para_jp = """これは、介入期間全体を考慮した場合、応答変数に対して介入が負の効果を及ぼしたように見えるかもしれませんが、この効果は統計的に有意ではないため、意味のある解釈はできないことを意味します。"""
            report_jp = report_jp.replace(alt_negative_para_match.group(0), alt_negative_para_jp)
        
        # パターン5: 五番目の "The apparent effect could be the result of random fluctuations..." 段落
        fifth_para_match = re.search(r"The apparent effect could be the result of random fluctuations.*?during the learning period.", report_jp, re.DOTALL)
        if fifth_para_match:
            fifth_para_jp = """見かけ上の効果は、介入と無関係なランダムな変動の結果である可能性があります。これは、介入期間が非常に長く、効果が既に消失した時間の多くを含む場合によく起こります。また、介入期間が短すぎてシグナルとノイズを区別できない場合にも起こり得ます。最後に、有意な効果が見つからないのは、制御変数が十分でない場合や、これらの変数が学習期間中に応答変数とうまく相関していない場合にも起こることがあります。"""
            report_jp = report_jp.replace(fifth_para_match.group(0), fifth_para_jp)
        
        # パターン6: 最後の "The probability of obtaining this effect by chance..." 段落（有意でない場合）
        sixth_para_match = re.search(r"The probability of obtaining this effect by chance is p = [0-9]+%.*?considered statistically significant.", report_jp, re.DOTALL)
        if sixth_para_match:
            p_value = re.search(r"p = ([0-9]+%)", sixth_para_match.group(0))
            if p_value:
                sixth_para_jp = f"""この効果が偶然によって得られる確率はp = {p_value.group(1)}です。これは、この効果が見せかけのものである可能性があり、一般的には統計的に有意とはみなされないことを意味します。"""
                report_jp = report_jp.replace(sixth_para_match.group(0), sixth_para_jp)
        
        # パターン6b: 最後の段落の別パターン（効果が統計的に有意な場合）
        alt_sixth_para_match = re.search(r"The probability of obtaining this effect by chance is very small.*?considered statistically\s+significant\.", report_jp, re.DOTALL)
        if alt_sixth_para_match:
            # p値を抽出
            p_value = re.search(r"probability p = ([0-9.]+)", alt_sixth_para_match.group(0))
            p_str = p_value.group(1) if p_value else "X"
            alt_sixth_para_jp = f"""この効果が偶然によって得られる確率は非常に小さいです（ベイズ単側尾部確率 p = {p_str}）。これは、因果効果が統計的に有意であると考えられることを意味します。"""
            report_jp = report_jp.replace(alt_sixth_para_match.group(0), alt_sixth_para_jp)
        
        # p値の行を日本語に置換
        p_line_match = re.search(r"Posterior tail-area probability p: [0-9.]+", report_jp)
        if p_line_match:
            p_value = re.search(r"p: ([0-9.]+)", p_line_match.group(0))
            if p_value:
                p_line_jp = f"事後確率 p値: {p_value.group(1)}"
                report_jp = report_jp.replace(p_line_match.group(0), p_line_jp)
        
        # 因果効果の確率の行を日本語に置換
        prob_line_match = re.search(r"Posterior probability of a causal effect: [0-9.]+%", report_jp)
        if prob_line_match:
            prob_value = re.search(r": ([0-9.]+%)", prob_line_match.group(0))
            if prob_value:
                prob_line_jp = f"因果効果の事後確率: {prob_value.group(1)}"
                report_jp = report_jp.replace(prob_line_match.group(0), prob_line_jp)
        
        # 改行の調整：連続する改行を1つに統一して段落間の余白を調整
        report_jp = re.sub(r'\n\s*\n\s*\n+', '\n\n', report_jp)
        
        return report_jp


def translate_causal_impact_report(report, alpha=0.95):
    """
    CausalImpactレポートを日本語に翻訳する便利な関数
    
    Parameters:
    -----------
    report : str
        原文の英語レポート文字列
    alpha : float, optional (default=0.95)
        信頼区間の値（0〜1の間）
        
    Returns:
    --------
    str
        翻訳された日本語レポート
    """
    translator = CausalImpactTranslator()
    return translator.translate_report(report, alpha) 