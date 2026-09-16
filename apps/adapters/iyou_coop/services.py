from catalog.models import CoffeeProduct


class CoopManifestService:
    """Service to publish the decentralized cooperative manifest for mesh federation."""

    @classmethod
    def get_manifest(cls) -> dict:
        offerings = []
        products = (
            CoffeeProduct.objects.filter(is_active=True)
            .select_related("roast_profile", "lot")
            .order_by("name")
        )

        for p in products:
            lot_data = None
            if p.lot:
                lot_data = {
                    "origin_country": p.lot.origin_country,
                    "region_farm": p.lot.region_farm,
                    "producer_coop": p.lot.producer_coop,
                    "varietal": p.lot.varietal,
                    "altitude_meters": float(p.lot.altitude_meters) if p.lot.altitude_meters else None,
                    "process_method": p.lot.process_method,
                    "harvest_date": p.lot.harvest_date.isoformat() if p.lot.harvest_date else None,
                    "fair_price_paid_usd": str(p.lot.fair_price_paid_usd) if p.lot.fair_price_paid_usd else None,
                }

            roast_data = None
            if p.roast_profile:
                roast_data = {
                    "roast_name": p.roast_profile.roast_name,
                    "roast_level": p.roast_profile.roast_level,
                    "target_drop_temp_f": p.roast_profile.target_drop_temp_f,
                    "development_time_sec": p.roast_profile.development_time_sec,
                }

            tasting_notes = p.roast_profile.tasting_notes if p.roast_profile else p.description

            offerings.append(
                {
                    "id": str(p.id),
                    "name": p.name,
                    "slug": p.slug,
                    "brand_line": p.brand_line,
                    "description": p.description,
                    "tasting_notes": tasting_notes,
                    "roast_profile": roast_data,
                    "origin_lot": lot_data,
                }
            )

        manifest = {
            "coop_name": "Green Bean Coffee Collective",
            "brand_domain": "greenbean.app",
            "established_year": 2017,
            "entity_type": "Worker-Owned Cooperative",
            "governance_model": "Democratic Assembly + Community Participatory Budgeting",
            "participatory_budget_bridge": "iyou_poly",
            "ledger_engine": "iyou_bean",
            "active_locations": [
                {
                    "label": "Store #001 (Flagship)",
                    "curbside_enabled": True,
                    "pos_protocol": "v1",
                }
            ],
            "current_roast_offerings": offerings,
            "sourcing_charter": "Direct trade, ethical price floors, regenerative single-origins.",
        }
        return manifest
