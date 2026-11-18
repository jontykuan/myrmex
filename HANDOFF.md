# `myrmex` — Handoff & Architecture Specification

> **Status**: Architecture & Experiment Design Finalized  
> **Repo / Project Slug**: `myrmex`  
> **Target Environment**: Local (`agy` Architect Terminal) + Cloud/Colab (`myrmex-runner` Headless Workers)

---

## 1. 核心定位與問題定義

`myrmex`（古希臘語：螞蟻）是一個**去官僚化、基於 Stigmergy（費洛蒙間接協調）的 Multi-Agent 編碼系統**。

### 解決傳統 MAS 的官僚負面影響
1. **消除對話膨脹（Token Explosion）**：移除 Agent 間的直接聊天（Message-passing）與階層式匯報鏈，避免 Context Window 被無效協調對話填滿。
2. **消除同步阻塞（Latency Bottleneck）**：無狀態工蟻（Stateless Workers）不等待上下游回覆，直接感知環境狀態觸發動作。
3. **消除狀態漂移（State Drift）**：程式碼庫、Git 狀態、測試結果與靜態檢查即唯一真實來源（SSOT），不再依賴 Agent 口頭宣稱「已完成」。

### 維持工程紀律（Matt Pocock & Uncle Bob 原則）
去中心化僅指**任務調度無官僚**，程式碼品質由**環境的確定性物理法則（不可繞過的靜態閘門）**強制執行：
* **Matt Pocock 原則**：
  * 嚴格型別檢查（禁止 `as`、`any`、`@ts-ignore`）作為費洛蒙感測器，型別錯誤自動產生高濃度修復信號。
  * 垂直切片（Tracer Bullets，單一切片 ≤ 20 LOC 增量）作為任務目標點，透過 Deep Modules 窄介面（Seams）整合。
* **Uncle Bob 原則**：
  * **Red（釋放費洛蒙）**：寫入失敗測試即向環境釋放需求信號。
  * **Green（消耗費洛蒙）**：工蟻在隔離 Worktree 實作最小程式碼轉綠。
  * **Refactor（異味費洛蒙）**：合併前執行靜態 AST 度量（函式長度、圈複雜度、SOLID 依賴方向），超標則阻止完成並釋放重構信號。

---

## 2. 系統架構與落地形態

採用 **「MCP 為骨架 + Skills 為神經 + Headless Runner 為執行體 + `agy` 為控制終端」** 的四層解耦架構：

```text
[ agy IDE (Architect Terminal) ]  <-- Entry 釐清、規格凍結、異常人工接管
               │
               ▼ (讀寫同一個共享環境)
[ myrmex-mcp (State & Physics) ]  <-- 費洛蒙壓力場(SQLite+TTL)、原子鎖、Worktree 隔離、確定性合併閘門
               ▲
               │ (感知 / 領取 / 提交候選變更)
[ myrmex-runner (Headless Ants) ] <-- 無狀態 Worker 進程 (可跑於本機或 Colab/雲端容器)
  └─ 載入 myrmex-skills           <-- 單隻工蟻的 TDD 與 Clean Code 行為準則
```

### 各組件職責
1. **`myrmex-mcp`（核心狀態與物理法則層）**：
   * `sense_field`：回傳當前環境的壓力場（待處理紅燈、型別錯誤、可用切片、熱點排斥區）。
   * `claim_slice`：對目標切片與相關檔案施加原子鎖與 **TTL（Time-To-Live）時間衰減**，防止併發修改衝突與 Worker 崩潰造成的永久死鎖。
   * `emit_pheromone`：寫入/更新狀態標記（如 `conflict`、`refactor-needed`、`blocked`）。
   * `verify_and_merge`：在獨立 `git worktree` 執行模擬合併 + Typecheck + Linter + 單元測試；通過才原子合併至目標分支並清除費洛蒙，失敗則回滾並留下負向費洛蒙。
2. **`myrmex-skills`（行為規範層）**：精簡的 Prompt 協議，定義工蟻如何閱讀局部環境、遵守 TDD 循環與型別邊界，不負責狀態管理。
3. **`myrmex-runner`（無頭執行層）**：獨立於 IDE 的事件驅動迴圈，具備**無狀態與冪等性（Idempotent）**。即便運行在易斷線的環境（如 Google Colab），容器重啟後仍可從外部 Git 與 DB 接續未完成工作。
4. **`agy`（架構師終端）**：保留用於初期 `mnb-entry` / `mnb-grill` 規格釐清、觀測費洛蒙熱點，以及當異常濃度過高時由人類直接接管 Worktree 除錯。

---

## 3. 學術基礎與開源實作參考

