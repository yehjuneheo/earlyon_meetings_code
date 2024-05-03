from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from . import views
from django.contrib.auth import views as auth_views
from .views import check_username

urlpatterns = [
    path('', views.home, name='home'),
    path('selection', views.selection, name='selection'),
    path('about_us', views.about_us, name='about_us'),
    path('contact_us', views.contact_us, name='contact_us'),
    path('privacy_policy', views.privacy_policy, name='privacy_policy'),
    path('terms_and_conditions', views.terms_and_conditions, name='terms_and_conditions'),
    path('cookie_policy', views.cookie_policy, name='cookie_policy'),
    path('help', views.help, name='help'),
    
    path('login', views.login, name='login'),
    path('logout', views.logout_view, name='logout_view'),
    path('register', views.register, name='register'),
    path('register/register_teacher', views.register_teacher, name='register_teacher'),
    path('register/register_student', views.register_student, name='register_student'),
    path('send-activation-email/', views.send_activation_email_view, name='send_activation_email'),
    path('ajax/check_username/', check_username, name='check_username'),
    path('agreement/', views.agreement_view, name="agreement"),
    path('university-autocomplete/', views.university_autocomplete, name='university-autocomplete'),
    path('major-autocomplete/', views.major_autocomplete, name='major-autocomplete'),
    path('change-email/', views.change_email, name='change_email'),

    path('reset_password', auth_views.PasswordResetView.as_view(template_name="password_reset.html"), name="reset_password"),
    path('reset_password_sent', auth_views.PasswordResetDoneView.as_view(template_name="password_reset_sent.html"), name="password_reset_done"),
    path('reset/<uidb64>/<token>', auth_views.PasswordResetConfirmView.as_view(template_name="password_reset_form.html"), name="password_reset_confirm"),
    path('reset_password_complete', auth_views.PasswordResetCompleteView.as_view(template_name="password_reset_done.html"), name="password_reset_complete"),

    path('search', views.search, name='search'),
    path('profile/<int:pk>', views.profile, name='profile'),
    path('ajax/search_slots/', views.search_slots, name='search_slots'),
    
    path('profile/<int:pk>/create_checkout_session/<str:pk2>', views.CreateCheckoutSessionView.as_view(), name='create-checkout-session'),
    path('webhook', views.stripe_webhook, name='stripe-webhook'),
    path('profile/<int:pk>/success/<str:pk2>/', views.SuccessView.as_view(), name='success'),

    path('profile/<int:pk>/confirm_reservation', views.confirm_reservation, name='confirm_reservation'),
    path('profile/<int:pk>/confirm_reservation/confirmed', views.confirmed, name='confirmed'),
    path('activate-user<uidb64>/<token>', views.activate_user, name='activate'),
    path('confirm_meeting<uidb64>/<token>', views.confirm_meeting, name='confirm_meeting'),
    path('reject_meeting<uidb64>/<token>', views.reject_meeting, name='reject_meeting'),
    path('update-timezone/<str:pk>/', views.update_timezone, name='update_timezone'),

    path('student_profile/<str:pk>', views.student_profile, name='student_profile'),
    path('student_profile/<str:pk>/student_meetings', views.student_meetings, name='student_meetings'),
    path('student_profile/<str:pk>/payment_history', views.payment_history, name='payment_history'),
    path('student_profile/<str:pk>/settings', views.student_settings, name='student_settings'),
    path('student_profile/<str:pk>/settings/delete_account/', views.delete_account, name='delete_account'),
    path('student_profile/<str:pk>/update', views.update_profile, name='profile_update'),
    path('student_profile/<str:pk>/student_meetings/cancel_reservation/<str:pk2>', views.cancel_reservation, name='cancel_reservation'),
    path('student_profile/<str:pk>/student_meetings/cancel_reservation/<str:pk2>/cancelled', views.cancel_for_sure, name='cancel_for_sure'),
    path('student_profile/<str:pk>/student_meetings/submit_rating/<str:pk2>', views.submit_rating, name='submit_rating'),
    path('student_profile/<str:pk>/student_meetings/submit_rating/<str:pk2>/rating_upload_completed', views.rating_upload_completed, name='rating_upload_completed'),
    path('student_profile/<str:pk>/student_meetings/meeting_failed/<str:pk2>', views.meeting_failed, name='meeting_failed'),
    path('student_profile/<str:pk>/student_meetings/meeting_failed/<str:pk2>/submitted_reason', views.submitted_reason, name='submitted_reason'),

    path('my_profile/<str:pk>', views.my_profile, name='my_profile'),
    path('my_profile/<str:pk>/my_meetings', views.my_meetings, name='my_meetings'),
    path('my_profile/<str:pk>/my_guideline', views.my_guideline, name='my_guideline'),
    path('my_profile/<str:pk>/my_payment_history', views.my_payment_history, name='my_payment_history'),
    path('my_profile/<str:pk>/my_meetings/confirmation_successful/<str:pk2>', views.confirmation_successful, name='confirmation_successful'),
    path('my_profile/<str:pk>/my_meetings/reject_reservation/<str:pk2>', views.reject_reservation, name='reject_reservation'),
    path('my_profile/<str:pk>/my_meetings/reject_reservation/<str:pk2>/rejected', views.reject_for_sure, name='reject_for_sure'),
    path('my_profile/<str:pk>/my_meetings/cancel_reservation/<str:pk2>', views.my_cancel_reservation, name='my_cancel_reservation'),
    path('my_profile/<str:pk>/my_meetings/cancel_reservation/<str:pk2>/cancelled', views.my_cancel_for_sure, name='my_cancel_for_sure'),
    path('my_profile/<str:pk>/my_meetings/meeting_failed/<str:pk2>', views.my_meeting_failed, name='my_meeting_failed'),
    path('my_profile/<str:pk>/my_meetings/meeting_failed/<str:pk2>/submitted_reason', views.my_submitted_reason, name='my_submitted_reason'),
    path('my_profile/<str:pk>/my_meetings/upload_video/<str:pk2>', views.upload_video, name='upload_video'),
    path('my_profile/<str:pk>/settings', views.my_settings, name='my_settings'),
    path('my_profile/<str:pk>/update', views.my_update_profile, name='my_update_profile'),
    path('my_profile/<str:pk>/settings/delete_account/', views.my_delete_account, name='my_delete_account'),
    path('my_profile/<str:pk>/settings/deactivate_account/', views.deactivate_account, name='deactivate_account'),
    path('my_profile/<str:pk>/settings/pause_account/', views.pause_account, name='pause_account'),
    path('view_agreement/', views.my_profile_view_agreement, name='view_agreement'),
    path('my_profile/<str:pk>/stripe/authorize/', views.StripeAuthorizeView.as_view(), name='authorize'),
    path('my_profile/<str:pk>/stripe/callback/', views.StripeAuthorizeCallbackView.as_view(), name='authorize_callback'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)