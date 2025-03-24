import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re
import spacy
from sklearn.cluster import KMeans

from django.conf import settings
from ..models import KnowledgeNode, Relationship

# Download NLTK resources if they haven't been downloaded
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
    
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

# Load spaCy model
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    # If the model isn't installed, download a smaller one
    try:
        import os
        os.system('python -m spacy download en_core_web_sm')
        nlp = spacy.load('en_core_web_sm')
    except:
        nlp = None


class TextProcessor:
    """Handles text preprocessing for NLP tasks"""
    
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
    def preprocess_text(self, text):
        """Preprocess text for NLP analysis"""
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove HTML tags
        text = re.sub(r'<.*?>', '', text)
        
        # Remove special characters and numbers
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\d+', '', text)
        
        # Tokenize
        tokens = word_tokenize(text)
        
        # Remove stopwords and lemmatize
        processed_tokens = [
            self.lemmatizer.lemmatize(token) for token in tokens
            if token not in self.stop_words and len(token) > 2
        ]
        
        return ' '.join(processed_tokens)


class KeywordExtractor:
    """Extracts keywords from text using TF-IDF"""
    
    def __init__(self):
        self.text_processor = TextProcessor()
        self.vectorizer = TfidfVectorizer(max_features=1000)
        
    def extract_keywords(self, text, top_n=10):
        """Extract most important keywords from a text"""
        if not text or len(text) < 10:
            return []
            
        processed_text = self.text_processor.preprocess_text(text)
        
        # Transform the text using TF-IDF
        tfidf_matrix = self.vectorizer.fit_transform([processed_text])
        
        # Get feature names
        feature_names = self.vectorizer.get_feature_names_out()
        
        # Get TF-IDF scores
        tfidf_scores = tfidf_matrix.toarray()[0]
        
        # Create a dictionary of words and their TF-IDF scores
        word_scores = {feature_names[i]: tfidf_scores[i] for i in range(len(feature_names))}
        
        # Sort by score and take top_n
        sorted_keywords = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_keywords[:top_n]
    
    def extract_keywords_from_node(self, node, top_n=10):
        """Extract keywords from a knowledge node"""
        # Combine title and description for better keyword extraction
        combined_text = f"{node.title} {node.description}"
        return self.extract_keywords(combined_text, top_n)


class EntityExtractor:
    """Extracts named entities using spaCy"""
    
    def __init__(self):
        self.nlp = nlp
        
    def extract_entities(self, text):
        """Extract named entities from text"""
        if not text or not self.nlp:
            return []
            
        doc = self.nlp(text)
        
        entities = []
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char
            })
            
        return entities


class RelationshipSuggester:
    """Suggests potential relationships between nodes"""
    
    def __init__(self):
        self.text_processor = TextProcessor()
        self.keyword_extractor = KeywordExtractor()
        
    def _compute_similarity_matrix(self, nodes):
        """Compute similarity matrix between nodes"""
        # Preprocess all node texts
        processed_texts = []
        
        for node in nodes:
            combined_text = f"{node.title} {node.description}"
            processed_text = self.text_processor.preprocess_text(combined_text)
            processed_texts.append(processed_text)
        
        # Create TF-IDF matrix
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(processed_texts)
        
        # Compute cosine similarity
        similarity_matrix = cosine_similarity(tfidf_matrix)
        
        return similarity_matrix
    
    def suggest_relationships(self, threshold=0.3, max_suggestions=50):
        """Suggest potential relationships between nodes based on content similarity"""
        # Get all nodes
        nodes = KnowledgeNode.objects.all()
        
        if not nodes or len(nodes) < 2:
            return []
        
        # Compute similarity matrix
        similarity_matrix = self._compute_similarity_matrix(nodes)
        
        # Find pairs above threshold
        suggestions = []
        for i in range(len(nodes)):
            for j in range(i+1, len(nodes)):
                if similarity_matrix[i][j] >= threshold:
                    # Check if relationship already exists
                    existing_relationship = Relationship.objects.filter(
                        source=nodes[i], target=nodes[j]
                    ).exists() or Relationship.objects.filter(
                        source=nodes[j], target=nodes[i]
                    ).exists()
                    
                    if not existing_relationship:
                        # Determine relationship type (simplified logic)
                        rel_type = 'RELATED'
                        
                        # If one is course and one is ideology, use INFLUENCE
                        if (nodes[i].knowledge_type != nodes[j].knowledge_type):
                            if nodes[i].knowledge_type == 'COURSE' and nodes[j].knowledge_type == 'IDEOLOGY':
                                rel_type = 'INFLUENCE'
                            elif nodes[i].knowledge_type == 'IDEOLOGY' and nodes[j].knowledge_type == 'COURSE':
                                # Swap i and j so course is always source
                                i, j = j, i
                                rel_type = 'INFLUENCE'
                        
                        suggestions.append({
                            'source': nodes[i],
                            'target': nodes[j],
                            'similarity': similarity_matrix[i][j],
                            'suggested_type': rel_type
                        })
        
        # Sort by similarity and return top suggestions
        suggestions.sort(key=lambda x: x['similarity'], reverse=True)
        return suggestions[:max_suggestions]


