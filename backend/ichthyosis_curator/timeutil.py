"""日本時間（JST）で「今日」を決めるためのユーティリティ

GitHub Actions のランナーは UTC で動く。ワークフローは 22:00 UTC 起動、
つまり JST の翌朝7時に配信されるため、datetime.now() をそのまま使うと
日付も曜日も1日ずれる（JST月曜の朝に届く回は UTC では日曜になる）。

読者は日本にいるので、日付表示・週次まとめの曜日判定・配信履歴の
日付はすべて JST を基準にする。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))


def now_jst() -> datetime:
    return datetime.now(JST)


def today_jst() -> date:
    return now_jst().date()
