from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, FileResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.contrib.auth.models import auth
from django.contrib.auth import logout
from django.contrib import messages
from django.db.models import Q, Count
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.decorators import login_required
from django.utils.encoding import force_bytes, force_str
from django.utils.dateparse import parse_time
from django.utils.timezone import make_aware, datetime, now
from django.urls import reverse
from django.core.mail import EmailMessage, send_mail
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views import View
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.db.models.functions import Lower
from .models import Giver, Universities, Receiver, User, Meeting, Product, Language, Major, AvailableTime
from .utils import generate_email_token, generate_confirmation_token, create_meeting, generate_access_token
import threading
from .forms import *
from django.core.serializers.json import DjangoJSONEncoder
import stripe
import urllib
import requests
import json
import calendar
from datetime import datetime, timedelta
from pytz import common_timezones
from django.utils.formats import date_format
from .templatetags.timezone_filters import convert_timezone, convert_timezone_time
from django.db.models import Case, When, Value, IntegerField
import re




########################################################################################
#       MAIN SYSTEM
########################################################################################


# HOME--------------------------------------------------------------------------------------
def home(request):
    givers = Giver.objects.all()
    universities = Universities.objects.all()
    return render(request, 'home.html', {'givers': givers, 'universities':universities})


def selection(request):
    givers = Giver.objects.all()
    universities = Universities.objects.all()
    return render(request, 'selection2.html', {'givers': givers, 'universities':universities})


def about_us(request):
    return render(request, 'about-us.html')

def contact_us(request):
    if request.method == 'POST':
        name = request.POST['Name']
        email = request.POST['Email']
        message = request.POST['Message']
        # Prepare the email message
        email_subject = f"New contact form submission: {name}"
        email_message = f"From: {name}\nEmail: {email}\n\nMessage:\n{message}"
        # Send email
        send_mail(
            subject=email_subject,
            message=email_message,
            from_email=email,
            recipient_list=[settings.EMAIL_FROM_USER],
        )
        return render(request, 'message-sent.html', {'name': name})
    return render(request, 'contact-us.html')

def privacy_policy(request):
    return render(request, 'privacy-policy.html')

def terms_and_conditions(request):
    return render(request, 'terms-and-conditions.html')

def help(request):
    return render(request, 'help.html')


def cookie_policy(request):
    return render(request, 'cookie-policy.html')


# LOGIN--------------------------------------------------------------------------------------
def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(username=username, password=password)

        if user is not None:
            auth.login(request, user)
            return redirect('home')
        else:
            messages.info(request, 'Credentials Invalid')
            return redirect('login')
    return render(request, 'login.html')


# LOGOUT
def logout_view(request):
    logout(request)
    return redirect('home')


def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None
# REGISTER FOR STUDENT--------------------------------------------------------------------------------------
def register_student(request):
    if request.method == 'POST':
        firstname = request.POST['firstname']
        lastname = request.POST['lastname']
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        password2 = request.POST['password2']
        
        if not is_valid_email(email):
            messages.error(request, 'Invalid email format.')
            return redirect('register_student')
        
        if password == password2:
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email Already Used')
                return redirect('register_student')
            elif User.objects.filter(username=username).exists():
                messages.error(request, 'Username Already Used')
                return redirect('register_student')
            else:
                # Create the User instance
                user = User.objects.create_user(
                    username=username, 
                    password=password, 
                    email=email, 
                    first_name=firstname, 
                    last_name=lastname
                )
                # Create the Receiver instance
                Receiver.objects.create(
                    user=user, 
                )

                # Assuming you have a function to send an activation email
                send_activation_email(user, request)

                messages.success(request, 'Account created successfully! Please check your email to verify your account.')
                return redirect('login')
        else:
            messages.error(request, 'Passwords do not match.')
            return redirect('register_student')

    return render(request, 'register_student.html')

def timezone_list():
    gmt_offsets = [f"Etc/GMT{'+' if x < 0 else '-' if x > 0 else ''}{abs(x)}" for x in range(-14, 15)]
    return gmt_offsets

# REGISTER FOR TEACHER--------------------------------------------------------------------------------------
def register_teacher(request):
    
    days_of_week = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    time_slots = range(0, 24)  # assuming 9AM to 5PM, increment by 1 hour
    timezones = timezone_list()
    languages = Language.objects.all()
    context = {
        'days_of_week': days_of_week,
        'time_slots': time_slots,
        'timezones': timezones,
        'languages': languages
        # ... include other context variables as needed
    }
    if request.method == 'POST':
        # Basic information
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        gender = request.POST.get('gender')
        email = request.POST.get('email').lower()  # Convert email to lowercase

        # Specific to Giver
        university = request.POST.get('university')
        majors = request.POST.getlist('majors')  # Fetch multiple majors if applicable
        education_level = request.POST.get('education_level')
        grade_level = request.POST.get('grade_level')

        # File uploads
        imagefile = request.FILES.get('imagefile')
        resumefile = request.FILES.get('resumefile')

        # Additional information
        brief_introduction = request.POST.get('brief_introduction')
        linkedin = request.POST.get('linkedin', '')  # Default to empty string if not provided
        additional_information = request.POST.get('additional_information', '')  # Default to empty string if not provided
        
        timezone = request.POST.get('timezone')
        selected_languages = request.POST.getlist('languages')
        
        signature_data_url = request.POST.get('signature')
        
        if password == password2:
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email Already Used')
                return redirect('register_teacher')
            elif User.objects.filter(username=username).exists():
                messages.error(request, 'Username Already Used')
                return redirect('register_teacher')
            else:
                user = User.objects.create_user(username=username, password=password, email=email, first_name=firstname, last_name=lastname, is_mentor=True)

                giver = Giver.objects.create(
                    user=user,
                    gender=gender,
                    university=university,
                    education_level=education_level,
                    grade_level=grade_level,
                    brief_introduction=brief_introduction,
                    linkedin=linkedin,
                    additional_information=additional_information,
                    timezone=timezone,
                    signature_data_url=signature_data_url,
                )

                for language_id in selected_languages:
                    language = Language.objects.get(id=language_id)
                    giver.languages.add(language)
                    
                for day in days_of_week:
                    start_times = request.POST.getlist(f'{day}_start[]')
                    end_times = request.POST.getlist(f'{day}_end[]')

                    # Check if there are any times provided for the day
                    if start_times and end_times:  # Proceed only if lists are not empty
                        # Convert to datetime for easier manipulation and sorting
                        time_slots = sorted([
                            (datetime.strptime(start_time_str, "%H:%M"), datetime.strptime(end_time_str if end_time_str != "00:00" else "23:59", "%H:%M"))
                            for start_time_str, end_time_str in zip(start_times, end_times)
                        ], key=lambda x: x[0])  # Sort by start time

                        merged_slots = []
                        if time_slots:  # Ensure time_slots is not empty before proceeding
                            prev_start, prev_end = time_slots[0]

                            for start, end in time_slots[1:]:
                                if start <= prev_end:  # Overlapping or contiguous
                                    prev_end = max(prev_end, end)  # Extend the previous slot
                                else:
                                    merged_slots.append((prev_start, prev_end))  # Save the previous slot
                                    prev_start, prev_end = start, end  # Start a new slot
                        
                            # Don't forget to add the last slot
                            merged_slots.append((prev_start, prev_end))

                            # Save merged slots to database
                            for start, end in merged_slots:
                                # Convert back to time objects if necessary
                                start_time = start.time()
                                end_time = end.time()

                                # Create and link the availability time to the giver
                                available_time = AvailableTime.objects.create(
                                    giver=giver,
                                    day=day,
                                    start_time=start_time,
                                    end_time=end_time,
                                    timezone=timezone
                                )
                    else:
                        # Handle days with no start and end times provided
                        print(f"No times provided for {day}.")

                # Handling multiple majors selection
                for major in majors:
                    major = Major.objects.get(name=major)
                    giver.major.add(major)

                # Handling file uploads
                if imagefile:
                    giver.profile_image = imagefile
                if resumefile:
                    giver.resume = resumefile

                user.save()
                giver.save()

                
                # Assuming you have a function to send an activation email
                send_activation_email(user, request)

                messages.success(request, 'Account created successfully! Please check your email to verify your account.')
                return redirect('login')
        else:
            messages.error(request, 'Passwords do not match')
            return redirect('register_teacher')

    return render(request, 'register_teacher.html', context)


