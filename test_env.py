import os
from dotenv import load_dotenv

load_dotenv()

account_id = os.getenv("EDGEX_ACCOUNT_ID")

print("=== 環境変数テスト ===")
print(f"Account ID: {account_id}")
print(f"長さ: {len(account_id) if account_id else 0}")
print(f"型: {type(account_id)}")

# 1文字ずつ表示
if account_id:
    print("\n文字コード解析:")
    for i, char in enumerate(account_id):
        print(f"  [{i}] '{char}' (ord: {ord(char)})")

# 正しい値と比較
correct = "678726936080866030"
print(f"\n正しい値: {correct}")
print(f"一致: {account_id == correct}")

if account_id != correct:
    print("\n❌ 不一致箇所:")
    for i, (c1, c2) in enumerate(zip(account_id or "", correct)):
        if c1 != c2:
            print(f"  位置{i}: '{c1}' != '{c2}'")