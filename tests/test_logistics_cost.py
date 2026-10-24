from logistics_cost import ShipmentEvent, triage_shipment


class FakeMessage:
    content = "Review the missing signature."


class FakeChoice:
    message = FakeMessage()


class FakeParsed:
    choices = [FakeChoice()]


class FakeResponse:
    headers = {"x-infrai-cost-usd": "0.001"}

    def parse(self):
        return FakeParsed()


class FakeCompletions:
    def create(self, **kwargs):
        assert kwargs["model"] == "auto"
        return FakeResponse()


class FakeChat:
    completions = type("Completions", (), {"with_raw_response": FakeCompletions()})()


class FakeClient:
    chat = FakeChat()


def test_exception_routes_shipment_to_review():
    event = ShipmentEvent("SHP-2048", "delivered", "signature missing", "pod/SHP-2048.pdf")
    result = triage_shipment(event, FakeClient())
    assert result.decision == "review"
    assert result.cost_usd == "0.001"
