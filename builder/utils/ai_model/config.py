# ai_models/config.py
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from langchain_openai import ChatOpenAI
from langchain.schema.language_model import BaseLanguageModel
from ai.models import AIModel

# Updated import for Ollama
try:
    from langchain_ollama import OllamaLLM
except ImportError:
    # Fallback to community version if langchain-ollama not installed
    from langchain_community.llms import Ollama as OllamaLLM

logger = logging.getLogger(__name__)

class AIModelConfig:
    """Dynamic AI model configuration manager"""
    
    def __init__(self):
        self._models_cache = {}
        
    def get_active_model(self, model_type: str = 'CHAT') -> Optional[AIModel]:
        """Get the active AI model for a specific type"""
        try:
            # You can add logic here to determine which model is "active"
            # For now, we'll get the first available model of the requested type
            return AIModel.objects.filter(model_type=model_type).first()
        except Exception as e:
            logger.error(f"Error fetching active model: {e}")
            return None
    
    def create_langchain_model(self, model_type: str = 'CHAT') -> Optional[BaseLanguageModel]:
        """Create a LangChain model instance from AIModel configuration"""
        ai_model = self.get_active_model(model_type)
        if not ai_model:
            logger.error(f"No active model found for type: {model_type}")
            return None
            
        cache_key = f"{ai_model.provider}_{ai_model.name}_{model_type}"
        
        # Check cache first
        if cache_key in self._models_cache:
            return self._models_cache[cache_key]
        
        try:
            if ai_model.provider.lower() == 'ollama':
                model = OllamaLLM(
                    model=ai_model.name,
                    base_url=getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434'),
                    temperature=0.1,  # Low temperature for structured extraction
                    num_ctx=ai_model.context_length,
                )
            elif ai_model.provider.lower() == 'openai':
                model = ChatOpenAI(
                    model=ai_model.name,  # Updated from model_name to model
                    temperature=0.1,
                    max_tokens=4000,
                    api_key=getattr(settings, 'OPENAI_API_KEY', None)
                )
            else:
                logger.error(f"Unsupported provider: {ai_model.provider}")
                return None
            
            # Cache the model
            self._models_cache[cache_key] = model
            logger.info(f"Created {ai_model.provider} model: {ai_model.name}")
            return model
            
        except Exception as e:
            logger.error(f"Error creating model {ai_model.name}: {e}")
            return None
    
    def get_model_config(self, model_type: str = 'CHAT') -> Dict[str, Any]:
        """Get model configuration as dictionary"""
        ai_model = self.get_active_model(model_type)
        if not ai_model:
            return {}
            
        return {
            'name': ai_model.name,
            'provider': ai_model.provider,
            'model_type': ai_model.model_type,
            'model_size': ai_model.model_size,
            'context_length': ai_model.context_length,
        }
    
    def clear_cache(self):
        """Clear the models cache"""
        self._models_cache.clear()

# Global instance
ai_config = AIModelConfig()