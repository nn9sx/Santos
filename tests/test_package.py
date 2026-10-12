import importlib.metadata


def test_pitch_flap_console_script_is_installed():
    scripts = importlib.metadata.entry_points(group="console_scripts")
    matches = [ep for ep in scripts if ep.name == "pitch-flap"]
    assert len(matches) == 1
    assert matches[0].value == "santos:main"
