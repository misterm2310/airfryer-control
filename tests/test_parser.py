"""Tests für den Übersetzer der Cloud-Antworten (ohne Home Assistant)."""

from custom_components.cosori_bedienung.const import (
    STATE_COOKING,
    STATE_FINISHED,
    STATE_PAUSED,
    STATE_PREHEAT,
    STATE_STANDBY,
    STATE_UNKNOWN,
    TIME_UNIT_AUTO,
    TIME_UNIT_MINUTES,
    TIME_UNIT_SECONDS,
)
from custom_components.cosori_bedienung.parser import (
    guess_unit,
    map_status,
    parse,
    zone_view,
    zones_for_device,
)
from custom_components.cosori_bedienung.senden import build_variants


def test_status_mapping():
    assert map_status("cooking") == STATE_COOKING
    assert map_status("cookStop") == STATE_PAUSED
    assert map_status("cookEnd") == STATE_FINISHED
    assert map_status("heating") == STATE_PREHEAT
    assert map_status("standby") == STATE_STANDBY
    assert map_status("irgendwas") == STATE_UNKNOWN
    assert map_status(None) == STATE_UNKNOWN


def test_unit_guess():
    assert guess_unit("CAF-TF101S-AEUR", TIME_UNIT_AUTO) == TIME_UNIT_SECONDS
    assert guess_unit("CS158-AF", TIME_UNIT_AUTO) == TIME_UNIT_MINUTES
    assert guess_unit("CAF-TF101S", TIME_UNIT_MINUTES) == TIME_UNIT_MINUTES


def test_twinfry_two_zones():
    multi = {
        "statusList": [
            {"chamber": 1, "cookStatus": "cooking", "cookSetTime": 900, "cookLastTime": 400,
             "cookTemp": 200, "currentTemp": 185, "mode": "AirFry"},
            {"chamber": 2, "cookStatus": "cooking", "cookSetTime": 600, "cookLastTime": 650,
             "cookTemp": 180, "mode": "Roast"},
        ],
        "totalTimeRemaining": 650,
    }
    state = parse({"cookStatus": "cooking"}, multi, TIME_UNIT_SECONDS)
    assert state.status == STATE_COOKING
    assert state.remaining_s == 650
    assert state.zones[1].remaining_s == 400
    assert state.zones[1].set_temp == 200
    assert state.zones[1].current_temp == 185
    assert state.zones[2].mode == "Roast"
    assert state.active
    assert zones_for_device(state, multizone=True) == [1, 2]


def test_whole_drawer_counts_as_zone_one():
    multi = {"statusList": [{"chamber": 3, "cookStatus": "cooking", "cookLastTime": 120}]}
    state = parse({}, multi, TIME_UNIT_SECONDS)
    assert zone_view(state, 1).remaining_s == 120
    assert zone_view(state, 2) is None
    assert state.status == STATE_COOKING


def test_finished_has_no_remaining_time():
    multi = {"statusList": [{"chamber": 1, "cookStatus": "cookEnd", "cookLastTime": 30}]}
    state = parse({"cookStatus": "cookEnd"}, multi, TIME_UNIT_SECONDS)
    assert state.status == STATE_FINISHED
    assert state.remaining_s == 0
    assert not state.active


def test_single_chamber_minutes():
    status = {"returnStatus": {"cookStatus": "cooking", "cookLastTime": 7, "cookSetTemp": 180,
                                "currentTemp": 150, "mode": "Chicken", "tempUnit": "c"}}
    state = parse(status, {}, TIME_UNIT_MINUTES)
    assert state.status == STATE_COOKING
    assert state.remaining_s == 420
    assert state.zones[1].set_temp == 180
    assert zones_for_device(state, multizone=False) == []


def test_status_from_zones_when_top_missing():
    multi = {"statusList": [{"chamber": 1, "cookStatus": "cookStop"},
                            {"chamber": 2, "cookStatus": "standby"}]}
    state = parse({}, multi, TIME_UNIT_SECONDS)
    assert state.status == STATE_PAUSED


def test_garbage_does_not_crash():
    state = parse({"foo": [1, 2, {"bar": None}]}, {"x": "y"}, TIME_UNIT_SECONDS)
    assert state.status == STATE_UNKNOWN
    assert state.zones == {}


def test_send_variants_never_start_and_carry_values():
    variants = build_variants("acc", 2, 180, 10, "bake")
    names = [v.name for v in variants]
    assert len(names) == len(set(names)) >= 6
    for v in variants:
        assert v.payload["readyStart"] is False
        assert v.payload["accountId"] == "acc"
    multi = variants[0].payload
    assert multi["cookConfigs"] == [
        {"cookSetTime": 600, "cookTemp": 180, "mode": "Bake", "chamber": 2}
    ]
    assert multi["workChamber"] == 2
