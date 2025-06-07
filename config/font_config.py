# フォント設定管理モジュール
# Streamlit Cloud対応の日本語フォント設定

import os
import platform
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import urllib.request


def get_japanese_font_config():
    """
    環境に応じて適切な日本語フォント設定を取得
    
    Returns:
    --------
    tuple: (font_name, font_path)
        使用するフォント名とパス
    """
    
    # フォント優先順位リスト
    font_candidates = [
        # 同梱フォント（最優先）
        {
            'name': 'NotoSansCJK',
            'path': 'fonts/NotoSansCJK-Regular.ttc',
            'url': 'https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTC/NotoSansCJK-Regular.ttc'
        },
        # Windowsシステムフォント
        {
            'name': 'MSGothic',
            'path': 'C:/Windows/Fonts/msgothic.ttc',
            'url': None
        },
        # Linuxシステムフォント候補
        {
            'name': 'DejaVuSans',
            'path': '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            'url': None
        }
    ]
    
    for font_config in font_candidates:
        font_path = font_config['path']
        
        # 同梱フォントの場合、存在しなければダウンロード
        if font_config['name'] == 'NotoSansCJK' and font_config['url']:
            if not os.path.exists(font_path):
                try:
                    # フォントディレクトリ作成
                    os.makedirs(os.path.dirname(font_path), exist_ok=True)
                    
                    # フォントダウンロード（開発時のみ、本番では事前配置推奨）
                    print(f"日本語フォントをダウンロード中: {font_config['url']}")
                    urllib.request.urlretrieve(font_config['url'], font_path)
                    print(f"フォントダウンロード完了: {font_path}")
                except Exception as e:
                    print(f"フォントダウンロードエラー: {e}")
                    continue
        
        # フォントファイル存在確認
        if os.path.exists(font_path):
            try:
                # フォント登録テスト
                pdfmetrics.registerFont(TTFont(font_config['name'], font_path))
                print(f"日本語フォント設定成功: {font_config['name']} ({font_path})")
                return font_config['name'], font_path
            except Exception as e:
                print(f"フォント登録エラー ({font_config['name']}): {e}")
                continue
    
    # フォールバック: デフォルトフォント
    print("⚠️ 日本語フォントが見つかりません。デフォルトフォントを使用します。")
    return 'Helvetica', None


def setup_japanese_font():
    """
    日本語フォントの初期設定を実行
    
    Returns:
    --------
    str: 設定されたフォント名
    """
    try:
        font_name, font_path = get_japanese_font_config()
        
        # 既に登録済みの場合はスキップ
        if font_name in pdfmetrics.getRegisteredFontNames():
            print(f"フォントは既に登録済み: {font_name}")
            return font_name
        
        # 新規フォント登録
        if font_path and os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            print(f"日本語フォント登録完了: {font_name}")
        
        return font_name
        
    except Exception as e:
        print(f"フォント設定エラー: {e}")
        print("デフォルトフォント (Helvetica) を使用します")
        return 'Helvetica'


def get_font_name():
    """
    現在設定されている日本語フォント名を取得
    
    Returns:
    --------
    str: フォント名
    """
    return setup_japanese_font()


# 軽量版設定（既存フォントのみ使用・確実版）
def get_simple_japanese_font():
    """
    システム既存フォントのみを使用する軽量版設定
    Streamlit Cloud環境での安全性を最大化
    
    Returns:
    --------
    str: フォント名
    """
    
    # デバッグ情報出力
    system = platform.system()
    print(f"システム環境: {system}")
    
    if system == "Windows":
        font_candidates = [
            ('MSGothic', 'C:/Windows/Fonts/msgothic.ttc'),
            ('MSPGothic', 'C:/Windows/Fonts/msgothic.ttc'),
            ('YuGothic', 'C:/Windows/Fonts/YuGoth.ttf'),
        ]
    elif system == "Darwin":  # macOS
        font_candidates = [
            ('HiraginoSans', '/System/Library/Fonts/Hiragino Sans GB.ttc'),
            ('AppleGothic', '/System/Library/Fonts/AppleGothic.ttf'),
        ]
    else:  # Linux (Streamlit Cloud)
        # Streamlit Cloud環境では日本語フォントが利用できないため
        # 英語フォントのみを使用し、PDF内容も英語に切り替える
        print("⚠️ Linux環境（Streamlit Cloud）を検出：英語レポート生成モードに切り替えます")
        font_candidates = [
            ('Helvetica', None),  # reportlabのビルトインフォント
            ('Times-Roman', None),  # reportlabのビルトインフォント
        ]
    
    for font_name, font_path in font_candidates:
        try:
            # ビルトインフォントの場合はパス不要
            if font_path is None:
                print(f"ビルトインフォント使用: {font_name}")
                return font_name
            
            # ファイルベースフォントの場合
            if os.path.exists(font_path):
                if font_name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                print(f"日本語フォント登録成功: {font_name}")
                return font_name
            else:
                print(f"フォントファイル未発見: {font_path}")
        except Exception as e:
            print(f"フォント登録エラー ({font_name}): {e}")
            continue
    
    # 最終フォールバック
    print("デフォルトフォント (Helvetica) を使用")
    return 'Helvetica'

def is_japanese_font_available():
    """
    日本語フォントが利用可能かどうかを判定
    
    Returns:
    --------
    bool: 日本語フォントが利用可能な場合True
    """
    system = platform.system()
    
    # Windowsの場合は通常日本語フォントが利用可能
    if system == "Windows":
        return True
    
    # macOSの場合も通常利用可能
    elif system == "Darwin":
        return True
    
    # Linux（Streamlit Cloud）の場合は利用不可とみなす
    else:
        return False 