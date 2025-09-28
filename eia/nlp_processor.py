from typing import Dict, Any, List, TypedDict, Optional
import datetime
import re
import spacy
import yaml
from dateutil.parser import parse
from transformers import pipeline

# --- Data Structures for NLP Results ---

class ExtractedEntities(TypedDict, total=False):
    """A dictionary to hold entities extracted from text."""
    entidad: Optional[str]
    contacto_email: Optional[str]
    productos: List[str]
    fecha_limite: Optional[datetime.date]
    monto: Optional[float]

class NLPResult(TypedDict):
    """The standardized output from the NLP processor."""
    clasificacion: str
    confianza_clasificacion: float
    entidades: ExtractedEntities
    resumen: str
    es_relevante: bool
    confianza_relevancia: float

# --- NLP Processor ---

class NlpProcessor:
    """
    An NLP processing module that uses transformer models for classification
    and spaCy for entity extraction.
    """
    def __init__(self, catalog_path: str = "catalog.yml"):
        """
        Initializes the NLP processor, loading the required models.

        Args:
            catalog_path: Path to the product catalog file.
        """
        print("Initializing NLP Processor...")

        # 1. Load Intent Classification Model (Zero-Shot)
        # We use a zero-shot model because it's flexible and doesn't require
        # retraining to adjust the classification labels.
        print("Loading Zero-Shot Classification model...")
        self.classification_pipeline = pipeline(
            "zero-shot-classification",
            model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
        )
        print("Classification model loaded.")

        # 2. Load Entity Extraction Model (spaCy)
        print("Loading spaCy model for NER...")
        self.nlp_ner = spacy.load("es_core_news_lg")
        print("spaCy model loaded.")

        self.intent_labels = [
            "Licitación o requerimiento público",
            "Cotización o solicitud de precios",
            "Notificación judicial o acción urgente",
            "Factura o documento de pago",
            "Consulta o reclamo de cliente",
            "Publicidad o boletín informativo",
            "Conversación interna o sin acción requerida"
        ]

        # 3. Load Product Catalog
        self.product_catalog = []
        self.product_catalog_original_case = {} # Maps lowercase keyword to original name
        try:
            with open(catalog_path, 'r', encoding='utf-8') as f:
                catalog_data = yaml.safe_load(f)
                if 'productos' in catalog_data and isinstance(catalog_data['productos'], list):
                    for product_entry in catalog_data['productos']:
                        if 'nombre' in product_entry and 'sinonimos' in product_entry:
                            canonical_name = product_entry['nombre']
                            # Add the canonical name itself as a keyword
                            self.product_catalog.append(canonical_name.lower())
                            self.product_catalog_original_case[canonical_name.lower()] = canonical_name
                            # Add all synonyms
                            for synonym in product_entry['sinonimos']:
                                self.product_catalog.append(synonym.lower())
                                self.product_catalog_original_case[synonym.lower()] = canonical_name
                    print(f"Loaded {len(self.product_catalog)} product keywords from catalog.")
                else:
                    print(f"Warning: 'productos' key not found or not a list in '{catalog_path}'.")
        except FileNotFoundError:
            print(f"Warning: Product catalog '{catalog_path}' not found. Product matching will be disabled.")
        except Exception as e:
            print(f"Error loading catalog '{catalog_path}': {e}")

    def analyze(self, email_body: str) -> NLPResult:
        """
        Performs a full NLP analysis on the given email text.

        This is the main entry point that orchestrates the different NLP tasks.

        Args:
            email_body: The plain text content of the email.

        Returns:
            An NLPResult dictionary containing the analysis.
        """
        # --- 1. Classify Intent ---
        clasificacion, confianza_clasificacion = self._classify_intent(email_body)

        # --- 2. Extract Entities ---
        entidades = self._extract_entities(email_body)

        # --- 3. Check Relevance (based on classification and entities) ---
        es_relevante, confianza_relevancia = self._check_relevance(clasificacion, entidades)

        # --- 4. Generate Summary (Dummy) ---
        resumen = self._summarize(email_body, entidades)

        return NLPResult(
            clasificacion=clasificacion,
            confianza_clasificacion=confianza_clasificacion,
            entidades=entidades,
            resumen=resumen,
            es_relevante=es_relevante,
            confianza_relevancia=confianza_relevancia
        )

    def _classify_intent(self, text: str) -> (str, float):
        """
        Classifies the intent of the text using a zero-shot model.
        """
        # Truncate text to avoid errors with very long emails
        truncated_text = text[:1024]

        # Perform classification
        try:
            result = self.classification_pipeline(
                truncated_text,
                candidate_labels=self.intent_labels,
            )
            # The result gives us a list of labels sorted by score
            top_result = result['labels'][0]
            confidence = round(float(result['scores'][0]), 4)
            return top_result, confidence
        except Exception as e:
            print(f"Error during classification: {e}")
            return "Error de Clasificación", 0.0

    def _extract_entities(self, text: str) -> ExtractedEntities:
        """
        Extracts entities from the text using spaCy for NER and regex for others.
        """
        doc = self.nlp_ner(text)

        # --- Entity Extraction Logic ---
        entidad = self._find_organization(doc)
        contacto_email = self._find_email(text)
        productos = self._find_products(text)
        fecha_limite = self._find_deadline(text)
        monto = self._find_amount(text)

        return ExtractedEntities(
            entidad=entidad,
            contacto_email=contacto_email,
            productos=productos,
            fecha_limite=fecha_limite,
            monto=monto
        )

    def _find_organization(self, doc) -> Optional[str]:
        """
        Find the most likely organization name from spaCy entities.
        This version is more robust against common misclassifications.
        """
        candidates = []
        # Keywords that suggest a line is an organization, even if misclassified
        org_keywords = ['constructora', 'minera', 'gobierno', 'corp', 's.a.', 'asociados']
        # Common words that get misclassified as ORG
        ignore_list = ['estimados', 'saludos', 'buenas tardes', 'gracias', 'repuestos', 'servicios']

        for ent in doc.ents:
            text = ent.text.strip()
            text_lower = text.lower()

            # Skip if the entity is in our ignore list
            if text_lower in ignore_list:
                continue

            # Highest priority: ORG entities that are not ignored
            if ent.label_ == "ORG":
                candidates.append(text)

            # Second priority: PER entities that might contain the org name
            elif ent.label_ == "PER":
                # If a person's name contains a newline, the org is often on the next line
                if '\n' in text:
                    parts = text.split('\n')
                    # Often the last part is the company name
                    potential_org = parts[-1].strip()
                    candidates.append(potential_org)
                # Also check if the person's name contains an org keyword
                elif any(keyword in text_lower for keyword in org_keywords):
                    candidates.append(text)

            # Third priority: LOC entities that might be organizations
            elif ent.label_ == "LOC":
                if any(keyword in text_lower for keyword in org_keywords):
                    candidates.append(text)

        # From the candidates, prefer longer, more descriptive ones
        if not candidates:
            return None

        # Sort by length, descending, to get the most descriptive candidate
        candidates.sort(key=len, reverse=True)
        return candidates[0]

    def _find_email(self, text: str) -> Optional[str]:
        """Find the first valid email address."""
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        return match.group(0) if match else None

    def _find_products(self, text: str) -> List[str]:
        """Find product keywords from the catalog in the text."""
        found_products = set()
        text_lower = text.lower()
        for keyword in self.product_catalog:
            if keyword in text_lower:
                # Map the found keyword back to its canonical name
                canonical_name = self.product_catalog_original_case[keyword]
                found_products.add(canonical_name)
        return list(found_products)

    def _find_deadline(self, text: str) -> Optional[datetime.date]:
        """Find a potential deadline date."""
        # Regex for dates and keywords like "plazo", "fecha límite", "entrega"
        # This is a simple approach; more advanced parsing could be used.
        try:
            # A very forgiving parser
            match = parse(text, fuzzy=True, languages=['es'])
            return match.date()
        except (ValueError, TypeError):
            return None

    def _find_amount(self, text: str) -> Optional[float]:
        """Find a monetary amount."""
        # Regex for amounts like $1,234.56, 5.000 USD, 150.000, etc.
        # This regex handles CLP and USD formats with/without symbols and decimals
        pattern = r'[\$|USD]?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?|\d+([.,]\d{1,2})?)\b'
        match = re.search(pattern, text)
        if match:
            amount_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                return float(amount_str)
            except ValueError:
                return None
        return None

    def _check_relevance(self, clasificacion: str, entidades: ExtractedEntities) -> (bool, float):
        """
        Relevance check based on classification and the presence of key entities.
        """
        relevant_categories = {
            "Licitación o requerimiento público": {"requires": ["entidad"]},
            "Cotización o solicitud de precios": {"requires": ["productos"]},
            "Notificación judicial o acción urgente": {"requires": ["entidad"]},
        }

        if clasificacion not in relevant_categories:
            return False, 0.90 # Not a relevant category

        # Check if the required entities for this category are present
        requirements = relevant_categories[clasificacion]["requires"]
        for req in requirements:
            if not entidades.get(req):
                # e.g., It's a quotation, but no products were found.
                return False, 0.85

        # If we passed all checks, it's relevant
        return True, 0.95

    def _summarize(self, text: str, entidades: ExtractedEntities) -> str:
        """Generates a dynamic summary based on the extracted entities."""
        entidad = entidades.get('entidad')
        if not entidad:
            return "No se pudo generar un resumen claro (no se identificó la entidad)."

        summary = f"Oportunidad detectada de '{entidad}'"

        productos = entidades.get('productos')
        if productos:
            summary += f" para el suministro de {', '.join(productos)}"

        monto = entidades.get('monto')
        if monto:
            # Format with comma as thousands separator and 2 decimal places
            summary += f", por un monto aproximado de ${monto:,.2f}"

        fecha_limite = entidades.get('fecha_limite')
        if fecha_limite:
            summary += f", con fecha límite estimada el {fecha_limite.strftime('%Y-%m-%d')}"

        return summary + "."

if __name__ == '__main__':
    # Example of how to use the NLP Processor Stub
    print("--- Running NLP Processor Stub Demo ---")

    processor = NlpProcessor()

    # --- Example 1: A Quotation Email ---
    email_cotizacion = """
    Buenas tardes,

    Por favor, necesitaríamos una cotización para 500 unidades de Repuestos de tren de rodaje.
    La entrega sería para el próximo mes.

    Agradecemos su pronta respuesta.

    Saludos,
    Juan Pérez
    Constructora XYZ
    """

    print("\n--- Analyzing Quotation Email ---")
    analysis_result = processor.analyze(email_cotizacion)
    import json
    print(json.dumps(analysis_result, indent=2, default=str))

    # --- Example 2: An Informative Email ---
    email_informativo = """
    Estimados,

    Les informamos que nuestras oficinas permanecerán cerradas por el feriado nacional.

    Atentamente,
    El equipo de Soporte
    """
    print("\n--- Analyzing Informative Email ---")
    analysis_result_info = processor.analyze(email_informativo)
    print(json.dumps(analysis_result_info, indent=2, default=str))