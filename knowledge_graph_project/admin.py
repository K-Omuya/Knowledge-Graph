from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.db.models import Count, Q
import datetime

# Customize admin site
admin.site.site_header = 'Knowledge Graph Admin'
admin.site.site_title = 'Knowledge Graph Admin Portal'
admin.site.index_title = 'Welcome to Knowledge Graph Management Portal'

class AdminSite(admin.AdminSite):
    """Custom Admin Site with a Dashboard"""
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='admin_dashboard'),
        ]
        return custom_urls + urls
    
    def dashboard_view(self, request):
        """Admin dashboard with system statistics"""
        # Import models
        try:
            from knowledge_app.models import KnowledgeNode, Relationship
            from knowledge_app.models_learning import LearningPath, UserProgress
            from knowledge_app.models_assessment import Quiz, QuizAttempt
            from accounts.models import UserProfile, UserActivity
            from django.contrib.auth.models import User
            
            # Get basic stats
            stats = {
                'total_users': User.objects.count(),
                'active_users': User.objects.filter(last_login__gte=datetime.datetime.now() - datetime.timedelta(days=30)).count(),
                'total_course_nodes': KnowledgeNode.objects.filter(knowledge_type='COURSE').count(),
                'total_ideology_nodes': KnowledgeNode.objects.filter(knowledge_type='IDEOLOGY').count(),
                'total_relationships': Relationship.objects.count(),
                'total_learning_paths': LearningPath.objects.count(),
                'total_quizzes': Quiz.objects.count(),
                'completed_paths': UserProgress.objects.filter(status='COMPLETED').count(),
                'quiz_attempts': QuizAttempt.objects.count(),
                'recent_activity': UserActivity.objects.order_by('-timestamp')[:10],
            }
            
            # Get user roles distribution
            user_roles = UserProfile.objects.values('role').annotate(count=Count('role'))
            stats['user_roles'] = user_roles
            
            # Get activity by date (last 30 days)
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=30)
            
            activity_by_date = []
            current_date = start_date
            while current_date <= end_date:
                next_date = current_date + datetime.timedelta(days=1)
                count = UserActivity.objects.filter(
                    timestamp__gte=current_date,
                    timestamp__lt=next_date
                ).count()
                
                activity_by_date.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'count': count
                })
                current_date = next_date
            
            stats['activity_by_date'] = activity_by_date
            
            # Get recent registrations
            stats['recent_registrations'] = User.objects.order_by('-date_joined')[:5]
            
            # Get most active users
            stats['most_active_users'] = User.objects.annotate(
                activity_count=Count('activities')
            ).order_by('-activity_count')[:5]
            
            # Get most popular nodes
            stats['popular_nodes'] = KnowledgeNode.objects.annotate(
                view_count=Count('activities', filter=Q(activities__activity_type='VIEW'))
            ).order_by('-view_count')[:5]
            
        except Exception as e:
            # If models aren't fully set up yet
            stats = {
                'error': str(e)
            }
        
        context = {
            'title': 'Admin Dashboard',
            'stats': stats,
        }
        
        return render(request, 'admin/dashboard.html', context)

# Use this to replace the default admin site if needed
# admin.site = AdminSite()