class NodeCategorizer:
    """Automatically categorizes nodes based on content"""
    
    def __init__(self):
        self.text_processor = TextProcessor()
        
    def suggest_category(self, text):
        """Suggest whether a node is a course knowledge or ideological element"""
        # Load predefined keywords for each category
        course_keywords = {
            'algorithm', 'data', 'analysis', 'visualization', 'database', 'programming',
            'code', 'software', 'hardware', 'network', 'system', 'computer', 'technology',
            'tool', 'method', 'function', 'process', 'technical', 'implementation',
            'development', 'application', 'design', 'engineering', 'model', 'framework'
        }
        
        ideology_keywords = {
            'ethics', 'responsibility', 'society', 'privacy', 'security', 'impact',
            'social', 'political', 'economic', 'cultural', 'environmental', 'moral',
            'value', 'principle', 'philosophy', 'belief', 'perspective', 'critical',
            'justice', 'equality', 'freedom', 'rights', 'democracy', 'governance'
        }
        
        # Preprocess text
        processed_text = self.text_processor.preprocess_text(text)
        tokens = processed_text.split()
        
        # Count keyword matches for each category
        course_count = sum(1 for token in tokens if token in course_keywords)
        ideology_count = sum(1 for token in tokens if token in ideology_keywords)
        
        # Determine category and confidence
        total_matches = course_count + ideology_count
        if total_matches == 0:
            return {'category': 'COURSE', 'confidence': 0.5}
            
        course_ratio = course_count / total_matches
        
        if course_ratio >= 0.6:
            return {'category': 'COURSE', 'confidence': course_ratio}
        elif course_ratio <= 0.4:
            return {'category': 'IDEOLOGY', 'confidence': 1 - course_ratio}
        else:
            return {'category': 'UNCERTAIN', 'confidence': 0.5}


class ContentClusterer:
    """Clusters nodes based on content similarity"""
    
    def __init__(self):
        self.text_processor = TextProcessor()
        
    def cluster_nodes(self, num_clusters=5):
        """Cluster nodes based on content similarity"""
        # Get all nodes
        nodes = KnowledgeNode.objects.all()
        
        if not nodes or len(nodes) < num_clusters:
            return {}
            
        # Preprocess texts
        processed_texts = []
        for node in nodes:
            combined_text = f"{node.title} {node.description}"
            processed_text = self.text_processor.preprocess_text(combined_text)
            processed_texts.append(processed_text)
            
        # Create TF-IDF matrix
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(processed_texts)
        
        # Apply K-means clustering
        kmeans = KMeans(n_clusters=min(num_clusters, len(nodes)), random_state=42)
        kmeans.fit(tfidf_matrix)
        
        # Get cluster labels
        labels = kmeans.labels_
        
        # Organize nodes by cluster
        clusters = {}
        for i, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(nodes[i])
            
        return clusters