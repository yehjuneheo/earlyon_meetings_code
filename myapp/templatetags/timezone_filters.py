from django import template
import pytz
from django.utils.timezone import make_aware, is_naive
from django.utils.dateformat import DateFormat

register = template.Library()

@register.filter
def convert_timezone(value, timezone_info):
    """Converts a datetime from the meeting's timezone to the user's (receiver's) timezone.

    Args:
        value (datetime): The datetime to be converted.
        timezone_info (str): A string combining the meeting's timezone and the user's timezone, separated by a comma.

    Returns:
        datetime: The datetime converted to the user's timezone.
    """
    if value is None or timezone_info is None:
        return value

    try:
        meeting_timezone_str, user_timezone_str = timezone_info.split(',')
        meeting_timezone = pytz.timezone(meeting_timezone_str)
        user_timezone = pytz.timezone(user_timezone_str)
                
        # Convert the datetime to the giver's timezone
        giver_aware_dt = meeting_timezone.localize(value.replace(tzinfo=None))

        # Convert the datetime to the user's timezone
        user_timezone_dt = giver_aware_dt.astimezone(user_timezone)
        # Return the datetime formatted in the user's timezone
        return DateFormat(user_timezone_dt).format('F j, Y, P')  # Example format, adjust as needed
    except Exception as e:
        print(f"Error converting timezone: {e}")
        return value  # In case of an error, return the original value



@register.filter
def convert_timezone_time(value, timezone_info):
    """Converts a datetime from the meeting's timezone to the user's (receiver's) timezone.

    Args:
        value (datetime): The datetime to be converted.
        timezone_info (str): A string combining the meeting's timezone and the user's timezone, separated by a comma.

    Returns:
        datetime: The datetime converted to the user's timezone.
    """
    if value is None or timezone_info is None:
        return value

    try:
        meeting_timezone_str, user_timezone_str = timezone_info.split(',')
        meeting_timezone = pytz.timezone(meeting_timezone_str)
        user_timezone = pytz.timezone(user_timezone_str)
                
        # Convert the datetime to the giver's timezone
        giver_aware_dt = meeting_timezone.localize(value.replace(tzinfo=None))
        # Convert the datetime to the user's timezone
        user_timezone_dt = giver_aware_dt.astimezone(user_timezone)
        # Convert the datetime to the user's (receiver's) timezone
        return DateFormat(user_timezone_dt).format('P')  # Example format, adjust as needed
    except Exception as e:
        print(f"Error converting timezone: {e}")
        return value  # In case of an error, return the original value

