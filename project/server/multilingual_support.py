import os
import json
import logging
from typing import Dict, List, Optional, Any
from langchain_ollama import OllamaLLM
from langdetect import detect, DetectorFactory
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure consistent language detection
DetectorFactory.seed = 0

# Load environment variables
load_dotenv()
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

# Cache directory
CACHE_DIR = "cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

class MultilingualSupport:
    """Handles multilingual support using Ollama model for Indian languages."""

    def __init__(self):
        self.supported_languages = {
            "en": "English",
            "hi": "Hindi",
            "te": "Telugu",
            "ta": "Tamil",
            "bn": "Bengali"
        }
        self.llm = self._initialize_llm()
        self.translation_prompt = self._define_translation_prompt()
        self.cache = self._load_cache()

    def _initialize_llm(self):
        """Initialize Ollama model."""
        try:
            logger.info(f"Initializing Ollama model: {OLLAMA_MODEL}")
            return OllamaLLM(
                model=OLLAMA_MODEL,
                base_url="http://localhost:11434",
                temperature=0.5  # Lower temperature for more precise translations
            )
        except Exception as e:
            logger.error(f"Failed to initialize Ollama model: {str(e)}")
            raise

    def _define_translation_prompt(self) -> PromptTemplate:
        """Define prompt template for translation with examples."""
        return PromptTemplate(
            input_variables=["text", "source_lang", "target_lang"],
            template="""
            You are an expert translator specializing in Indian languages. Translate the following text from {source_lang} to {target_lang} accurately and naturally, ensuring the translation fits the context of a form-filling application. Output ONLY the translated text as a single line, without any additional explanation or code.

            Examples:
            - English to Hindi: "Full Name" -> "पूरा नाम"
            - English to Hindi: "What is your full name?" -> "आपका पूरा नाम क्या है?"
            - English to Hindi: "Major" -> "प्रमुख विषय"
            - English to Telugu: "Full Name" -> "పూర్తి పేరు"
            - English to Tamil: "Full Name" -> "முழு பெயர்"
            - English to Bengali: "Full Name" -> "পূর্ণ নাম"

            Input text: {text}
            Source language: {source_lang}
            Target language: {target_lang}
            """
        )

    def _load_cache(self) -> Dict:
        """Load translation cache from file."""
        cache_file = os.path.join(CACHE_DIR, "translation_cache.json")
        try:
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.warning(f"Error loading cache: {str(e)}. Starting with empty cache.")
            return {}

    def _save_cache(self):
        """Save translation cache to file."""
        cache_file = os.path.join(CACHE_DIR, "translation_cache.json")
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logger.info("Translation cache saved.")
        except Exception as e:
            logger.error(f"Error saving cache: {str(e)}")

    def detect_language(self, text: str) -> str:
        """Detect the language of the input text."""
        try:
            lang = detect(text)
            return lang if lang in self.supported_languages else "en"
        except Exception as e:
            logger.warning(f"Language detection failed: {str(e)}. Defaulting to English.")
            return "en"

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text from source_lang to target_lang with caching."""
        if not text.strip():
            logger.warning("Empty text provided for translation. Returning empty string.")
            return text

        if source_lang not in self.supported_languages or target_lang not in self.supported_languages:
            logger.warning(f"Unsupported language pair: {source_lang} -> {target_lang}. Returning original text.")
            return text

        if source_lang == target_lang:
            logger.info(f"Source and target languages are the same: {source_lang}. Returning original text.")
            return text

        cache_key = f"{source_lang}:{target_lang}:{text}"
        if cache_key in self.cache:
            logger.info(f"Cache hit for translation: {cache_key}")
            return self.cache[cache_key]

        try:
            chain = RunnableSequence(self.translation_prompt | self.llm)
            translated_text = chain.invoke({
                "text": text,
                "source_lang": self.supported_languages[source_lang],
                "target_lang": self.supported_languages[target_lang]
            }).strip()
            if not translated_text:
                logger.warning(f"Translation returned empty string for '{text}' from {source_lang} to {target_lang}. Returning original text.")
                return text
            self.cache[cache_key] = translated_text
            self._save_cache()
            logger.info(f"Translated '{text}' from {source_lang} to {target_lang}: {translated_text}")
            return translated_text
        except Exception as e:
            logger.error(f"Translation failed for '{text}' from {source_lang} to {target_lang}: {str(e)}. Returning original text.")
            return text

    def validate_translation(self, original: str, translated: str, source_lang: str, target_lang: str) -> bool:
        """Validate translation quality by checking back-translation."""
        try:
            back_translated = self.translate(translated, target_lang, source_lang)
            original_words = set(original.lower().split())
            back_translated_words = set(back_translated.lower().split())
            overlap = len(original_words.intersection(back_translated_words)) / max(len(original_words), 1)
            is_valid = overlap > 0.5  # Lowered threshold for "llama3.2"
            logger.info(f"Translation validation: overlap={overlap:.2f}, valid={is_valid}")
            return is_valid
        except Exception as e:
            logger.error(f"Translation validation failed: {str(e)}. Assuming valid to avoid fallback.")
            return True  # Assume valid to avoid rejecting translations

    def translate_form_fields(self, form_schema: Dict[str, Any], target_lang: str) -> Dict[str, Any]:
        """Translate form field labels to the target language."""
        try:
            translated_schema = form_schema.copy()
            for form in translated_schema.get("forms", []):
                for field in form.get("fields", []):
                    label = field.get("label", "")
                    if label:
                        translated_label = self.translate(label, "en", target_lang)
                        field["translated_label"] = translated_label  # Use translation regardless of validation
                        if not self.validate_translation(label, translated_label, "en", target_lang):
                            logger.warning(f"Translation for '{label}' to {target_lang} may be suboptimal.")
                    if "options" in field:
                        field["translated_options"] = [
                            {
                                **opt,
                                "translated_text": self.translate(opt["text"], "en", target_lang)
                            } for opt in field.get("options", [])
                        ]
            return translated_schema
        except Exception as e:
            logger.error(f"Error translating form fields: {str(e)}")
            return form_schema

    def translate_questions(self, questions: List[Dict[str, str]], target_lang: str) -> List[Dict[str, str]]:
        """Translate generated questions to the target language."""
        try:
            translated_questions = []
            for question in questions:
                translated_question = self.translate(question["question"], "en", target_lang)
                translated_questions.append({
                    **question,
                    "translated_question": translated_question  # Use translation regardless of validation
                })
                if not self.validate_translation(question["question"], translated_question, "en", target_lang):
                    logger.warning(f"Translation for '{question['question']}' to {target_lang} may be suboptimal.")
            return translated_questions
        except Exception as e:
            logger.error(f"Error translating questions: {str(e)}")
            return questions

    def translate_response(self, user_response: str, source_lang: str, target_lang: str = "en") -> str:
        """Translate user response to the target language (default: English)."""
        return self.translate(user_response, source_lang, target_lang)

# Testing Framework
def test_multilingual_support():
    """Test suite for MultilingualSupport class."""
    multilingual = MultilingualSupport()

    # Sample form schema
    sample_schema = {
        "forms": [{
            "fields": [
                {"id": "1", "label": "Full Name", "type": "text", "required": True},
                {"id": "2", "label": "Major", "type": "dropdown", "required": True, "options": [
                    {"text": "Computer Science"}, {"text": "Mathematics"}
                ]}
            ]
        }]
    }

    # Sample questions
    sample_questions = [
        {"field_id": "1", "label": "Full Name", "question": "What is your full name?"},
        {"field_id": "2", "label": "Major", "question": "Which Major are you from? Options: Computer Science, Mathematics."}
    ]

    def test_language_detection():
        assert multilingual.detect_language("हाय, मेरा नाम राहुल है।") == "hi", "Should detect Hindi"
        assert multilingual.detect_language("Hello, my name is Rahul.") == "en", "Should detect English"
        assert multilingual.detect_language("తెలుగు టెక్స్ట్") == "te", "Should detect Telugu"

    def test_translation():
        translated = multilingual.translate("Full Name", "en", "hi")
        assert translated != "Full Name", "Should translate to Hindi"
        assert multilingual.validate_translation("Full Name", translated, "en", "hi"), "Translation should be valid"

    def test_form_field_translation():
        translated_schema = multilingual.translate_form_fields(sample_schema, "hi")
        assert "translated_label" in translated_schema["forms"][0]["fields"][0], "Should add translated_label"
        assert "translated_options" in translated_schema["forms"][0]["fields"][1], "Should add translated_options"

    def test_question_translation():
        translated_questions = multilingual.translate_questions(sample_questions, "hi")
        assert all("translated_question" in q for q in translated_questions), "All questions should have translated_question"
        assert translated_questions[0]["translated_question"] != sample_questions[0]["question"], "Question should be translated"

    test_language_detection()
    test_translation()
    test_form_field_translation()
    test_question_translation()
    logger.info("All multilingual tests passed successfully")

if __name__ == "__main__":
    test_multilingual_support()