from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    """
    Extended user profile with additional information
    """
    USER_ROLES = [
        ('ADMIN', 'Administrator'),
        ('EDITOR', 'Editor'),
        ('VIEWER', 'Viewer'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=USER_ROLES, default='VIEWER')
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    
    # Academic information
    institution = models.CharField(max_length=200, blank=True)
    department = models.CharField(max_length=200, blank=True)
    position = models.CharField(max_length=200, blank=True)
    
    # Activity tracking
    last_activity = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
    @property
    
    def is_admin(self):
        return self.role == 'ADMIN'
    
    @property
    def is_editor(self):
        return self.role in ['ADMIN', 'EDITOR']


class UserActivity(models.Model):
    """
    Tracking user activities in the system
    """
    ACTIVITY_TYPES = [
        ('VIEW', 'Viewed'),
        ('CREATE', 'Created'),
        ('EDIT', 'Edited'),
        ('DELETE', 'Deleted'),
        ('COMMENT', 'Commented'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=10, choices=ACTIVITY_TYPES)
    content_type = models.CharField(max_length=20)  # e.g., 'node', 'relationship'
    object_id = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.user.username} {self.get_activity_type_display()} {self.content_type} #{self.object_id}"
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'User activities'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile automatically when a User is created"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile when the User is saved"""
    instance.profile.save()