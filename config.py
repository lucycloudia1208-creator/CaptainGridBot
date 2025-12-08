# config.py  ← 秘密鍵を守る最強の設定ファイルだよ！

import os

class Config:
    # KoyebかPCから自動で秘密鍵を読むよ
    STARK_PRIVATE_KEY = os.getenv("STARK_PRIVATE_KEY")
    
    # テストネットか本番かを切り替えるスイッチ
    TESTNET_MODE = os.getenv("TESTNET_MODE", "true").lower() == "true"
    
    # 自動でURLを変える魔法
    BASE_URL = "https://testnet.edgex.exchange" if TESTNET_MODE else "https://api.edgex.exchange"
    
    # ボットの設定（あとで自由に変えられるよ）
    SYMBOL = os.getenv("SYMBOL", "BTC-USDT")
    GRID_INTERVAL = int(os.getenv("GRID_INTERVAL", "50"))
    GRID_COUNT = int(os.getenv("GRID_COUNT", "20"))
    INVEST_USD = float(os.getenv("INVEST_USD", "50.0"))

    @staticmethod
    def validate():
        if not Config.STARK_PRIVATE_KEY:
            print("エラー！STARK_PRIVATE_KEYが見つかりません！")
            print("→ KoyebのSecrets か .envファイルに入れてね")
            exit()
        print("設定全部OK！サソリが動き出す準備できたよ！")
        print(f"モード → {'テストネット（お金かからないよ）' if Config.TESTNET_MODE else '本番（ガチでお金動くよ）'}")
        print(f"取引ペア → {Config.SYMBOL}")

# このファイルを開いた瞬間にチェックするよ
Config.validate()