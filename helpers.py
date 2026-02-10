import math


def time_difference(date1, date2):
    """Calculate the difference between two dates in seconds."""
    difference = math.floor(date1) - math.floor(date2)

    diff_in_days = math.floor(difference / 60 / 60 / 24)
    diff_in_hours = math.floor(difference / 60 / 60)
    diff_in_minutes = math.floor(difference / 60)
    diff_in_seconds = math.floor(difference)

    return {
        "date1": date1,
        "date2": date2,
        "diffInDays": diff_in_days,
        "diffInHours": diff_in_hours,
        "diffInMinutes": diff_in_minutes,
        "diffInSeconds": diff_in_seconds,
    }
