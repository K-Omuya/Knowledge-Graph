from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.utils import timezone

import networkx as nx
import json
from pyvis.network import Network
from django.core.paginator import Paginator

from .models import KnowledgeNode, Relationship
from .forms import KnowledgeNodeForm, RelationshipForm, CommentForm, NodeAttachmentForm

# Import models from other files
from .models_collaborative import Comment, NodeHistory, SharedEdit
from .models_learning import LearningPath, LearningPathRecommendation, UserProgress
from accounts.models import UserActivity

# Import services
from .services.nlp_service import RelationshipSuggester, KeywordExtractor

from django import template

register = template.Library()

def index(request):
    """Home page view with stats and personalized content"""
    # Get basic statistics
    course_nodes_count = KnowledgeNode.objects.filter(knowledge_type='COURSE').count()
    ideology_nodes_count = KnowledgeNode.objects.filter(knowledge_type='IDEOLOGY').count()
    relationships_count = Relationship.objects.count()
    learning_paths_count = LearningPath.objects.filter(is_public=True).count()
    
    context = {
        'course_nodes_count': course_nodes_count,
        'ideology_nodes_count': ideology_nodes_count,
        'relationships_count': relationships_count,
        'learning_paths_count': learning_paths_count,
    }
    
    # Add personalized content for logged-in users
    if request.user.is_authenticated:
        # Get recommended learning paths
        recommended_paths = []
        user_recommendations = LearningPathRecommendation.objects.filter(
            user=request.user, 
            is_viewed=False
        ).select_related('path')[:3]
        
        for recommendation in user_recommendations:
            path = recommendation.path
            
            # Get user progress for this path if it exists
            try:
                progress = UserProgress.objects.get(user=request.user, path=path)
                path.user_progress = progress
            except UserProgress.DoesNotExist:
                path.user_progress = None
                
            recommended_paths.append(path)
        
        # Get recent user activity
        recent_activities = UserActivity.objects.filter(
            user=request.user
        ).order_by('-timestamp')[:5]
        
        context.update({
            'recommended_paths': recommended_paths,
            'recent_activities': recent_activities,
        })
    
    return render(request, 'index.html', context)

def about_view(request):
    """About page view"""
    return render(request, 'about.html')

def contact_view(request):
    """Contact page view"""
    return render(request, 'contact.html')

def help_documentation_view(request):
    """Help and documentation page"""
    return render(request, 'help_documentation.html')

def search_results_view(request):
    """View for full search results"""
    query = request.GET.get('q', '')
    
    if not query:
        return render(request, 'search_results.html', {'query': query, 'results': []})
    
    # Search in nodes
    nodes = KnowledgeNode.objects.filter(
        Q(title__icontains=query) | 
        Q(description__icontains=query)
    )
    
    # Extract keywords from query
    keyword_extractor = KeywordExtractor()
    keywords = [kw[0] for kw in keyword_extractor.extract_keywords(query)]
    
    # Get related nodes based on keywords
    related_nodes = []
    if keywords:
        related_nodes = KnowledgeNode.objects.filter(
            Q(title__icontains=keywords[0]) |
            Q(description__icontains=keywords[0])
        ).exclude(id__in=nodes.values_list('id', flat=True))[:5]
    
    # Search in learning paths if available
    try:
        learning_paths = LearningPath.objects.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(learning_objectives__icontains=query)
        ).filter(is_public=True)
    except:
        learning_paths = []
    
    context = {
        'query': query,
        'nodes': nodes,
        'related_nodes': related_nodes,
        'keywords': keywords,
        'learning_paths': learning_paths,
    }
    
    return render(request, 'search_results.html', context)

class KnowledgeNodeListView(ListView):
    """View to list all knowledge nodes"""
    model = KnowledgeNode
    template_name = 'node_list.html'
    context_object_name = 'nodes'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by node type if requested
        node_type = self.request.GET.get('type')
        if node_type:
            queryset = queryset.filter(knowledge_type=node_type)
        
        # Filter by search term if provided
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['node_types'] = KnowledgeNode.KNOWLEDGE_TYPES
        return context

