# MARKETSPEED II RSS Bridge

Windows上でMARKETSPEED IIとExcelのRSSアドインを起動・接続した状態で使用する、読み取り専用のローカルAPIです。

## 安全方針

- 注文作成なし
- 注文送信なし
- 取消なし
- GETのみ

## セットアップ

```powershell
py -m pip install -r tools/requirements-rss.txt
```

Excelの`Sheet1`に次の順でRSS関数を配置してください。

- A1: 4755.T
- A2: 9432.T
- A3: 7203.T
- A4: 9984.T

## 起動

```powershell
py -m uvicorn tools.rss_bridge:app --host 127.0.0.1 --port 8000
```

## 確認

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/price/4755.T
