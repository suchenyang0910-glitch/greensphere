from fastapi import APIRouter
from fastapi.responses import Response

from app.services.co2_service import get_co2_points_from_db, render_trend_svg

router = APIRouter()


@router.get("/api/co2/trend.svg")
def co2_trend_svg() -> Response:
    points = get_co2_points_from_db()
    svg = render_trend_svg(points)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store"},
    )

