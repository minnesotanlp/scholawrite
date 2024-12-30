from .utils import *


def _find_top_n_users(start, end, n):
    field_name = "username"
    pipeline = [
        {"$match": {"timestamp": {"$gte": start, "$lt": end}}},
        {"$group": {"_id": f"${field_name}", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": n},
        {"$project": {"_id": 0, field_name: "$_id", "count": 1}}
    ]

    result = list(collection.aggregate(pipeline))
    edits_each_project = _fetch_projects_edit(start, end, result)

    return edits_each_project


def _find_top_n_projects(start, end, n):
    field_name = "project"
    pipeline = [
        {"$match": {"timestamp": {"$gte": start, "$lt": end}}},
        {"$group": {"_id": f"${field_name}", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": n},
        {"$project": {"_id": 0, field_name: "$_id", "count": 1}}
    ]

    result = list(collection.aggregate(pipeline))

    edits_each_author = _fetch_authors_edit(start, end, result)

    return edits_each_author


def _fetch_edits_each_day(start_time_seconds, count):
    edits_each_day = {}

    for i in range(count):
        offset_days = 1 * mili_a_day
        end_time_seconds = start_time_seconds + offset_days
        documents = collection.count_documents(
            {"timestamp": {"$gte": start_time_seconds, "$lt": end_time_seconds}})

        pipeline = [
            {"$match": {"timestamp": {"$gte": start_time_seconds, "$lt": end_time_seconds}}},
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


def _fetch_edits_each_month(date_obj):
    edits_each_month = {}

    for i in range(12):
        start_time_seconds = int(date_obj.timestamp()) * 1000
        month_later_dt = date_obj + relativedelta(months=1)
        end_time_seconds = int(month_later_dt.timestamp()) * 1000

        documents = collection.count_documents(
            {"timestamp": {"$gte": start_time_seconds, "$lt": end_time_seconds}})

        pipeline = [
            {"$match": {"timestamp": {"$gte": start_time_seconds, "$lt": end_time_seconds}}},
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


def _fetch_authors_edit(start, end, result):
    field_name = "username"
    edits_each_author = {}
    for each in result:
        pipeline = [
            {"$match": {"project": each["project"], "timestamp": {"$gte": start, "$lte": end}}},
            {"$group": {"_id": f"${field_name}", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {
                "$group": {
                    "_id": None,
                    "data": {"$push": {"k": "$_id", "v": "$count"}}
                }
            },
            {
                "$replaceRoot": {
                    "newRoot": {"$arrayToObject": "$data"}
                }
            }
        ]

        project_edits = list(collection.aggregate(pipeline))
        project_edits.insert(0, each["count"])
        edits_each_author[each["project"]] = project_edits

    return edits_each_author


def _fetch_projects_edit(start, end, result):
    field_name = "project"
    edits_each_project = {}
    for each in result:
        pipeline = [
            {"$match": {"username": each["username"], "timestamp": {"$gte": start, "$lte": end}}},
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

        user_edits = list(collection.aggregate(pipeline))
        user_edits.insert(0, each["count"])
        edits_each_project[each["username"]] = user_edits

    return edits_each_project


def fetch_edits_by_week(date):
    result = {}

    time_string = date.split("W")[0] + date.split("W")[1] + '-1'
    date_time_format = "%Y-%W-%w"
    dt = datetime.strptime(time_string, date_time_format)
    start_time_seconds = int(dt.timestamp())
    start_time_seconds = start_time_seconds * 1000

    offset_days = 7 * mili_a_day
    end_time_seconds = start_time_seconds + offset_days

    edits_each_day = _fetch_edits_each_day(start_time_seconds, 7)
    top_n_users = _find_top_n_users(start_time_seconds, end_time_seconds, 5)
    top_n_projects = _find_top_n_projects(start_time_seconds, end_time_seconds, 5)

    result["edits_each_date"] = edits_each_day
    result["top_n_users"] = top_n_users
    result["top_n_projects"] = top_n_projects

    console.log(result)
    return result


def fetch_edits_by_month(date):
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

    edits_each_day = _fetch_edits_each_day(start_time_seconds, days_in_month)
    top_n_users = _find_top_n_users(start_time_seconds, end_time_seconds, 5)
    top_n_projects = _find_top_n_projects(start_time_seconds, end_time_seconds, 5)

    result["edits_each_date"] = edits_each_day
    result["top_n_users"] = top_n_users
    result["top_n_projects"] = top_n_projects

    console.log(result)
    return result


def fetch_edits_by_year(date):
    result = {}

    time_string = date
    date_time_format = "%Y-%m-%d"
    dt = datetime.strptime(time_string, date_time_format)
    year_later_dt = dt + relativedelta(years=1)

    start_time_seconds = int(dt.timestamp())
    end_time_seconds = int(year_later_dt.timestamp())

    start_time_seconds = start_time_seconds * 1000
    end_time_seconds = end_time_seconds * 1000

    edits_each_month = _fetch_edits_each_month(dt)
    top_n_users = _find_top_n_users(start_time_seconds, end_time_seconds, 5)
    top_n_projects = _find_top_n_projects(start_time_seconds, end_time_seconds, 5)

    result["edits_each_date"] = edits_each_month
    result["top_n_users"] = top_n_users
    result["top_n_projects"] = top_n_projects

    console.log(result)
    return result


__all__ = ['fetch_edits_by_week', 'fetch_edits_by_month', 'fetch_edits_by_year']