### 學界研究（arXiv）
* **SwarmWorld** *(Pal, Wang, & Buehler / MIT, 2026)*：數百個無直接對話管道、無預先角色的同質 LLM Agent 僅透過修改共享環境與留下痕跡（Stigmergy），自發分化出探索者、建造者與維護者並達成技術累積。
* **Emergent Coordination via Pressure Fields and Temporal Decay** *(2026)*：以環境壓力場與時間衰減機制取代對話樹，證明 LLM 可透過 In-context Learning 將環境狀態作為費洛蒙記憶，大幅降低通訊成本。
* **SwarmSys** *(Li et al., 2025)*：結合自適應 Agent 畫像、向量匹配與受費洛蒙啟發的強化機制，在無全域監督下達成去中心化任務收斂。
* **AMRO / AMRO-S** *(2026)* & **PhGPO** *(2026)*：分別將蟻群演算法（ACO）與自適應衰減費洛蒙用於多 Agent LLM 任務路由，以及將驗證成功的工具軌跡蒸餾為費洛蒙轉移先驗（Transition Priors）。

### GitHub 與工程實作方向
* **Pressure-Field Coordination Benchmarks**：將對話式 MAS 與基於壓力場/時間衰減的 Stigmergy 架構進行對比實作，在解決率與 Token 經濟性上呈現顯著優勢。
* **無狀態編碼 Agent 路由（如 `PheroPath` 及 SQLite 狀態引擎）**：利用檔案系統變更、SQLite 狀態表、Git Diff 軌跡與 CI 日誌作為數位費洛蒙，驅動非同步的 Coder / Tester / Reviewer 管線。
* **認知與確定性引擎解耦**：將 LLM 認知（提出變更）與確定性執行引擎（編譯、測試、Git 合併後果）徹底分離。

---

## 4. A/B 對照測試方案（`mnb` 工作流 vs. `myrmex` 蟻群模式）

### 實驗設計（控制變因）
1. **基準任務集**：挑選 5–10 個真實歷史任務（涵蓋單檔 Bug Fix、跨模組 Feature、重構），凍結於相同起始 `base-commit`。
2. **模型一致性**：對照組與實驗組必須使用**相同的底層商用 LLM API**，避免 Colab 本地開源模型與 API 模型的智商差異干擾工作流效能評估。
3. **隱藏驗收測試（Holdout Suite）**：預先撰寫不對開發 Agent 公開的整合與邊界測試，作為最終正確率的客觀裁判。
4. **雙軌執行**：
   * **對照組 (`exp/mnb-baseline`)**：在 `agy` 端以現行 `mnb` 技能執行。
   * **實驗組 (`exp/myrmex-colony`)**：在 Google Colab 單一實例內拉起多個 `myrmex-runner` 進程（共享本機磁碟與 SQLite/Git Worktree，零網路延遲），消耗同一個 `base-commit`。

### 指標採集方法

| 指標維度 | 採集方式 | 核心計算指標 |
| :--- | :--- | :--- |
| **Token 消耗** | 透過 API Proxy（如 LiteLLM）或 Runner SDK 攔截回傳的 `usage` 物件，綁定 `experiment_id` 與 `task_id` 寫入資料庫。 | `Tokens per Solved Task`（僅計入通過 Holdout 的成功任務） |
| **步數 (Steps)** | **對照組**：解析 `transcript.jsonl` 中 `PLANNER_RESPONSE` 總數（含 Subagent）。<br>**實驗組**：由 `myrmex-runner` 記錄每次 Wake-up 到結束的迭代次數。 | 平均步數 / 任務、溝通交接步數佔比 |
| **Tool 呼叫數** | **對照組**：解析 `transcript.jsonl` 的 `tool_calls` 陣列長度。<br>**實驗組**：在 `myrmex-mcp` Handler 外包一層遙測 Decorator 自動記數。 | 總呼叫數、無效溝通/狀態查詢類呼叫佔比 |
| **正確率與品質** | 合併後執行 Holdout 驗收測試、Typecheck（零 `as`）、Linter 與 AST 複雜度檢查。 | `Holdout Pass Rate (%)`、`First-pass Gate Rate (%)` |
| **工程摩擦與速度** | 由 Git 與 Runner 事件日誌統計。 | `Merge 衝突次數`、`Worktree 回滾次數`、`Wall-clock 總耗時` |

---

## 5. 下一步行動清單（Next Steps）

- [ ] **Step 1**：初始化 `myrmex` GitHub 倉庫與本地目錄結構（`packages/mcp`、`packages/runner`、`skills/`、`benchmarks/`）。
- [ ] **Step 2**：實作最小可行 `myrmex-mcp`（SQLite 費洛蒙表 + TTL 衰減查詢 + Git Worktree 建立與確定性 Gate 腳本）。
- [ ] **Step 3**：撰寫極簡版工蟻技能（`myrmex-worker/SKILL.md`），僅包含感測 → 領取 → TDD → 提交四步驟。
- [ ] **Step 4**：在 `agy` 選定第一個基準任務產出 `base-commit` 與 Holdout 測試，分別於 `agy` 與 Colab 啟動雙軌 A/B 實驗並匯出遙測數據。
