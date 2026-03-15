#!/bin/bash
# ============================================
# IchthyoCure 自動スリープスクリプト
# キュレーション完了後にMacをスリープさせる
# ============================================

LOG_FILE="/Users/naoya/.gemini/antigravity/scratch/sales-copilot/.claude/worktrees/peaceful-bhabha/backend/curation.log"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 自動スリープ実行 =====" >> "$LOG_FILE"

# Macをスリープさせる
osascript -e 'tell application "System Events" to sleep'
