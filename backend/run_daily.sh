#!/bin/bash
# ============================================
# IchthyoCure 毎朝自動キュレーション & デプロイ
# ============================================

# プロジェクトのパス
PROJECT_DIR="/Users/naoya/.gemini/antigravity/scratch/sales-copilot/.claude/worktrees/peaceful-bhabha"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# Pythonのパス
PYTHON="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"

# ログファイル（実行記録が残ります）
LOG_FILE="$BACKEND_DIR/curation.log"

# Git設定
export PATH="/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:$PATH"

# ===== Step 1: キュレーション実行 =====
cd "$BACKEND_DIR"
echo "===== $(date '+%Y-%m-%d %H:%M:%S') キュレーション開始 =====" >> "$LOG_FILE"
PYTHONPATH="$BACKEND_DIR" "$PYTHON" -m ichthyosis_curator >> "$LOG_FILE" 2>&1
echo "===== $(date '+%Y-%m-%d %H:%M:%S') キュレーション完了 =====" >> "$LOG_FILE"

# ===== Step 2: 静的JSONエクスポート =====
echo "===== $(date '+%Y-%m-%d %H:%M:%S') JSONエクスポート開始 =====" >> "$LOG_FILE"
PYTHONPATH="$BACKEND_DIR" "$PYTHON" -m ichthyosis_curator --export "$FRONTEND_DIR/public/data" >> "$LOG_FILE" 2>&1
echo "===== $(date '+%Y-%m-%d %H:%M:%S') JSONエクスポート完了 =====" >> "$LOG_FILE"

# ===== Step 3: GitHubにプッシュ（Vercel自動デプロイ） =====
echo "===== $(date '+%Y-%m-%d %H:%M:%S') GitHubプッシュ開始 =====" >> "$LOG_FILE"
cd "$PROJECT_DIR"
git add frontend/public/data/ >> "$LOG_FILE" 2>&1
git commit -m "daily: $(date '+%Y-%m-%d') curated articles" >> "$LOG_FILE" 2>&1
git push origin main >> "$LOG_FILE" 2>&1
echo "===== $(date '+%Y-%m-%d %H:%M:%S') GitHubプッシュ完了 =====" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
