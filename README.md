# Causal Impact Analyzer ver2

Causal Impactを用いて介入効果を可視化・分析するPython Streamlitアプリケーションです。
二群比較（Two-Group）と単群推定（Single Group）の両方の分析手法に対応しています。

## アプリケーション概要

このアプリケーションでは、以下の2つの分析手法を選択できます：

### 1. 二群比較分析（Two-Group Causal Impact）
処置群（介入効果を測定したい対象）と対照群（比較対象）のデータを用いて介入効果を分析

### 2. 単群推定分析（Single Group Causal Impact）  
処置群のみのデータを用いて介入効果を推定（対照群なしの分析）

## 主な機能
- **多様なデータ取り込み**: CSVファイル・テキスト入力対応
- **柔軟な分析期間設定**: 介入前期間・介入期間の詳細設定
- **高度な可視化**: 時系列プロット・分析結果グラフ・統計情報表示
- **包括的なレポート**: PDF・CSV形式での分析結果ダウンロード
- **多言語対応**: 日本語・英語対応（環境に応じた自動切り替え）
- **Streamlit Cloud対応**: クロスプラットフォーム動作保証

## ファイル構成

### メインアプリケーション
- `app_enhanced.py`: メインアプリケーションファイル（2342行）
- `utils_step1.py`: データ取り込み・可視化（STEP1）用の補助関数モジュール
- `utils_step2.py`: 分析期間・パラメータ設定（STEP2）用の補助関数モジュール
- `utils_step3.py`: 二群比較分析実行・結果表示（STEP3）用の補助関数モジュール（1580行）
- `utils_step3_single_group.py`: 単群推定分析実行・結果表示用の補助関数モジュール（1290行）
- `utils_common.py`: 共通処理・セッション管理モジュール
- `causal_impact_translator.py`: 分析レポートの日本語翻訳モジュール

### 設定ファイル
- `config/constants.py`: 定数・設定値管理
- `config/help_texts.py`: ヘルプテキスト・HTML管理
- `config/inline_styles.py`: インラインHTMLスタイル定数管理
- `config/validation_messages.py`: 検証・エラーメッセージ管理
- `config/font_config.py`: クロスプラットフォーム対応フォント設定
- `config/pdf_templates.py`: 多言語対応PDFテンプレート
- `config/graph_config.py`: グラフタイトル多言語対応設定

### スタイル・データ
- `styles/custom.css`: カスタムスタイルシート
- `data/`: サンプルデータ格納ディレクトリ
  - `treatment_data/`: 処置群データCSVファイル
  - `control_data/`: 対照群データCSVファイル
- `requirements.txt`: 必要パッケージリスト（134パッケージ）

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

### ローカル環境での実行
```bash
# リポジトリのクローン
git clone <repository-url>
cd CausalImpact-Analyzer_ver2

# Python仮想環境の作成（推奨）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate     # Windows

# 必要パッケージのインストール
pip install -r requirements.txt

# アプリケーションの実行
streamlit run app_enhanced.py
```

### Streamlit Cloudでの実行
1. GitHubリポジトリにプッシュ
2. [Streamlit Cloud](https://streamlit.io/cloud) でデプロイ
3. 多言語対応により、環境に応じて自動的に日本語/英語が切り替わります

## 最新の更新内容（Phase 6.7）

- ✅ **PDF分析期間件数表示の修正**: STEP2で設定した介入期間の件数がPDFに正確に反映されるよう修正
- ✅ **Streamlit Cloud完全対応**: 日本語フォント・グラフタイトルの文字化け対策完了
- ✅ **多言語自動切り替え**: 環境に応じて日本語/英語が自動選択される機能
- ✅ **エラーハンドリング強化**: 確実な動作を保証するフォールバック機能

---

**開発バージョン**: ver2 (Phase 6.7完了)  
**対応環境**: Windows, macOS, Linux (Streamlit Cloud)  
**Python要件**: 3.8以上（推奨: 3.13） 