def check_username(request):
    username = request.GET.get('username', None)
    data = {
        'is_taken': User.objects.filter(username__iexact=username).exists()
    }
    return JsonResponse(data)


def agreement_view(request):
    # Capture first and last names from query parameters
    first_name = request.GET.get('firstname', 'User')
    last_name = request.GET.get('lastname', '')

    # Create the full name or handle it however you prefer
    full_name = f"{first_name} {last_name}".strip()

    # Get today's date in the desired format, e.g., "March 25, 2024"
    today_date = datetime.now().strftime("%B %d, %Y")

    # Pass the name(s) and today's date to the template via context
    context = {
        'full_name': full_name,
        'today_date': today_date
    }

    return render(request, 'Independent_Contract_Agreement_html.html', context)

def university_autocomplete(request):
    if 'term' in request.GET:
        qs = Universities.objects.filter(name__icontains=request.GET['term'])[:10]  # Adjust the limit as needed
        universities = list(qs.values_list('name', flat=True))
        return JsonResponse(universities, safe=False)
    return JsonResponse([])

def major_autocomplete(request):
    if 'term' in request.GET:
        qs = Major.objects.filter(name__icontains=request.GET['term'])[:10]
        majors = list(qs.values_list('name', flat=True))
        return JsonResponse(majors, safe=False)
    return JsonResponse([])



#Class Email
class EmailThread(threading.Thread):
    def __init__(self, email):
        self.email = email
        threading.Thread.__init__(self)
    def run(self):
        self.email.send()


#Send Verification Email
def send_activation_email(user, request):
    current_site = get_current_site(request)
    email_subject = 'Activate your account'
    email_body = render_to_string('activate.html',{
        'user': user,
        'domain':current_site,
        'uid':urlsafe_base64_encode(force_bytes(user.pk)),
        'token': generate_email_token.make_token(user)
    })
    email = EmailMessage(subject=email_subject, body=email_body, from_email=settings.EMAIL_FROM_USER,to=[user.email])
    email.content_subtype = 'html'
    email.send()


def send_activation_email_view(request):
    user = request.user
    if not user.is_authenticated:
        messages.error(request, "You need to be logged in to activate your account.")
        return redirect('login')  # Assuming you have a 'login' named URL
    if not user.is_email_verified:
        send_activation_email(user, request)
        messages.success(request, "Activation email sent. Please check your inbox.")
    else:
        messages.info(request, "Your account is already activated.")
    return redirect('login')  # Redirect back to the profile page or wherever appropriate

#Activate User
def activate_user(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception as e:
        user = None

    if user and generate_email_token.check_token(user, token):
        user.is_email_verified = True
        user.save()
        messages.add_message(request, messages.SUCCESS,'Email verified, you can now login')
        return redirect(reverse('login'))
    return render(request, 'activate-failed.html', {"user": user})



def change_email(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            new_email = data['new_email']
            user = request.user

            # Validate the new email
            validate_email(new_email)
            if User.objects.filter(email=new_email).exists():
                return JsonResponse({'error': 'This email is already in use.'}, status=400)
            
            
            user.email = new_email
            user.is_email_verified = False
            user.save()
            
            send_activation_email(user, request)  # Ensure you define this function to send an activation email

            return JsonResponse({'success': 'Activation email sent. Please check your inbox.'})
        except ValidationError:
            return JsonResponse({'error': 'Invalid email.'}, status=400)
        except KeyError:
            return JsonResponse({'error': 'Incorrect data format. New email is required.'}, status=400)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON")
    else:
        return HttpResponseBadRequest("Invalid request method")
    

    
# REGISTER PAGE--------------------------------------------------------------------------------------
def register(request):
    return render(request, 'register.html')


# SEARCH SYSTEM--------------------------------------------------------------------------------------
def search(request):
    university_query = request.GET.get('university', '').upper()
    major_query = request.GET.get('major', '').upper()
    language_query = request.GET.get('language', '')
    education_level_query = request.GET.get('education_level', '')
    grade_level_query = request.GET.get('grade_level', '')
    keyword_query = request.GET.get('keywords', '').lower()


    # Initial filtered givers based on exact matches
    exact_filtered_givers = Giver.objects.filter(is_displaying=True, user__is_active=True, user__is_email_verified=True)
    if university_query:
        exact_filtered_givers = exact_filtered_givers.filter(university__icontains=university_query)
    if major_query:
        exact_filtered_givers = exact_filtered_givers.filter(major__name__icontains=major_query).distinct()

     # Apply additional filters if they are provided
    if language_query:
        exact_filtered_givers = exact_filtered_givers.filter(languages__id__icontains=language_query)
    if education_level_query:
        exact_filtered_givers = exact_filtered_givers.filter(education_level__icontains=education_level_query)
    if grade_level_query:
        exact_filtered_givers = exact_filtered_givers.filter(grade_level__icontains=grade_level_query)
    if keyword_query:
        exact_filtered_givers = exact_filtered_givers.annotate(
            lower_gender=Lower('gender'),
            lower_brief_introduction=Lower('brief_introduction'),
            lower_additional_information=Lower('additional_information'),
            lower_university=Lower('university'),
            lower_education_level=Lower('education_level'),
            lower_user_first_name=Lower('user__first_name'),
            lower_user_last_name=Lower('user__last_name'),
            lower_major_name=Lower('major__name'),
        ).filter(
            Q(lower_gender__icontains=keyword_query) |
            Q(languages__name__icontains=keyword_query) |
            Q(lower_brief_introduction__icontains=keyword_query) |
            Q(lower_additional_information__icontains=keyword_query) |
            Q(lower_university__icontains=keyword_query) |
            Q(lower_education_level__icontains=keyword_query) |
            Q(lower_user_first_name__icontains=keyword_query) |
            Q(lower_user_last_name__icontains=keyword_query) |
            Q(lower_major_name__icontains=keyword_query))

    # Calculate relevance for all givers, not just filtered ones
    givers_with_relevance = [(giver, calculate_relevance(giver, university_query, major_query)) for giver in Giver.objects.filter(is_displaying=True, user__is_active=True, user__is_email_verified=True)]
    
    # Sort all givers by relevance
    sorted_givers_with_relevance = sorted(givers_with_relevance, key=lambda x: x[1], reverse=True)
    
    # Separate exact matches from the rest based on relevance score
    exact_matches = [giver for giver, relevance in sorted_givers_with_relevance if giver in exact_filtered_givers]
    other_matches_by_relevance = [giver for giver, relevance in sorted_givers_with_relevance if giver not in exact_filtered_givers]

    all_matches = exact_matches + other_matches_by_relevance
    universities = Universities.objects.all()
    languages = Language.objects.all()

    request.session['exact_matches_ids'] = [giver.id for giver in all_matches[:4]]
    page_number = request.GET.get('page', 1)
    paginator = Paginator(all_matches, 10)

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        page_obj = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g., 9999), deliver last page of results.
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'selection2.html', {
        'query_university': university_query,
        'query_major': major_query,
        'page_obj': page_obj,
        'exact_matches': all_matches,
        'universities': universities,
        'languages': languages
    })


