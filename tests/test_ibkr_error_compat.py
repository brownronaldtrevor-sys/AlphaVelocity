from alpha_velocity.broker.ibkr import IBKRApp


class AuditCapture:
    def __init__(self):
        self.events = []

    def record(self, event_type, payload):
        self.events.append((event_type, payload))


def make_app():
    app = object.__new__(IBKRApp)
    app.audit = AuditCapture()
    return app


def test_error_callback_api_1033_signature():
    app = make_app()
    app.error(7, 1720000000, 2104, "Market data farm connection is OK", "")
    payload = app.audit.events[-1][1]
    assert payload["error_time"] == 1720000000
    assert payload["code"] == 2104


def test_error_callback_legacy_signature():
    app = make_app()
    app.error(7, 2104, "Market data farm connection is OK", "")
    payload = app.audit.events[-1][1]
    assert payload["error_time"] is None
    assert payload["code"] == 2104