class KnowledgeNodeDetailView(DetailView):
    """View to show details of a specific knowledge node"""
    model = KnowledgeNode
    template_name = 'node_detail.html'
    context_object_name = 'node'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        node = self.get_object()
        
        # Get related nodes (both source and target relationships)
        source_relationships = node.source_relationships.all().select_related('target')
        target_relationships = node.target_relationships.all().select_related('source')
        
        # Get attachments
        try:
            attachments = node.attachments.all()
        except:
            attachments = []
        
        # Get comments
        try:
            comments = Comment.objects.filter(
                content_type='NODE',
                object_id=node.id,
                parent=None
            ).order_by('-created_at')
            
            # Add comment form for logged-in users
            if self.request.user.is_authenticated:
                comment_form = CommentForm()
                attachment_form = NodeAttachmentForm()
            else:
                comment_form = None
                attachment_form = None
        except:
            comments = []
            comment_form = None
            attachment_form = None
        
        # Get node history if available
        try:
            history = node.history.all().order_by('-created_at')[:5]
        except:
            history = []
        
        # Log user activity if authenticated
        if self.request.user.is_authenticated:
            try:
                UserActivity.objects.create(
                    user=self.request.user,
                    activity_type='VIEW',
                    content_type='node',
                    object_id=node.id,
                    details=node.title
                )
            except:
                pass
        
        # Get keywords
        try:
            keyword_extractor = KeywordExtractor()
            keywords = keyword_extractor.extract_keywords_from_node(node)
        except:
            keywords = []
        
        context.update({
            'source_relationships': source_relationships,
            'target_relationships': target_relationships,
            'attachments': attachments,
            'comments': comments,
            'comment_form': comment_form,
            'attachment_form': attachment_form,
            'history': history,
            'keywords': keywords,
        })
        
        return context

class KnowledgeNodeCreateView(LoginRequiredMixin, CreateView):
    """View to create a new knowledge node"""
    model = KnowledgeNode
    form_class = KnowledgeNodeForm
    template_name = 'node_form.html'
    success_url = reverse_lazy('node-list')
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Pre-select node type if provided in URL
        node_type = self.request.GET.get('type')
        if node_type:
            initial['knowledge_type'] = node_type
            
        return initial
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Create node history entry
        try:
            NodeHistory.objects.create(
                node=self.object,
                user=self.request.user,
                title=self.object.title,
                description=self.object.description,
                knowledge_type=self.object.knowledge_type,
                change_type='creation',
                change_summary='Initial creation of node'
            )
        except:
            pass
        
        # Log user activity
        try:
            UserActivity.objects.create(
                user=self.request.user,
                activity_type='CREATE',
                content_type='node',
                object_id=self.object.id,
                details=self.object.title
            )
        except:
            pass
        
        messages.success(self.request, 'Knowledge node created successfully.')
        return response