def calculate_relevance(giver, university_query, major_query):
    relevance_score = 0
    
    # Increase relevance score for exact university match
    if university_query.lower() in giver.university.lower():
        relevance_score += 10  # Higher score for direct university match
    
    # Increase relevance score for exact or related major match
    major_query_words = set(major_query.lower().split())
    for major in giver.major.all():
        giver_major_words = set(major.name.lower().split())
        for query_word in major_query_words:
            if query_word in giver_major_words:
                relevance_score += 5  # Adjust score for major match or relevance

    return relevance_score

########################################################################################
#       RESERVATION
########################################################################################


# GO TO PROFILE PAGE--------------------------------------------------------------------------------------
def profile(request, pk):
    profile = Giver.objects.get(id=pk)
    universities = Universities.objects.all()
    meetings = Meeting.objects.filter(giver=profile.user.username)
    available_times = profile.available_times.all()
    # Get the available slots, excluding those that conflict with existing meetings
    search_date = datetime.today().date()
    available_slots = get_available_slots(available_times, meetings, search_date)
    past_meetings = profile.giver_meetings.filter(is_successful=True)
    
    exact_matches_ids = request.session.get('exact_matches_ids', [])
    exact_matches = Giver.objects.filter(id__in=exact_matches_ids).exclude(id=pk)
    return render(request, 'profile2.html', {'profile': profile, 'givers':exact_matches, 'universities':universities, 'meetings':meetings, 'available_slots': available_slots, 'past_meetings': past_meetings, 'timezones': timezone_list()})


def search_slots(request):
    # Get the date from the AJAX request
    search_date_str = request.GET.get('date')
    if search_date_str:
        search_date = datetime.strptime(search_date_str, '%Y-%m-%d').date()
    else:
        search_date = now().date()  # Use today's date if none is provided

    day_of_week = search_date.strftime('%a').upper() 

    # Get the profile id from the session or another source
    pk = request.session.get('profile_id') or request.GET.get('pk')
    try:
        profile = Giver.objects.get(id=pk)
    except Giver.DoesNotExist:
        return JsonResponse({'error': 'Giver not found'}, status=404)
    
    # Filter available times by the day of the week
    available_times = profile.available_times.filter(day=day_of_week)

    # Prepare the datetime range for the selected date
    search_date_start = make_aware(datetime.combine(search_date, datetime.min.time()))
    search_date_end = make_aware(datetime.combine(search_date, datetime.max.time()))

    # Filter meetings based on the datetime range
    meetings = Meeting.objects.filter(datetime__range=(search_date_start, search_date_end), giver=profile.user.username) 

    # Get the available slots for the selected date, excluding those that conflict with existing meetings
    available_slots = get_available_slots(available_times, meetings, search_date)

    if search_date <= now().date():
        return JsonResponse({
            'slots': [],
            'message': 'No reservations can be made on the same day or past dates.',
        })


    if not available_slots:
    # Assuming pk is the Giver's ID and is available here
        next_available_date = find_next_available_date(search_date, pk)
        if next_available_date:
            return JsonResponse({
                'slots': [],
                'message': 'No available reservations.',
                'next_available_date': next_available_date.strftime('%Y-%m-%d')
            })
        else:
            return JsonResponse({
                'slots': [],
                'message': 'No available reservations in the near future.'
            })

    # Convert available_slots to a list of strings for JSON serialization
    slots = [slot for slot in available_slots]

    # Return a JSON response with the slots
    return JsonResponse({'slots': slots})

def get_available_slots(available_times, meetings, search_date, slot_duration=timedelta(minutes=30)):
    available_slots = []

    for availability in available_times:
        current_time = make_aware(datetime.combine(search_date, availability.start_time))
        end_time = make_aware(datetime.combine(search_date, availability.end_time))

        while current_time + slot_duration <= end_time + timedelta(minutes=1):
            slot_conflicts = any(
                ((meeting.datetime - timedelta(hours=1)) <= current_time < (meeting.datetime + timedelta(hours=1, minutes=30))) and not (meeting.is_rejected or meeting.is_cancelled)
                for meeting in meetings
            )
            if not slot_conflicts:
                available_slots.append(current_time.time())
            current_time += slot_duration

    return [slot.strftime('%I:%M %p') for slot in available_slots]




def find_next_available_date(start_date, giver_id, max_days=60):
    for day_offset in range(1, max_days + 1):
        potential_date = start_date + timedelta(days=day_offset)
        try:
            giver = Giver.objects.get(id=giver_id)
        except Giver.DoesNotExist:
            return None  # Or handle the error as appropriate

        day_of_week = potential_date.strftime('%a').upper()
        available_times = giver.available_times.filter(day=day_of_week)
        search_date_start = make_aware(datetime.combine(potential_date, datetime.min.time()))
        search_date_end = make_aware(datetime.combine(potential_date, datetime.max.time()))
        meetings = Meeting.objects.filter(datetime__range=(search_date_start, search_date_end), giver=giver.user.username)
        
        if get_available_slots(available_times, meetings, potential_date):
            return potential_date  # Found a day with available slots
    
    return None  # No available dates found within max_days


#GO TO CONFIRM RESERVATION PAGE

def confirm_reservation(request, pk):
    if request.user.is_authenticated:
        profiles = Giver.objects.get(id=pk)
        timezones = timezone_list()

        if request.user.is_mentor:  # Assuming is_mentor is a boolean field on your user model
            messages.add_message(request, messages.SUCCESS, 'You need a student account to reserve a meeting')
            return redirect('register_student')
        
        my_profile = Receiver.objects.get(user=request.user)
        receiver_timezone = pytz.timezone(my_profile.timezone)
        giver_timezone = pytz.timezone(profiles.timezone)
        
        # Retrieve date and time from the query parameters
        selected_date_str = request.GET.get('date', '')  # "YYYY-MM-DD"
        selected_time_str = request.GET.get('time', '')  # "02:00 PM"

        format_str = '%I:%M %p'  # Format for 12-hour time with AM/PM
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d')
        selected_time_naive = datetime.strptime(selected_time_str, format_str).time()
        selected_datetime_naive = datetime.combine(selected_date, selected_time_naive)

        # Localize to receiver's timezone
        selected_datetime_local = giver_timezone.localize(selected_datetime_naive)
        

        # Add an hour to calculate end_time
        end_datetime_local = selected_datetime_local + timedelta(hours=1)

        # Now, for comparison, convert the receiver's localized time to another timezone (e.g., US/Pacific)
        selected_datetime_in_profiles_timezone = selected_datetime_local.astimezone(receiver_timezone)
        end_datetime_in_profiles_timezone = end_datetime_local.astimezone(receiver_timezone)

        # Formatting for display
        formatted_selected_date_local = selected_datetime_local.strftime('%A, %B %d, %Y')
        selected_time_str_local = selected_datetime_local.strftime(format_str)
        end_time_str_local = end_datetime_local.strftime(format_str)

        formatted_selected_date_profiles_timezone = selected_datetime_in_profiles_timezone.strftime('%A, %B %d, %Y')
        selected_time_str_profiles_timezone = selected_datetime_in_profiles_timezone.strftime(format_str)
        end_time_str_profiles_timezone = end_datetime_in_profiles_timezone.strftime(format_str)

        selected_datetime_utc = selected_datetime_local.astimezone(pytz.utc)

        product = Product.objects.get(name="EarlyOn 1 Hour Meeting")

        context = {
            'selected_date': formatted_selected_date_local,  # Localized selected date in receiver's timezone
            'selected_time': selected_time_str_local,  # Localized selected time in receiver's timezone
            'end_time': end_time_str_local,  # Localized end time in receiver's timezone
            'selected_date_naive': formatted_selected_date_profiles_timezone,  # Selected date in comparison timezone
            'selected_time_naive': selected_time_str_profiles_timezone,  # Selected time in comparison timezone
            'end_time_naive': end_time_str_profiles_timezone,  # End time in comparison timezone
            'profiles': profiles,
            "product": product,
            "my_profile": my_profile,
            "timezones": timezones,
            "receiver_timezone": receiver_timezone,  # Receiver's timezone object
            "giver_timezone": giver_timezone,  # Comparison timezone object, assuming profiles.timezone is the source of the comparison timezone
            "utc_datetime": selected_datetime_utc,
            "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY
        }

        return render(request, 'confirm_reservation.html', context)
    else:
        messages.add_message(request, messages.SUCCESS, 'You need to login to reserve a meeting')
        return redirect('login')


