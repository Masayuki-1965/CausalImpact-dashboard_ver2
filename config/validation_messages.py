# 検証メッセージとエラーメッセージの定数管理
# アプリケーション全体で使用される各種メッセージを統一管理

# データ検証関連メッセージ
DATA_VALIDATION_MESSAGES = {
    'insufficient_data': "⚠️ データが不足しています。最低37日間のデータを推奨します。",
    'invalid_date_format': "⚠️ 日付形式が正しくありません。YYYY-MM-DD形式で入力してください。",
    'date_out_of_range': "⚠️ 指定した日付がデータ範囲外です。",
    'intervention_ratio_warning': "⚠️ 介入前期間は全体の60%以上を推奨します。",
    'missing_required_fields': "⚠️ 必須項目が入力されていません。",
}

# 期間設定関連メッセージ
PERIOD_VALIDATION_MESSAGES = {
    'pre_period_too_short': "介入前期間が短すぎます。より長い期間を設定してください。",
    'post_period_too_short': "介入期間が短すぎます。より長い期間を設定してください。",
    'period_overlap': "期間設定に重複があります。期間を見直してください。",
    'invalid_period_order': "期間の順序が正しくありません。開始日は終了日より前である必要があります。",
}

# 分析実行関連メッセージ
ANALYSIS_EXECUTION_MESSAGES = {
    'analysis_start': "分析を開始しています...",
    'analysis_complete': "分析が完了しました！",
    'analysis_failed': "分析中にエラーが発生しました。データまたは設定を確認してください。",
    'insufficient_variation': "データの変動が少なすぎて分析できません。",
}

# 成功メッセージ
SUCCESS_MESSAGES = {
    'data_loaded': "データの読み込みが完了しました。",
    'analysis_complete': "分析が正常に完了しました。",
    'export_complete': "エクスポートが完了しました。",
}

# 単群推定分析特有のメッセージ
SINGLE_GROUP_MESSAGES = {
    'method_explanation': "単群推定では、介入前のデータから季節性やトレンドを学習し、介入後の予測値（反事実シナリオ）と実測値を比較して効果を測定します。",
    'reliability_note': "この分析結果は処置群のみのデータに基づいています。外部要因の影響を完全に排除できない点にご注意ください。",
    'data_requirement': "（最低37日間のデータを推奨、介入前期間は全体の60%以上が必要）",
}

# 二群比較分析特有のメッセージ
TWO_GROUP_MESSAGES = {
    'method_explanation': "二群比較では、介入の影響を受けた処置群と影響を受けていない対照群の関係性をもとに、介入後の予測値と実測値を比較して効果を測定します。",
    'reliability_note': "この分析結果は処置群と対照群の両方のデータに基づいた信頼性の高い結果です。",
}

# UI表示用メッセージ
UI_DISPLAY_MESSAGES = {
    'upload_csv_instruction': "（上の入力欄にCSVデータをコピペしてください）",
    'file_upload_help': "CSVファイルをアップロードしてください。",
    'analysis_type_help': "二群比較は処置群と対照群の両方を比較します。単群推定は処置群のみで介入前後のトレンド変化を分析します。",
    'upload_method_help': "CSVデータを直接入力する方法と、ファイルをアップロードする方法があります。",
}

# 終了メッセージ
COMPLETION_MESSAGES = {
    'thank_you': "🎉 ご利用ありがとうございました",
    'analysis_finished': "分析が完了しました。結果をご確認ください。",
    'download_ready': "結果のダウンロードができます。",
} 