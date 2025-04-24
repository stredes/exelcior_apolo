from app.utils import helpers

def test_generate_timestamp():
    ts = helpers.generate_timestamp()
    assert isinstance(ts, str)
    assert len(ts) > 0
