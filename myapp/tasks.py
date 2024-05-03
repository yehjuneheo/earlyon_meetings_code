from celery import shared_task
from django.utils import timezone
from .models import Meeting, Giver, Receiver
from django.conf import settings
import logging
from django.template.loader import render_to_string
from django.utils.formats import date_format
from .templatetags.timezone_filters import convert_timezone, convert_timezone_time
from django.core.mail import EmailMessage
from .views import EmailThread
from datetime import timedelta
from .utils import generate_confirmation_token
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

logger = logging.getLogger(__name__)

@shared_task
def send_meeting_reminders():
    now = timezone.now()
    logger.info(now)
    # Define target datetimes for 24 hours and 2 hours before the meeting
    target_datetime_24h = now + timedelta(hours=24)
    target_datetime_2h = now + timedelta(hours=2)

    # Define time ranges
    time_range_start_24h = target_datetime_24h - timedelta(minutes=5)
    time_range_end_24h = target_datetime_24h + timedelta(minutes=5)
    time_range_start_2h = target_datetime_2h - timedelta(minutes=5)
    time_range_end_2h = target_datetime_2h + timedelta(minutes=5)

    
    time_12h_ahead = now + timezone.timedelta(hours=12)
    meetings_to_cancel = Meeting.objects.filter(
        utc_datetime__lte=time_12h_ahead,
        is_confirmed=False,
        is_cancelled=False,
        is_rejected=False,
        is_completed=False,
    )
    for meeting in meetings_to_cancel:
        # Assuming you have a relationship to 'Giver' and 'Receiver' models from 'Meeting'
        giver = meeting.giver_profile
        receiver = meeting.receiver_profile
        send_meeting_cancelled(meeting, giver, receiver)
        my_send_meeting_cancelled(meeting, giver, receiver)
        logger.info(f"Sent cancelled email for meeting {meeting.pk}.")
    meetings_to_cancel.update(is_cancelled=True, is_confirmed=False)
    
    start_window = target_datetime_24h - timezone.timedelta(minutes=5)
    end_window = target_datetime_24h + timezone.timedelta(minutes=5)

    unconfirmed_meetings = Meeting.objects.filter(
        utc_datetime__gte=start_window,
        utc_datetime__lte=end_window,
        is_confirmed=False,
        is_cancelled=False,
        is_rejected=False,
    )

    for meeting in unconfirmed_meetings:
            # Assuming you have a relationship to 'Giver' and 'Receiver' models from 'Meeting'
            giver = meeting.giver_profile
            receiver = meeting.receiver_profile
            send_confirmation_email(meeting, giver, receiver)
            logger.info(f"Sent 24-hour reminder email for meeting {meeting.pk}.")

    
    now_1_hour = now - timedelta(hours=1)
    now_5_ahead = now_1_hour - timedelta(minutes=5)
    now_5_behind = now_1_hour + timedelta(minutes=5)
    completed_meetings = Meeting.objects.filter(
        utc_datetime__gte=now_5_ahead,
        utc_datetime__lte=now_5_behind,  # Assuming 'endtime' is your field name for when the meeting ends
        is_completed=False,
        is_confirmed=True,
        is_cancelled=False,
        is_rejected=False,
    )

    for meeting in completed_meetings:
         logger.info(f"{meeting.pk} meeting completed at {meeting.utc_datetime}")
         giver = meeting.giver_profile
         receiver = meeting.receiver_profile
         send_submit_rating_email(meeting, giver, receiver)
         logger.info(f"Sent submit rating email for meeting {meeting.pk}.")
         
    completed_meetings.update(is_completed=True, is_confirmed=False, is_waiting_for_rating=True)

    
    target_datetime_24h_2 = now - timedelta(hours=24)
    start_window_2 = target_datetime_24h_2 - timezone.timedelta(minutes=5)
    end_window_2 = target_datetime_24h_2 + timezone.timedelta(minutes=5)

    completed_meetings_24hours = Meeting.objects.filter(
        utc_datetime__gte=start_window_2,
        utc_datetime__lte=end_window_2,  # Assuming 'endtime' is your field name for when the meeting ends
        is_completed=True,
        is_confirmed=False,
        is_cancelled=False,
        is_rejected=False,
        is_successful=False,
        is_failed = False,
        is_failed_by_giver = False,
        is_failed_by_receiver = False
    )

    for meeting in completed_meetings_24hours:
         logger.info(f"{meeting.pk} meeting completed at {meeting.utc_datetime}")
         giver = meeting.giver_profile
         receiver = meeting.receiver_profile
         send_submit_rating_email(meeting, giver, receiver)
         logger.info(f"Sent submit rating email for meeting {meeting.pk}.")

    
    
    # Define target datetimes for 24 hours and 2 hours before the meeting
    target_datetime_48h = now - timedelta(hours=48)
    # Define time ranges
    time_range_start_48h = target_datetime_48h - timedelta(minutes=5)
    time_range_end_48h = target_datetime_48h + timedelta(minutes=5)
    successful_meetings = Meeting.objects.filter(
        utc_datetime__gte=time_range_start_48h,
        utc_datetime__lte=time_range_end_48h,  # Assuming 'endtime' is your field name for when the meeting ends
        is_completed=True,
        is_confirmed=False,
        is_cancelled=False,
        is_rejected=False,
        is_successful=False,
        is_failed = False,
        is_failed_by_giver = False,
        is_failed_by_receiver = False
    )
    successful_meetings.update(is_successful=True, is_confirmed=False)



    # Filter for upcoming meetings within the 24-hour range
    upcoming_meetings_24h = Meeting.objects.filter(utc_datetime__gte=time_range_start_24h, utc_datetime__lte=time_range_end_24h, is_confirmed=True)
    # Filter for upcoming meetings within the 2-hour range
    upcoming_meetings_2h = Meeting.objects.filter(utc_datetime__gte=time_range_start_2h, utc_datetime__lte=time_range_end_2h, is_confirmed=True)

    # Send reminders for meetings happening in 24 hours
    for meeting in upcoming_meetings_24h:
        giver = Giver.objects.get(user__username=meeting.giver)
        receiver = Receiver.objects.get(user__username=meeting.receiver)
        send_reminder_email(meeting, giver, receiver)
        logger.info(f"24-hour reminder sent for meeting {meeting.pk} scheduled at {meeting.datetime}")

    # Send reminders for meetings happening in 2 hours
    for meeting in upcoming_meetings_2h:
        giver = Giver.objects.get(user__username=meeting.giver)
        receiver = Receiver.objects.get(user__username=meeting.receiver)
        send_reminder_email(meeting, giver, receiver)
        logger.info(f"2-hour reminder sent for meeting {meeting.pk} scheduled at {meeting.datetime}")
    pass



