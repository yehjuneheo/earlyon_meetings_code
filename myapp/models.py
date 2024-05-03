from django.db import models, connection
from django.contrib.auth.models import AbstractUser
from datetime import datetime
import pytz
from django.conf import settings


# Extending the built-in User model
class User(AbstractUser):
    is_email_verified = models.BooleanField(default=False)
    is_mentor = models.BooleanField(default=False)
    # firstname and lastname are already provided by AbstractUser



class AvailableTime(models.Model):
    giver = models.ForeignKey('Giver', on_delete=models.CASCADE, related_name='available_times', default=None)
    day = models.CharField(max_length=9)  # Monday, Tuesday, etc.
    start_time = models.TimeField()  # Use the 24-hour format
    end_time = models.TimeField()  # Use the 24-hour format
    timezone = models.CharField(max_length=50, default='UTC')  # You can make this a choice field if you like

    def __str__(self):
        return f"{self.day} {self.start_time.strftime('%H:%M')} to {self.end_time.strftime('%H:%M')} ({self.timezone})"

    class Meta:
        ordering = ['day', 'start_time', 'end_time']


class Language(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# Giver model linked with User
class Giver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='giver_profile', null=True)
    gender = models.CharField(max_length=100)
    university = models.CharField(max_length=100)
    major = models.ManyToManyField('Major', related_name='givers')
    grade_level = models.CharField(max_length=100, null=True, blank=True)
    profile_image = models.ImageField(upload_to="images/", null=True, blank=True, default='images/user_profile.png')
    resume = models.FileField(upload_to="resumes/", null=True, blank=True)
    linkedin = models.URLField(max_length=300, null=True, blank=True)
    brief_introduction = models.TextField()
    additional_information = models.TextField(null=True, blank=True)
    languages = models.ManyToManyField(Language, related_name='givers', blank=True)
    education_level = models.CharField(max_length=100)
    is_payout_setup = models.BooleanField(default=False)
    stripe_account_id = models.CharField(max_length=100, null=True, blank=True)
    availability = models.ManyToManyField(AvailableTime, related_name='available_givers', null=True, blank=True)
    timezone = models.CharField(max_length=100, choices=[(tz, tz) for tz in pytz.all_timezones], null=True, blank=True)
    signature_data_url = models.TextField(blank=True, null=True)

    is_working = models.BooleanField(default=True)
    is_displaying = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.first_name} / {self.user.username} / {self.user.email}"

# Receiver model linked with User
class Receiver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='receiver_profile', null=True)
    timezone = models.CharField(max_length=100, choices=[(tz, tz) for tz in pytz.all_timezones], null=True, blank=True, default='UTC')

    def __str__(self):
        return f"{self.user.first_name} / {self.user.username} / {self.user.email}"



class Meeting(models.Model):
    is_confirmed = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)

    is_successful = models.BooleanField(default=False)
    is_failed = models.BooleanField(default=False)

    is_failed_by_giver = models.BooleanField(default=False)
    is_failed_by_receiver = models.BooleanField(default=False)

    failed_reason_by_giver = models.CharField(max_length=10000, null=True, blank=True)
    failed_reason_by_receiver = models.CharField(max_length=10000, null=True, blank=True)

    is_rejected = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)

    giver = models.CharField(max_length=100)
    giver_profile = models.ForeignKey(Giver, on_delete=models.PROTECT, related_name='giver_meetings', default=None, null=True, )
    receiver = models.CharField(max_length=100)
    receiver_profile = models.ForeignKey(Receiver, on_delete=models.PROTECT, related_name='receiver_meetings', default=None, null=True)
    
    is_waiting_for_rating =  models.BooleanField(default=False)
    is_rating_submitted = models.BooleanField(default=False)
    stars = models.IntegerField(default=0)
    feedback = models.CharField(max_length=10000, null=True, blank=True)

    datetime = models.DateTimeField(default=datetime.now, blank=True)
    endtime = models.DateTimeField(null=True, blank=True)  # Add this line
    timezone = models.CharField(max_length=100, choices=[(tz, tz) for tz in pytz.all_timezones], null=True, blank=True, default='UTC')
    utc_datetime = models.DateTimeField(null=True, blank=True)  # Add this line

    timezone_info = models.CharField(max_length=1000, null=True, blank=True)

    zoom_link = models.URLField(max_length=1000, null=True, default=None, blank=True)
    zoom_meeting_id = models.CharField(max_length=100, null=True, blank=True)
    zoom_start_url = models.URLField(max_length=1000, null=True, blank=True, default=None) 


    def __str__(self):
        return f"{self.giver_profile.user.first_name} / {self.giver_profile.user.username} / {self.giver_profile.user.email} / {self.receiver_profile.user.first_name} / {self.receiver_profile.user.username} / {self.receiver_profile.user.email}"


class Universities(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
         return self.name
    
class Major(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.IntegerField(default=0)  # cents
    file = models.FileField(upload_to="product_files/", blank=True, null=True)
    url = models.URLField()

    def __str__(self):
        return self.name
    
    def get_display_price(self):
        return "{0:.2f}".format(self.price / 100)

class Review(models.Model):
    giver = models.ForeignKey(Giver, on_delete=models.CASCADE, related_name='reviews')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='given_reviews')
    rating = models.IntegerField(default=1, choices=[(i, i) for i in range(1, 6)])  # Ratings from 1 to 5
    review_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review by {self.author.username} for {self.giver.user.username} - Rating: {self.rating}"
    

class Payment(models.Model):
    receiver = models.ForeignKey(Receiver, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=100)
    transaction_id = models.CharField(max_length=100, unique=True)
    meeting = models.ForeignKey(Meeting, on_delete=models.PROTECT, related_name='payments', default=None, null=True)
    giver = models.ForeignKey(Giver, on_delete=models.PROTECT, related_name='payments', default=None, null=True)

    def __str__(self):
        return f"Payment {self.id} by {self.receiver.user.username}"