from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import KnowledgeNode, Relationship
from .services.nlp_service import RelationshipSuggester

@login_required
def relationship_suggestions_view(request):
    """View for relationship suggestions based on content similarity"""
    
    # Get threshold from request or use default
    threshold = float(request.GET.get('threshold', 0.3))
    
    # Get filter type
    filter_type = request.GET.get('filter', 'all')
    
    # Get suggested relationships
    try:
        suggester = RelationshipSuggester()
        suggested_relationships = suggester.suggest_relationships(threshold=threshold)
        
        # Apply filters if needed
        if filter_type == 'course_ideology':
            suggested_relationships = [s for s in suggested_relationships 
                                      if s['source'].knowledge_type == 'COURSE' and 
                                         s['target'].knowledge_type == 'IDEOLOGY']
        elif filter_type == 'ideology_course':
            suggested_relationships = [s for s in suggested_relationships 
                                      if s['source'].knowledge_type == 'IDEOLOGY' and 
                                         s['target'].knowledge_type == 'COURSE']
        elif filter_type == 'course_course':
            suggested_relationships = [s for s in suggested_relationships 
                                      if s['source'].knowledge_type == 'COURSE' and 
                                         s['target'].knowledge_type == 'COURSE']
        elif filter_type == 'ideology_ideology':
            suggested_relationships = [s for s in suggested_relationships 
                                      if s['source'].knowledge_type == 'IDEOLOGY' and 
                                         s['target'].knowledge_type == 'IDEOLOGY']
    except:
        suggested_relationships = []
    
    context = {
        'suggested_relationships': suggested_relationships,
    }
    
    return render(request, 'relationship_suggestions.html', context)

@login_required
@require_POST
def create_batch_relationships_view(request):
    """View for creating multiple relationships in batch"""
    
    suggestions = request.POST.getlist('suggestions[]')
    created_count = 0
    
    for suggestion in suggestions:
        try:
            # Parse the suggestion string (format: source_id-target_id-relationship_type)
            parts = suggestion.split('-')
            if len(parts) != 3:
                continue
                
            source_id, target_id, relationship_type = parts
            
            # Get the nodes
            source = get_object_or_404(KnowledgeNode, id=source_id)
            target = get_object_or_404(KnowledgeNode, id=target_id)
            
            # Check if relationship already exists
            existing = Relationship.objects.filter(
                source=source,
                target=target,
                relationship_type=relationship_type
            ).exists()
            
            if not existing:
                # Create the relationship
                relationship = Relationship(
                    source=source,
                    target=target,
                    relationship_type=relationship_type,
                    creator=request.user  # If you track who created the relationship
                )
                relationship.save()
                created_count += 1
                
                # Log activity if you're tracking user activities
                try:
                    from accounts.models import UserActivity
                    UserActivity.objects.create(
                        user=request.user,
                        activity_type='CREATE',
                        content_type='relationship',
                        object_id=relationship.id,
                        details=f"between {source.title} and {target.title}"
                    )
                except:
                    pass
                
        except Exception as e:
            continue
    
    if created_count > 0:
        messages.success(request, f'Successfully created {created_count} relationships!')
    else:
        messages.info(request, 'No new relationships were created.')
    
    return redirect('relationship-suggestions')

@login_required
def relationship_detail_view(request, pk):
    """View for relationship details"""
    relationship = get_object_or_404(Relationship, pk=pk)
    
    context = {
        'relationship': relationship,
    }
    
    return render(request, 'relationship_detail.html', context)