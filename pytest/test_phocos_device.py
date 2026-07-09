from collections import Counter
from types import SimpleNamespace

from devices.Phocos import Phocos


class FakeSerial:
    is_open = True

    def close(self):
        self.is_open = False


def _config(interval_s=1, qpigs_interval_s=3, max_cached_power_age_s=12.0):
    return SimpleNamespace(
        config_data={
            "phocos": {
                "serial_port": "/dev/test",
                "unit": 0,
                "timeout_s": 2.0,
                "enable_pi30_probe": True,
                "verbose_protocol_logging": False,
                "qpigs_interval_s": qpigs_interval_s,
                "warning_interval_s": 240.0,
                "static_refresh_interval_s": 86400.0,
                "max_cached_power_age_s": max_cached_power_age_s,
            },
            "grabber": {"interval_s": interval_s},
        }
    )


def _fake_result(command):
    name = "QPGS0" if command.startswith("QPGS") else command
    parsed = {"command": name, "field_count": 1}
    if name == "QPI":
        parsed["protocol_id"] = "PI30"
    elif name == "QPGS0":
        parsed.update(
            {
                "pv_power_w": 100.0,
                "pv_power_semantics": "derived",
                "ac_output_active_power_w": 50.0,
            }
        )
    elif name == "QPIGS":
        parsed.update(
            {
                "pv_power_w": 120,
                "pv_power_semantics": "exact",
                "solar_feed_to_grid_power_w": 0,
            }
        )
    elif name == "QID":
        parsed["device_id"] = "TEST"
    elif name == "QPIWS":
        parsed["warning_bitmap"] = "0"
        parsed["warning_bits"] = {"active_bits": []}
    elif name == "QFLAG":
        parsed["flags"] = ""
    elif name == "QPIRI":
        parsed["output_source_priority"] = "SBU"
    return {
        "command": name,
        "request_hex": "",
        "response_hex": "",
        "payload_ascii": "()",
        "crc_ok": True,
        "parsed": parsed,
    }


def test_phocos_probe_seeds_extension_caches_without_duplicate_reads(monkeypatch):
    device = Phocos(_config(interval_s=1, qpigs_interval_s=3))
    counts = Counter()
    ports = []

    def fake_open_port():
        port = FakeSerial()
        ports.append(port)
        return port

    def fake_read_command(_ser, command):
        name = "QPGS0" if command.startswith("QPGS") else command
        counts[name] += 1
        return _fake_result(command)

    monkeypatch.setattr(device, "_open_port", fake_open_port)
    monkeypatch.setattr(device, "_read_command", fake_read_command)

    first = device.poll()
    second = device.poll()

    assert len(ports) == 1
    assert counts["QMOD"] == 0
    assert counts["QPI"] == 1
    assert counts["QPIGS"] == 1
    assert counts["QPIWS"] == 1
    assert counts["QPIRI"] == 1
    assert counts["QFLAG"] == 1
    assert counts["QID"] == 1
    assert counts["QPGS0"] == 2
    assert first["snapshot"]["pv_power_w"] == 120
    assert first["snapshot"]["pv_power_semantics"] == "exact"
    assert first["snapshot"]["pv_power_derived_w"] == 100.0
    assert second["snapshot"]["pv_power_w"] == 120
    assert second["snapshot"]["pv_power_semantics"] == "cached"
    assert second["snapshot"]["source_freshness"]["QPIGS"] == "cached"
    assert first["capabilities_changed"] is True
    assert second["capabilities_changed"] is False


def test_phocos_qpigs_refresh_follows_configured_cadence(monkeypatch):
    device = Phocos(_config(interval_s=1, qpigs_interval_s=3))
    counts = Counter()

    monkeypatch.setattr(device, "_open_port", lambda: FakeSerial())

    def fake_read_command(_ser, command):
        name = "QPGS0" if command.startswith("QPGS") else command
        counts[name] += 1
        return _fake_result(command)

    monkeypatch.setattr(device, "_read_command", fake_read_command)

    for _ in range(4):
        device.poll()

    assert counts["QPGS0"] == 4
    assert counts["QPIGS"] == 2


def test_phocos_timestamps_snapshot_after_qpgs_read(monkeypatch):
    device = Phocos(_config(interval_s=1, qpigs_interval_s=3))
    device.capabilities = {"QPI": {"supported": True, "protocol_id": "PI30"}}
    device.cached_probe_payloads["QPI"] = {"protocol_id": "PI30"}
    events = []

    monkeypatch.setattr(device, "_open_port", lambda: FakeSerial())

    def fake_read_command(_ser, command):
        name = "QPGS0" if command.startswith("QPGS") else command
        events.append(("read", name))
        return _fake_result(command)

    def fake_now():
        value = f"2026-01-01T00:00:0{len(events)}+00:00"
        events.append(("time", value))
        return value

    monkeypatch.setattr(device, "_read_command", fake_read_command)
    monkeypatch.setattr("devices.Phocos.utc_now_iso", fake_now)

    result = device.poll()

    assert events[0] == ("read", "QPGS0")
    assert events[1][0] == "time"
    assert result["snapshot"]["recorded_at"] == events[1][1]


def test_phocos_does_not_reuse_stale_qpigs_power_fields(monkeypatch):
    device = Phocos(
        _config(
            interval_s=1,
            qpigs_interval_s=3600,
            max_cached_power_age_s=0.1,
        )
    )

    monkeypatch.setattr(device, "_open_port", lambda: FakeSerial())
    monkeypatch.setattr(device, "_read_command", lambda _ser, command: _fake_result(command))

    first = device.poll()
    device.cached_payload_timestamps["QPIGS"] = "2000-01-01T00:00:00+00:00"
    second = device.poll()

    assert first["snapshot"]["pv_power_w"] == 120
    assert first["snapshot"]["solar_feed_to_grid_power_w"] == 0
    assert second["snapshot"]["pv_power_w"] == 100.0
    assert "solar_feed_to_grid_power_w" not in second["snapshot"]
    assert second["snapshot"]["source_freshness"]["QPIGS"] == "stale"


def test_phocos_optional_live_extension_failure_keeps_qpgs_sample(monkeypatch):
    device = Phocos(_config(interval_s=1, qpigs_interval_s=1))
    device.capabilities = {
        "QPI": {"supported": True, "protocol_id": "PI30"},
        "QPIGS": {"supported": True},
    }
    device.cached_probe_payloads["QPI"] = {"protocol_id": "PI30"}

    monkeypatch.setattr(device, "_open_port", lambda: FakeSerial())

    def fake_read_command(_ser, command):
        name = "QPGS0" if command.startswith("QPGS") else command
        if name == "QPIGS":
            raise TimeoutError("timeout")
        return _fake_result(command)

    monkeypatch.setattr(device, "_read_command", fake_read_command)

    result = device.poll()

    assert result["snapshot"]["pv_power_w"] == 100.0
    assert result["snapshot"]["pv_power_semantics"] == "derived"
    assert "solar_feed_to_grid_power_w" not in result["snapshot"]
    assert [frame["command"] for frame in result["raw_frames"]] == ["QPGS0"]
