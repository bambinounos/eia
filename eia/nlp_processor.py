from typing import Dict, Any, List, TypedDict, Optional
import datetime
import random

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

# --- NLP Processor Stub ---

class NlpProcessor:
    """
    A stub for the NLP processing module.

    This class mimics the interface of the real NLP processor but returns
    hardcoded dummy data. This allows for the development and testing of other
    parts of the application without needing to load the actual (and heavy)
    NLP models.
    """
    def __init__(self, catalog_path: str = "catalog.yml"):
        """
        Initializes the NLP processor stub.

        Args:
            catalog_path: Path to the product catalog file (ignored by the stub).
        """
        print("Initializing NLP Processor STUB.")
        # In the real implementation, this is where we would load models.
        # For the stub, we might load the catalog to make the dummy data
        # slightly more realistic.
        self.dummy_products = ["Repuestos de tren de rodaje", "Sistemas Hidráulicos"]
        self.dummy_entities = [
            "Constructora XYZ", "Minera del Sur", "Gobierno Regional", "ACME Corp"
        ]

    def analyze(self, email_body: str) -> NLPResult:
        """
        Performs a full NLP analysis on the given email text.

        This is the main entry point that orchestrates the different NLP tasks.

        Args:
            email_body: The plain text content of the email.

        Returns:
            An NLPResult dictionary containing the analysis.
        """
        # --- 1. Classify Intent (Dummy) ---
        clasificacion, confianza_clasificacion = self._classify_intent(email_body)

        # --- 2. Extract Entities (Dummy) ---
        entidades = self._extract_entities(email_body)

        # --- 3. Check Relevance (Dummy) ---
        es_relevante, confianza_relevancia = self._check_relevance(email_body)

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
        """Dummy classification."""
        # Simulate classification based on keywords
        if "licitación" in text.lower() or "requerimiento" in text.lower():
            return "Licitación/requerimiento público", random.uniform(0.85, 0.99)
        if "cotización" in text.lower() or "precio" in text.lower():
            return "Cotización directa", random.uniform(0.80, 0.95)
        if "notificación judicial" in text.lower() or "urgente" in text.lower():
            return "Notificaciones tipo judicial, accion urgente", random.uniform(0.90, 0.99)

        return "Informativo (sin acción)", random.uniform(0.60, 0.80)

    def _extract_entities(self, text: str) -> ExtractedEntities:
        """Dummy entity extraction."""
        return {
            "entidad": random.choice(self.dummy_entities),
            "contacto_email": "contacto@" + random.choice(self.dummy_entities).lower().replace(" ", "") + ".com",
            "productos": [random.choice(self.dummy_products)],
            "fecha_limite": datetime.date.today() + datetime.timedelta(days=random.randint(15, 60)),
            "monto": round(random.uniform(5000, 150000), 2)
        }

    def _check_relevance(self, text: str) -> (bool, float):
        """Dummy relevance check against the product catalog."""
        # In a real scenario, this would use semantic search.
        # Here, we just pretend it's relevant if it's not "Informativo".
        clasificacion, _ = self._classify_intent(text)
        is_relevant = clasificacion != "Informativo (sin acción)"
        confidence = random.uniform(0.8, 0.98) if is_relevant else random.uniform(0.3, 0.5)
        return is_relevant, confidence

    def _summarize(self, text: str, entidades: ExtractedEntities) -> str:
        """Dummy summary generation."""
        if not entidades.get("entidad"):
            return "No se pudo generar un resumen."

        return (
            f"Oportunidad detectada de {entidades['entidad']} para el suministro de "
            f"{', '.join(entidades.get('productos', ['N/A']))}. "
            f"Plazo estimado: {entidades.get('fecha_limite', 'no especificado')}."
        )

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