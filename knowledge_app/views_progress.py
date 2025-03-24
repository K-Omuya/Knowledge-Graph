from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.core.paginator import Paginator

@login_required
def user_progress_view(request):
    """View for showing user progress across learning paths and quizzes"""
    user = request.user
    context = {}
    
    try:
        # Import models if they exist
        from .models_learning import UserProgress, LearningPath, StepCompletion
        from .models_assessment import QuizAttempt
        
        # Get statistics
        stats = {
            'total_paths': UserProgress.objects.filter(user=user).count(),
            'completed_paths': UserProgress.objects.filter(user=user, status='COMPLETED').count(),
            'total_quizzes': QuizAttempt.objects.filter(user=user).count(),
            'average_score': QuizAttempt.objects.filter(
                user=user, 
                status='COMPLETED'
            ).aggregate(avg=Avg('score'))['avg'] or 0
        }
        
        # Filter learning paths if needed
        path_status = request.GET.get('status')
        search_query = request.GET.get('search')
        
        learning_progress_query = UserProgress.objects.filter(user=user).select_related('path', 'current_step')
        
        if path_status:
            learning_progress_query = learning_progress_query.filter(status=path_status)
        
        if search_query:
            learning_progress_query = learning_progress_query.filter(
                Q(path__title__icontains=search_query) | 
                Q(path__description__icontains=search_query)
            )
        
        # Paginate learning paths
        paginator = Paginator(learning_progress_query.order_by('-last_activity'), 6)
        page_number = request.GET.get('page')
        learning_progress = paginator.get_page(page_number)
        
        # Enhance the learning progress with more data
        for progress in learning_progress:
            # Get completed steps count
            progress.completed_steps = StepCompletion.objects.filter(
                user=user,
                step__path=progress.path,
                is_completed=True
            ).count()
        
        # Get quiz attempts
        quiz_attempts = QuizAttempt.objects.filter(user=user).select_related('quiz').order_by('-started_at')[:4]
        
        # Enhance quiz attempts with more data
        for attempt in quiz_attempts:
            if hasattr(attempt, 'responses'):
                attempt.total_questions = attempt.quiz.questions.count()
                attempt.correct_answers = attempt.responses.filter(is_correct=True).count()
            else:
                attempt.total_questions = 0
                attempt.correct_answers = 0
        
        # Check if there are more quiz attempts than shown
        quiz_attempts.has_more = QuizAttempt.objects.filter(user=user).count() > 4
        
        context.update({
            'stats': stats,
            'learning_progress': learning_progress,
            'quiz_attempts': quiz_attempts,
            'is_paginated': learning_progress.has_other_pages()
        })
    except (ImportError, ModuleNotFoundError):
        # Models not yet implemented
        context.update({
            'stats': {
                'total_paths': 0,
                'completed_paths': 0,
                'total_quizzes': 0,
                'average_score': 0
            },
            'learning_progress': [],
            'quiz_attempts': [],
            'is_paginated': False
        })
    
    return render(request, 'user_progress.html', context)