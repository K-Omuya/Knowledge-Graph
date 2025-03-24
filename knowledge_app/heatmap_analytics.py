from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.template.defaulttags import register

from .models import KnowledgeNode, Relationship

# Custom template filters for the heatmap
@register.filter
def get_item(lst, i):
    try:
        return lst[i]
    except:
        return None

@register.filter
def get_row(matrix, i):
    try:
        return matrix[i]
    except:
        return []

@register.filter
def get_intensity(value):
    if not value or value == 0:
        return 0
    elif value == 1:
        return 0.25
    elif value == 2:
        return 0.5
    elif value == 3:
        return 0.75
    else:
        return 1.0

@register.filter
def get_relationship_types(matrix_info, row_idx, col_idx):
    try:
        return matrix_info[row_idx][col_idx]['types']
    except:
        return ""

class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    """View for analytics dashboard"""
    template_name = 'analytics_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add analytics data when implemented
        return context

class HeatmapView(LoginRequiredMixin, TemplateView):
    """View for relationship heatmap"""
    template_name = 'heatmap.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter parameters
        threshold = self.request.GET.get('threshold', 'all')
        relationship_type = self.request.GET.get('relationship_type', 'all')
        
        # Get course nodes and ideology nodes
        course_nodes = KnowledgeNode.objects.filter(knowledge_type='COURSE')
        ideology_nodes = KnowledgeNode.objects.filter(knowledge_type='IDEOLOGY')
        
        # Count total nodes
        total_nodes = course_nodes.count() + ideology_nodes.count()
        
        # Get relationship counts by type
        relationship_counts = {}
        for rel_type, rel_name in Relationship.RELATIONSHIP_TYPES:
            count = Relationship.objects.filter(relationship_type=rel_type).count()
            if count > 0:
                relationship_counts[rel_name] = count
        
        # Total connection count
        connection_count = Relationship.objects.count()
        
        # Create a matrix for the heatmap
        matrix = []
        matrix_info = []  # Additional information about relationships
        
        for ideology in ideology_nodes:
            row = []
            row_info = []
            
            for course in course_nodes:
                # Query for relationships between these nodes
                relationship_query = Relationship.objects.filter(
                    (Q(source=course) & Q(target=ideology)) | 
                    (Q(source=ideology) & Q(target=course))
                )
                
                # Apply relationship type filter if specified
                if relationship_type != 'all':
                    relationship_query = relationship_query.filter(relationship_type=relationship_type)
                
                # Count relationships
                relationship_count = relationship_query.count()
                
                # Apply threshold filter
                if threshold != 'all' and relationship_count < int(threshold):
                    relationship_count = 0
                
                row.append(relationship_count)
                
                # Get relationship type information
                if relationship_count > 0:
                    rel_types = relationship_query.values_list('relationship_type', flat=True)
                    rel_type_names = [dict(Relationship.RELATIONSHIP_TYPES).get(rt, rt) for rt in rel_types]
                    rel_type_counts = {}
                    for rt in rel_type_names:
                        rel_type_counts[rt] = rel_type_counts.get(rt, 0) + 1
                    
                    # Format for display
                    rel_type_str = ", ".join([f"{count} {name}" for name, count in rel_type_counts.items()])
                    
                    row_info.append({
                        'count': relationship_count,
                        'types': rel_type_str
                    })
                else:
                    row_info.append({
                        'count': 0,
                        'types': ""
                    })
            
            matrix.append(row)
            matrix_info.append(row_info)
        
        context.update({
            'matrix': matrix,
            'matrix_info': matrix_info,
            'course_nodes': course_nodes,
            'ideology_nodes': ideology_nodes,
            'threshold': threshold,
            'relationship_type': relationship_type,
            'total_nodes': total_nodes,
            'course_nodes_count': course_nodes.count(),
            'ideology_nodes_count': ideology_nodes.count(),
            'connection_count': connection_count,
            'relationship_counts': relationship_counts,
        })
        
        return context

def metrics_view(request):
    """View for system metrics"""
    context = {
        # Add metrics data here when implemented
    }
    return render(request, 'metrics.html')