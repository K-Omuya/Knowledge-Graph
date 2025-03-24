from django.urls import path
from . import views
from . import views_analytics
from . import views_import_export
from . import views_learning
from . import views_relationships  # Import the new views

# Main views
urlpatterns = [
    # Base views
    path('', views.index, name='index'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('help-documentation/', views.help_documentation_view, name='help-documentation'),
    path('search/', views.search_results_view, name='search-results'),
    
    # Node views
    path('nodes/', views.KnowledgeNodeListView.as_view(), name='node-list'),
    path('nodes/<int:pk>/', views.KnowledgeNodeDetailView.as_view(), name='node-detail'),
    path('nodes/create/', views.KnowledgeNodeCreateView.as_view(), name='node-create'),
    path('nodes/<int:pk>/update/', views.KnowledgeNodeUpdateView.as_view(), name='node-update'),
    path('nodes/<int:pk>/delete/', views.KnowledgeNodeDeleteView.as_view(), name='node-delete'),
    
    # Relationships
    path('relationships/create/', views.RelationshipCreateView.as_view(), name='relationship-create'),
    path('relationships/<int:pk>/', views_relationships.relationship_detail_view, name='relationship-detail'),
    path('relationships/<int:pk>/delete/', views.relationship_delete_view, name='relationship-delete'),
    
    # Relationship suggestions - new paths
    path('tools/relationship-suggestions/', views_relationships.relationship_suggestions_view, name='relationship-suggestions'),
    path('tools/create-batch-relationships/', views_relationships.create_batch_relationships_view, name='create-batch-relationships'),
    
    # Graph visualization
    path('graph/', views.visualize_graph, name='graph-visualization'),
    path('graph/advanced/', views.advanced_visualization, name='advanced-visualization'),
    
    # API views
    path('api/search/', views.api_search, name='api-search'),
    path('api/suggest-relationships/', views.api_suggest_relationships, name='api-suggest-relationships'),
    path('api/get-node-data/<int:pk>/', views.api_get_node_data, name='api-get-node-data'),
]

# User and collaboration views
user_patterns = [
    path('accounts/profile/', views.user_profile_view, name='user-profile'),
    path('accounts/activity/', views.user_activity_view, name='my-activity'),
    path('nodes/<int:pk>/comments/', views.node_comments_view, name='node-comments'),
    path('relationships/<int:pk>/comments/', views.relationship_comments_view, name='relationship-comments'),
    path('comments/<int:pk>/delete/', views.delete_comment_view, name='delete-comment'),
    path('comments/<int:pk>/reply/', views.reply_to_comment_view, name='reply-to-comment'),
]

# Analytics and tools
analytics_patterns = [
    path('analytics/', views_analytics.AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    path('analytics/heatmap/', views_analytics.HeatmapView.as_view(), name='heatmap'),
    path('analytics/metrics/', views_analytics.metrics_view, name='metrics'),
]

# Import/Export functionality
import_export_patterns = [
    path('import-export/', views_import_export.import_export_view, name='import-export'),
    path('export/<str:format>/', views_import_export.ExportGraphView.as_view(), name='export-graph'),
    path('import/', views_import_export.ImportGraphView.as_view(), name='import-graph'),
]

# Learning paths and quizzes
learning_patterns = [
    # Learning paths
    path('learning-paths/', views_learning.LearningPathListView.as_view(), name='learning-paths'),
    path('learning-paths/<int:pk>/', views_learning.LearningPathDetailView.as_view(), name='learning-path-detail'),
    path('learning-paths/create/', views_learning.LearningPathCreateView.as_view(), name='learning-path-create'),
    path('learning-paths/<int:pk>/update/', views_learning.LearningPathUpdateView.as_view(), name='learning-path-update'),
    path('learning-paths/<int:pk>/delete/', views_learning.LearningPathDeleteView.as_view(), name='learning-path-delete'),
    path('learning-paths/<int:path_id>/steps/<int:step_id>/', views_learning.learning_path_step_view, name='learning-path-step'),
    path('learning-paths/<int:path_id>/steps/<int:step_id>/complete/', views_learning.complete_step_view, name='complete-step'),
    
    # Quizzes
    path('quizzes/', views_learning.QuizListView.as_view(), name='quizzes'),
    path('quizzes/<int:pk>/', views_learning.QuizDetailView.as_view(), name='quiz-detail'),
    path('quizzes/create/', views_learning.QuizCreateView.as_view(), name='quiz-create'),
    path('quizzes/generate/', views_learning.generate_quiz_view, name='generate-quiz'),
    path('quizzes/<int:pk>/take/', views_learning.take_quiz_view, name='take-quiz'),
    path('quizzes/<int:quiz_id>/attempt/<int:attempt_id>/', views_learning.quiz_attempt_view, name='quiz-attempt'),
    path('quizzes/<int:quiz_id>/attempt/<int:attempt_id>/results/', views_learning.quiz_results_view, name='quiz-results'),
    
    # User progress
    path('my-progress/', views_learning.user_progress_view, name='my-progress'),
]

# Add all patterns to main urlpatterns
urlpatterns += user_patterns
urlpatterns += analytics_patterns
urlpatterns += import_export_patterns
urlpatterns += learning_patterns