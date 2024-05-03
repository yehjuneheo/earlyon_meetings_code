from django import forms
from .models import *

class RegisterTeacherForm(forms.ModelForm):
    firstname = forms.CharField(required=True)
    lastname = forms.CharField(required=True)
    username = forms.CharField(required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    password2 = forms.CharField(label='Confirm password', widget=forms.PasswordInput, required=True)
    gender = forms.ChoiceField(choices=[('male', 'Male'), ('female', 'Female'), ...], required=True)
    university = forms.CharField(required=True)
    majors = forms.ModelMultipleChoiceField(queryset=Major.objects.all(), widget=forms.CheckboxSelectMultiple, required=True)
    education_level = forms.ChoiceField(choices=[('associate', 'Associate'), ('bachelor', 'Bachelor\'s'), ...], required=True)
    grade_level = forms.ChoiceField(choices=[('freshman', 'Freshman'), ('sophomore', 'Sophomore'), ...], required=True)
    brief_introduction = forms.CharField(widget=forms.Textarea, required=True)
    linkedin = forms.URLField(required=False)
    additional_information = forms.CharField(widget=forms.Textarea, required=False)
    profile_image = forms.ImageField(required=False)
    resume = forms.FileField(required=False)

    class Meta:
        model = User
        fields = ['firstname', 'lastname', 'username', 'email', 'password', 'password2', 'gender', 'university', 'majors', 'education_level', 'grade_level', 'brief_introduction', 'linkedin', 'additional_information', 'profile_image', 'resume']
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")

        if password != password2:
            self.add_error('password2', "Password does not match")

        return cleaned_data

