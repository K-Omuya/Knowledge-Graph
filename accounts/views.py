# Replace this line in views.py
from accounts.models import UserActivity
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm  # Add AuthenticationForm here
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.models import User
from django import forms
# With this temporary solution
try:
 from accounts.models import UserActivity
except ImportError:
 # Define a minimal version for now
 from django.db import models
 from django.contrib.auth.models import User
 
 class UserActivity(models.Model):
     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
     activity_type = models.CharField(max_length=10)
     content_type = models.CharField(max_length=20) 
     object_id = models.IntegerField()
     timestamp = models.DateTimeField(auto_now_add=True)
     details = models.TextField(blank=True)
     
     def __str__(self):
         return f"{self.user.username} {self.activity_type} {self.content_type}"


from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.models import User
from django import forms

class ExtendedUserCreationForm(UserCreationForm):
    """Extended user creation form with email and name fields"""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
        return user


def register_view(request):
    """View for user registration"""
    if request.method == 'POST':
        form = ExtendedUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Automatically log in the user
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            
            messages.success(request, f'Account created for {username}. You are now logged in.')
            return redirect('index')
    else:
        form = ExtendedUserCreationForm()
    
    return render(request, 'register.html', {'form': form})


def login_view(request):
    """Custom login view"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.POST.get('next', 'index')
                messages.success(request, f'Welcome back, {username}!')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'login.html', {'form': form})         