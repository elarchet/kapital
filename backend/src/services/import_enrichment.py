from __future__ import annotations

from typing import TYPE_CHECKING

from src.services.import_parsers import resolve_config_value

if TYPE_CHECKING:
    from sqlmodel import Session

    from src.services.financial_info import FinancialInfoService


def resolve_enrich_option(enrich_option: str | dict | None, csv_action: str | None, op_type: str | None) -> str:
    # ponytail: Delegated lookup to centralized resolve_config_value helper.
    return resolve_config_value(enrich_option, None, op_type, csv_action, default="when_empty")


async def run_enrichment_pipeline(
    processed_ops: list[dict],
    schema_mappings: dict,
    financial_info_service: FinancialInfoService,
    db: Session,  # noqa: ARG001
) -> None:
    """Run sequential enrichment steps on parsed operations before saving to DB.

    Add future enricher modules by appending them to this list.
    """
    # 1. Asset name enrichment
    enrich_asset_names = schema_mappings.get("enrich_asset_names")
    if enrich_asset_names is None:
        # Fallback to legacy boolean
        legacy = schema_mappings.get("enrich_missing_fields", True)
        enrich_asset_names = "when_empty" if legacy else "never"

    await enrich_asset_names_service(
        processed_ops=processed_ops,
        financial_info_service=financial_info_service,
        enrich_option=enrich_asset_names,
    )


async def enrich_asset_names_service(
    processed_ops: list[dict],
    financial_info_service: FinancialInfoService,
    enrich_option: str | dict,
) -> None:
    """Enrich operations with resolved asset names by querying the profile of their ticker symbols."""
    ticker_name_cache: dict[str, str | None] = {}
    for op in processed_ops:
        csv_action = op.get("csv_action")
        op_type = op.get("op_type")
        opt = resolve_enrich_option(enrich_option, csv_action, op_type)
        if opt == "never":
            continue

        should_enrich = (opt == "always") or (not op.get("name_was_set"))
        if should_enrich and op.get("ticker"):
            ticker = op["ticker"]
            if ticker not in ticker_name_cache:
                try:
                    profile = await financial_info_service.get_profile(ticker)
                    if profile and profile.name:
                        ticker_name_cache[ticker] = profile.name
                    else:
                        ticker_name_cache[ticker] = None
                except Exception:  # noqa: BLE001
                    ticker_name_cache[ticker] = None

            resolved = ticker_name_cache[ticker]
            if resolved:
                op["name"] = resolved
            else:
                raise ValueError(
                    f"Ticker '{ticker}' could not be resolved to a valid asset name.",
                )