#RESERVATION CONFIRMED
def confirmed(request,pk):
    if request.user.is_authenticated==True:
        profiles = Giver.objects.get(id=pk)
        student = Receiver.objects.get(username=request.user.username)
        meeting = Meeting.objects.create(giver=profiles.username, receiver=request.user.username)
        send_confirmation_email(meeting, profiles, student, request)
        return render(request, 'reservation_request_sent.html', {'profiles': profiles})
    else:
        messages.add_message(request, messages.SUCCESS,
                                    'You need to login to reserve a meeting')
        return redirect('login')

def update_timezone(request, pk):
    try:
        new_timezone = request.POST.get('timezone')
        receiver = Receiver.objects.get(id=pk)
        receiver.timezone = new_timezone
        receiver.save()

        meetings = Meeting.objects.filter(receiver=receiver.user.username)
        for meeting in meetings:
            # Split the existing timezone_info to preserve the giver's timezone
            giver_timezone, _ = meeting.timezone_info.split(',', 1)
            # Update only the receiver's timezone
            meeting.timezone_info = f"{giver_timezone},{new_timezone}"
            meeting.save()

        return JsonResponse({"status": "success", "message": "Timezone updated successfully."})
    except Giver.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Receiver not found."}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


#CONFIRM MEETING FROM MENTOR
def confirm_meeting(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        meeting = Meeting.objects.get(pk=uid)
    except Exception as e:
        meeting = None
    
    if meeting:
        # Check if current time is more than 12 hours before the meeting start time
        giver_timezone = pytz.timezone(meeting.giver_profile.timezone)
        now_in_givers_timezone = now().astimezone(giver_timezone)
        
        if now_in_givers_timezone > (meeting.datetime - timedelta(hours=12)):
            # Time limit exceeded
            return render(request, 'time-limit-exceeded.html', {"meeting": meeting})

        if generate_confirmation_token.check_token(meeting, token):
            giver = Giver.objects.get(user__username=meeting.giver)
            receiver = Receiver.objects.get(user__username=meeting.receiver)

            jwt_token = generate_access_token(settings.ZOOMMEETING_USER_ID, settings.ZOOMMEETING_CLIENT_ID, settings.ZOOMMEETING_CLIENT_SECRET)
            if jwt_token:
                zoom_meeting_details = create_meeting(
                    jwt_token,
                    settings.EMAIL_MAIN_USER,
                    f"Meeting with {receiver.user.get_full_name()}",
                    meeting.datetime,
                    meeting.timezone,
                )

                if zoom_meeting_details:
                    meeting.zoom_link = zoom_meeting_details.get('join_url')
                    meeting.zoom_meeting_id = str(zoom_meeting_details.get('id'))
                    meeting.zoom_start_url = zoom_meeting_details.get('start_url')
                    send_meeting_set(meeting, giver, receiver, request)
                    meeting.is_confirmed = True
                    meeting.save()


            return render(request, 'confirm_success.html', {"my_meeting": meeting, "giver": giver, "receiver": receiver})
    return render(request, 'activate-failed.html', {"meeting": meeting})


def reject_meeting(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        meeting = Meeting.objects.get(pk=uid)
    except Exception as e:
        meeting = None

    if meeting:
        # Check if current time is more than 12 hours before the meeting start time
        giver_timezone = pytz.timezone(meeting.giver_profile.timezone)
        now_in_givers_timezone = now().astimezone(giver_timezone)

        if now_in_givers_timezone > (meeting.datetime - timedelta(hours=12)):
            # Time limit exceeded
            return render(request, 'time-limit-exceeded.html', {"meeting": meeting})

        if generate_confirmation_token.check_token(meeting, token):
            meeting.is_rejected = True
            meeting.save()
            giver = Giver.objects.get(user__username=meeting.giver)
            receiver = Receiver.objects.get(user__username=meeting.receiver)
            send_meeting_rejected(meeting, giver, receiver, request)
            return render(request, 'reject_for_sure.html', {"my_meeting": meeting, "giver": giver, "profiles": receiver})

    return render(request, 'activate-failed.html', {"meeting": meeting})




########################################################################################
#       EMAILING
########################################################################################


#SEND COMFIRMATION EMAIL TO MENTOR
def send_confirmation_email(meeting, giver, receiver, request):
    current_site = get_current_site(request)
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

#MEETING RESERVATION COMPLETED EMAIL
def send_meeting_set(meeting, giver, receiver, request):
    current_site = get_current_site(request)
    timezone_info = f"{giver.timezone},{receiver.timezone}"
    start_datetime_formatted = date_format(meeting.datetime, "F j, Y, P")
    end_time_formatted = date_format(meeting.endtime, "P")
    start_datetime_converted = convert_timezone(meeting.datetime, timezone_info)
    end_time_converted = convert_timezone_time(meeting.endtime, timezone_info)
    email_subject = 'Meeting Confirmed With ' + str(receiver.user.get_full_name())
    email_body = render_to_string('email_meeting_set_mentor.html',{
        'meeting': meeting,
        'meeting_start': start_datetime_formatted,
        'meeting_end': end_time_formatted,
        'student': receiver,
        'giver': giver,
        'domain':current_site,
        'uid':urlsafe_base64_encode(force_bytes(meeting.pk)),
    })
    email_subject2 = 'Meeting Confirmed From ' + str(giver.user.get_full_name())
    email_body2 = render_to_string('email_meeting_set_student.html',{
        'meeting': meeting,
        'meeting_start': start_datetime_converted,
        'meeting_end': end_time_converted,
        'student': receiver,
        'giver': giver,
        'domain':current_site,
        'uid':urlsafe_base64_encode(force_bytes(meeting.pk)),
    })
    email = EmailMessage(subject=email_subject, body=email_body, from_email=settings.EMAIL_FROM_USER,to=[giver.user.email])
    email2 = EmailMessage(subject=email_subject2, body=email_body2, from_email=settings.EMAIL_FROM_USER,to=[receiver.user.email])
    email.content_subtype = 'html'
    email2.content_subtype = 'html'
    email.send()
    email2.send()


def send_meeting_cancelled(meeting, giver, receiver, request):
    current_site = get_current_site(request)
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
        'uid':urlsafe_base64_encode(force_bytes(meeting.pk)),
    })
    email = EmailMessage(subject=email_subject, body=email_body, from_email=settings.EMAIL_FROM_USER,to=[receiver.user.email])
    email.content_subtype = 'html'
    email.send()


def my_send_meeting_cancelled(meeting, giver, receiver, request):
    current_site = get_current_site(request)
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
        'uid':urlsafe_base64_encode(force_bytes(meeting.pk)),
    })
    email = EmailMessage(subject=email_subject, body=email_body, from_email=settings.EMAIL_FROM_USER,to=[giver.user.email])
    email.content_subtype = 'html'
    email.send()


def send_meeting_rejected(meeting, giver, receiver, request):
    current_site = get_current_site(request)
    timezone_info = f"{giver.timezone},{receiver.timezone}"
    start_datetime_converted = convert_timezone(meeting.datetime, timezone_info)
    end_time_converted = convert_timezone_time(meeting.endtime, timezone_info)
    email_subject = 'Meeting Rejected From ' + str(giver.user.get_full_name())
    email_body = render_to_string('email_meeting_rejected.html',{
        'meeting': meeting,
        'meeting_start': start_datetime_converted,
        'meeting_end': end_time_converted,
        'student':receiver,
        'giver': giver,
        'domain':current_site,
        'uid':urlsafe_base64_encode(force_bytes(meeting.pk)),
    })
    email = EmailMessage(subject=email_subject, body=email_body, from_email=settings.EMAIL_FROM_USER,to=[receiver.user.email])
    email.content_subtype = 'html'
    email.send()



