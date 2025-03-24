from django import forms
from .models import KnowledgeNode, Relationship

class KnowledgeNodeForm(forms.ModelForm):
    class Meta:
        model = KnowledgeNode
        fields = ['title', 'description', 'knowledge_type']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class RelationshipForm(forms.ModelForm):
    class Meta:
        model = Relationship
        fields = ['source', 'target', 'relationship_type', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        source = cleaned_data.get('source')
        target = cleaned_data.get('target')
        relationship_type = cleaned_data.get('relationship_type')
        
        # Check if source and target are the same
        if source and target and source == target:
            raise forms.ValidationError("A node cannot have a relationship with itself.")
        
        # Check if this relationship already exists
        if source and target and relationship_type:
            if Relationship.objects.filter(
                source=source, 
                target=target,
                relationship_type=relationship_type
            ).exists():
                raise forms.ValidationError("This relationship already exists.")
        
        return cleaned_data


# Add these imports at the top of your forms.py file
from django import forms
from .models import KnowledgeNode, Relationship
from .models_collaborative import Comment
from ckeditor.widgets import CKEditorWidget

# Make sure you already have KnowledgeNodeForm and RelationshipForm defined

class CommentForm(forms.ModelForm):
    """Form for adding comments to nodes and relationships"""
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add your comment...'}),
        }

class NodeAttachmentForm(forms.Form):
    """Form for uploading files to be attached to nodes"""
    title = forms.CharField(max_length=100)
    file = forms.FileField()