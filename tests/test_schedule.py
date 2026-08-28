from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from cuesheet.api.domain.cue.cue import Cue
from cuesheet.api.domain.cue.seq import Seq
from cuesheet.api.domain.cue.cue_title import CueTitle
from cuesheet.api.domain.cue.planned_sec import PlannedSec
from cuesheet.api.domain.cuesheet.cuesheet import Cuesheet
from cuesheet.api.domain.cuesheet.cuesheet_title import CuesheetTitle
from cuesheet.api.domain.cuesheet.scheduled_at import ScheduledAt
from cuesheet.api.domain.cuesheet.invite_token import InviteToken
from cuesheet.api.domain.cuesheet.cue_started_at import CueStartedAt

from cuesheet.api.usecase.cuesheet_get import _schedule


# #
# fixture

BASE = datetime(2026, 8, 28, 19, 0, tzinfo=timezone.utc)


def _cuesheet() -> Cuesheet:
    return Cuesheet.new(
        owner_user_id=uuid4(),
        title=CuesheetTitle.from_str("정기공연"),
        scheduled_at=ScheduledAt.from_datetime(BASE),
        manager_token=InviteToken.from_str("m"),
        viewer_token=InviteToken.from_str("v"),
    )


def _cues() -> list[Cue]:
    cuesheet_id = uuid4()
    return [
        Cue.new(
            cuesheet_id=cuesheet_id,
            seq=Seq.from_int(index),
            title=CueTitle.from_str(f"순서 {index}"),
            planned_sec=PlannedSec.from_int(sec),
        )
        for index, sec in enumerate([300, 600, 1200], start=1)
    ]


# #
# schedule

def test_ready_uses_scheduled_at():
    cues = _cues()
    scheduled = _schedule(cuesheet=_cuesheet(), cues=cues, now=BASE - timedelta(minutes=5))

    assert scheduled["delay_sec"] == 0
    assert scheduled["eta"][str(cues[0].id)] == BASE.isoformat()
    assert scheduled["eta"][str(cues[1].id)] == (BASE + timedelta(seconds=300)).isoformat()
    assert scheduled["eta"][str(cues[2].id)] == (BASE + timedelta(seconds=900)).isoformat()


def test_running_on_time_uses_cue_started_at():
    cues = _cues()
    started = BASE + timedelta(seconds=60)
    running = _cuesheet().start(cue_id=cues[0].id, at=CueStartedAt.from_datetime(started))

    # 1분 경과, 계획 5분 — 아직 지연 아님
    scheduled = _schedule(cuesheet=running, cues=cues, now=started + timedelta(seconds=60))

    assert scheduled["delay_sec"] == 0
    assert scheduled["eta"][str(cues[0].id)] == started.isoformat()
    assert scheduled["eta"][str(cues[1].id)] == (started + timedelta(seconds=300)).isoformat()


def test_delay_pushes_every_later_eta():
    cues = _cues()
    started = BASE
    running = _cuesheet().start(cue_id=cues[0].id, at=CueStartedAt.from_datetime(started))

    # 계획 300초인데 480초 경과 → 180초 지연
    scheduled = _schedule(cuesheet=running, cues=cues, now=started + timedelta(seconds=480))

    assert scheduled["delay_sec"] == 180
    assert scheduled["eta"][str(cues[1].id)] == (started + timedelta(seconds=480)).isoformat()
    assert scheduled["eta"][str(cues[2].id)] == (started + timedelta(seconds=1080)).isoformat()


def test_passed_cues_have_no_eta():
    cues = _cues()
    started = BASE
    running = _cuesheet().advance(next_cue_id=cues[1].id, at=CueStartedAt.from_datetime(started))

    scheduled = _schedule(cuesheet=running, cues=cues, now=started)

    assert scheduled["eta"][str(cues[0].id)] is None
    assert scheduled["eta"][str(cues[1].id)] == started.isoformat()


# #
# transition

def test_rewind_restores_previous_cue_once():
    cues = _cues()
    at = CueStartedAt.from_datetime(BASE)

    running = _cuesheet().start(cue_id=cues[0].id, at=at)
    advanced = running.advance(next_cue_id=cues[1].id, at=at)
    rewound = advanced.rewind(at=at)

    assert rewound.current_cue_id == cues[0].id
    # 1단계만 — 되돌린 뒤엔 더 되돌릴 것이 없다
    assert rewound.prev_cue_id is None


def test_state_reflects_lifecycle():
    cues = _cues()
    at = CueStartedAt.from_datetime(BASE)

    ready = _cuesheet()
    assert ready.state() == "ready"
    assert ready.start(cue_id=cues[0].id, at=at).state() == "running"
