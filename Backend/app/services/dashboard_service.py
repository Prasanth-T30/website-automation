"""Aggregation queries powering the admin dashboard cards, charts, and tables."""
from datetime import datetime, time

from app.core.constants import STATUS_APPROVED, STATUS_PENDING, STATUS_REJECTED
from app.database.mongodb import registrations_collection


async def get_dashboard_summary() -> dict:
    col = registrations_collection()

    total = await col.count_documents({})
    pending = await col.count_documents({"status": STATUS_PENDING})
    approved = await col.count_documents({"status": STATUS_APPROVED})
    rejected = await col.count_documents({"status": STATUS_REJECTED})

    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    todays = await col.count_documents({"created_at": {"$gte": today_start}})

    return {
        "total_registrations": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "todays_registrations": todays,
    }


async def get_monthly_registrations() -> list[dict]:
    col = registrations_collection()
    pipeline = [
        {
            "$group": {
                "_id": {"year": {"$year": "$created_at"}, "month": {"$month": "$created_at"}},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1}},
    ]
    results = []
    async for row in col.aggregate(pipeline):
        results.append({"year": row["_id"]["year"], "month": row["_id"]["month"], "count": row["count"]})
    return results


async def get_domain_wise_counts() -> list[dict]:
    col = registrations_collection()
    pipeline = [
        {"$group": {"_id": "$domain", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    return [{"domain": row["_id"], "count": row["count"]} async for row in col.aggregate(pipeline)]


async def get_college_wise_counts() -> list[dict]:
    col = registrations_collection()
    pipeline = [
        {"$group": {"_id": "$college", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 15},
    ]
    return [{"college": row["_id"], "count": row["count"]} async for row in col.aggregate(pipeline)]


async def get_approval_ratio() -> dict:
    summary = await get_dashboard_summary()
    decided = summary["approved"] + summary["rejected"]
    ratio = round((summary["approved"] / decided) * 100, 2) if decided else 0.0
    return {"approved": summary["approved"], "rejected": summary["rejected"], "approval_ratio_percent": ratio}


async def get_full_analytics() -> dict:
    return {
        "summary": await get_dashboard_summary(),
        "monthly_registrations": await get_monthly_registrations(),
        "domain_wise": await get_domain_wise_counts(),
        "college_wise": await get_college_wise_counts(),
        "approval_ratio": await get_approval_ratio(),
    }
