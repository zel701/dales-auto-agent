"""Listing repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from car_agent.db.models.search import Listing as ListingORM
from car_agent.domain import Listing


async def bulk_create_listings(
    session: AsyncSession, search_id: int, listings: list[Listing]
) -> list[Listing]:
    """Persist a batch of listings under a search; return them as domain entities."""
    rows: list[ListingORM] = []
    for listing in listings:
        rows.append(
            ListingORM(
                search_id=search_id,
                marketcheck_id=listing.marketcheck_id,
                vin=listing.vin,
                year=listing.year,
                make=listing.make,
                model=listing.model,
                trim=listing.trim,
                exterior_color=listing.exterior_color,
                interior_color=listing.interior_color,
                drivetrain=listing.drivetrain,
                price=listing.price,
                msrp=listing.msrp,
                days_on_lot=listing.days_on_lot,
                dealer_name=listing.dealer_name,
                dealer_email=listing.dealer_email,
                dealer_phone=listing.dealer_phone,
                dealer_city=listing.dealer_city,
                dealer_state=listing.dealer_state,
                dealer_zip=listing.dealer_zip,
                distance_miles=listing.distance_miles,
                vdp_url=listing.vdp_url,
                raw_json=listing.model_dump(mode="json"),
            )
        )
    session.add_all(rows)
    await session.commit()
    for row in rows:
        await session.refresh(row)
    return [Listing.model_validate(row) for row in rows]


async def get_listings_by_search(
    session: AsyncSession, search_id: int
) -> list[Listing]:
    result = await session.execute(
        select(ListingORM).where(ListingORM.search_id == search_id)
    )
    return [Listing.model_validate(row) for row in result.scalars().all()]


async def get_competing_listings(
    session: AsyncSession, search_id: int, exclude_listing_id: int
) -> list[Listing]:
    """Listings from the same search excluding one — used as negotiation leverage."""
    result = await session.execute(
        select(ListingORM)
        .where(ListingORM.search_id == search_id, ListingORM.id != exclude_listing_id)
        .order_by(ListingORM.price.asc())
    )
    return [Listing.model_validate(row) for row in result.scalars().all()]


async def get_listing_by_marketcheck_id(
    session: AsyncSession, marketcheck_id: str
) -> Listing | None:
    result = await session.execute(
        select(ListingORM).where(ListingORM.marketcheck_id == marketcheck_id)
    )
    row = result.scalar_one_or_none()
    return Listing.model_validate(row) if row else None
