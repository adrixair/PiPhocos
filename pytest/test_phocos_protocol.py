from phocos_protocol import (
    SEMANTICS_DERIVED,
    SEMANTICS_EXACT,
    build_command_frame,
    parse_qpigs_payload,
    parse_qpgs_payload,
    parse_qpiri_payload,
)


def test_build_command_frame_for_qpgs0():
    assert build_command_frame("QPGS0").hex().upper() == "51504753303FDA0D"


def test_parse_qpgs_payload_live_sample():
    parsed = parse_qpgs_payload(
        "(0 TEST-SERIAL-0001 L 00 234.4 49.96 234.4 49.96 0304 0260 006 55.2 002 100 282.2 002 00304 00260 005 11100010 0 3 080 080 60 01.5 000"
    )
    assert parsed["serial_number"] == "TEST-SERIAL-0001"
    assert parsed["operation_mode"] == "Grid / Line mode"
    assert parsed["fault"] == "No fault"
    assert parsed["ac_output_active_power_w"] == 260
    assert parsed["battery_voltage_v"] == 55.2
    assert parsed["pv_power_semantics"] == SEMANTICS_DERIVED
    assert parsed["inverter_status"]["mppt_active"] is True
    assert parsed["inverter_status"]["solar_charging_on"] is True


def test_parse_qpigs_payload_live_sample():
    parsed = parse_qpigs_payload(
        "(236.8 50.0 236.8 50.0 0284 0245 005 427 55.30 002 100 0039 01.5 283.2 00.00 00000 00010110 00 00 00430 110 0 01 0000"
    )
    assert parsed["ac_output_active_power_w"] == 245
    assert parsed["battery_state_of_charge_percent"] == 100
    assert parsed["pv_input_voltage_v"] == 283.2
    assert parsed["pv_power_w"] == 430
    assert parsed["pv_power_semantics"] == SEMANTICS_EXACT
    assert parsed["solar_feed_to_grid_enabled"] is False
    assert parsed["solar_feed_to_grid_power_w"] == 0


def test_parse_qpiri_payload_live_sample():
    parsed = parse_qpiri_payload(
        "(230.0 21.7 230.0 50.0 21.7 5000 5000 48.0 48.0 44.0 57.6 55.2 0 60 080 0 1 3 9 00 0 0 54.0 0 1 120 0 000 54.7"
    )
    assert parsed["ac_output_rating_active_power_w"] == 5000
    assert parsed["battery_float_voltage_v"] == 55.2
    assert parsed["max_ac_charging_current_a"] == 60
    assert parsed["max_charging_current_a"] == 80
    assert parsed["charger_source_priority_code"] == "3"
    assert parsed["charger_source_priority"] == "Solar only"
    assert parsed["battery_redischarge_voltage_v"] == 54.0