class KnowledgeNodeUpdateView(LoginRequiredMixin, UpdateView):
    """View to update an existing knowledge node"""
    model = KnowledgeNode
    form_class = KnowledgeNodeForm
    template_name = 'node_form.html'
    
    def get_success_url(self):
        return reverse('node-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # Get original state to track changes
        original_node = KnowledgeNode.objects.get(pk=self.object.pk)
        original_title = original_node.title
        original_description = original_node.description
        original_type = original_node.knowledge_type
        
        # Create list of changes
        changes = []
        if original_title != form.cleaned_data['title']:
            changes.append(f"Title changed from '{original_title}' to '{form.cleaned_data['title']}'")
        
        if original_description != form.cleaned_data['description']:
            changes.append("Description updated")
        
        if original_type != form.cleaned_data['knowledge_type']:
            changes.append(f"Type changed from '{original_node.get_knowledge_type_display()}' "
                          f"to '{dict(KnowledgeNode.KNOWLEDGE_TYPES)[form.cleaned_data['knowledge_type']]}'")
        
        response = super().form_valid(form)
        
        # Create node history entry
        change_summary = ". ".join(changes)
        try:
            NodeHistory.objects.create(
                node=self.object,
                user=self.request.user,
                title=self.object.title,
                description=self.object.description,
                knowledge_type=self.object.knowledge_type,
                change_type='update',
                change_summary=change_summary
            )
        except:
            pass
        
        # Log user activity
        try:
            UserActivity.objects.create(
                user=self.request.user,
                activity_type='EDIT',
                content_type='node',
                object_id=self.object.id,
                details=self.object.title
            )
        except:
            pass
        
        messages.success(self.request, 'Knowledge node updated successfully.')
        return response

class KnowledgeNodeDeleteView(LoginRequiredMixin, DeleteView):
    """View to delete a knowledge node"""
    model = KnowledgeNode
    template_name = 'node_confirm_delete.html'
    success_url = reverse_lazy('node-list')
    
    def delete(self, request, *args, **kwargs):
        node = self.get_object()
        
        # Log user activity
        try:
            UserActivity.objects.create(
                user=self.request.user,
                activity_type='DELETE',
                content_type='node',
                object_id=node.id,
                details=node.title
            )
        except:
            pass
        
        messages.success(request, 'Knowledge node deleted successfully.')
        return super().delete(request, *args, **kwargs)

class RelationshipCreateView(LoginRequiredMixin, CreateView):
    """View to create a new relationship"""
    model = Relationship
    form_class = RelationshipForm
    template_name = 'relationship_form.html'
    success_url = reverse_lazy('node-list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Pre-select source or target node if provided in URL
        source_id = self.request.GET.get('source')
        if source_id:
            try:
                source_node = KnowledgeNode.objects.get(pk=source_id)
                form.fields['source'].initial = source_node
            except KnowledgeNode.DoesNotExist:
                pass
        
        target_id = self.request.GET.get('target')
        if target_id:
            try:
                target_node = KnowledgeNode.objects.get(pk=target_id)
                form.fields['target'].initial = target_node
            except KnowledgeNode.DoesNotExist:
                pass
        
        return form
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log user activity
        try:
            UserActivity.objects.create(
                user=self.request.user,
                activity_type='CREATE',
                content_type='relationship',
                object_id=self.object.id,
                details=f"between {self.object.source.title} and {self.object.target.title}"
            )
        except:
            pass
        
        messages.success(self.request, 'Relationship created successfully.')
        return response

@login_required
def relationship_detail_view(request, pk):
    """View to show details of a specific relationship"""
    relationship = get_object_or_404(Relationship, pk=pk)
    
    # Get comments
    try:
        comments = Comment.objects.filter(
            content_type='RELATIONSHIP',
            object_id=relationship.id,
            parent=None
        ).order_by('-created_at')
        
        # Add comment form
        comment_form = CommentForm()
    except:
        comments = []
        comment_form = None
    
    # Log user activity
    try:
        UserActivity.objects.create(
            user=request.user,
            activity_type='VIEW',
            content_type='relationship',
            object_id=relationship.id,
            details=f"between {relationship.source.title} and {relationship.target.title}"
        )
    except:
        pass
    
    context = {
        'relationship': relationship,
        'comments': comments,
        'comment_form': comment_form,
    }
    
    return render(request, 'relationship_detail.html', context)

@login_required
def relationship_delete_view(request, pk):
    """View to delete a relationship"""
    relationship = get_object_or_404(Relationship, pk=pk)
    
    if request.method == 'POST':
        # Record details for activity log before deletion
        source_title = relationship.source.title
        target_title = relationship.target.title
        
        # Delete the relationship
        relationship.delete()
        
        # Log user activity
        try:
            UserActivity.objects.create(
                user=request.user,
                activity_type='DELETE',
                content_type='relationship',
                object_id=pk,
                details=f"between {source_title} and {target_title}"
            )
        except:
            pass
        
        messages.success(request, 'Relationship deleted successfully.')
        return redirect('node-list')
    
    return render(request, 'relationship_confirm_delete.html', {'relationship': relationship})

def visualize_graph(request):
    """View to visualize the knowledge graph"""
    # Filter nodes if requested
    node_type = request.GET.get('type')
    query = request.GET.get('q')
    
    nodes_query = KnowledgeNode.objects.all()
    
    if node_type:
        nodes_query = nodes_query.filter(knowledge_type=node_type)
    
    if query:
        nodes_query = nodes_query.filter(Q(title__icontains=query) | Q(description__icontains=query))
    
    # Get all nodes and relationships
    nodes = nodes_query
    
    # Create networkx graph
    G = nx.Graph()
    
    # Add nodes
    for node in nodes:
        G.add_node(node.id, 
                  title=node.title, 
                  group=1 if node.knowledge_type == 'COURSE' else 2)
    
    # Get node IDs for relationship filtering
    node_ids = list(nodes.values_list('id', flat=True))
    
    # Add edges (relationships)
    relationships = Relationship.objects.filter(
        source__in=node_ids, 
        target__in=node_ids
    )
    
    for rel in relationships:
        G.add_edge(rel.source.id, rel.target.id, 
                  title=rel.get_relationship_type_display())
    
    # Create pyvis network
    net = Network(height="700px", width="100%", bgcolor="#ffffff", 
                 font_color="black")
    
    # Set options - fixed version
    net.barnes_hut(gravity=-80000, central_gravity=0.3, spring_length=250)
    
    # Convert the physics options to a JSON string instead of using a dictionary
    physics_options = '''
    {
        "nodes": {
            "shape": "dot",
            "size": 25,
            "font": {
                "size": 14
            }
        },
        "edges": {
            "color": {
                "inherit": true
            },
            "smooth": {
                "enabled": true,
                "type": "dynamic"
            }
        },
        "physics": {
            "enabled": true,
            "hierarchicalRepulsion": {
                "centralGravity": 0.0,
                "springLength": 100,
                "springConstant": 0.01,
                "nodeDistance": 120
            },
            "maxVelocity": 50,
            "minVelocity": 0.1,
            "solver": "hierarchicalRepulsion"
        }
    }
    '''
    
    net.set_options(physics_options)
    
    # From networkx to pyvis
    net.from_nx(G)
    
    # Generate HTML
    graph_html = net.generate_html()
    graph_html = graph_html.replace('<!doctype html>\n<html>\n<head>\n', '')
    graph_html = graph_html.replace('</head>\n<body>\n', '')
    graph_html = graph_html.replace('</body>\n</html>', '')
    
    context = {
        'graph_html': graph_html,
        'node_count': nodes.count(),
        'relationship_count': relationships.count(),
        'course_count': nodes.filter(knowledge_type='COURSE').count(),
        'ideology_count': nodes.filter(knowledge_type='IDEOLOGY').count(),
    }
    
    return render(request, 'graph_visualization.html', context)
@login_required
def user_profile_view(request):
    """View for user profile page"""
    user = request.user
    
    # Get user profile if it exists
    try:
        profile = user.profile
    except:
        profile = None
    
    # Get user activity
    try:
        recent_activities = UserActivity.objects.filter(user=user).order_by('-timestamp')[:10]
    except:
        recent_activities = []
    
    # Get user progress on learning paths
    try:
        learning_progress = UserProgress.objects.filter(user=user).select_related('path')
    except:
        learning_progress = []
    
    # Get quiz attempts
    try:
        from .models_assessment import QuizAttempt
        quiz_attempts = QuizAttempt.objects.filter(user=user).select_related('quiz').order_by('-started_at')[:5]
    except:
        quiz_attempts = []
    
    context = {
        'profile': profile,
        'recent_activities': recent_activities,
        'learning_progress': learning_progress,
        'quiz_attempts': quiz_attempts,
    }
    
    return render(request, 'user_profile.html', context)
def advanced_visualization(request):
    """Advanced visualization with more controls and filtering options"""
    # Simple placeholder for now
    return render(request, 'graph_visualization.html', {'graph_html': ''})


@login_required
def user_activity_view(request):
    """View for user activity history"""
    activities = UserActivity.objects.filter(user=request.user).order_by('-timestamp')
    
    # Paginate results
    paginator = Paginator(activities, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'user_activity.html', context)


from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm

def login_view(request):
    """Custom login view"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.POST.get('next', 'index')
                messages.success(request, f'Welcome back, {username}!')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'login.html', {'form': form})   

def register_view(request):
    """User registration view"""
    if request.method == 'POST':
        # Process registration form
        pass
    else:
        # Show registration form
        pass
    
    return render(request, 'register.html')

@login_required
def node_comments_view(request, pk):
    """View for handling node comments"""
    node = get_object_or_404(KnowledgeNode, pk=pk)
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.content_type = 'NODE'
            comment.object_id = node.id
            comment.save()
            
            # Log user activity
            try:
                UserActivity.objects.create(
                    user=request.user,
                    activity_type='COMMENT',
                    content_type='node',
                    object_id=node.id,
                    details=f"Commented on {node.title}"
                )
            except:
                pass
            
            messages.success(request, 'Comment added successfully.')
            return redirect('node-detail', pk=pk)
    
    return redirect('node-detail', pk=pk)

@login_required
def relationship_comments_view(request, pk):
    """View for handling relationship comments"""
    relationship = get_object_or_404(Relationship, pk=pk)
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.content_type = 'RELATIONSHIP'
            comment.object_id = relationship.id
            comment.save()
            
            # Log user activity
            try:
                UserActivity.objects.create(
                    user=request.user,
                    activity_type='COMMENT',
                    content_type='relationship',
                    object_id=relationship.id,
                    details=f"Commented on relationship between {relationship.source.title} and {relationship.target.title}"
                )
            except:
                pass
            
            messages.success(request, 'Comment added successfully.')
            return redirect('relationship-detail', pk=pk)
    
    return redirect('relationship-detail', pk=pk)

@login_required
def delete_comment_view(request, pk):
    """View for deleting a comment"""
    comment = get_object_or_404(Comment, pk=pk)
    
    # Check if user is the comment author
    if comment.user != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to delete this comment.')
        
        # Redirect based on comment type
        if comment.content_type == 'NODE':
            return redirect('node-detail', pk=comment.object_id)
        else:
            return redirect('relationship-detail', pk=comment.object_id)
    
    if request.method == 'POST':
        # Remember details for redirect
        content_type = comment.content_type
        object_id = comment.object_id
        
        # Delete the comment
        comment.delete()
        
        messages.success(request, 'Comment deleted successfully.')
        
        # Redirect based on comment type
        if content_type == 'NODE':
            return redirect('node-detail', pk=object_id)
        else:
            return redirect('relationship-detail', pk=object_id)
    
    return render(request, 'comment_confirm_delete.html', {'comment': comment})

@login_required
def reply_to_comment_view(request, pk):
    """View for replying to a comment"""
    parent_comment = get_object_or_404(Comment, pk=pk)
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.user = request.user
            reply.content_type = parent_comment.content_type
            reply.object_id = parent_comment.object_id
            reply.parent = parent_comment
            reply.save()
            
            messages.success(request, 'Reply added successfully.')
            
            # Redirect based on comment type
            if parent_comment.content_type == 'NODE':
                return redirect('node-detail', pk=parent_comment.object_id)
            else:
                return redirect('relationship-detail', pk=parent_comment.object_id)
    
    # Redirect based on comment type
    if parent_comment.content_type == 'NODE':
        return redirect('node-detail', pk=parent_comment.object_id)
    else:
        return redirect('relationship-detail', pk=parent_comment.object_id)

@login_required
def relationship_suggestions_view(request):
    """View for relationship suggestions based on content similarity"""
    # Get suggested relationships
    try:
        suggester = RelationshipSuggester()
        suggested_relationships = suggester.suggest_relationships(threshold=0.25)
    except:
        suggested_relationships = []
    
    context = {
        'suggested_relationships': suggested_relationships,
    }
    
    return render(request, 'relationship_suggestions.html', context)

# API endpoints
def api_search(request):
    """API endpoint for search suggestions"""
    query = request.GET.get('q', '')
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    # Search in nodes
    nodes = KnowledgeNode.objects.filter(
        Q(title__icontains=query) | 
        Q(description__icontains=query)
    )[:10]
    
    results = []
    for node in nodes:
        results.append({
            'id': node.id,
            'title': node.title,
            'type': node.knowledge_type,
            'url': reverse('node-detail', kwargs={'pk': node.id}),
        })
    
    return JsonResponse({'results': results})

def api_suggest_relationships(request):
    """API endpoint for suggesting relationships"""
    threshold = float(request.GET.get('threshold', 0.3))
    try:
        suggester = RelationshipSuggester()
        suggested_relationships = suggester.suggest_relationships(threshold=threshold, max_suggestions=20)
        
        # Format for JSON response
        results = []
        for suggestion in suggested_relationships:
            results.append({
                'source_id': suggestion['source'].id,
                'source_title': suggestion['source'].title,
                'source_type': suggestion['source'].knowledge_type,
                'target_id': suggestion['target'].id,
                'target_title': suggestion['target'].title,
                'target_type': suggestion['target'].knowledge_type,
                'similarity': round(suggestion['similarity'], 3),
                'suggested_type': suggestion['suggested_type'],
            })
        
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def api_get_node_data(request, pk):
    """API endpoint for getting node data for dynamic loading in visualization"""
    try:
        # Get the node
        node = KnowledgeNode.objects.get(pk=pk)
        
        # Get related nodes (both source and target relationships)
        related_nodes = {}
        relationships = []
        
        # Source relationships
        for rel in node.source_relationships.all():
            target = rel.target
            if target.id not in related_nodes:
                related_nodes[target.id] = {
                    'id': target.id,
                    'title': target.title,
                    'group': 1 if target.knowledge_type == 'COURSE' else 2,
                }
            
            relationships.append({
                'from': node.id,
                'to': target.id,
                'title': rel.get_relationship_type_display(),
            })
        
        # Target relationships
        for rel in node.target_relationships.all():
            source = rel.source
            if source.id not in related_nodes:
                related_nodes[source.id] = {
                    'id': source.id,
                    'title': source.title,
                    'group': 1 if source.knowledge_type == 'COURSE' else 2,
                }
            
            relationships.append({
                'from': source.id,
                'to': node.id,
                'title': rel.get_relationship_type_display(),
            })
        
        # Prepare node data
        node_data = {
            'id': node.id,
            'title': node.title,
            'description': node.description,
            'type': node.knowledge_type,
            'group': 1 if node.knowledge_type == 'COURSE' else 2,
        }
        
        return JsonResponse({
            'node': node_data,
            'related_nodes': list(related_nodes.values()),
            'relationships': relationships,
        })
    except KnowledgeNode.DoesNotExist:
        return JsonResponse({'error': 'Node not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# In views_learning.py
class LearningPathListView(LoginRequiredMixin, ListView):
    template_name = 'learning_paths.html'
    # ...

class LearningPathDetailView(LoginRequiredMixin, DetailView):
    template_name = 'learning_path_detail.html'
    # ...

@login_required
def learning_path_step_view(request, path_id, step_id):
    # ...
    return render(request, 'learning_path_step.html', context)        