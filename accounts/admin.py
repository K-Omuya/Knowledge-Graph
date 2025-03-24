from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, UserActivity

# Define an inline admin descriptor for UserProfile model
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'profile'
    fieldsets = (
        ('Personal Information', {
            'fields': ('bio', 'profile_picture')
        }),
        ('Academic Information', {
            'fields': ('institution', 'department', 'position')
        }),
        ('System Settings', {
            'fields': ('role', 'last_activity'),
            'classes': ('collapse',)
        }),
    )

# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role', 'date_joined')
    list_filter = BaseUserAdmin.list_filter + ('userprofile__role',)
    search_fields = ('username', 'email', 'first_name', 'last_name', 'userprofile__bio', 
                    'userprofile__institution', 'userprofile__department')
    
    def get_role(self, obj):
        return obj.profile.get_role_display()
    get_role.short_description = 'Role'
    get_role.admin_order_field = 'userprofile__role'

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'content_type', 'object_id', 'timestamp')
    list_filter = ('activity_type', 'content_type', 'timestamp')
    search_fields = ('user__username', 'details')
    readonly_fields = ('timestamp',)
    fieldsets = (
        ('Activity Information', {
            'fields': ('user', 'activity_type', 'content_type', 'object_id', 'details')
        }),
        ('Timestamps', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    
    # Add a link to the related object if possible
    def view_related_object_link(self, obj):
        if obj.content_type == 'node':
            return f'<a href="/admin/knowledge_app/knowledgenode/{obj.object_id}/change/">View Node</a>'
        elif obj.content_type == 'relationship':
            return f'<a href="/admin/knowledge_app/relationship/{obj.object_id}/change/">View Relationship</a>'
        return "N/A"
    
    view_related_object_link.short_description = 'View Object'
    view_related_object_link.allow_tags = True