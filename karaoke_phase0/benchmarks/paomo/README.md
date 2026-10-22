# 泡沫：第一輪 Forced Alignment A/B 資料

- `line0.wav`：全曲 8–17 秒；`line3.wav`：30–38 秒；44.1 kHz stereo PCM16，均來自使用者提供的 Demucs `vocals.wav`。
- 同名 `.txt`：使用者提供的正確歌詞，UTF-8。
- `whisperx_baseline.csv`：已執行的 WhisperX 逐字結果，**全曲秒數**。
- `ground_truth_template.csv`：人工標註用空白欄位，**不要用 WhisperX 結果當真值**。

## 執行順序

1. 用音訊編輯器聆聽兩個 WAV，填寫 ground_truth_template.csv 每個字的開始與結束秒數（全曲秒數）。
2. 在獨立環境安裝 MFA 並取得**授權相容**的中文 acoustic model 與 pronunciation dictionary；先檢查詞典是否涵蓋歌詞及繁體字。MFA 的模型/詞典尚未在此環境安裝或驗證。
3. MFA 通常需將文字按模型詞典分詞並可能轉換繁體字；保留原歌詞作為最終顯示文字。輸出 TextGrid 後將局部時間加 8 或 30 秒，並將音素/詞邊界映射至中文字。
4. 比較兩種模型與人工標註的起點/終點誤差（MAE、P90）、缺字數、異常短時間數與運算時間。沒有 Ground Truth 前不可聲稱 MFA 比 WhisperX 準。

**注意**：本 ZIP 是 A/B 測試資料與評估框架，**不是已完成 MFA 推論**。不得把此測試資料覆蓋原本的 songs/ 或 lyrics_timeline.json。
