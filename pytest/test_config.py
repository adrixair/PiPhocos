from config import Config
import logging


def test_template_config_is_readable():
    cfg = Config("templates/config.yml")
    assert cfg is not None
    assert cfg.log_level is logging.INFO
    assert cfg.config_data["time_zone"] == "Europe/Paris"
    assert cfg.config_data["device"]["type"] == "Phocos"
    assert cfg.config_data["phocos"]["unit"] == 0
    assert cfg.config_data["server"]["public_host"] == "localhost"
    assert cfg.config_data["diagnostics"]["enabled"] is False
    assert cfg.config_data["tempo"]["enabled"] is True
    assert cfg.config_data["instance"]["name"] == "PiPhocos"
