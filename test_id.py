# test_id.py (最終勝利修正版)
import asyncio
from dotenv import load_dotenv
import os
from edgex_sdk import Client

load_dotenv()  # .env を読み込む

async def test_account_id():
    try:
        client = Client(
            base_url=os.getenv("EDGEX_BASE_URL"),
            account_id=os.getenv("EDGEX_ACCOUNT_ID"),
            stark_private_key=os.getenv("EDGEX_STARK_PRIVATE_KEY")
        )
        
        # 正しいメソッドでアカウント資産を取得
        assets = await client.get_account_asset()
        print("【公式SDKが認めたアカウント資産】→", assets)
        
        # 正しいパスでAccount ID抽出（data.account.id）
        official_id = assets.get("data", {}).get("account", {}).get("id", "不明")
        print("【SDKが計算したAccount ID】→", official_id)
        print("【あなたが.envに書いたID】→", os.getenv("EDGEX_ACCOUNT_ID"))
        
        if str(official_id) == os.getenv("EDGEX_ACCOUNT_ID"):
            print("🎉 一致した！！！ 署名&認証完璧！！！ これでグリッドボット本番OK！！！")
            print("📊 残高サマリー: USDT ≈", assets.get("data", {}).get("collateralList", [{}])[0].get("amount", "不明"))
        else:
            print("❌ まだ違う… .envのIDを公式の数字に上書きして再実行！")
            
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        print("原因: Private KeyかBase URLが間違ってるかも。ダッシュボードで再確認！")

# async実行
asyncio.run(test_account_id())