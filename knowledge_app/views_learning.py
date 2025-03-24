# knowledge_app/views_learning.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Avg

# This is a placeholder - you'll need to create the actual models later
try:
    from .models_learning import (
        LearningPath, LearningPathStep, UserProgress, StepCompletion,
        LearningPathRecommendation
    )
    from .models_assessment import (
        Quiz, QuizGenerationParams, Question, Answer, 
        QuizAttempt, QuestionResponse
    )
    from .models import KnowledgeNode, Relationship
    from accounts.models import UserActivity
except ImportError:
    # Create placeholder classes for development
    class LearningPath:
        pass
    
    class LearningPathStep:
        pass
        
    class UserProgress:
        pass
        
    class Quiz:
        pass


class LearningPathListView(LoginRequiredMixin, ListView):
    """View to list all learning paths"""
    template_name = 'learning_paths.html'
    context_object_name = 'paths'
    paginate_by = 9
    
    def get_queryset(self):
        # Return an empty list for now - replace with actual query when models exist
        try:
            queryset = LearningPath.objects.filter(is_public=True)
            
            # Apply filters
            difficulty = self.request.GET.get('difficulty')
            if difficulty:
                queryset = queryset.filter(difficulty_level=difficulty)
            
            # Apply search
            search = self.request.GET.get('search')
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) | 
                    Q(description__icontains=search) |
                    Q(learning_objectives__icontains=search)
                )
            
            return queryset
        except:
            return []

class LearningPathDetailView(LoginRequiredMixin, DetailView):
    """View to show details of a learning path"""
    template_name = 'learning_path_detail.html'
    context_object_name = 'path'
    
    def get_object(self):
        # Return None for now - replace with actual query when models exist
        try:
            return get_object_or_404(LearningPath, pk=self.kwargs['pk'])
        except:
            return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            path = self.get_object()
            
            # Get user progress for this path
            try:
                progress = UserProgress.objects.get(user=self.request.user, path=path)
            except UserProgress.DoesNotExist:
                # Create new progress entry
                progress = UserProgress.objects.create(
                    user=self.request.user,
                    path=path,
                    status='NOT_STARTED'
                )
            
            # Get completed steps
            completed_steps = StepCompletion.objects.filter(
                user=self.request.user,
                step__path=path,
                is_completed=True
            ).values_list('step_id', flat=True)
            
            # Mark steps as completed or active
            for step in path.steps.all():
                step.is_completed = step.id in completed_steps
                # A step is active if it's the first non-completed step
                if not step.is_completed and not hasattr(context, 'active_step'):
                    step.is_active = True
                    context['active_step'] = step
                else:
                    step.is_active = False
            
            context['progress'] = progress
            
            # Log activity
            try:
                UserActivity.objects.create(
                    user=self.request.user,
                    activity_type='VIEW',
                    content_type='learning_path',
                    object_id=path.id,
                    details=path.title
                )
            except:
                pass
            
        except:
            pass
        
        return context

class LearningPathCreateView(LoginRequiredMixin, CreateView):
    """View to create a new learning path"""
    template_name = 'learning_path_form.html'
    
    def get_form(self):
        # Placeholder
        return None

class LearningPathUpdateView(LoginRequiredMixin, UpdateView):
    """View to update a learning path"""
    template_name = 'learning_path_form.html'
    
    def get_object(self):
        # Return None for now
        return None

class LearningPathDeleteView(LoginRequiredMixin, DeleteView):
    """View to delete a learning path"""
    template_name = 'learning_path_confirm_delete.html'
    
    def get_object(self):
        # Return None for now
        return None

