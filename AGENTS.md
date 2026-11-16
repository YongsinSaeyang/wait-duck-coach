# 等等鴨專案導覽

這個儲存庫包含投資決策練習室與可持續擴充的研究筆記。

- 根目錄 index.html 是原先的投資決策練習室。
- 第九週作業位於 research-notes/，其入口為 research-notes/index.html。
- 修改或新增研究筆記前，先讀 research-notes/AGENTS.md、README.md、templates/note.md 和 content/sources.json。
- 進入 research-notes 後，執行 python3 scripts/build.py 和 python3 scripts/check.py。
- 新內容加入 content/notes，首頁、獨立文章和搜尋索引由同一建置程式產生。
- 每次發布將原始內容、來源登記與產物一起提交。
- 開發過程請保留可核對的修改紀錄、教學假設和來源。

完整規則請見 [研究筆記工作手冊](research-notes/AGENTS.md)。
