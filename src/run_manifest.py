"""Runnable shipment manifest example."""

from logistics_cost import ShipmentEvent, configure_budget, triage_shipment


def main() -> None:
    configure_budget(10.0, "monthly")
    event = ShipmentEvent(
        shipment_id="SHP-2048",
        status="delivered",
        exception="signature missing",
        proof_of_delivery="pod/SHP-2048.pdf",
    )
    result = triage_shipment(event)
    print({"shipment_id": result.shipment_id, "decision": result.decision, "cost_usd": result.cost_usd})


if __name__ == "__main__":
    main()
