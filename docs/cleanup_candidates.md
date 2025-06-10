# プロジェクト整理・削除候補リスト

**更新日**: 2025年1月  
**目的**: Google Cloud Run移行・ITS分析統合準備のためのコードベース整理

---

## 🎯 削除対象ファイル・ディレクトリ

### 1. 即座削除推奨（開発完了後不要）

#### 1.1 旧バージョンアプリケーション
- **ファイル**: `app.py` 
- **サイズ**: 98KB (1,598行)
- **理由**: 二群比較専用の旧バージョン。現在は`app_enhanced.py`（二群比較＋単群推定兼用）を使用中
- **削減効果**: 98KB削減、コードベース簡潔化
- **削除タイミング**: 即座実行可能

#### 1.2 Pythonキャッシュファイル
- **ディレクトリ**: `__pycache__/`
- **内容**: 7ファイル（約290KB）
  - `utils_step3_single_group.cpython-313.pyc` (68KB)
  - `utils_step3.cpython-313.pyc` (82KB)
  - `app_enhanced.cpython-313.pyc` (108KB)
  - その他4ファイル (約32KB)
- **理由**: Python実行時自動生成される一時ファイル
- **削減効果**: 約290KB削減
- **削除タイミング**: GitHubプッシュ前必須

### 2. GitHub/Cloudデプロイ前削除推奨

#### 2.1 サンプルデータファイル
- **ディレクトリ**: `data/`
- **内容**: 
  - `data/treatment_data/` (2ファイル、約13KB)
    - `雨戸_台風の影響あり.csv` (2.0KB)
    - `ヒシクロス面格子.csv` (11KB)
  - `data/control_data/` (2ファイル、約9KB)
    - `一般サッシ.csv` (2.2KB)
    - `たて面格子.csv` (6.9KB)
- **理由**: 開発・テスト用サンプルデータ、本番環境不要
- **削減効果**: 約22KB削減、プライバシー保護
- **削除タイミング**: GitHub公開前推奨

#### 2.2 空フォントディレクトリ
- **ディレクトリ**: `fonts/`
- **理由**: 現在空ディレクトリ、フォント設定は`config/font_config.py`で管理
- **削減効果**: ディレクトリ構造の簡潔化
- **削除タイミング**: 任意（即座実行可能）

### 3. 保持必須ファイル（削除禁止）

#### 3.1 次期開発準備ファイル
- **ファイル**: `utils_its_analysis.py` (10KB, 294行)
- **理由**: ITS（Interrupted Time Series）分析統合で使用予定
- **保持期間**: Phase 8（ITS分析統合）完了まで

#### 3.2 クロスプラットフォーム対応設定
- **ディレクトリ**: `config/` (全8ファイル)
- **理由**: Streamlit Cloud・Google Cloud Run両対応に必要
- **重要ファイル**:
  - `font_config.py` - 環境別フォント設定
  - `pdf_templates.py` - 多言語PDF対応
  - `graph_config.py` - グラフ文字化け対策

#### 3.3 プロジェクト管理ドキュメント
- **ディレクトリ**: `docs/` (6ファイル)
- **理由**: 引き継ぎ・保守・機能拡張時に必要
- **保持対象**: 全ファイル

---

## 🔧 削除実行手順

### Phase 1: 即座実行可能な削除
```bash
# 1. 旧バージョンアプリケーション削除
rm app.py

# 2. Pythonキャッシュファイル削除
rm -rf __pycache__/
rm -rf config/__pycache__/

# 3. 空フォントディレクトリ削除（存在する場合）
rmdir fonts/ 2>/dev/null || true
```

### Phase 2: GitHub公開前削除（optional）
```bash
# 4. サンプルデータ削除（GitHub公開時のみ）
rm -rf data/
```

### PowerShell版（Windows環境）
```powershell
# 1. 旧バージョンアプリケーション削除
Remove-Item app.py

# 2. Pythonキャッシュファイル削除
Remove-Item __pycache__ -Recurse -Force
Remove-Item config\__pycache__ -Recurse -Force -ErrorAction SilentlyContinue

# 3. 空フォントディレクトリ削除
Remove-Item fonts -Force -ErrorAction SilentlyContinue

# 4. サンプルデータ削除（GitHub公開時のみ）
# Remove-Item data -Recurse -Force
```

---

## 📊 削除効果まとめ

### ファイルサイズ削減効果
- **app.py削除**: 98KB削減
- **__pycache__削除**: 約290KB削減  
- **data/削除**: 約22KB削減
- **合計削減効果**: 約410KB削減

### コードベース改善効果
- **メインアプリの一本化**: `app_enhanced.py`のみに統一
- **ディレクトリ構造簡潔化**: 不要なディレクトリ除去
- **GitHub公開準備**: プライベートデータ・キャッシュファイル除去
- **保守性向上**: 開発完了ファイルと次期開発ファイルの明確な分離

### 次期開発への影響
- **Google Cloud Run移行**: 影響なし（設定ファイル完備）
- **ITS分析統合**: 影響なし（utils_its_analysis.py保持）
- **既存機能**: 影響なし（コア機能ファイル全て保持）

---

## ⚠️ 注意事項・確認事項

### 削除前の最終確認
1. **app.py vs app_enhanced.py**: 現在使用中が`app_enhanced.py`であることを確認
2. **動作テスト**: 削除後のアプリケーション正常動作確認
3. **バックアップ**: 削除前に現在の状態をGitでコミット

### 削除実行のタイミング
- **Phase 1**: 開発完了確認後、即座実行可能
- **Phase 2**: GitHub公開・Cloud Run移行前に実行
- **復旧対応**: Git履歴から必要に応じて復旧可能

### 削除後の構成（予想）
```
CausalImpact-Analyzer_ver2/
├── app_enhanced.py                 # メインアプリケーション（唯一）
├── utils_step3.py                  # 二群比較分析エンジン
├── utils_step3_single_group.py     # 単群推定分析エンジン
├── utils_step1.py                  # データ取り込み処理
├── utils_step2.py                  # 期間・パラメータ設定処理
├── utils_common.py                 # 共通処理・セッション管理
├── utils_its_analysis.py           # ITS分析準備ファイル（次期開発用）
├── causal_impact_translator.py     # 分析結果日本語化処理
├── requirements.txt                # 依存パッケージ
├── README.md                       # 使用説明書
├── CHANGELOG.md                    # 変更履歴
├── config/                         # 設定ファイル群（8ファイル）
├── styles/
│   └── custom.css                 # カスタムスタイルシート
├── docs/                          # ドキュメント一式（6ファイル）
└── venv/                          # Python仮想環境
```

**最終更新**: 2025年1月  
**承認状況**: Phase 7.1 完了・削除実行準備完了 