########################################################################################
#       PROFILE - MENTOR
########################################################################################


#MY PROFLE PAGE
def my_profile(request, pk):
    if request.user.is_authenticated:
        try:
            my_profile = Giver.objects.get(user=request.user)  # Access Giver profile via User
            days_of_week = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
            time_slots = range(0, 24)  # assuming 9AM to 5PM, increment by 1 hour
            timezones = timezone_list()
            languages = Language.objects.all()
            selected_languages = [language.id for language in my_profile.languages.all()]
            selected_majors = list(my_profile.major.all().values('id', 'name'))
            # Convert each major into the format {id: ..., text: ...} for Select2
            selected_majors_for_select2 = [
                {"id": major["id"], "text": major["name"]} for major in selected_majors
            ]
            
            # Serialize this list to JSON to safely pass it into your JavaScript
            selected_majors_json = json.dumps(selected_majors_for_select2)
            
            monday_availabilities = my_profile.available_times.filter(day='MON')
            tuesday_availabilities = my_profile.available_times.filter(day='TUE')
            wednesday_availabilities = my_profile.available_times.filter(day='WED')
            thursday_availabilities = my_profile.available_times.filter(day='THU')
            friday_availabilities = my_profile.available_times.filter(day='FRI')
            saturday_availabilities = my_profile.available_times.filter(day='SAT')
            sunday_availabilities = my_profile.available_times.filter(day='SUN')
                        
            user_availabilities = list(my_profile.available_times.all().values('day', 'start_time', 'end_time'))

            # Convert start_time and end_time to string format before serialization
            for availability in user_availabilities:
                availability['start_time'] = availability['start_time'].strftime('%H:%M')
                # Check if end_time is '23:59' and convert it to '24:00'
                if availability['end_time'].strftime('%H:%M') == '23:59':
                    availability['end_time'] = "24:00"
                else:
                    availability['end_time'] = availability['end_time'].strftime('%H:%M')

            user_availabilities_json = json.dumps(user_availabilities, cls=DjangoJSONEncoder)

            return render(request, 'my_profile.html', {"my_profile": my_profile, "selected_languages":selected_languages, 
            'selected_majors_json': selected_majors_json,"timezones": timezones, "days_of_week": days_of_week, "time_slots":time_slots, "languages":languages,
            "monday_availabilities": monday_availabilities,
            "tuesday_availabilities": tuesday_availabilities,
            "wednesday_availabilities": wednesday_availabilities,
            "thursday_availabilities": thursday_availabilities,
            "friday_availabilities": friday_availabilities,
            "saturday_availabilities": saturday_availabilities,
            "sunday_availabilities": sunday_availabilities,
            "user_availabilities_json": user_availabilities_json})
        except Giver.DoesNotExist:
            return redirect('some_error_page')  # Redirect to an error page or similar
    return redirect(reverse('login'))


    
#MY MEETINGS PAGE
def my_meetings(request, pk):
    if request.user.is_authenticated:
        try:
            my_profile = Giver.objects.get(user__username=request.user.username)
            my_meetings = Meeting.objects.filter(giver=request.user.username)\
                .annotate(
                    sort_priority=Case(
                        When(Q(is_confirmed=False) & Q(is_completed=False) & Q(is_cancelled=False) & Q(is_rejected=False), then=Value(1)),  # Highest priority
                        When(is_confirmed=True, then=Value(2)),
                        When(Q(is_completed=True) & Q(is_successful=False) & Q(is_failed=False), then=Value(3)),
                        When(is_completed=True, then=Value(4)),  # Same priority as cancelled
                        default=Value(5),  # For any other status
                        output_field=IntegerField()
                    )
                ).order_by('sort_priority', 'datetime')
            return render(request, 'my_meetings.html', {"my_profile": my_profile, "my_meetings": my_meetings})
        except Giver.DoesNotExist:
            return redirect('some_error_page')
    return redirect(reverse('login'))

def my_payment_history(request, pk):
    if request.user.is_authenticated==True:
        my_profile = Giver.objects.get(user__username=request.user.username)
        payments = Payment.objects.filter(giver=my_profile).order_by('-date')
        return render(request, 'my_payment_history.html', {'payments': payments})
    return redirect(reverse('login'))


def my_guideline(request, pk):
    if request.user.is_authenticated==True:
        return render(request, 'my_guideline.html')
    return redirect(reverse('login'))


#MEETING CONFIRMATION SUCCESSFUL
def confirmation_successful(request, pk, pk2):
    if request.user.is_authenticated:
        my_meeting = Meeting.objects.get(id=pk2)
        giver_profile = my_meeting.giver_profile  # Assuming Meeting model has a Giver field
        receiver_profile = my_meeting.receiver_profile  # Assuming Meeting model has a Receiver field

        jwt_token = generate_access_token(settings.ZOOMMEETING_USER_ID, settings.ZOOMMEETING_CLIENT_ID, settings.ZOOMMEETING_CLIENT_SECRET)
        if jwt_token:
            zoom_meeting_details = create_meeting(
                jwt_token,
                settings.EMAIL_MAIN_USER,
                f"Meeting with {receiver_profile.user.get_full_name()}",
                my_meeting.datetime,
                my_meeting.timezone,
            )

            if zoom_meeting_details:
                my_meeting.zoom_link = zoom_meeting_details.get('join_url')
                my_meeting.zoom_meeting_id = str(zoom_meeting_details.get('id'))
                my_meeting.zoom_start_url = zoom_meeting_details.get('start_url')
                send_meeting_set(my_meeting, giver_profile, receiver_profile, request)
                my_meeting.is_confirmed = True
                my_meeting.save()
                # Proceed with notification logic or any further steps

        return render(request, 'my_confirm_success.html', {"my_meeting": my_meeting})
    return redirect(reverse('login'))


#MEETING REJECTION FROM MENTOR
def reject_reservation(request, pk, pk2):
    if request.user.is_authenticated:
        my_meeting = Meeting.objects.get(id=pk2)
        profile = my_meeting.receiver_profile  # Access directly if Meeting has a Receiver field
        return render(request, 'reject_reservation.html', {"my_meeting": my_meeting, "profiles": profile})
    return redirect(reverse('login'))


#MEETING REJECTED
def reject_for_sure(request, pk, pk2):
    if request.user.is_authenticated:
        my_meeting = Meeting.objects.get(id=pk2)
        my_meeting.is_rejected = True
        my_meeting.is_confirmed = False
        my_meeting.save()
        giver_profile = my_meeting.giver_profile
        receiver_profile = my_meeting.receiver_profile
        send_meeting_rejected(my_meeting, giver_profile, receiver_profile, request)
        return render(request, 'reject_for_sure.html', {"my_meeting": my_meeting, "profiles": receiver_profile})
    return redirect(reverse('login'))



#CANCEL RESERVATION
def my_cancel_reservation(request, pk, pk2):
    if request.user.is_authenticated==True:
        my_meeting = Meeting.objects.get(id=pk2)
        profile = Giver.objects.get(user__username=my_meeting.giver)
        receiver = Receiver.objects.get(user__username=my_meeting.receiver)
        return render(request, 'my_cancel_reservation.html', {"my_meeting": my_meeting, "profiles": profile, "receiver": receiver})
    return redirect(reverse('login'))