@login_required
def learning_path_step_view(request, path_id, step_id):
    """View for showing a learning path step"""
    try:
        path = get_object_or_404(LearningPath, pk=path_id)
        step = get_object_or_404(LearningPathStep, pk=step_id, path=path)
        
        # Get user progress
        try:
            progress = UserProgress.objects.get(user=request.user, path=path)
            progress.current_step = step
            progress.last_activity = timezone.now()
            progress.save()
        except UserProgress.DoesNotExist:
            progress = UserProgress.objects.create(
                user=request.user,
                path=path,
                current_step=step,
                status='IN_PROGRESS'
            )
        
        # Check if step is completed
        try:
            completion = StepCompletion.objects.get(user=request.user, step=step)
            step.is_completed = completion.is_completed
            step.completed_at = completion.completed_at
        except StepCompletion.DoesNotExist:
            step.is_completed = False
        
        # Get previous and next steps
        previous_step = step.previous_step
        next_step = step.next_step
        
        # Get related nodes
        related_nodes = []
        
        # Get source relationships
        for rel in step.node.source_relationships.all()[:3]:
            related_nodes.append(rel.target)
        
        # Get target relationships
        for rel in step.node.target_relationships.all()[:3]:
            related_nodes.append(rel.source)
        
        # Calculate current progress
        total_steps = path.steps.count()
        current_step_index = list(path.steps.values_list('id', flat=True)).index(step.id)
        current_progress = (current_step_index / total_steps) * 100
        
        # Log activity
        try:
            UserActivity.objects.create(
                user=request.user,
                activity_type='VIEW',
                content_type='learning_step',
                object_id=step.id,
                details=f"Step {step.order} of {path.title}"
            )
        except:
            pass
        
        context = {
            'path': path,
            'step': step,
            'previous_step': previous_step,
            'next_step': next_step,
            'related_nodes': related_nodes,
            'current_progress': current_progress,
        }
        
        return render(request, 'learning_path_step.html', context)
    except:
        # If there's an error, render a simple template
        return render(request, 'learning_path_step.html')

@login_required
def complete_step_view(request, path_id, step_id):
    """View for marking a step as complete"""
    try:
        path = get_object_or_404(LearningPath, pk=path_id)
        step = get_object_or_404(LearningPathStep, pk=step_id, path=path)
        
        # Get or create step completion
        completion, created = StepCompletion.objects.get_or_create(
            user=request.user,
            step=step,
            defaults={'is_completed': False}
        )
        
        # Toggle completion status
        if 'mark_incomplete' in request.POST:
            completion.is_completed = False
            completion.completed_at = None
            messages.success(request, f"Step '{step.get_title()}' marked as incomplete.")
        else:
            completion.is_completed = True
            completion.completed_at = timezone.now()
            messages.success(request, f"Step '{step.get_title()}' completed!")
        
        completion.save()
        
        # Update overall progress
        try:
            progress = UserProgress.objects.get(user=request.user, path=path)
            progress.update_progress()
            
            # If this was the last step and all are completed, mark path as completed
            if progress.status == 'COMPLETED' and progress.completed_at is None:
                progress.completed_at = timezone.now()
                progress.save()
                
                messages.success(request, f"Congratulations! You've completed the '{path.title}' learning path!")
        except UserProgress.DoesNotExist:
            pass
        
        # Log activity
        try:
            UserActivity.objects.create(
                user=request.user,
                activity_type='COMPLETE' if completion.is_completed else 'UNCOMPLETE',
                content_type='learning_step',
                object_id=step.id,
                details=f"{'Completed' if completion.is_completed else 'Marked as incomplete'} step {step.order} of {path.title}"
            )
        except:
            pass
            
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
    
    return redirect('learning-path-step', path_id=path_id, step_id=step_id)

class QuizListView(LoginRequiredMixin, ListView):
    """View to list all quizzes"""
    template_name = 'quizzes.html'
    context_object_name = 'quizzes'
    
    def get_queryset(self):
        # Return an empty list for now
        return []

class QuizDetailView(LoginRequiredMixin, DetailView):
    """View to show details of a quiz"""
    template_name = 'quiz_detail.html'
    context_object_name = 'quiz'
    
    def get_object(self):
        # Return None for now
        return None

class QuizCreateView(LoginRequiredMixin, CreateView):
    """View to create a new quiz"""
    template_name = 'quiz_form.html'
    
    def get_form(self):
        # Placeholder
        return None

@login_required
def generate_quiz_view(request):
    """View for generating a quiz automatically"""
    return render(request, 'generate_quiz.html')

@login_required
def take_quiz_view(request, pk):
    """View for taking a quiz"""
    return render(request, 'take_quiz.html')

@login_required
def quiz_attempt_view(request, quiz_id, attempt_id):
    """View for a specific quiz attempt"""
    return render(request, 'quiz_attempt.html')

@login_required
def quiz_results_view(request, quiz_id, attempt_id):
    """View for quiz results"""
    return render(request, 'quiz_results.html')

@login_required
def user_progress_view(request):
    """View for showing user progress"""
    context = {
        'learning_progress': [],
        'quiz_attempts': [],
    }
    
    try:
        # Get learning path progress
        learning_progress = UserProgress.objects.filter(user=request.user).select_related('path')
        
        # Get quiz attempts
        quiz_attempts = QuizAttempt.objects.filter(user=request.user).select_related('quiz')
        
        context.update({
            'learning_progress': learning_progress,
            'quiz_attempts': quiz_attempts,
        })
    except:
        pass
    
    return render(request, 'user_progress.html', context)
    