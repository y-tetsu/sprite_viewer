import pytest
import os
from unittest import mock
from sprite_viewer.main import parse_color, parse_size, load_data

def test_parse_color_valid():
    assert parse_color("#ffffff") == (255, 255, 255)
    assert parse_color("#000000") == (0, 0, 0)
    assert parse_color("#123abc") == (18, 58, 188)

def test_parse_color_invalid():
    with pytest.raises(ValueError):
        parse_color("12345")  # 文字数不足
    with pytest.raises(ValueError):
        parse_color("#zzzzzz")  # 不正な16進数

def test_parse_size_valid():
    assert parse_size("800x600") == (800, 600)
    assert parse_size("1024x768") == (1024, 768)

def test_parse_size_invalid():
    with pytest.raises(ValueError):
        parse_size("800*600")
    with pytest.raises(ValueError):
        parse_size("800")

def test_load_data_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_data("nonexistent_file")
