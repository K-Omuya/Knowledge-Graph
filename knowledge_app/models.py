from django.db import models
from ckeditor.fields import RichTextField


from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class KnowledgeNode(models.Model):
    """
    Represents a node in the knowledge graph.
    Each node can be either a course knowledge point or an ideological element.
    """
    KNOWLEDGE_TYPES = [
        ('COURSE', 'Course Knowledge'),
        ('IDEOLOGY', 'Ideological Element'),
    ]
    
    title = models.CharField(max_length=200)
    description = RichTextField()  # Rich text field instead of TextField
    knowledge_type = models.CharField(max_length=10, choices=KNOWLEDGE_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Content enrichment fields
    external_links = models.TextField(blank=True, help_text="Comma-separated list of external URLs")
    video_embed = models.TextField(blank=True, help_text="Embed code for videos")
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['title']


class NodeAttachment(models.Model):
    """
    Represents files attached to knowledge nodes
    """
    node = models.ForeignKey(KnowledgeNode, related_name='attachments', on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to='node_attachments/')
    file_type = models.CharField(max_length=50, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} ({self.node.title})"
    
    def save(self, *args, **kwargs):
        # Determine file type based on extension
        if self.file:
            file_name = self.file.name.lower()
            if file_name.endswith('.pdf'):
                self.file_type = 'PDF'
            elif file_name.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                self.file_type = 'Image'
            elif file_name.endswith(('.doc', '.docx')):
                self.file_type = 'Word Document'
            elif file_name.endswith(('.ppt', '.pptx')):
                self.file_type = 'Presentation'
            elif file_name.endswith(('.xls', '.xlsx')):
                self.file_type = 'Spreadsheet'
            else:
                self.file_type = 'Other'
        super().save(*args, **kwargs)


class Relationship(models.Model):
    """
    Represents a relationship between two knowledge nodes.
    """
    RELATIONSHIP_TYPES = [
        ('RELATED', 'Related To'),
        ('PART_OF', 'Part Of'),
        ('INFLUENCE', 'Influences'),
        ('EXAMPLE', 'Example Of'),
    ]
    
    source = models.ForeignKey(KnowledgeNode, related_name='source_relationships', 
                               on_delete=models.CASCADE)
    target = models.ForeignKey(KnowledgeNode, related_name='target_relationships', 
                               on_delete=models.CASCADE)
    relationship_type = models.CharField(max_length=10, choices=RELATIONSHIP_TYPES)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.source} {self.get_relationship_type_display()} {self.target}"
    
    class Meta:
        unique_together = ['source', 'target', 'relationship_type']