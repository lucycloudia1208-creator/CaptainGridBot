from config import Config
import time

print("CaptainGridBot 起動！！")
print(f"接続先 → {Config.BASE_URL}")
print(f"秘密鍵 → 読み込みOK！（長さ：{len(Config.STARK_PRIVATE_KEY)}文字）")

for i in range(10, 0, -1):
    print(f"あと {i} 秒・・・")
    time.sleep(1)

print("サソリ爆誕！！！")