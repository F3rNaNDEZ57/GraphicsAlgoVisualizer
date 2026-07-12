from algoviz.theme import (
    BUILTIN_THEMES,
    DARK,
    LIGHT,
    array_kind_color,
    graph_state_color,
    load_theme,
)


def test_builtin_themes_are_distinct_and_named():
    assert DARK.name == "dark"
    assert LIGHT.name == "light"
    assert DARK.bg != LIGHT.bg
    assert BUILTIN_THEMES["dark"] is DARK
    assert BUILTIN_THEMES["light"] is LIGHT


def test_graph_state_color_maps_known_and_unknown_states():
    assert graph_state_color(DARK, "start") == DARK.graph_start
    assert graph_state_color(DARK, "path") == DARK.graph_path
    assert graph_state_color(DARK, "__nonsense__") == DARK.graph_default


def test_array_kind_color_maps_known_and_unknown_kinds():
    assert array_kind_color(DARK, "compare") == DARK.array_compare
    assert array_kind_color(DARK, "swap") == DARK.array_swap
    assert array_kind_color(DARK, "write") == DARK.array_write
    assert array_kind_color(DARK, "__nonsense__") == DARK.array_bar


def test_load_theme_missing_file_returns_builtin(tmp_path):
    theme = load_theme("dark", path=tmp_path / "does-not-exist.toml")
    assert theme == DARK


def test_load_theme_malformed_file_falls_back_to_builtin(tmp_path):
    bad = tmp_path / "theme.toml"
    bad.write_text("not [valid toml", encoding="utf-8")
    theme = load_theme("dark", path=bad)
    assert theme == DARK


def test_load_theme_applies_valid_overrides(tmp_path):
    path = tmp_path / "theme.toml"
    path.write_text('[theme]\naccent = "#ff00ff"\narray_bar = "#123456"\n', encoding="utf-8")
    theme = load_theme("dark", path=path)
    assert theme.accent == "#ff00ff"
    assert theme.array_bar == "#123456"
    # everything else still comes from the base theme
    assert theme.grid_background == DARK.grid_background
    assert theme.name == "dark"


def test_load_theme_ignores_unknown_keys(tmp_path):
    path = tmp_path / "theme.toml"
    path.write_text('[theme]\nnot_a_real_field = "nope"\n', encoding="utf-8")
    theme = load_theme("dark", path=path)
    assert theme == DARK
