from .utils import *


def _find_project_progress(start, end, uid):
    field_name = "project"
    pipeline = [
        {"$match": {"username": uid, "timestamp": {"$gte": start, "$lt": end}}},
        {"$group": {"_id": f"${field_name}", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {
            "$group": {
                "_id": None,
                "data": {"$push": {"k": {"$ifNull": ["$_id", "null"]},
                                    "v": "$count"}}
            }
        },
        {
            "$replaceRoot": {
                "newRoot": {"$arrayToObject": "$data"}
            }
        }
    ]

    result = list(collection.aggregate(pipeline))

    return result


def _user_edits_each_day(start_time_seconds, count, uid):
    edits_each_day = {}

    for i in range(count):
        offset_days = 1 * mili_a_day
        end_time_seconds = start_time_seconds + offset_days
        documents = collection.count_documents(
            {"username": uid, "timestamp": {"$gte": start_time_seconds, "$lt": end_time_seconds}})

        pipeline = [
            {"$match": {"username": uid, "timestamp": {"$gte": start_time_seconds, "$lt": end_time_seconds}}},
            {"$group": {"_id": "$project", "count": {"$sum": 1}}},
            {"$group": {
                "_id": None,
                "data": {"$push": {"k": {"$ifNull": ["$_id", "null"]},
                                   "v": "$count"}}
            }},
            {"$replaceRoot": {"newRoot": {"$arrayToObject": "$data"}}}
        ]

        result = list(collection.aggregate(pipeline))
        result.insert(0, documents)

        start_time_seconds = start_time_seconds / 1000
        start_obj = datetime.utcfromtimestamp(start_time_seconds)
        start_string = start_obj.strftime('%Y-%m-%d')
        edits_each_day[start_string] = result

        start_time_seconds = end_time_seconds

    return edits_each_day


def _user_edits_each_month(date_obj, uid):
    edits_each_month = {}

    for i in range(12):
        start_time_seconds = int(date_obj.timestamp()) * 1000
        month_later_dt = date_obj + relativedelta(months=1)
        end_time_seconds = int(month_later_dt.timestamp()) * 1000

        documents = collection.count_documents(
            {"username": uid, "timestamp": {"$gte": start_time_seconds, "$lt": end_time_seconds}})

        pipeline = [
            {"$match": {"username": uid, "timestamp": {"$gte": start_time_seconds, "$lt": end_time_seconds}}},
            {"$group": {"_id": "$project", "count": {"$sum": 1}}},
            {"$group": {
                "_id": None,
                "data": {"$push": {"k": {"$ifNull": ["$_id", "null"]},
                                   "v": "$count"}}
            }},
            {"$replaceRoot": {"newRoot": {"$arrayToObject": "$data"}}}
        ]

        result = list(collection.aggregate(pipeline))
        result.insert(0, documents)

        start_time_seconds = start_time_seconds / 1000
        start_obj = datetime.utcfromtimestamp(start_time_seconds)
        start_string = start_obj.strftime('%Y-%m-%d')
        edits_each_month[start_string] = result

        date_obj = month_later_dt

    return edits_each_month


def distinct_usernames():
    return collection.distinct("username")


def user_edits_by_week(date, uid):
    result = {}

    time_string = date.split("W")[0] + date.split("W")[1] + '-1'
    date_time_format = "%Y-%W-%w"
    dt = datetime.strptime(time_string, date_time_format)
    start_time_seconds = int(dt.timestamp())
    start_time_seconds = start_time_seconds * 1000

    edits_each_day = _user_edits_each_day(start_time_seconds, 7, uid)

    offset_days = 7 * mili_a_day
    end_time_seconds = start_time_seconds + offset_days
    projects = _find_project_progress(start_time_seconds, end_time_seconds, uid)

    result["edits_each_date"] = edits_each_day
    result["projects"] = projects

    return result


def user_edits_by_month(date, uid):
    result = {}

    time_string = date + "-01"
    date_time_format = "%Y-%m-%d"
    dt = datetime.strptime(time_string, date_time_format)
    month_later_dt = dt + relativedelta(months=1)

    start_time_seconds = int(dt.timestamp())
    end_time_seconds = int(month_later_dt.timestamp())

    days_in_month = int((end_time_seconds - start_time_seconds) / (24 * 3600))
    start_time_seconds = start_time_seconds * 1000
    end_time_seconds = end_time_seconds * 1000

    edits_each_day = _user_edits_each_day(start_time_seconds, days_in_month, uid)
    projects = _find_project_progress(start_time_seconds, end_time_seconds, uid)

    result["edits_each_date"] = edits_each_day
    result["projects"] = projects

    return result


def user_edits_by_year(date, uid):
    result = {}

    time_string = date
    date_time_format = "%Y-%m-%d"
    dt = datetime.strptime(time_string, date_time_format)
    year_later_dt = dt + relativedelta(years=1)

    start_time_seconds = int(dt.timestamp())
    end_time_seconds = int(year_later_dt.timestamp())

    start_time_seconds = start_time_seconds * 1000
    end_time_seconds = end_time_seconds * 1000

    edits_each_month = _user_edits_each_month(dt, uid)
    projects = _find_project_progress(start_time_seconds, end_time_seconds, uid)

    result["edits_each_date"] = edits_each_month
    result["projects"] = projects

    return result




__all__ = ['distinct_usernames', 'user_edits_by_week', 'user_edits_by_month', 'user_edits_by_year']