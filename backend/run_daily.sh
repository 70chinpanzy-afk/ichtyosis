#!/bin/bash
# ============================================
# IchthyoCure 毎朝自動キュレーションスクリプト
# ============================================

# プロジェクトのパス
PROJECT_DIR="/Users/naoya/.gemini/antigravity/scratch/sales-copilot/.claude/worktrees/peaceful-bhabha/backend"

# Pythonのパス
PYTHON="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"

# ログファイル（実行記録が残ります）
LOG_FILE="$PROJECT_DIR/curation.log"

# 実行
cd "$PROJECT_DIR"
echo "===== $(date '+%Y-%m-%d %H:%M:%S') キュレーション開始 =====" >> "$LOG_FILE"
PYTHONPATH="$PROJECT_DIR" "$PYTHON" -m ichthyosis_curator >> "$LOG_FILE" 2>&1
echo "===== $(date '+%Y-%m-%d %H:%M:%S') キュレーション完了 =====" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
