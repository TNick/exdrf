"""Tests for cmp widget generation: file emission, API export, plugin hook."""

import os


def test_creator_emits_cmp_file():
    """Creator widget list includes {res_snake}_cmp.py with cmp.py.j2 template."""
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    creator_path = os.path.join(
        pkg_dir,
        "exdrf_gen_al2qt",
        "creator.py",
    )
    assert os.path.isfile(creator_path)
    content = open(creator_path, encoding="utf-8").read()
    assert '"{res_snake}_cmp.py"' in content
    assert '"c/m/w/cmp.py.j2"' in content


def test_cmp_template_exists():
    """Template file c/m/w/cmp.py.j2 exists and contains expected patterns."""
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_path = os.path.join(
        pkg_dir,
        "exdrf_gen_al2qt",
        "al2qt_templates",
        "c",
        "m",
        "w",
        "cmp.py.j2",
    )
    assert os.path.isfile(template_path)
    content = open(template_path, encoding="utf-8").read()
    assert "RecordComparatorBase" in content
    assert "Qt{{ ResPascal }}Cmp" in content
    assert (
        "RecordToNodeAdapter" in content or "FieldAwareRecordAdapter" in content
    )
    assert "safe_hook_call" in content
    assert "cmp_created" in content


def test_api_template_exports_cmp():
    """c/m/api.py.j2 exports Qt{ResPascal}Cmp from cmp module."""
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    api_path = os.path.join(
        pkg_dir,
        "exdrf_gen_al2qt",
        "al2qt_templates",
        "c",
        "m",
        "api.py.j2",
    )
    assert os.path.isfile(api_path)
    content = open(api_path, encoding="utf-8").read()
    assert "_cmp" in content
    assert "Cmp" in content
    assert "Qt{{ ResPascal }}Cmp" in content


def test_plugins_template_has_cmp_hook():
    """plugins.py.j2 defines {res_snake}_cmp_created hook and TYPE_CHECKING Cmp."""
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plugins_path = os.path.join(
        pkg_dir,
        "exdrf_gen_al2qt",
        "al2qt_templates",
        "plugins.py.j2",
    )
    assert os.path.isfile(plugins_path)
    content = open(plugins_path, encoding="utf-8").read()
    assert "cmp_created" in content
    assert "Cmp" in content