#CANCEL RESERVATION FOR SURE
def my_cancel_for_sure(request, pk, pk2):
    if request.user.is_authenticated==True:
        my_meeting = Meeting.objects.get(id=pk2)
        my_meeting.is_cancelled = True
        my_meeting.is_confirmed = False
        my_meeting.save()
        giver_profile = Giver.objects.get(user__username=my_meeting.giver)
        receiver_profile = Receiver.objects.get(user__username=my_meeting.receiver)
        send_meeting_cancelled(my_meeting, giver_profile, receiver_profile, request)
        return render(request, 'my_cancel_for_sure.html', {"my_meeting": my_meeting, "profiles": giver_profile, 'receiver': receiver_profile})
    return redirect(reverse('login'))


def my_settings(request, pk):
    if request.user.is_authenticated==True:
        my_profile = Giver.objects.get(user__username=request.user.username)
        return render(request, 'my_settings.html', {'my_profile': my_profile})
    return redirect(reverse('login'))


def my_delete_account(request, pk):
    if request.user.is_authenticated==True:
        user = request.user
        user.is_active = False  # Deactivate the user account
        user.save()  # Don't forget to save the user object after modification
        logout(request)  # Log the user out
        messages.success(request, 'Your account has been successfully removed.')
        return redirect(reverse('login'))
    return redirect(reverse('login'))
    

def deactivate_account(request, pk):
    if request.user.is_authenticated==True:
        giver = Giver.objects.get(user__username=request.user.username)
        if giver.is_displaying==True:
            giver.is_displaying = False
        else:
            giver.is_displaying = True
        giver.save()
        return redirect('my_profile', pk)
    return redirect(reverse('login'))


def pause_account(request, pk):
    if request.user.is_authenticated==True:
        giver = Giver.objects.get(user__username=request.user.username)
        if giver.is_working==True:
            giver.is_working = False
        else:
            giver.is_working = True
        giver.save()
        return redirect('my_profile', pk)
    return redirect(reverse('login'))


def my_update_profile(request, pk):
    if request.method == 'POST':
        my_profile = Giver.objects.get(user__username=request.user.username)
        user = request.user
        first_name = request.POST.get('firstname')
        last_name = request.POST.get('lastname')
        gender = request.POST.get('gender')
        # Specific to Giver
        university = request.POST.get('university')
        majors = request.POST.getlist('majors')  # Fetch multiple majors if applicable
        education_level = request.POST.get('education_level')
        grade_level = request.POST.get('grade_level')
        # File uploads
        imagefile = request.FILES.get('imagefile')
        resumefile = request.FILES.get('resumefile')
        
        # Additional information
        brief_introduction = request.POST.get('brief_introduction')
        linkedin = request.POST.get('linkedin', '')  # Default to empty string if not provided
        additional_information = request.POST.get('additional_information', '')  # Default to empty string if not provided
        
        timezone = request.POST.get('timezone')
        selected_languages = request.POST.getlist('languages')

        # Update the user's information
        user.first_name = first_name
        user.last_name = last_name
        my_profile.gender = gender
        my_profile.university = university
        
        my_profile.major.clear()
        for major in majors:
            if major.isdigit():
                major_instance = Major.objects.get(id=major)
            else:
                major_instance = Major.objects.get(name=major)
            my_profile.major.add(major_instance)

        my_profile.education_level = education_level
        my_profile.grade_level = grade_level

        if imagefile:
            my_profile.profile_image = imagefile
        if resumefile:
            my_profile.resume = resumefile

        my_profile.brief_introduction = brief_introduction
        my_profile.linkedin = linkedin
        my_profile.additional_information = additional_information
        my_profile.timezone = timezone

        my_profile.languages.clear()

        
        for language_id in selected_languages:
            language = Language.objects.get(id=language_id)
            my_profile.languages.add(language)


        days_of_week = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
        # Clear all available times before updating
        my_profile.availability.clear()
        AvailableTime.objects.filter(giver=my_profile).delete()
        for day in days_of_week:
            start_times = request.POST.getlist(f'{day}_start[]')
            end_times = request.POST.getlist(f'{day}_end[]')

            # Check if there are any times provided for the day
            if start_times and end_times:  # Proceed only if lists are not empty
                # Convert to datetime for easier manipulation and sorting
                time_slots = sorted([
                    (datetime.strptime(start_time_str, "%H:%M"), datetime.strptime(end_time_str if end_time_str != "00:00" else "23:59", "%H:%M"))
                    for start_time_str, end_time_str in zip(start_times, end_times)
                ], key=lambda x: x[0])  # Sort by start time

                merged_slots = []
                if time_slots:  # Ensure time_slots is not empty before proceeding
                    prev_start, prev_end = time_slots[0]

                    for start, end in time_slots[1:]:
                        if start <= prev_end:  # Overlapping or contiguous
                            prev_end = max(prev_end, end)  # Extend the previous slot
                        else:
                            merged_slots.append((prev_start, prev_end))  # Save the previous slot
                            prev_start, prev_end = start, end  # Start a new slot
                
                    # Don't forget to add the last slot
                    merged_slots.append((prev_start, prev_end))

                    # Save merged slots to database
                    for start, end in merged_slots:
                        # Convert back to time objects if necessary
                        start_time = start.time()
                        end_time = end.time()

                        # Create and link the availability time to the giver
                        available_time = AvailableTime.objects.create(
                            giver=my_profile,
                            day=day,
                            start_time=start_time,
                            end_time=end_time,
                            timezone=timezone
                        )
            else:
                # Handle days with no start and end times provided
                print(f"No times provided for {day}.")


        my_profile.save()
        user.save()

        messages.success(request, "Your profile has been updated.")
        return redirect('my_profile', pk)  # Redirect to the profile page or wherever appropriate

    # If not POST, render the form page (you might also handle this GET request differently)
    return render(request, 'my_profile.html', {"my_profile":my_profile})



def my_profile_view_agreement(request):
    if request.user.is_authenticated:
        try:
            my_profile = Giver.objects.get(user__username=request.user.username)
            signature_data = my_profile.signature_data_url  # Assuming 'signature' is the field name where the data URL is stored
            return render(request, 'Independent_Contract_Agreement_Profile.html', {'signature_data': signature_data, 'my_profile': my_profile})
        except Giver.DoesNotExist:
            return HttpResponse("User profile not found.", status=404)
    else:
        return redirect('login')



#MEETING FAILED
def my_meeting_failed(request, pk, pk2):
    if request.user.is_authenticated==True:
        my_meeting = Meeting.objects.get(id=pk2)
        return render(request,'my_meeting_failed.html', {"my_meeting": my_meeting})
    return redirect(reverse('login'))

def my_submitted_reason(request, pk, pk2):
    if request.user.is_authenticated:
        # Get the meeting instance
        my_meeting = Meeting.objects.get(id=pk2)
        
        if request.method == 'GET':
            # Collecting selected reasons based on the checkbox values directly
            failure_reasons = [value for key, value in request.GET.items() if key.startswith('failure_checkbox')]

            detailed_reason = request.GET.get('reasoning-input', '').strip()

            # Update the meeting instance
            my_meeting.is_failed_by_giver = True  # Assuming this view is only for receivers, adjust as needed
            my_meeting.failed_reason_by_giver = ', '.join(failure_reasons) + " | Detailed reason: " + detailed_reason
            my_meeting.save()

            # Prepare the email message
            email_subject = f"New failure request submission: {my_meeting.giver_profile.user.get_full_name()} "
            email_message = f"Meeting ID: {my_meeting.id}\n\n Reason: {my_meeting.failed_reason_by_giver}\n\n Mentor: {my_meeting.giver_profile.user.get_full_name()}\n\n Mentor Username: {my_meeting.giver_profile.user.username}\n\n Mentee: {my_meeting.receiver_profile.user.get_full_name()}\n\n Mentee Username: {my_meeting.receiver_profile.user.username}\n\n"
            # Send email
            send_mail(
                subject=email_subject,
                message=email_message,
                from_email=my_meeting.giver_profile.user.email,
                recipient_list=[settings.EMAIL_FROM_USER],
            )

            return render(request,'my_submitted_reason.html', {"my_meeting": my_meeting})
    else:
        return redirect(reverse('login'))




