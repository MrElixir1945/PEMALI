"""
Intent Classifier Service
=========================
Deteksi intent menggunakan BGE-M3 + Logistic Regression (.pkl).
Zero token usage, ~50ms inference.
"""

import logging
from typing import Literal, Optional, Tuple
import os
import joblib
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

IntentMode = Literal["OBROLAN", "BELAJAR", "UJIAN", "OUT_OF_SCOPE"]
QueryType  = Literal["simple", "comparison", "multi_topic", "detailed", "quiz_request"]

BGE_QUERY_PREFIX = "query: "  # WAJIB untuk BGE-M3 inference

class IntentClassifier:
    def __init__(self):
        self.local_classifier = None
        self.embed_model: Optional[SentenceTransformer] = None
        self._load_models()

    def _load_models(self) -> None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "intent_classifier.pkl")
        
        print(f"[DEBUG] Looking for pkl at: {model_path}")
        print(f"[DEBUG] File exists: {os.path.exists(model_path)}")
        
        if not os.path.exists(model_path):
            print("[DEBUG] PKL NOT FOUND")
            return

        try:
            model_data = joblib.load(model_path)
            print(f"[DEBUG] PKL loaded, type: {type(model_data)}")
            if isinstance(model_data, dict) and 'classifier' in model_data:
                self.local_classifier = model_data['classifier']
            else:
                self.local_classifier = model_data
            logger.info("[IntentClassifier] Logistic Regression loaded.")

            self.embed_model = SentenceTransformer('BAAI/bge-m3')
            logger.info("[IntentClassifier] BGE-M3 loaded.")
        except Exception as e:
            logger.error(f"[IntentClassifier] Gagal load model: {e}")

    def analyze_intent(
        self,
        user_input: str,
        has_context: bool
    ) -> Tuple[IntentMode, QueryType]:
        
        # Fallback jika model belum siap
        if not self.local_classifier or not self.embed_model:
            logger.warning("[IntentClassifier] Model belum siap, pakai fallback.")
            return "BELAJAR", "simple"

        # BGE-M3: WAJIB prefix "query:" saat inference
        try:
            embedding = self.embed_model.encode(
                [BGE_QUERY_PREFIX + user_input],
                show_progress_bar=False
            )
            ai_prediction = self.local_classifier.predict(embedding)[0]
        except Exception as e:
            logger.error(f"[IntentClassifier] Predict error: {e}")
            return "BELAJAR", "simple"

        # Map hasil .pkl → IntentMode
        mode: IntentMode
        if ai_prediction == "exam":
            mode = "UJIAN"
        elif ai_prediction == "casual":
            mode = "OBROLAN"
        elif ai_prediction == "out_of_scope":
            mode = "OUT_OF_SCOPE"
        else:  # "academic"
            mode = "BELAJAR"

        # QueryType
        input_lower = user_input.lower()
        query_type: QueryType = "simple"

        if mode == "UJIAN":
            query_type = "quiz_request"
        elif mode == "BELAJAR":
            if any(k in input_lower for k in ["bandingkan", "beda", "versus", "vs"]):
                query_type = "comparison"
            elif "jelaskan" in input_lower or len(user_input.split()) > 10:
                query_type = "detailed"

        # ✅ Force output hanya BELAJAR atau UJIAN
        if mode not in ("BELAJAR", "UJIAN"):
            mode = "BELAJAR"
            query_type = "simple"

        return mode, query_type


# Singleton — lazy load saat first import
classifier = IntentClassifier()