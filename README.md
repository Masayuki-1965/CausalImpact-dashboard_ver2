# Causal Impact Analyzer

Causal Impactを用いて介入効果を可視化・分析するPython Streamlitアプリケーションです。

## アプリケーション概要

このアプリケーションでは、処置群（介入効果を測定したい対象）と対照群（比較対象）のデータを用いて、
CausalImpactによる介入効果の測定・分析を行うことができます。

主な機能：
- CSVファイルからの時系列データ読み込み
- データの可視化と統計情報の表示
- 分析期間（介入前期間・介入期間）の設定
- モデルパラメータの詳細設定
- CausalImpact分析の実行と結果表示
- 分析レポートの日本語化表示

## ファイル構成

- `app.py`: メインアプリケーションファイル
- `utils_step1.py`: データ取り込み・可視化（STEP1）用の補助関数モジュール
- `utils_step2.py`: 分析期間・パラメータ設定（STEP2）用の補助関数モジュール
- `utils_step3.py`: 分析実行・結果表示（STEP3）用の補助関数モジュール
- `causal_impact_translator.py`: 分析レポートの日本語翻訳モジュール
- `data/` : サンプルデータ格納ディレクトリ
  - `treatment_data/`: 処置群データCSVファイル
  - `control_data/`: 対照群データCSVファイル
- `requirements.txt`: 必要パッケージリスト

## モジュール分割について

- `utils_step1.py`：
  - データファイル取得、読み込み、集計、可視化用の関数を提供します。
  - 例：`get_csv_files`, `load_and_clean_csv`, `aggregate_df` など
- `utils_step2.py`：
  - 分析期間・パラメータ設定、バリデーション、日数計算などの関数を提供します。
  - 例：`get_period_defaults`, `validate_periods`, `build_analysis_params` など
- `utils_step3.py`：
  - CausalImpact分析実行、summary/report生成、グラフ・サマリーDataFrame生成などの関数を提供します。
  - 例：`run_causal_impact_analysis`, `build_summary_dataframe`

## 翻訳モジュールについて

`causal_impact_translator.py` は、CausalImpactの分析レポート（英語）を日本語に翻訳するためのモジュールです。

### 使用方法

```python
from causal_impact_translator import translate_causal_impact_report

# CausalImpactの分析実行
ci = CausalImpact(data, pre_period, post_period)

# 英語の分析レポート取得
report = ci.summary(output='report')

# 日本語に翻訳
report_jp = translate_causal_impact_report(report, alpha=0.95)

# 翻訳されたレポートの表示
print(report_jp)
```

### 翻訳パターンの追加方法

`CausalImpactTranslator` クラスの `translate_report` メソッドに新しいパターンを追加することで、
対応範囲を拡張できます。

```python
# 新しいパターンの追加例
new_pattern_match = re.search(r"英語の正規表現パターン", report_jp, re.DOTALL)
if new_pattern_match:
    new_pattern_jp = "対応する日本語訳"
    report_jp = report_jp.replace(new_pattern_match.group(0), new_pattern_jp)
```

各パターンは以下の要素で構成されています：
1. 検索用の正規表現パターン
2. マッチした場合の日本語訳（必要に応じて値を抽出して埋め込み）
3. 置換処理

## インストールと実行

```bash
# 必要パッケージのインストール
pip install -r requirements.txt

# アプリケーションの実行
streamlit run app.py
``` 