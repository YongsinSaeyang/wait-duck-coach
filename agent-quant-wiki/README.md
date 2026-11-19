# AI Agent 與量化研究：LLM Wiki 與 HTML 教材

第十週作品。先確認主題和進階深度，再從七份來源的已讀章節整理成八篇互連 Wiki，最後生成十八頁教學簡報。來源、主張、Wiki、投影片與工具輸出均有對應。

## 本機執行

Python 3.11 以上，只有標準庫；瀏覽器使用原生 HTML／CSS／JS。

```sh
python3 scripts/research.py --generate-data --check
python3 scripts/research.py --check
python3 scripts/pipeline.py --check
python3 scripts/build.py
python3 scripts/check.py
python3 -m unittest discover -s tests -v
python3 -m http.server 8944 --bind 127.0.0.1
```

開啟 index.html 進入入口，slides.html 是簡報，wiki/index.html 是 Wiki，evidence.html 是流程紀錄。

## 誠實呈現 LLM 的位置

本次 Codex 對話中的 LLM 根據已讀來源和作者需求，協作來源整理、Wiki 與教材。Python 程式重播已保存的作者輸出、計算和檢查，沒有藏著呼叫即時 LLM，也不接券商。這不是一個可以線上任意聊天的研究 Agent。工具與條件邊是研究架構教學，不冒稱安裝了 LangGraph。

七份來源都有實際本地整理內容，並保留定位、讀取範圍、日期和本地雜湊。整理檔不等於外部全文快照；S07 僅讀摘要。Wiki 依研究問題重組並互連，投影片再透過 claim 回查 Wiki 與原始來源。

## 兩份合成資料的用途

主要固定合成資料的最後測試期沒有交易，報酬為零。保留此結果，並以活動度檢查停止解讀策略績效。另設 coverage fixture，開發資料前綴與選參數結果保持相同，只在最後區段使用不同的明列混合報酬，驗證交易與成本機制。它不是為了改出漂亮獲利，也不能代替原先的市場研究。兩份結果和資料都公開保存。

候選為 3／7、5／12、8／20 均線；三段時間驗證後選 3／7，才讀最後三十筆。此為合成教學，不計算 PBO、統計顯著性或真實台股績效。稅、最低費用、滑價、部分成交、價格限制及股利未建模。

## 本次執行與反思

- 2026-11-17 開始來源整理與需求確認；2026-11-19 重新執行及驗收。
- 14 次前後對照：一個正常情境與六個故意錯誤，各在前置／後置檢查執行。六個錯誤中，前置檢查使不必要的工具執行由 6 次降至 1 次、暫存草稿由 6 份降至 0 份。這不是模型錯誤率。
- 另外一個明列快照回復迴圈實際執行兩次：缺成本先被拒絕，回復完整教學規格後通過但保留零交易警示。本輪共 16 次節點執行，不是 16 次模型 API 呼叫。
- 自然觀察只有資料取得逾時與零交易各一次，無法據此聲稱哪個節點長期最常失敗。來源完整性檢查移到 ingest，規格檢查移到工具之前；算術與活動度仍在結果後檢查。
- 31 項 unittest 涵蓋來源雜湊、引用、時間切分、最後測試不回流、成本、現金流、故意錯誤、回復預算與產物一致性。程式不代替來源語意的人工覆核。

## 結構

AGENTS.md 定義規則；docs/discussion.md 保留需求；prompts/ 保存作者指令；content/sources/ 是 ingest 整理；content/wiki/ 與 claims.json 是互連知識；content/slides.json 是教材結構；runs/ 保存真實程式執行與觀察；workflow.json 記錄節點和退回條件。

圖中的修訂上限是兩次；未知依據不得自動補造，回復只使用明列的教學快照。單元測試另驗證無法回復時最多三次嘗試後交人工，不會一直循環。
