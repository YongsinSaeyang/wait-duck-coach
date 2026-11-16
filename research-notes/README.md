# 等等鴨投資研究筆記庫

一個可持續增加內容的繁體中文筆記網站。以量化觀念、回測實作和資料查核為主題，每篇有具體問題、教學例子、檢查方式、限制與原始來源。第九週作業的重點是讓 AI 先讀 AGENTS.md，依同一模板繼續新增內容。

網站有全文搜尋、分類、這台裝置的收藏、相關筆記及回撤教學試算。所有文章有獨立網址。靜態網站採 HTML、CSS、JavaScript，內容以 Markdown 保存，Python 標準函式庫負責產生頁面。

## 瀏覽與建置

Python 3.11 以上可直接執行，不需安裝第三方套件。

```sh
python3 scripts/build.py
python3 scripts/check.py
python3 -m unittest discover -s tests -v
python3 scripts/execution_demo.py --check
python3 -m http.server 8940 --bind 127.0.0.1
```

開啟 http://127.0.0.1:8940/ 。先建置再檢查，會核對來源 ID、必要段落、檔名、日期、延伸閱讀，以及每個內部檔案連結。檢查還會比對目前產物是否與來源一致，並檢查佔位文字、教學標示、正文引用、作者觀察路徑和 11 項登記算術。來源對主張的語意支持仍需人工判讀。

## 新增內容

1. 先讀 AGENTS.md、來源登記和一篇現有筆記。
2. 複製 templates/note.md 到 content/notes/YYYY-MM-DD-english-slug.md。
3. 填入 metadata、四節正文、可確認的來源和延伸閱讀。
4. 執行建置和檢查。首頁、搜尋索引與獨立文章頁自動更新。
5. 預覽新內容後，把來源和產物一起提交。

可交給 AI 的指令範例。

> 請先讀 AGENTS.md。新增「走過一段漂亮回測，怎麼知道只是碰巧」的筆記，使用模板、明列教學假設、查證來源，再建置和檢查。缺少我的個人經驗時請保留為公開文件整理。

## 專案結構

```text
AGENTS.md                 AI 專案規則
README.md                 啟動及新增方法
CHANGELOG.md              實際修改與檢查紀錄
templates/note.md         唯一筆記模板
content/notes/*.md        原始筆記
content/sources.json      來源登記
content/examples.json     每篇的可重算例子
content/observations/     作者提供的原始觀察與限制
content/experiments/      可重現教學輸入
scripts/build.py          靜態頁面產生器
scripts/check.py          內容與產物驗證
scripts/content_lint.py   內容門檻與安全算術
scripts/execution_demo.py 三條本地執行路徑實驗
tests/                    18 項正常與反例測試
assets/                   共用樣式、互動和產生的搜尋索引
notes/*.html              產生的文章頁
index.html                首頁
rules.html                直接由 AGENTS.md 產生的規則頁
.nojekyll                 GitHub Pages 原樣提供靜態檔案
```

## GitHub Pages

本作品以 research-notes/ 子專案放在既有 YongsinSaeyang/wait-duck-coach 儲存庫。網站網址為 https://yongsinsaeyang.github.io/wait-duck-coach/research-notes/ 。clone 整個儲存庫後先 cd research-notes，再執行上述指令。

完整專案提交至 main。根目錄 .github/workflows/research-notes.yml 在 push 和 PR 執行內容檢查、18 項回歸測試、實驗產物核對及重新建置。deploy 工作透過 needs: validate 等待驗證通過。Settings → Pages 的 Source 設為 GitHub Actions。這是部署關卡，儲存庫的合併保護規則另行設定。首頁保留在儲存庫根目錄，研究筆記位於 research-notes/，內部連結使用相對路徑。

AI 協助規則整理、程式與筆記草稿。個人實測觀察僅使用作者先前提供的內容。其餘數字例子都標為教學假設，來源優先採官方文件。

## 如何閱讀檢查結果

用 python3 scripts/check.py --json 可分別取得筆記數、可計算例子、教學標示、來源使用率、內部連結出現次數、唯一檔案數、編輯的單向 related 數與生成回鏈數。連結次數包含重複導覽，不能當作已覆核主張數。

三條執行路徑實驗用明列的教學 CSV，區分未建立模擬單、建立後未成交和已成交的狀態，圖與資料可從對應文章下載。原先的第八週回饋保留在 observations，沒有把教學路徑寫成真實市場發現。