#UPLOAD VIDEO AFTER MEETING
def upload_video(request, pk, pk2):
    if request.user.is_authenticated==True :
        my_meeting = Meeting.objects.get(id=pk2)
        my_meeting.is_waiting_for_video = True
        my_meeting.is_video_uploaded = False
        my_meeting.save()
        if request.method == 'POST' and request.FILES['videofile']:
            fs = FileSystemStorage()
            videofile = request.FILES['videofile']
            fs.save(videofile.name, videofile)
            my_meeting.video = videofile
            my_meeting.is_waiting_for_video = False
            my_meeting.is_video_uploaded = True
            my_meeting.save()
            return render(request, 'video_upload_completed.html', {"my_meetings": my_meeting})
        return render(request, 'upload_video.html', {"my_meeting": my_meeting})
    return redirect(reverse('login'))



########################################################################################
#       PROFILE - STUDENT
########################################################################################


#STUDENT PROFILE PAGE
def student_profile(request, pk):
    if request.user.is_authenticated:
        try:
            # Assuming Receiver model has a OneToOne link to User model as 'user' field
            my_profile = Receiver.objects.get(user__username=request.user.username)
            timezones = timezone_list()
            return render(request, 'student_profile.html', {"my_profile": my_profile, "timezones": timezones})
        except Receiver.DoesNotExist:
            return redirect(reverse('login'))  # Or any other appropriate action
    return redirect(reverse('login'))

@login_required
def update_profile(request, pk):
    if request.method == 'POST':
        my_profile = Receiver.objects.get(user__username=request.user.username)
        user = request.user
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        timezone = request.POST.get('timezone')

        # Validate the input if necessary
        if not first_name or not last_name or not timezone:
            messages.error(request, "Name sections cannot be empty.")
            return redirect('profile_update')

        # Check if the username already exists
        if User.objects.exclude(pk=user.pk).filter(username=user.username).exists():
            messages.error(request, "Username is already taken.")
            return redirect('profile_update')

        # Update the user's information
        user.first_name = first_name
        user.last_name = last_name
        my_profile.timezone = timezone
        my_profile.save()
        user.save()


        meetings = Meeting.objects.filter(receiver=my_profile.user.username)
        for meeting in meetings:
            # Split the existing timezone_info to preserve the giver's timezone
            giver_timezone, _ = meeting.timezone_info.split(',', 1)
            # Update only the receiver's timezone
            meeting.timezone_info = f"{giver_timezone},{timezone}"
            meeting.save()


        messages.success(request, "Your profile has been updated.")
        return redirect('student_profile', pk)  # Redirect to the profile page or wherever appropriate

    # If not POST, render the form page (you might also handle this GET request differently)
    return render(request, 'student_profile.html', {"my_profile":my_profile})

#STUDENT MEETINGS PAGE
def student_meetings(request, pk):
    if request.user.is_authenticated==True:
        try:
            my_profile = Receiver.objects.get(user__username=request.user.username)
            my_meetings = Meeting.objects.filter(receiver=request.user.username)\
                .annotate(
                    sort_priority=Case(
                        When(is_confirmed=True, then=Value(1)),
                        When(Q(is_confirmed=False) & Q(is_completed=False) & Q(is_cancelled=False) & Q(is_rejected=False), then=Value(2)), 
                        When(Q(is_completed=True) & Q(is_successful=False) & Q(is_failed=False), then=Value(3)),
                        When(is_completed=True, then=Value(4)),  # Same priority as cancelled
                        default=Value(5),  # For any other status
                        output_field=IntegerField()
                    )
                ).order_by('sort_priority', 'datetime')
            return render(request, 'student_meetings.html', {"my_profile": my_profile, "my_meetings": my_meetings})
        except Giver.DoesNotExist:
            return redirect('some_error_page')
    return redirect(reverse('login'))

def payment_history(request, pk):
    if request.user.is_authenticated==True:
        my_profile = Receiver.objects.get(user__username=request.user.username)
        payments = Payment.objects.filter(receiver=my_profile).order_by('-date')
        return render(request, 'student_payment_history.html', {'payments': payments})
    return redirect(reverse('login'))

def student_settings(request, pk):
    if request.user.is_authenticated==True:
        my_profile = Receiver.objects.get(user__username=request.user.username)
        return render(request, 'student_settings.html', {'my_profile': my_profile})
    return redirect(reverse('login'))


def delete_account(request, pk):
    if request.user.is_authenticated==True:
        user = request.user
        user.is_active = False  # Deactivate the user account
        user.save()  # Don't forget to save the user object after modification
        logout(request)  # Log the user out
        messages.success(request, 'Your account has been successfully removed.')
        return redirect(reverse('login'))
    return redirect(reverse('login'))



#SUBMIT RATING
def submit_rating(request, pk, pk2):
    if request.user.is_authenticated==True:
        my_meeting = Meeting.objects.get(id=pk2)
        return render(request, 'submit_rating.html', {"my_meeting": my_meeting})
    return redirect(reverse('login'))


#RATING COMPLETED
def rating_upload_completed(request, pk, pk2):
    if request.user.is_authenticated==True:
        if request.method == 'GET':
            star= request.GET.get('rate')
            feedback = request.GET.get('feedback-input')
            my_meeting = Meeting.objects.get(id=pk2)
            my_meeting.is_waiting_for_rating = False
            my_meeting.is_rating_submitted = True
            my_meeting.is_successful = True
            my_meeting.stars = int(star)
            my_meeting.feedback = feedback
            my_meeting.save()
            return render(request, 'rating_upload_completed.html', {"my_meetings": my_meeting})
    return redirect(reverse('login'))


#CANCEL RESERVATION
def cancel_reservation(request, pk, pk2):
    if request.user.is_authenticated==True:
        my_meeting = Meeting.objects.get(id=pk2)
        profile = Giver.objects.get(user__username=my_meeting.giver)
        receiver = Receiver.objects.get(user__username=my_meeting.receiver)
        return render(request, 'cancel_reservation.html', {"my_meeting": my_meeting, "profiles": profile, "receiver": receiver})
    return redirect(reverse('login'))


#CANCEL RESERVATION FOR SURE
def cancel_for_sure(request, pk, pk2):
    if request.user.is_authenticated==True:
        my_meeting = Meeting.objects.get(id=pk2)
        my_meeting.is_cancelled = True
        my_meeting.is_confirmed = False
        my_meeting.save()
        giver_profile = Giver.objects.get(user__username=my_meeting.giver)
        receiver_profile = Receiver.objects.get(user__username=my_meeting.receiver)
        my_send_meeting_cancelled(my_meeting, giver_profile, receiver_profile, request)
        return render(request, 'cancel_for_sure.html', {"my_meeting": my_meeting, "profiles": giver_profile, 'receiver': receiver_profile})
    return redirect(reverse('login'))


#MEETING FAILED
def meeting_failed(request, pk, pk2):
    if request.user.is_authenticated==True:
        my_meeting = Meeting.objects.get(id=pk2)
        return render(request,'student_meeting_failed.html', {"my_meeting": my_meeting})
    return redirect(reverse('login'))

