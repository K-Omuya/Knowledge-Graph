from django.db import models
from django.contrib.auth.models import User
from .models import KnowledgeNode, Relationship


class Comment(models.Model):
    """
    Comments that can be added to nodes or relationships
    """
    CONTENT_TYPES = [
        ('NODE', 'Knowledge Node'),
        ('RELATIONSHIP', 'Relationship'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content_type = models.CharField(max_length=15, choices=CONTENT_TYPES)
    object_id = models.IntegerField()
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.content_type} #{self.object_id}"
    
    class Meta:
        ordering = ['-created_at']
    
    @property
    def content_object(self):
        """Get the actual object this comment refers to"""
        if self.content_type == 'NODE':
            return KnowledgeNode.objects.get(id=self.object_id)
        elif self.content_type == 'RELATIONSHIP':
            return Relationship.objects.get(id=self.object_id)
        return None


class NodeHistory(models.Model):
    """
    Track changes to knowledge nodes
    """
    node = models.ForeignKey(KnowledgeNode, on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='node_edits')
    title = models.CharField(max_length=200)
    description = models.TextField()
    knowledge_type = models.CharField(max_length=10, choices=KnowledgeNode.KNOWLEDGE_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    change_type = models.CharField(max_length=20)  # 'creation', 'update', etc.
    change_summary = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.change_type} of {self.node.title} by {self.user.username} at {self.created_at}"
    
    class Meta:
        ordering = ['-created_at']


class CollaborationRequest(models.Model):
    """
    Requests for collaboration on nodes
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    node = models.ForeignKey(KnowledgeNode, on_delete=models.CASCADE, related_name='collaboration_requests')
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requested_collaborations')
    approver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collaboration_approvals', 
                                 null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    request_message = models.TextField()
    response_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Collaboration request by {self.requester.username} for '{self.node.title}' ({self.status})"


class SharedEdit(models.Model):
    """
    Record of currently active shared editing sessions
    """
    node = models.ForeignKey(KnowledgeNode, on_delete=models.CASCADE, related_name='editing_sessions')
    users = models.ManyToManyField(User, related_name='active_editing_sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Editing session for {self.node.title} started at {self.started_at}"
    
    class Meta:
        ordering = ['-last_activity']