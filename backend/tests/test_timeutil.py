"""JST基準の日付判定のテスト（CIランナーがUTCで動くための対策）"""

from datetime import datetime, timezone

from ichthyosis_curator.delivery import policy
from ichthyosis_curator.timeutil import JST, today_jst


def test_JSTはUTC9時間先():
    assert JST.utcoffset(None).total_seconds() == 9 * 3600


def test_UTC日曜22時はJSTでは月曜(monkeypatch):
    """ワークフローは 22:00 UTC 起動。JSTでは翌朝7時なので月曜扱いにしたい"""
    utc_sunday_night = datetime(2026, 8, 23, 22, 30, tzinfo=timezone.utc)

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return utc_sunday_night.astimezone(tz) if tz else utc_sunday_night

    monkeypatch.setattr("ichthyosis_curator.timeutil.datetime", _FixedDatetime)

    assert utc_sunday_night.weekday() == 6  # UTCでは日曜
    assert today_jst().weekday() == 0  # JSTでは月曜
    assert policy.should_send_weekly() is True