def send_reminder_email(meeting, giver, receiver):
    current_site = settings.SITE_URL
    timezone_info = f"{giver.timezone},{receiver.timezone}"
    start_datetime_formatted = date_format(meeting.datetime, "F j, Y, P")
    end_time_formatted = date_format(meeting.endtime, "P")
    start_datetime_converted = convert_timezone(meeting.datetime, timezone_info)
    end_time_converted = convert_timezone_time(meeting.endtime, timezone_info)
    email_subject = 'Meeting Reminder With ' + str(receiver.user.get_full_name())
    email_body = render_to_string('email_meeting_reminder_mentor.html',{
        'meeting': meeting,
        'meeting_start': start_datetime_formatted,
        'meeting_end': end_time_formatted,
        'student': receiver,
        'giver': giver,
        'domain':current_site,
    })
    email_subject2 = 'Meeting Reminder With ' + str(giver.user.get_full_name())
    email_body2 = render_to_string('email_meeting_reminder_student.html',{
        'meeting': meeting,
        'meeting_start': start_datetime_converted,
        'meeting_end': end_time_converted,
        'student': receiver,
        'giver': giver,
        'domain':current_site,
    })
    email = EmailMessage(subject=email_subject, body=email_body, from_email=settings.EMAIL_FROM_USER,to=[giver.user.email])
    email2 = EmailMessage(subject=email_subject2, body=email_body2, from_email=settings.EMAIL_FROM_USER,to=[receiver.user.email])
    email.content_subtype = 'html'
    email2.content_subtype = 'html'
    email.send()
    email2.send()



#SEND COMFIRMATION EMAIL TO MENTOR
def send_confirmation_email(meeting, giver, receiver,):
    current_site = settings.SITE_URL
    start_datetime_formatted = date_format(meeting.datetime, "F j, Y, P")
    end_time_formatted = date_format(meeting.endtime, "P")
    email_subject = 'Meeting Request From EarlyOn! Confirm now.'
    email_body = render_to_string('email_confirm_meeting.html',{
        'meeting': meeting,
        'meeting_start': start_datetime_formatted,
        'meeting_end': end_time_formatted,
        'domain':current_site,
        'student':receiver,
        'giver': giver,
        'uid':urlsafe_base64_encode(force_bytes(meeting.pk)),
        'token': generate_confirmation_token.make_token(meeting)
    })
    email = EmailMessage(subject=email_subject, body=email_body, from_email=settings.EMAIL_FROM_USER,to=[giver.user.email])
    email.content_subtype = 'html'
    email.send()


def send_submit_rating_email(meeting, giver, receiver):
    current_site = settings.SITE_URL
    email_subject = 'Submit Review For Your Meeting With ' + str(giver.user.get_full_name())
    email_body = render_to_string('email_submit_rating.html',{
        'meeting': meeting,
        'student': receiver,
        'giver': giver,
        'domain':current_site,
    })
    email = EmailMessage(subject=email_subject, body=email_body, from_email=settings.EMAIL_FROM_USER,to=[receiver.user.email])
    email.content_subtype = 'html'
    email.send()
    
    


def send_meeting_cancelled(meeting, giver, receiver):
    current_site = settings.SITE_URL
    timezone_info = f"{giver.timezone},{receiver.timezone}"
    start_datetime_converted = convert_timezone(meeting.datetime, timezone_info)
    end_time_converted = convert_timezone_time(meeting.endtime, timezone_info)
    email_subject = 'Meeting Cancelled From ' + str(giver.user.get_full_name())
    email_body = render_to_string('email_meeting_cancelled.html',{
        'meeting': meeting,
        'meeting_start': start_datetime_converted,
        'meeting_end': end_time_converted,
        'student':receiver,
        'giver': giver,
        'domain':current_site,
    })
    email = EmailMessage(subject=email_subject, body=email_body, from_email=settings.EMAIL_FROM_USER,to=[receiver.user.email])
    email.content_subtype = 'html'
    email.send()


def my_send_meeting_cancelled(meeting, giver, receiver):
    current_site = settings.SITE_URL
    start_datetime_formatted = date_format(meeting.datetime, "F j, Y, P")
    end_time_formatted = date_format(meeting.endtime, "P")
    email_subject = 'Meeting Cancelled From ' + str(receiver.user.get_full_name())
    email_body = render_to_string('email_meeting_cancelled_mentor.html',{
        'meeting': meeting,
        'meeting_start': start_datetime_formatted,
        'meeting_end': end_time_formatted,
        'student':receiver,
        'giver': giver,
        'domain':current_site,
    })
    email = EmailMessage(subject=email_subject, body=email_body, from_email=settings.EMAIL_FROM_USER,to=[giver.user.email])
    email.content_subtype = 'html'
    email.send()