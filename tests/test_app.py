import importlib


def test_import_app():
    mod = importlib.import_module('app')
    assert hasattr(mod, 'main')
