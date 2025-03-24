from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import KnowledgeNode, Relationship

# Register basic models
@admin.register(KnowledgeNode)
class KnowledgeNodeAdmin(admin.ModelAdmin):
    list_display = ('title', 'knowledge_type', 'created_at', 'updated_at')
    list_filter = ('knowledge_type', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'knowledge_type')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Relationship)
class RelationshipAdmin(admin.ModelAdmin):
    list_display = ('source', 'relationship_type', 'target')
    list_filter = ('relationship_type',)
    search_fields = ('source__title', 'target__title', 'description')
    autocomplete_fields = ('source', 'target')

# Register optional models if they exist
try:
    from .models_collaborative import Comment, NodeHistory, SharedEdit
    
    @admin.register(Comment)
    class CommentAdmin(admin.ModelAdmin):
        list_display = ('user', 'content_type', 'object_id', 'created_at')
        list_filter = ('content_type', 'created_at')
        search_fields = ('text', 'user__username')
        readonly_fields = ('created_at', 'updated_at')
    
    @admin.register(NodeHistory)
    class NodeHistoryAdmin(admin.ModelAdmin):
        list_display = ('node', 'user', 'change_type', 'created_at')
        list_filter = ('change_type', 'created_at')
        search_fields = ('node__title', 'user__username', 'change_summary')
        readonly_fields = ('created_at',)
    
    @admin.register(SharedEdit)
    class SharedEditAdmin(admin.ModelAdmin):
        list_display = ('node', 'started_at', 'last_activity', 'is_active')
        list_filter = ('is_active', 'started_at')
        search_fields = ('node__title',)
        readonly_fields = ('started_at', 'last_activity')
except:
    pass

# Register learning models if they exist
try:
    from .models_learning import (
        LearningPath, LearningPathStep, UserProgress, 
        StepCompletion, LearningPathRecommendation
    )
    
    class LearningPathStepInline(admin.TabularInline):
        model = LearningPathStep
        extra = 1
        autocomplete_fields = ('node',)
    
    @admin.register(LearningPath)
    class LearningPathAdmin(admin.ModelAdmin):
        list_display = ('title', 'creator', 'is_public', 'created_at')
        list_filter = ('is_public', 'created_at', 'difficulty_level')
        search_fields = ('title', 'description', 'creator__username')
        readonly_fields = ('created_at', 'updated_at')
        inlines = [LearningPathStepInline]
        fieldsets = (
            ('Basic Information', {
                'fields': ('title', 'description', 'creator', 'is_public', 'thumbnail')
            }),
            ('Learning Details', {
                'fields': ('learning_objectives', 'estimated_time', 'difficulty_level')
            }),
            ('Timestamps', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            }),
        )
    
    @admin.register(UserProgress)
    class UserProgressAdmin(admin.ModelAdmin):
        list_display = ('user', 'path', 'status', 'completion_percentage', 'started_at')
        list_filter = ('status', 'started_at')
        search_fields = ('user__username', 'path__title')
        readonly_fields = ('started_at', 'completed_at', 'last_activity')
except:
    pass

# Register assessment models if they exist
try:
    from .models_assessment import (
        Quiz, QuizGenerationParams, Question, Answer, 
        QuizAttempt, QuestionResponse
    )
    
    class AnswerInline(admin.TabularInline):
        model = Answer
        extra = 2
    
    @admin.register(Question)
    class QuestionAdmin(admin.ModelAdmin):
        list_display = ('question_text', 'quiz', 'question_type', 'points')
        list_filter = ('question_type', 'quiz')
        search_fields = ('question_text', 'explanation')
        inlines = [AnswerInline]
    
    class QuestionInline(admin.TabularInline):
        model = Question
        extra = 1
    
    @admin.register(Quiz)
    class QuizAdmin(admin.ModelAdmin):
        list_display = ('title', 'creator', 'quiz_type', 'is_public', 'created_at')
        list_filter = ('quiz_type', 'is_public', 'created_at')
        search_fields = ('title', 'description', 'creator__username')
        readonly_fields = ('created_at', 'updated_at')
        inlines = [QuestionInline]
        fieldsets = (
            ('Basic Information', {
                'fields': ('title', 'description', 'creator', 'quiz_type', 'is_public')
            }),
            ('Related Content', {
                'fields': ('related_node', 'related_path'),
                'classes': ('collapse',)
            }),
            ('Quiz Settings', {
                'fields': ('time_limit', 'passing_score', 'randomize_questions', 
                          'show_correct_answers', 'max_attempts')
            }),
            ('Timestamps', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            }),
        )
    
    @admin.register(QuizAttempt)
    class QuizAttemptAdmin(admin.ModelAdmin):
        list_display = ('user', 'quiz', 'status', 'score', 'started_at', 'completed_at')
        list_filter = ('status', 'started_at')
        search_fields = ('user__username', 'quiz__title')
        readonly_fields = ('started_at', 'completed_at')
except:
    pass