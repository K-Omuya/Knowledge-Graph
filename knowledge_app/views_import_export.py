from django.shortcuts import render, redirect
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.core.exceptions import ValidationError
from django.contrib import messages

import json
import csv
import networkx as nx
from io import StringIO, BytesIO
import zipfile

from .models import KnowledgeNode, Relationship


class ExportGraphView(LoginRequiredMixin, View):
    """
    Export the entire knowledge graph in different formats
    """
    def get(self, request, format='json'):
        # Collect all nodes and relationships
        nodes = KnowledgeNode.objects.all()
        relationships = Relationship.objects.all()
        
        if format == 'json':
            # Export as JSON
            data = {
                'nodes': [
                    {
                        'id': node.id,
                        'title': node.title,
                        'description': node.description,
                        'knowledge_type': node.knowledge_type,
                        'created_at': node.created_at.isoformat(),
                        'updated_at': node.updated_at.isoformat(),
                    }
                    for node in nodes
                ],
                'relationships': [
                    {
                        'id': rel.id,
                        'source_id': rel.source.id,
                        'target_id': rel.target.id,
                        'relationship_type': rel.relationship_type,
                        'description': rel.description,
                    }
                    for rel in relationships
                ]
            }
            
            response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
            response['Content-Disposition'] = 'attachment; filename="knowledge_graph.json"'
            return response
            
        elif format == 'csv':
            # Create a zip file with nodes.csv and relationships.csv
            buffer = BytesIO()
            with zipfile.ZipFile(buffer, 'w') as zip_file:
                # Generate nodes CSV
                nodes_csv = StringIO()
                writer = csv.writer(nodes_csv)
                writer.writerow(['id', 'title', 'description', 'knowledge_type', 'created_at', 'updated_at'])
                
                for node in nodes:
                    writer.writerow([
                        node.id,
                        node.title,
                        node.description,
                        node.knowledge_type,
                        node.created_at.isoformat(),
                        node.updated_at.isoformat()
                    ])
                
                zip_file.writestr('nodes.csv', nodes_csv.getvalue())
                
                # Generate relationships CSV
                relationships_csv = StringIO()
                writer = csv.writer(relationships_csv)
                writer.writerow(['id', 'source_id', 'target_id', 'relationship_type', 'description'])
                
                for rel in relationships:
                    writer.writerow([
                        rel.id,
                        rel.source.id,
                        rel.target.id,
                        rel.relationship_type,
                        rel.description or ''
                    ])
                
                zip_file.writestr('relationships.csv', relationships_csv.getvalue())
            
            buffer.seek(0)
            response = HttpResponse(buffer.read(), content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="knowledge_graph.zip"'
            return response
            
        elif format == 'graphml':
            # Create a NetworkX graph and export as GraphML
            G = nx.DiGraph()
            
            # Add nodes with attributes
            for node in nodes:
                G.add_node(
                    node.id,
                    title=node.title,
                    description=node.description,
                    knowledge_type=node.knowledge_type,
                    created_at=node.created_at.isoformat(),
                    updated_at=node.updated_at.isoformat()
                )
                
            # Add edges with attributes
            for rel in relationships:
                G.add_edge(
                    rel.source.id,
                    rel.target.id,
                    id=rel.id,
                    relationship_type=rel.relationship_type,
                    description=rel.description or ''
                )
                
            # Write to GraphML
            graphml_output = StringIO()
            nx.write_graphml(G, graphml_output)
            
            response = HttpResponse(graphml_output.getvalue(), content_type='application/xml')
            response['Content-Disposition'] = 'attachment; filename="knowledge_graph.graphml"'
            return response
        
        else:
            return JsonResponse({'error': 'Unsupported export format'}, status=400)


class ImportGraphView(LoginRequiredMixin, View):
    """
    Import nodes and relationships from various formats
    """
    template_name = 'knowledge_app/import_graph.html'
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        import_file = request.FILES.get('import_file')
        import_type = request.POST.get('import_type', 'json')
        conflict_resolution = request.POST.get('conflict_resolution', 'skip')
        
        if not import_file:
            messages.error(request, "No file was uploaded.")
            return render(request, self.template_name)
        
        try:
            if import_type == 'json':
                stats = self._import_from_json(import_file, conflict_resolution)
            elif import_type == 'csv':
                stats = self._import_from_csv(import_file, conflict_resolution)
            elif import_type == 'graphml':
                stats = self._import_from_graphml(import_file, conflict_resolution)
            else:
                messages.error(request, f"Unsupported import format: {import_type}")
                return render(request, self.template_name)
            
            messages.success(
                request, 
                f"Import successful. Added {stats['nodes_added']} nodes and {stats['relationships_added']} relationships. "
                f"Skipped {stats['nodes_skipped']} nodes and {stats['relationships_skipped']} relationships."
            )
            
        except Exception as e:
            messages.error(request, f"Error during import: {str(e)}")
            
        return render(request, self.template_name)
    
    def _import_from_json(self, import_file, conflict_resolution):
        """Import from JSON format"""
        data = json.loads(import_file.read().decode('utf-8'))
        
        stats = {
            'nodes_added': 0,
            'nodes_skipped': 0,
            'relationships_added': 0,
            'relationships_skipped': 0
        }
        
        # Import nodes
        node_id_mapping = {}  # Map original IDs to new IDs
        
        for node_data in data.get('nodes', []):
            original_id = node_data.get('id')
            title = node_data.get('title')
            
            # Check if node with this title already exists
            existing_node = KnowledgeNode.objects.filter(title=title).first()
            
            if existing_node:
                if conflict_resolution == 'skip':
                    # Skip this node
                    node_id_mapping[original_id] = existing_node.id
                    stats['nodes_skipped'] += 1
                    continue
                elif conflict_resolution == 'update':
                    # Update existing node
                    existing_node.description = node_data.get('description', '')
                    existing_node.knowledge_type = node_data.get('knowledge_type', 'COURSE')
                    existing_node.save()
                    node_id_mapping[original_id] = existing_node.id
                    stats['nodes_added'] += 1
                    continue
            
            # Create new node
            new_node = KnowledgeNode(
                title=title,
                description=node_data.get('description', ''),
                knowledge_type=node_data.get('knowledge_type', 'COURSE')
            )
            
            try:
                new_node.save()
                node_id_mapping[original_id] = new_node.id
                stats['nodes_added'] += 1
            except ValidationError:
                stats['nodes_skipped'] += 1
        
        # Import relationships
        for rel_data in data.get('relationships', []):
            source_id = rel_data.get('source_id')
            target_id = rel_data.get('target_id')
            
            # Skip if we don't have mapping for either source or target
            if source_id not in node_id_mapping or target_id not in node_id_mapping:
                stats['relationships_skipped'] += 1
                continue
            
            # Get the new IDs
            new_source_id = node_id_mapping[source_id]
            new_target_id = node_id_mapping[target_id]
            
            # Check if relationship already exists
            existing_rel = Relationship.objects.filter(
                source_id=new_source_id,
                target_id=new_target_id,
                relationship_type=rel_data.get('relationship_type', 'RELATED')
            ).first()
            
            if existing_rel:
                if conflict_resolution == 'skip':
                    stats['relationships_skipped'] += 1
                    continue
                elif conflict_resolution == 'update':
                    existing_rel.description = rel_data.get('description', '')
                    existing_rel.save()
                    stats['relationships_added'] += 1
                    continue
            
            # Create new relationship
            try:
                new_rel = Relationship(
                    source_id=new_source_id,
                    target_id=new_target_id,
                    relationship_type=rel_data.get('relationship_type', 'RELATED'),
                    description=rel_data.get('description', '')
                )
                new_rel.save()
                stats['relationships_added'] += 1
            except ValidationError:
                stats['relationships_skipped'] += 1
        
        return stats
    
    def _import_from_csv(self, import_file, conflict_resolution):
        """Import from CSV (ZIP file with nodes.csv and relationships.csv)"""
        with zipfile.ZipFile(import_file) as zip_ref:
            # First, process nodes
            with zip_ref.open('nodes.csv') as nodes_file:
                nodes_csv = StringIO(nodes_file.read().decode('utf-8'))
                return self._process_csv_import(nodes_csv, 'relationships.csv', zip_ref, conflict_resolution)
    
    def _process_csv_import(self, nodes_csv, relationships_filename, zip_ref, conflict_resolution):
        """Process the CSV import from the zip file"""
        stats = {
            'nodes_added': 0,
            'nodes_skipped': 0,
            'relationships_added': 0,
            'relationships_skipped': 0
        }
        
        # Process nodes
        node_id_mapping = {}
        reader = csv.DictReader(nodes_csv)
        
        for row in reader:
            original_id = row.get('id')
            title = row.get('title')
            
            # Check if node exists
            existing_node = KnowledgeNode.objects.filter(title=title).first()
            
            if existing_node:
                if conflict_resolution == 'skip':
                    node_id_mapping[original_id] = existing_node.id
                    stats['nodes_skipped'] += 1
                    continue
                elif conflict_resolution == 'update':
                    existing_node.description = row.get('description', '')
                    existing_node.knowledge_type = row.get('knowledge_type', 'COURSE')
                    existing_node.save()
                    node_id_mapping[original_id] = existing_node.id
                    stats['nodes_added'] += 1
                    continue
            
            # Create new node
            try:
                new_node = KnowledgeNode(
                    title=title,
                    description=row.get('description', ''),
                    knowledge_type=row.get('knowledge_type', 'COURSE')
                )
                new_node.save()
                node_id_mapping[original_id] = new_node.id
                stats['nodes_added'] += 1
            except ValidationError:
                stats['nodes_skipped'] += 1
        
        # Process relationships
        with zip_ref.open(relationships_filename) as relationships_file:
            relationships_csv = StringIO(relationships_file.read().decode('utf-8'))
            reader = csv.DictReader(relationships_csv)
            
            for row in reader:
                source_id = row.get('source_id')
                target_id = row.get('target_id')
                
                # Skip if we don't have mapping for either source or target
                if source_id not in node_id_mapping or target_id not in node_id_mapping:
                    stats['relationships_skipped'] += 1
                    continue
                
                # Get the new IDs
                new_source_id = node_id_mapping[source_id]
                new_target_id = node_id_mapping[target_id]
                
                # Check if relationship exists
                existing_rel = Relationship.objects.filter(
                    source_id=new_source_id,
                    target_id=new_target_id,
                    relationship_type=row.get('relationship_type', 'RELATED')
                ).first()
                
                if existing_rel:
                    if conflict_resolution == 'skip':
                        stats['relationships_skipped'] += 1
                        continue
                    elif conflict_resolution == 'update':
                        existing_rel.description = row.get('description', '')
                        existing_rel.save()
                        stats['relationships_added'] += 1
                        continue
                
                # Create new relationship
                try:
                    new_rel = Relationship(
                        source_id=new_source_id,
                        target_id=new_target_id,
                        relationship_type=row.get('relationship_type', 'RELATED'),
                        description=row.get('description', '')
                    )
                    new_rel.save()
                    stats['relationships_added'] += 1
                except ValidationError:
                    stats['relationships_skipped'] += 1
        
        return stats
    
    def _import_from_graphml(self, import_file, conflict_resolution):
        """Import from GraphML format"""
        # Parse GraphML file
        content = import_file.read().decode('utf-8')
        G = nx.parse_graphml(content)
        
        stats = {
            'nodes_added': 0,
            'nodes_skipped': 0,
            'relationships_added': 0,
            'relationships_skipped': 0
        }
        
        # Process nodes
        node_id_mapping = {}
        for node_id, attrs in G.nodes(data=True):
            title = attrs.get('title', f"Node {node_id}")
            
            # Check if node exists
            existing_node = KnowledgeNode.objects.filter(title=title).first()
            
            if existing_node:
                if conflict_resolution == 'skip':
                    node_id_mapping[node_id] = existing_node.id
                    stats['nodes_skipped'] += 1
                    continue
                elif conflict_resolution == 'update':
                    existing_node.description = attrs.get('description', '')
                    existing_node.knowledge_type = attrs.get('knowledge_type', 'COURSE')
                    existing_node.save()
                    node_id_mapping[node_id] = existing_node.id
                    stats['nodes_added'] += 1
                    continue
            
            # Create new node
            try:
                new_node = KnowledgeNode(
                    title=title,
                    description=attrs.get('description', ''),
                    knowledge_type=attrs.get('knowledge_type', 'COURSE')
                )
                new_node.save()
                node_id_mapping[node_id] = new_node.id
                stats['nodes_added'] += 1
            except ValidationError:
                stats['nodes_skipped'] += 1
        
        # Process edges (relationships)
        for source, target, attrs in G.edges(data=True):
            # Skip if we don't have mapping for either source or target
            if source not in node_id_mapping or target not in node_id_mapping:
                stats['relationships_skipped'] += 1
                continue
            
            # Get the new IDs
            new_source_id = node_id_mapping[source]
            new_target_id = node_id_mapping[target]
            
            # Check if relationship exists
            existing_rel = Relationship.objects.filter(
                source_id=new_source_id,
                target_id=new_target_id,
                relationship_type=attrs.get('relationship_type', 'RELATED')
            ).first()
            
            if existing_rel:
                if conflict_resolution == 'skip':
                    stats['relationships_skipped'] += 1
                    continue
                elif conflict_resolution == 'update':
                    existing_rel.description = attrs.get('description', '')
                    existing_rel.save()
                    stats['relationships_added'] += 1
                    continue
            
            # Create new relationship
            try:
                new_rel = Relationship(
                    source_id=new_source_id,
                    target_id=new_target_id,
                    relationship_type=attrs.get('relationship_type', 'RELATED'),
                    description=attrs.get('description', '')
                )
                new_rel.save()
                stats['relationships_added'] += 1
            except ValidationError:
                stats['relationships_skipped'] += 1
        
        return stats

def import_export_view(request):
    """Main import/export interface"""
    context = {
        # Add context data here when implemented
    }
    return render(request, 'import_export.html')        