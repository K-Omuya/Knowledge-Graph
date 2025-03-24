from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django import forms
from django.core.paginator import Paginator
from django.db.models import Q

from .models import UserProfile, UserActivity

class UserForm(forms.ModelForm):
    """Form for updating user information"""
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'username')

class ProfileForm(forms.ModelForm):
    """Form for updating user profile information"""
    class Meta:
        model = UserProfile
        fields = ('bio', 'profile_picture', 'institution', 'department', 'position')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

@login_required
def user_profile_view(request):
    """View for user profile page"""
    user = request.user
    
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        # Create profile if it doesn't exist
        profile = UserProfile.objects.create(user=user)
    
    # Get user activity
    recent_activities = UserActivity.objects.filter(user=user).order_by('-timestamp')[:10]
    
    # Get contributions
    try:
        from knowledge_app.models import KnowledgeNode, Relationship
        from knowledge_app.models_learning import LearningPath, UserProgress
        
        # Counts for different contribution types
        contributions = {
            'nodes': KnowledgeNode.objects.filter(creator=user).count(),
            'relationships': Relationship.objects.filter(creator=user).count(),
            'comments': UserActivity.objects.filter(user=user, activity_type='COMMENT').count(),
        }
        
        # Progress metrics
        completed_paths = UserProgress.objects.filter(user=user, status='COMPLETED').count()
        progress = {
            'completed_paths': completed_paths,
        }
        
        # Get created content for the contributions tab
        created_nodes = KnowledgeNode.objects.filter(creator=user).order_by('-created_at')[:5]
        created_nodes_count = KnowledgeNode.objects.filter(creator=user).count()
        created_relationships = Relationship.objects.filter(creator=user).order_by('-created_at')[:5]
        created_relationships_count = Relationship.objects.filter(creator=user).count()
        created_paths = LearningPath.objects.filter(creator=user).order_by('-created_at')[:4]
        
        # Learning progress
        learning_progress = UserProgress.objects.filter(user=user).select_related('path')[:6]
        
        # Quiz attempts
        try:
            from knowledge_app.models_assessment import QuizAttempt
            quiz_attempts = QuizAttempt.objects.filter(user=user).select_related('quiz').order_by('-started_at')[:4]
        except:
            quiz_attempts = []
    except:
        # Fallback if models aren't fully implemented yet
        contributions = {'nodes': 0, 'relationships': 0, 'comments': 0}
        progress = {'completed_paths': 0}
        created_nodes = []
        created_nodes_count = 0
        created_relationships = []
        created_relationships_count = 0
        created_paths = []
        learning_progress = []
        quiz_attempts = []
    
    context = {
        'profile': profile,
        'recent_activities': recent_activities,
        'contributions': contributions,
        'progress': progress,
        'created_nodes': created_nodes,
        'created_nodes_count': created_nodes_count,
        'created_relationships': created_relationships,
        'created_relationships_count': created_relationships_count,
        'created_paths': created_paths,
        'learning_progress': learning_progress,
        'quiz_attempts': quiz_attempts,
    }
    
    return render(request, 'user_profile.html', context)

@login_required
def user_activity_view(request):
    """View for user activity history"""
    user = request.user
    
    # Get filter params
    activity_type = request.GET.get('activity_type')
    content_type = request.GET.get('content_type')
    
    # Build query
    query = Q(user=user)
    
    if activity_type:
        query &= Q(activity_type=activity_type)
    
    if content_type:
        query &= Q(content_type=content_type)
    
    # Get activities based on filters
    activities = UserActivity.objects.filter(query).order_by('-timestamp')
    
    # Paginate results
    paginator = Paginator(activities, 20)  # 20 activities per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
    }
    
    return render(request, 'user_activity.html', context)

@login_required
def edit_profile_view(request):
    """View for editing user profile"""
    user = request.user
    profile = get_object_or_404(UserProfile, user=user)
    
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('user-profile')
    else:
        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=profile)
    
    context = {
        'user_form': user_form,
        'form': profile_form,
        'profile': profile,
    }
    
    return render(request, 'edit_profile.html', context)

@login_required
def remove_profile_picture_view(request):
    """View for removing profile picture"""
    if request.method == 'POST':
        profile = get_object_or_404(UserProfile, user=request.user)
        
        # Delete the profile picture
        if profile.profile_picture:
            profile.profile_picture.delete()
        
        messages.success(request, 'Profile picture removed successfully.')
    
    return redirect('edit-profile')