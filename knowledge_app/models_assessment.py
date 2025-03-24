from django.db import models
from django.contrib.auth.models import User
from .models import KnowledgeNode, Relationship


class Quiz(models.Model):
    """
    Quiz based on knowledge graph content
    """
    QUIZ_TYPES = [
        ('NODE', 'Knowledge Node Quiz'),
        ('RELATIONSHIP', 'Relationship Quiz'),
        ('PATH', 'Learning Path Quiz'),
        ('CUSTOM', 'Custom Quiz'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_quizzes')
    is_public = models.BooleanField(default=True)
    quiz_type = models.CharField(max_length=15, choices=QUIZ_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Optional associations
    related_node = models.ForeignKey(KnowledgeNode, on_delete=models.SET_NULL, 
                                     null=True, blank=True, related_name='quizzes')
    related_path = models.ForeignKey('LearningPath', on_delete=models.SET_NULL, 
                                    null=True, blank=True, related_name='quizzes')
    
    # Quiz settings
    time_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Time limit in seconds")
    passing_score = models.PositiveIntegerField(default=70, help_text="Passing score percentage")
    randomize_questions = models.BooleanField(default=True)
    show_correct_answers = models.BooleanField(default=True)
    max_attempts = models.PositiveIntegerField(default=0, help_text="0 for unlimited attempts")
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']
    
    @property
    def question_count(self):
        return self.questions.count()
    
    @property
    def is_auto_generated(self):
        return hasattr(self, 'generation_params')


class QuizGenerationParams(models.Model):
    """
    Parameters used for automatic quiz generation
    """
    DIFFICULTY_LEVELS = [
        ('EASY', 'Easy'),
        ('MEDIUM', 'Medium'),
        ('HARD', 'Hard'),
    ]
    
    quiz = models.OneToOneField(Quiz, on_delete=models.CASCADE, related_name='generation_params')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_LEVELS, default='MEDIUM')
    question_count = models.PositiveIntegerField(default=10)
    include_node_questions = models.BooleanField(default=True)
    include_relationship_questions = models.BooleanField(default=True)
    focus_on_course_knowledge = models.BooleanField(default=True)
    focus_on_ideology = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Generation params for {self.quiz.title}"


class Question(models.Model):
    """
    A quiz question
    """
    QUESTION_TYPES = [
        ('MULTIPLE_CHOICE', 'Multiple Choice'),
        ('TRUE_FALSE', 'True/False'),
        ('MATCHING', 'Matching'),
        ('TEXT', 'Text Response'),
        ('RELATIONSHIP', 'Relationship Identification'),
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)
    explanation = models.TextField(blank=True, help_text="Explanation of the correct answer")
    
    # Optional associations
    related_node = models.ForeignKey(KnowledgeNode, on_delete=models.SET_NULL, 
                                     null=True, blank=True, related_name='questions')
    related_relationship = models.ForeignKey(Relationship, on_delete=models.SET_NULL, 
                                            null=True, blank=True, related_name='questions')
    
    class Meta:
        ordering = ['quiz', 'order']
    
    def __str__(self):
        return f"Question {self.order + 1}: {self.question_text[:50]}..."
    
    @property
    def has_correct_answer(self):
        """Check if this question has at least one correct answer"""
        if self.question_type == 'TEXT':
            return True  # Text responses are manually graded
        return self.answers.filter(is_correct=True).exists()


class Answer(models.Model):
    """
    Possible answer for a quiz question
    """
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    # For matching questions
    matching_group = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['question', 'order']
    
    def __str__(self):
        return f"Answer: {self.answer_text[:50]}..."


class QuizAttempt(models.Model):
    """
    Record of a user's attempt at a quiz
    """
    STATUS_CHOICES = [
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('EXPIRED', 'Expired'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='IN_PROGRESS')
    score = models.FloatField(null=True, blank=True)
    time_taken = models.PositiveIntegerField(null=True, blank=True, help_text="Time taken in seconds")
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.user.username}'s attempt at {self.quiz.title}"
    
    @property
    def is_passing(self):
        if self.score is None:
            return False
        return self.score >= self.quiz.passing_score


class QuestionResponse(models.Model):
    """
    User's response to a quiz question
    """
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    selected_answers = models.ManyToManyField(Answer, blank=True, related_name='responses')
    text_response = models.TextField(blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    points_earned = models.FloatField(default=0)
    response_time = models.PositiveIntegerField(null=True, blank=True, help_text="Response time in seconds")
    
    class Meta:
        unique_together = ['attempt', 'question']
    
    def __str__(self):
        return f"Response to question {self.question.order + 1} in {self.attempt}"
    
    def calculate_score(self):
        """Calculate the score for this response"""
        question = self.question
        
        if question.question_type == 'TEXT':
            # Text responses need manual grading
            return None
            
        elif question.question_type == 'MULTIPLE_CHOICE':
            # Check if all and only correct answers are selected
            correct_answers = set(question.answers.filter(is_correct=True))
            selected_answers = set(self.selected_answers.all())
            
            if correct_answers == selected_answers:
                self.is_correct = True
                self.points_earned = question.points
            else:
                self.is_correct = False
                self.points_earned = 0
                
        elif question.question_type == 'TRUE_FALSE':
            # Only one answer should be selected
            if self.selected_answers.count() == 1:
                self.is_correct = self.selected_answers.first().is_correct
                self.points_earned = question.points if self.is_correct else 0
            else:
                self.is_correct = False
                self.points_earned = 0
                
        elif question.question_type == 'MATCHING':
            # All matches must be correct
            correct_count = 0
            total_matches = question.answers.filter(is_correct=True).count()
            
            for selected in self.selected_answers.all():
                correct_match = question.answers.filter(
                    matching_group=selected.matching_group, 
                    is_correct=True
                ).first()
                
                if correct_match and correct_match == selected:
                    correct_count += 1
            
            if correct_count == total_matches:
                self.is_correct = True
                self.points_earned = question.points
            else:
                self.is_correct = False
                # Partial credit for matching questions
                self.points_earned = (correct_count / total_matches) * question.points
                
        elif question.question_type == 'RELATIONSHIP':
            # Relationship identification
            if self.selected_answers.count() == 1:
                self.is_correct = self.selected_answers.first().is_correct
                self.points_earned = question.points if self.is_correct else 0
            else:
                self.is_correct = False
                self.points_earned = 0
        
        self.save()
        return self.points_earned