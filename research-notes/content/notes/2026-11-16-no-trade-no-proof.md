---
{
  "id": "no-trade-no-proof",
  "title": "資金不足未進場，和送單未成交差在哪？",
  "date": "2026-11-16",
  "updated": "2026-11-16",
  "category": "回測實作",
  "tags": [
    "成交條件",
    "實作觀察"
  ],
  "summary": "從第八週的零報酬回饋，拆開未建立模擬單、建立後未成交與已成交三條路徑。用公開的教學輸入與重現腳本，比較同樣 0% 的不同原因。",
  "sources": [
    "freqtrade-backtesting"
  ],
  "related": [
    "costs-matter",
    "next-bar-execution"
  ],
  "origin": "作者在第八週提供的 Gradio 實測觀察，另以可重跑的教學假設建立三條執行路徑。完整原始逐步工具日誌未另存。",
  "example_kind": "teaching",
  "experience_record": "content/observations/week08-no-entry.json",
  "experiment": {
    "script": "scripts/execution_demo.py",
    "input": "content/experiments/execution-input.csv",
    "output": "assets/execution-paths.json",
    "chart": "assets/execution-paths.svg"
  }
}
---
## 我想釐清的問題

第八週，我用相同本金測試兩次，把本地試算單位從 1,000 股改成 1 股。原回覆把第一種情況稱為「未成交」，但更精確的說法是資金不足、未建立本地買入紀錄。這段觀察的邊界是本地歷史試算，沒有送到券商的真實委託。原始完整工具參數與逐步日誌未另外保存，因此這份紀錄只能支持資金不足的回報。

報酬率 0% 只告訴我期初和期末的比例；是哪一步停下來，還要看執行狀態。下面把不同路徑分開重現。

## 一個算得出來的例子

教學假設，本金 100,000 元，每股 120 元，期末價格 110 元，先忽略費用。最小 1,000 股需要 120,000 元；改成 1 股單位最多可買 833 股。

| 路徑 | 建立本地模擬單 | 模擬成交股數 | 期末資產 | 停止或持有的狀態 |
| --- | --- | --- | --- | --- |
| A 資金不足 | 否 | 0 | 100,000 元 | 未進場 NO_ENTRY |
| B 假設無可用流動性 | 是 | 0 | 100,000 元 | 待成交 UNFILLED |
| C 假設可成交 | 是 | 833 | 91,670 元 | 已成交 FILLED |

C 的期末資產是剩餘現金 40 元，加 833 股乘 110 元，得到 91,670 元。A、B 都是 0%，執行階段不同。B 是為比較而設計的教學分支，並非第八週觀察到的市場現象。重現腳本只接受表中明列的輸入，沒有行情下載或券商連線。

### 自己重跑這個例子

在專案目錄執行以下指令，會從 CSV 重建 JSON 結果和 SVG 圖表，再核對產物。原始檔和圖在文末的「重現這個實驗」可以打開。

```sh
python3 scripts/execution_demo.py
python3 scripts/execution_demo.py --check
```

## 我會怎麼檢查

- 先看 order_created，確認是否建立了本地模擬單，接著才檢查 filled_quantity。
- 模擬單存在但成交量為零時，再讀當次的價格、流動性與其他明列的成交假設。
- 已有成交時，分開保存剩餘現金、期末持股與估值，避免把期末資產直接叫作已實現損益。

## 還需要注意什麼

原先的 0% 實測支持「資金不足未進場」這個個案。三條教學路徑可檢查程式對狀態的分類，策略未來的市場表現仍需要另外研究。真實券商委託還有拒單、部分成交及其他狀態，必須讀取實際回報。回測文件對資金限制與模擬假設也有說明。 [Freqtrade 回測文件](https://www.freqtrade.io/en/stable/backtesting/)
