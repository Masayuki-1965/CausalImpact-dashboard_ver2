# CausalImpact-Analyzer_ver2 変更履歴

## 2025-01-10 - UI改善・最終仕上げ

### ユーザビリティ改善
- **サマリー表補足説明追加**: 絶対効果に「（実測値 − 予測値）」、相対効果に「（絶対効果 ÷ 予測値）」の計算式を追加
- **冗長な注釈削除**: 「分析結果の解釈と品質評価」セクションを削除し、インターフェースを簡潔化
- **二群比較・単群推定両対応**: アプリ画面のサマリー表に統一的に適用
- **PDF出力**: 英語版PDFには変更なし（多言語対応維持）

### 修正対象ファイル
1. `config/app_templates.py` - サマリー表ラベルの補足説明追加
2. `app_enhanced.py` - 冗長な品質評価セクションの削除

### ドキュメント更新
- `docs/priority_development_checklist.md` - Phase 7完了・UI改善実績追加
- `README.md` - 最終更新日・プロジェクト状況の更新
- `CHANGELOG.md` - 本変更履歴の追加

### 最終状態
- ✅ 本格運用可能状態達成
- ✅ GitHub公開準備完了
- ✅ UI/UX最適化完了
- ✅ 全7フェーズ開発完了

---

## 2024-12-19 - Japanese Font Display Fix for Streamlit Cloud

### 問題
- Streamlit Cloud環境でのグラフタイトル文字化け発生
- 「実測値 vs 予測値」「時点効果」「累積効果」のサブプロットタイトルで文字化け
- PDF出力にも同様の文字化けが影響

### 解決方法
- グラフタイトルの環境判定による自動切り替えを実装
- Streamlit Cloud環境では英語タイトル、PC環境では日本語タイトルを表示
- アプリ画面の他の要素（サマリーテーブル、グラフ説明）は引き続き日本語固定

### 修正対象ファイル
1. `app_enhanced.py` - メインアプリケーションのグラフ表示処理
2. `utils_step3.py` - 二群比較分析のグラフ生成
3. `utils_step3_single_group.py` - 単群推定分析のグラフ生成

### 変更詳細
- ハードコードされた日本語タイトルを`config.graph_config.get_graph_config()`を使用した環境判定に変更
- フォールバック処理を英語固定に変更（安全性向上）
- 既存の環境判定ロジック（フォント利用可能性検出）を活用

### 最終状態
- ✅ アプリ画面サマリーテーブル: 常時日本語表示
- ✅ アプリ画面グラフ説明: 常時日本語表示  
- ✅ アプリ画面グラフタイトル: 環境判定（Streamlit Cloud: 英語、PC: 日本語）
- ✅ PDF出力: 環境判定（Streamlit Cloud: 英語、PC: 日本語）
- ✅ 動的信頼水準対応（95%, 90%等）

---

## 2024-12-18 - Japanese Text Fix Implementation

### アプリ画面日本語表示の統一
- サマリーテーブルの日本語固定実装完了
- グラフ説明文の日本語固定実装完了
- 動的信頼水準「予測値 XX% 信頼区間」対応
- PDF出力は引き続き環境依存（文字化け回避）

### 主要改善点
- `config/app_templates.py`の新規作成（アプリ画面専用テンプレート）
- 二群比較・単群推定両方の分析タイプに対応
- 複数レベルのエラーハンドリング実装

---

## 初期バージョン
- Causal Impact分析機能の基本実装
- 二群比較・単群推定の両分析手法対応
- PDF・CSV出力機能
- Streamlit Webアプリケーション 