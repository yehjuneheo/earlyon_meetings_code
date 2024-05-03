from django.contrib.auth.tokens import PasswordResetTokenGenerator
import six
import requests
from jose import jwt
import time
import pytz
import base64


class EmailTokenGenerator(PasswordResetTokenGenerator):

    def _make_hash_value(self, user, timestamp):
        return (six.text_type(user.pk)+six.text_type(timestamp)+six.text_type(user.is_email_verified))


class ConfirmationTokenGenerator(PasswordResetTokenGenerator):

    def _make_hash_value(self, meeting, timestamp):
        return (six.text_type(meeting.pk)+six.text_type(timestamp)+six.text_type(meeting.is_confirmed)+six.text_type(meeting.is_rejected))

generate_email_token = EmailTokenGenerator()
generate_confirmation_token = ConfirmationTokenGenerator()



def generate_access_token(account_id, client_id, client_secret):
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    url = "https://zoom.us/oauth/token"
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    body = {
        "grant_type": "account_credentials",
        "account_id": account_id
    }
    
    response = requests.post("https://zoom.us/oauth/token", headers=headers, data=body)
    
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print(f"Failed to obtain access token: {response.text}")
        return None

def create_meeting(access_token, user_id, topic, start_time, timezone):
    start_time_timezone = start_time.strftime('%Y-%m-%dT%H:%M:%S')
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "topic": topic,
        "type": 2,  # Scheduled meeting
        "start_time": start_time_timezone,
        "duration": 65,  # Duration in minutes
        "timezone": timezone,
        "settings": {
            "host_video": "true",
            "participant_video": "true",
            "join_before_host": True,
            "auto_recording": "cloud",
            "use_pmi": False,  # Do not use Personal Meeting ID
        },
    }
    
    response = requests.post(f"https://api.zoom.us/v2/users/{user_id}/meetings", json=payload, headers=headers)
    
    if response.status_code == 201:
        return response.json()  # Meeting created successfully
    else:
        print(f"Failed to create meeting: {response.text}")
        return None