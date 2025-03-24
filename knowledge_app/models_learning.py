from django.db import models
from django.contrib.auth.models import User
from .models import KnowledgeNode


class LearningPath(models.Model):
    """
    Defines a curated learning path through the knowledge graph
    """
    title = models.CharField(max_length=200)
    description = models.TextField()
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_paths')
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Optional thumbnail image
    thumbnail = models.ImageField(upload_to='learning_path_thumbnails/', blank=True, null=True)
    
    # Learning objectives and outcomes
    learning_objectives = models.TextField(blank=True, help_text="What students will learn from this path")
    estimated_time = models.CharField(max_length=50, blank=True, help_text="Estimated completion time")
    difficulty_level = models.CharField(max_length=20, blank=True, help_text="Beginner, Intermediate, Advanced")
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']
    
    @property
    def node_count(self):
        return self.steps.count()
    
    @property
    def first_step(self):
        return self.steps.order_by('order').first()


class LearningPathStep(models.Model):
    """
    Individual step in a learning path
    """
    path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name='steps')
    node = models.ForeignKey(KnowledgeNode, on_delete=models.CASCADE, related_name='path_steps')
    order = models.PositiveIntegerField(help_text="Order in the learning path")
    title = models.CharField(max_length=200, blank=True, help_text="Optional override title")
    description = models.TextField(blank=True, help_text="Additional context for this step")
    
    # Optional custom content for this step
    custom_content = models.TextField(blank=True, help_text="Additional content for this node in this context")
    
    class Meta:
        ordering = ['path', 'order']
        unique_together = ['path', 'order']  # Ensure order is unique within a path
    
    def __str__(self):
        return f"{self.path.title} - Step {self.order}: {self.node.title}"
    
    def get_title(self):
        """Return custom title if available, otherwise use node title"""
        return self.title if self.title else self.node.title
    
    @property
    def next_step(self):
        """Get the next step in the path"""
        return LearningPathStep.objects.filter(
            path=self.path, 
            order__gt=self.order
        ).order_by('order').first()
    
    @property
    def previous_step(self):
        """Get the previous step in the path"""
        return LearningPathStep.objects.filter(
            path=self.path, 
            order__lt=self.order
        ).order_by('-order').first()


class UserProgress(models.Model):
    """
    Track user progress through learning paths
    """
    STATUS_CHOICES = [
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='path_progress')
    path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name='user_progress')
    current_step = models.ForeignKey(LearningPathStep, on_delete=models.SET_NULL, 
                                    null=True, blank=True, related_name='current_users')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='NOT_STARTED')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    # Progress metrics
    completion_percentage = models.FloatField(default=0.0)
    notes = models.TextField(blank=True, help_text="User's personal notes about this path")
    
    class Meta:
        unique_together = ['user', 'path']
    
    def __str__(self):
        return f"{self.user.username}'s progress on {self.path.title}: {self.status}"
    
    def update_progress(self):
        """Update completion percentage based on completed steps"""
        total_steps = self.path.steps.count()
        if total_steps == 0:
            self.completion_percentage = 0
            return
        
        completed_steps = StepCompletion.objects.filter(
            user=self.user,
            step__path=self.path,
            is_completed=True
        ).count()
        
        self.completion_percentage = (completed_steps / total_steps) * 100
        
        # Update status based on completion
        if self.completion_percentage == 0:
            self.status = 'NOT_STARTED'
        elif self.completion_percentage == 100:
            self.status = 'COMPLETED'
        else:
            self.status = 'IN_PROGRESS'
        
        self.save()


class StepCompletion(models.Model):
    """
    Records completion of individual learning path steps
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='completed_steps')
    step = models.ForeignKey(LearningPathStep, on_delete=models.CASCADE, related_name='completions')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent = models.PositiveIntegerField(default=0, help_text="Time spent in seconds")
    
    class Meta:
        unique_together = ['user', 'step']
    
    def __str__(self):
        status = "completed" if self.is_completed else "not completed"
        return f"{self.user.username} has {status} step {self.step.order} of {self.step.path.title}"


class LearningPathRecommendation(models.Model):
    """
    System-generated or manually created recommendations for learning paths
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='path_recommendations')
    path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name='recommendations')
    reason = models.TextField(help_text="Why this path is recommended")
    created_at = models.DateTimeField(auto_now_add=True)
    is_viewed = models.BooleanField(default=False)
    is_system_generated = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Recommendation of {self.path.title} for {self.user.username}"