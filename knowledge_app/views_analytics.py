from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q

import networkx as nx
import numpy as np
from collections import Counter

from .models import KnowledgeNode, Relationship
from .services.nlp_service import RelationshipSuggester

class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    """View for analytics dashboard"""
    template_name = 'analytics_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add analytics data here when implemented
        return context

class HeatmapView(LoginRequiredMixin, TemplateView):
    """View for relationship heatmap"""
    template_name = 'heatmap.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Get course nodes and ideology nodes
            course_nodes = KnowledgeNode.objects.filter(knowledge_type='COURSE')
            ideology_nodes = KnowledgeNode.objects.filter(knowledge_type='IDEOLOGY')
            
            # Create a matrix to represent connections
            matrix = []
            for course in course_nodes:
                row = []
                for ideology in ideology_nodes:
                    # Check if there's a relationship in either direction
                    has_relationship = Relationship.objects.filter(
                        (Q(source=course) & Q(target=ideology)) | 
                        (Q(source=ideology) & Q(target=course))
                    ).exists()
                    
                    row.append(1 if has_relationship else 0)
                matrix.append(row)
            
            # Calculate connection metrics
            course_count = course_nodes.count()
            ideology_count = ideology_nodes.count()
            
            # Total possible connections
            possible_connections = course_count * ideology_count
            
            # Count actual connections
            total_connections = sum(sum(row) for row in matrix)
            
            # Calculate connection density
            connection_density = total_connections / possible_connections if possible_connections > 0 else 0
            
            # Calculate coverage (% of nodes with at least one connection)
            connected_courses = sum(1 for row in matrix if sum(row) > 0)
            connected_ideologies = sum(1 for col_idx in range(len(ideology_nodes)) 
                                       if any(row[col_idx] == 1 for row in matrix))
            
            total_nodes = course_count + ideology_count
            connected_nodes = connected_courses + connected_ideologies
            coverage_percentage = (connected_nodes / total_nodes * 100) if total_nodes > 0 else 0
            
            # Get suggested connections
            # Get nodes that are not connected but should be
            suggester = RelationshipSuggester()
            suggested_connections = []
            
            try:
                all_suggestions = suggester.suggest_relationships(threshold=0.3, max_suggestions=50)
                
                # Filter suggestions to only include course -> ideology or ideology -> course
                for suggestion in all_suggestions:
                    source = suggestion['source']
                    target = suggestion['target']
                    
                    # Ensure we have one course and one ideology node
                    if (source.knowledge_type == 'COURSE' and target.knowledge_type == 'IDEOLOGY') or \
                       (source.knowledge_type == 'IDEOLOGY' and target.knowledge_type == 'COURSE'):
                        
                        # Check if they're already connected
                        already_connected = Relationship.objects.filter(
                            (Q(source=source) & Q(target=target)) | 
                            (Q(source=target) & Q(target=source))
                        ).exists()
                        
                        if not already_connected:
                            suggested_connections.append(suggestion)
                
                # Sort by similarity score and take top 10
                suggested_connections = sorted(suggested_connections, key=lambda x: x['similarity'], reverse=True)[:10]
            except Exception as e:
                # If the suggester fails, just provide an empty list
                suggested_connections = []
            
            context.update({
                'matrix': matrix,
                'course_nodes': course_nodes,
                'ideology_nodes': ideology_nodes,
                'total_connections': total_connections,
                'possible_connections': possible_connections,
                'connection_density': connection_density,
                'coverage_percentage': coverage_percentage,
                'suggested_connections': suggested_connections,
            })
        except Exception as e:
            # If there's an error, provide empty data
            context.update({
                'matrix': [],
                'course_nodes': [],
                'ideology_nodes': [],
                'error': str(e)
            })
        
        return context

def metrics_view(request):
    """View for system metrics"""
    context = {
        # Add metrics data here when implemented
    }
    return render(request, 'metrics.html')