def submitted_reason(request, pk, pk2):
    if request.user.is_authenticated:
        # Get the meeting instance
        my_meeting = Meeting.objects.get(id=pk2)
        
        if request.method == 'GET':
            # Collecting selected reasons based on the checkbox values directly
            failure_reasons = [value for key, value in request.GET.items() if key.startswith('failure_checkbox')]

            detailed_reason = request.GET.get('reasoning-input', '').strip()

            # Update the meeting instance
            my_meeting.is_waiting_for_rating = False
            my_meeting.is_failed_by_receiver = True  # Assuming this view is only for receivers, adjust as needed
            my_meeting.failed_reason_by_receiver = ', '.join(failure_reasons) + " | Detailed reason: " + detailed_reason
            my_meeting.save()

            # Prepare the email message
            email_subject = f"New failure request submission: {my_meeting.receiver_profile.user.get_full_name()} "
            email_message = f"Meeting ID: {my_meeting.id}\n\n Reason: {my_meeting.failed_reason_by_receiver}\n\n Mentor: {my_meeting.giver_profile.user.get_full_name()}\n\n Mentor Username: {my_meeting.giver_profile.user.username}\n\n Mentee: {my_meeting.receiver_profile.user.get_full_name()}\n\n Mentee Username: {my_meeting.receiver_profile.user.username}\n\n"
            # Send email
            send_mail(
                subject=email_subject,
                message=email_message,
                from_email=my_meeting.receiver_profile.user.email,
                recipient_list=[settings.EMAIL_FROM_USER],
            )

            return render(request,'submitted_reason.html', {"my_meeting": my_meeting})
    else:
        return redirect(reverse('login'))



#STRIPE API

stripe.api_key = settings.STRIPE_SECRET_KEY

class SuccessView(TemplateView):
    template_name = "reservation_request_sent.html"

class CancelView(TemplateView):
    template_name = "payment_cancel.html"

class CreateCheckoutSessionView(View):
    def post(self, request, *args, **kwargs):
        product_id = self.kwargs["pk2"]
        user_id = self.kwargs["pk"]
        giver = Giver.objects.get(id=user_id)
        product = Product.objects.get(id=product_id)
        YOUR_DOMAIN = settings.SITE_URL
        data = json.loads(request.body)
        meeting_date = data.get('selected_date')
        meeting_time = data.get('selected_time')
        meeting_end_time = data.get('end_time')
        utc_datetime = data.get('utc_datetime')
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': product.price,
                        'product_data': {
                            'name': product.name,
                        },
                    },
                    'quantity': 1,
                },
            ],
            metadata={
                "product_id": product.id,
                "user_id": giver.id,
                "my_id": request.user.username,
                "meeting_date": meeting_date,
                "meeting_time": meeting_time,
                "meeting_end_time": meeting_end_time,
                "utc_datetime": utc_datetime
            },
            mode='payment',
                success_url=YOUR_DOMAIN + '/profile/'+str(user_id)+'/success/'+str(product_id)+'/',
                cancel_url=YOUR_DOMAIN + '/profile/'+str(user_id),
        )
        return JsonResponse({
            'id': checkout_session.id,
        })
    
def flexible_parse_datetime(date_string):
    date_formats = [
        '%B %d, %Y, %I:%M %p',  # Format with minutes
        '%B %d, %Y, %I %p'      # Format without minutes
    ]
    
    for date_format in date_formats:
        try:
            return datetime.strptime(date_string, date_format)
        except ValueError:
            continue
    raise ValueError(f"time data '{date_string}' does not match any expected format")

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        customer_email = session["customer_details"]["email"]
        product_id = session["metadata"]["product_id"]
        user_id = session["metadata"]["user_id"]
        my_id = session["metadata"]["my_id"]
        meeting_date = session["metadata"]["meeting_date"]
        meeting_time = session["metadata"]["meeting_time"]
        meeting_end_time = session["metadata"]["meeting_end_time"]
        utc_datetime = session["metadata"]["utc_datetime"]
        
        date_obj = datetime.strptime(meeting_date, '%A, %B %d, %Y').date()
        time_obj = datetime.strptime(meeting_time, '%I:%M %p').time()
        end_time_obj = datetime.strptime(meeting_end_time, '%I:%M %p').time()

        combined_datetime = datetime.combine(date_obj, time_obj)
        combined_end_datetime = datetime.combine(date_obj, end_time_obj)

        modified_utc_datetime = utc_datetime.replace('a.m.', 'AM').replace('p.m.', 'PM')

        
        utc_datetime_obj = flexible_parse_datetime(modified_utc_datetime)
        
        product = Product.objects.get(id=product_id)
        giver = Giver.objects.get(id=user_id)

        """
        email_subject = "Here is your product"
        email_body = f"Thanks for your purchase. Here is the product you ordered. The URL is {product.url}",
        email = EmailMessage(subject=email_subject, body=email_body, from_email=settings.EMAIL_FROM_USER,to=[customer_email])
        EmailThread(email).start()
        """

        student = Receiver.objects.get(user__username=my_id)
        timezone_info = f"{giver.timezone},{student.timezone}"

        meeting = Meeting.objects.create(giver=giver.user.username, giver_profile=giver, receiver_profile=student, receiver=my_id, datetime=combined_datetime, endtime=combined_end_datetime, timezone=giver.timezone, timezone_info=timezone_info, utc_datetime=utc_datetime_obj)
        meeting.save()

        
        Payment.objects.create(
            receiver=student,
            amount=product.price / 100, # Convert to dollars
            status='succeeded',
            transaction_id=event['data']['object']['id'],
            giver=giver,
            meeting=meeting
        )

        send_confirmation_email(meeting, giver, student, request)

    return HttpResponse(status=200)

class StripeAuthorizeView(View):
    def get(self, request, *args, **kwargs):
        user_id = self.kwargs["pk"]
        YOUR_DOMAIN = settings.SITE_URL
        # Create a new Express account
        account = stripe.Account.create(
            type='express',
            country='US',
            email=request.user.email,  # Ideally, this should come from your user model
        )
        
        # Here, save the stripe_account_id to your user or a related model
        try:
            giver = Giver.objects.get(user=request.user)  # Adjust based on your user model relation
        except Giver.DoesNotExist:
            giver = Giver(user=request.user)

        giver.stripe_account_id = account.id
        giver.save()

        # Create an account link for onboarding the user
        account_link = stripe.AccountLink.create(
            account=account.id,
            refresh_url=YOUR_DOMAIN + '/my_profile/'+str(user_id),  # URL to redirect users if they need to re-authenticate
            return_url=YOUR_DOMAIN + '/my_profile/'+str(user_id)+'/stripe/callback/',  # URL to redirect users after completion
            type='account_onboarding',
        )

        # Redirect to the account_link URL
        return HttpResponseRedirect(account_link.url)
    

class StripeAuthorizeCallbackView(View):
    def get(self, request, *args, **kwargs):
        # For Express accounts, you might not deal with 'code'
        # Instead, you could simply notify the user of success or perform additional checks here
        if request.user.is_authenticated:
            giver = Giver.objects.get(user=request.user)
            giver.is_payout_setup = True
            giver.save()
            # Perform any necessary actions, such as confirming the account setup via Stripe API
            # Redirect to the profile or a confirmation page
            return redirect(reverse('my_profile', kwargs={'pk': request.user.id}))
        else:
            messages.add_message(request, messages.ERROR, 'You are not logged in.')
            return redirect(reverse('login'))


class StripeDashboardView(View):
    def get(self, request, *args, **kwargs):
        user_id = self.kwargs["pk"]
        YOUR_DOMAIN = settings.SITE_URL
        try:
            giver = Giver.objects.get(user_id=user_id)
            stripe_account_id = giver.stripe_account_id
            # Ensure the user has a Stripe account ID saved
            if stripe_account_id:
                account_link = stripe.AccountLink.create(
                    account=stripe_account_id,
                    refresh_url=YOUR_DOMAIN + '/my_profile/'+str(user_id),  # Adjust as needed
                    return_url=YOUR_DOMAIN + '/my_profile/'+str(user_id),  # Adjust as needed
                    type='account_onboarding',
                )
                return HttpResponseRedirect(account_link.url)
            else:
                messages.error(request, "Stripe account not configured correctly.")
                return redirect(reverse('my_profile', kwargs={'pk': user_id}))
        except Giver.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect(reverse('home'))
