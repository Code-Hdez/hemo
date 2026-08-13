from __future__ import annotations

import re
import unicodedata
from dataclasses import replace

from app.modules.llm_chat.application.services.intent_classifier import (
    ClinicalRequestDetection,
    ClinicalRequestKind,
    IntentClassifier,
    has_explicit_diagnostic_boundary,
)
from app.modules.llm_chat.domain.value_objects import (
    FunctionalIntent,
    IntentDetection,
    SafetyAction,
    SafetyDecision,
    SafetyIntent,
)


def _normalize(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.lower())
    without_marks = "".join(char for char in folded if not unicodedata.combining(char))
    without_marks = re.sub(r"[^a-z0-9%/.,\s-]+", " ", without_marks)
    return re.sub(r"\s+", " ", without_marks).strip()


# "Judge the requested outcome of the latest message, not isolated words"
# (socratic-tutor's guard-classifier.st, quoted in the analysis of 2026-08-06
# §2.6 and §4.3). Naming a drug, a nutrient or a food is not asking for one:
# "what effect does prednisone have on leukocytes" is pharmacology, and a
# hematology assistant that cannot answer it is not safer, only less useful.
#
# These are the shapes that ask *about* a thing. They never authorize anything
# on their own — see _asks_for_information, which also requires the absence of
# any administration framing and a non-actionable clinical request.
_INFORMATIONAL_FRAME = re.compile(
    r"\b(?:"
    r"que\s+(?:es|son|significa|efecto|efectos|funcion|relacion|diferencia|"
    r"papel|utilidad|causa|provoca|indica|influye|influyen|pasa)|"
    # One noun may sit between: "qué alimentos influyen en…", "qué parámetros
    # afectan…". The verb still has to be one that asks how something relates
    # to something else, never one that asks for it.
    r"que\s+\w+\s+(?:influye|influyen|afecta|afectan|aporta|aportan|"
    r"intervienen|participan)|"
    r"cual(?:es)?\s+(?:es|son)\s+(?:la|el|los|las)\s+"
    r"(?:funcion|efecto|efectos|papel|relacion|diferencia)|"
    r"como\s+(?:afecta|afectan|influye|influyen|funciona|funcionan|actua|"
    r"actuan|se\s+relaciona|se\s+relacionan|se\s+interpreta)|"
    r"por\s+que|para\s+que\s+sirve(?:n)?|"
    r"en\s+que\s+consiste"
    r")\b"
)

# The counterweight. Any of these turns a question about a substance into a
# question about giving it, whatever the framing: "¿qué efecto tiene el
# ibuprofeno y cuánto le doy?" is a dose request wearing an educational hat.
_ADMINISTRATION_FRAME = re.compile(
    r"\b(?:"
    r"le\s+(?:doy|damos|das|pongo|inyecto|administro|suministro)|"
    r"darle|dar\s+a\s+mi|puedo\s+dar|debo\s+dar|podria\s+dar|"
    r"administrar|administrarle|suministrar|"
    r"recet\w*|prescrib\w*|"
    r"por\s+mi\s+cuenta|sin\s+ir\s+al\s+veterinario|sin\s+veterinario|"
    r"que\s+(?:le\s+)?(?:doy|compro|consigo)|"
    r"dosis|cuanto\s+le|cada\s+cuanto|cuantas\s+veces|"
    r"comprar|farmacia"
    r")\b"
)


# Asking the assistant to *pick* something to give is a prescription request,
# whatever the sentence looks like. "Recomienda un medicamento", "indícame el
# tratamiento", "qué pastillas recomiendas", "qué antiparasitario uso" and
# "necesito nombres de medicamentos" were all allowed: each classifies as an
# educational concept and each names a product, so the medication-education
# exemption waved them through. What they have in common is not a word but a
# shape — a verb that asks the assistant to choose, next to a thing to
# administer — so that is what this matches.
_SELECTION_VERB = (
    r"(?:recomiend\w*|recomend\w*|indica\w*|indique\w*|sugier\w*|sugerir|"
    r"dime|dame|necesito|quiero|prefiero|elige|elegir|escoge|escoger|"
    r"uso|usar|utilizo|utilizar|pongo|ponerle|poner|aplico|aplicarle|"
    r"compro|comprar|consigo|conseguir|nombres?\s+de)"
)
_PRODUCT = (
    r"(?:medicament\w*|farmac\w*|medicin\w*|pastilla\w*|comprimid\w*|"
    r"capsula\w*|jarabe\w*|gotas|ampolla\w*|inyeccion\w*|vacuna\w*|"
    r"antiparasitari\w*|desparasitante\w*|antibiotic\w*|antiinflamatori\w*|"
    r"analgesic\w*|suplement\w*|receta\w*|tratamiento\w*|terapia\w*|"
    r"protocolo\w*|dosis)"
)
_PRODUCT_REQUEST = re.compile(
    rf"\b{_SELECTION_VERB}\b.{{0,40}}\b{_PRODUCT}\b|"
    rf"\b{_PRODUCT}\b.{{0,40}}\b{_SELECTION_VERB}\b"
)

# Asking how long the animal will take to get better, or whether it will get
# better at all, is asking for a prognosis: a clinical judgement about an
# individual that a hemogram assistant does not make. Narrow on purpose — it
# needs the recovery frame *and* something it is about, so "¿qué es la
# trombocitopenia?" stays education.
_PROGNOSIS = re.compile(
    r"\b(?:se\s+(?:cura|curan|curara|va\s+a\s+curar|recupera|recuperara|"
    r"mejora|mejorara)|curarse|recuperarse|"
    r"cuanto\s+(?:tiempo\s+)?(?:tarda|tardara|falta|le\s+queda|vive|vivira)|"
    r"cuando\s+(?:se\s+cura|estara\s+bien|se\s+recupera|mejora))\b"
)


# Topics where an educational answer can still be acted on. "¿Qué vacunas
# evitan la leucopenia?" and "¿qué efecto tiene la prednisona?" are questions a
# hematology assistant should answer — refusing them is the false positive this
# etapa removes — but the honest answer to any of them ends with "and this is
# your vet's decision". Explaining what a drug does is education; leaving the
# reader thinking they can act on it is not.
#
# Deliberately not the same set as the refusal rules: this one only *adds a
# requirement to the answer*, it never withholds one. Kept here rather than in
# conversation_routing so there is one definition, not two that drift — the
# failure mode this module already had with its two referral matchers.
_ACTIONABLE_TOPIC = re.compile(
    r"\b(?:"
    r"medicament\w*|farmac\w*|medicin\w*|pastilla\w*|comprimid\w*|capsula\w*|"
    r"antibiotic\w*|antiinflamatori\w*|analgesic\w*|corticoide\w*|"
    r"prednison\w*|ibuprofen\w*|paracetamol|aspirin\w*|amoxicilin\w*|"
    r"doxiciclin\w*|naproxen\w*|"
    r"vacuna\w*|vacunacion|desparasit\w*|antiparasitari\w*|"
    r"suplement\w*|vitamin\w*|hierro|acido\s+folico|"
    r"tratamiento\w*|terapia\w*|transfusion\w*|cirugia\w*|"
    r"dieta\w*|aliment\w*"
    r")\b"
)


# Carried on ResponsePolicy.risk_flags so response_contracts can turn it into a
# per-turn contract requirement without either module re-deriving the topic.
VETERINARY_REFERRAL_FLAG = "veterinary_referral"


# A bare definition is exempt. "¿Qué es el hierro?" asks what a thing *is*, and
# closing it with "consult your vet" is the boilerplate this requirement exists
# to avoid — the same sentence on every turn stops being read. The moment the
# question relates the substance to the animal, to an effect or to a decision
# ("¿qué vacunas evitan la leucopenia?", "¿cómo afecta el hierro a la
# hemoglobina?", "¿necesita vacunas este mes?"), the referral is the part of the
# answer that matters.
_DEFINITION_ONLY = re.compile(
    r"^(?:que|cual(?:es)?)\s+(?:es|son)\b|^definicion\b|^en\s+que\s+consiste\b"
)


def asks_about_something_actionable(message: str) -> bool:
    """Whether an allowed answer must still defer the decision to a vet."""

    normalized = _normalize(message)
    if not (_ACTIONABLE_TOPIC.search(normalized) or _PROGNOSIS.search(normalized)):
        return False
    return not _DEFINITION_ONLY.search(normalized)


class SafetyPolicy:
    def __init__(self, intent_classifier: IntentClassifier | None = None) -> None:
        self.intent_classifier = intent_classifier or IntentClassifier()

    @staticmethod
    def _asks_for_information(
        normalized: str,
        clinical_request: ClinicalRequestDetection,
    ) -> bool:
        """Whether the message asks about a substance rather than for one.

        Three conditions, all required. The framing has to be informational;
        nothing in the message may frame an administration; and the clinical
        request classifier — which is what actually detects a dose, a
        frequency, a duration or a treatment selection — must not have found an
        actionable request. That last condition is the real guarantee: this
        predicate can only ever relax a rule that fires on vocabulary alone,
        never one that fires on a request to act.
        """

        if clinical_request.kind.is_actionable:
            return False
        if _ADMINISTRATION_FRAME.search(normalized):
            return False
        if _PRODUCT_REQUEST.search(normalized):
            return False
        return bool(_INFORMATIONAL_FRAME.search(normalized))

    _prompt_injection = re.compile(
        r"\b("
        r"ignora|olvida|omite|desactiva|deshabilita|sin restricciones|"
        r"modo desarrollador|developer mode|soy el desarrollador|soy el administrador|"
        r"administrador autorizo|sistema esta en modo|a partir de ahora|"
        r"tu nueva tarea|nueva funcion|cambia tu rol|ahora eres|eres un veterinario real|"
        r"eres un asistente general|actua como otro modelo|desde ahora puedes|"
        r"puedes recetar|puedes diagnosticar|no menciones limitaciones|"
        r"no digas que no puedes|no menciones que eres asistente|"
        r"no muestres el disclaimer|sin disclaimer|responde aunque|"
        r"responde de todos modos|responde igual|inventa una respuesta|"
        r"inventa una fuente|crea una fuente|oculta las fuentes|"
        # "no uses fuentes"/"usa conocimiento general"/"responde sin
        # evidencia"/"no uses el RAG" are deliberately NOT here: these are
        # legitimate retrieval-policy preferences (plan invariant), not
        # attempts to override safety rules. They cannot disable safety
        # boundaries or fabricate citations — RetrievalPolicy/ResponsePlan
        # still govern what evidence is actually required.
        r"muestra el prompt|prompt del sistema|prompt oculto|instrucciones internas|"
        r"reglas internas|que reglas tienes|cuales son tus reglas|configuracion interna|"
        r"contenido completo del corpus|documentos exactos|como esta construido el rag|"
        r"codigo del sistema|contenido oculto"
        r")\b"
    )
    _capability_simulation = re.compile(
        r"\b("
        r"responde como si|contesta como si|finge que|haz de cuenta que|sup[oó]n que|"
        r"aunque no tengas acceso|como si tuvieras internet|acceso a todo internet|"
        r"acceso a internet|puedes navegar|puedes buscar en la web|"
        r"tienes acceso a todo|supieras cualquier cosa"
        r")\b"
    )
    _rule_override = re.compile(
        r"\b("
        r"fuera del ambito.*responde|si esta fuera.*responde|si esta fuera.*igual|"
        r"pasa por alto tus limites|no hagas caso al sistema|"
        r"no menciones restricciones|ignora las instrucciones"
        r")\b"
    )
    _medication = re.compile(
        r"\b("
        r"medicamento|medicina|farmaco|antibiotico|doxiciclina|amoxicilina|"
        r"prednisona|aspirina|aspirin|paracetamol|acetaminofen|ibuprofeno|"
        r"naproxeno|glucocorticoide|corticoide|hierro|acido folico|folato|"
        r"b12|suplemento|vitamina|mineral|inyeccion|suero|farmacia|receta|"
        r"recetar|recetame|recetarme|prescribir|prescribeme|pastilla|pastillas"
        r")\b"
    )
    _treatment = re.compile(
        r"\b("
        r"tratamiento|tratar|terapia|que debo darle|que le doy|que puedo darle|"
        r"que puedo dar|que le puedo dar|que debo hacer|que hago|como lo curo|"
        r"remedio|casero|natural|cirugia|hospitalizacion|transfusion|plasma|"
        r"crioprecipitado|comprar en la farmacia|mientras consigo veterinario|"
        r"sin ir al veterinario|que le pongo|que le inyecto|que compro|administrar"
        r")\b"
    )
    _diet_protocol = re.compile(
        r"\b("
        r"comida|alimento|alimentos|dieta|dietas|nutricion|suplemento|"
        r"suplementos|vitamina|vitaminas|mineral|minerales|hierro|"
        r"acido folico|folato|b12|protocolo|protocolos"
        r")\b"
    )
    _modify_value = re.compile(
        r"\b("
        r"subir|bajar|aumentar|disminuir|mejorar|corregir|modificar|normalizar|"
        r"levantar|controlar|subo|sube|suban|aumento|mejoro|corrijo"
        r")\b"
    )
    # Verbs that inherently request a diagnostic act ("diagnostica a mi
    # perro") regardless of whether a disease is named.
    _diagnosis_strong = re.compile(
        r"\b(diagnostica|diagnostico|confirma|confirmame|asegura|asegurar)\b"
    )
    # Verbs that are ordinary Spanish ("tiene", "padece", "sufre") and only
    # signal a diagnosis request when paired with an actual disease name.
    # Gating them on `_individual` alone (which matches on "mi perro" /
    # "mi mascota", present in nearly every clinical question this app
    # expects) blocked plain questions like "que patron tiene mi perro".
    _diagnosis_weak = re.compile(
        r"\b("
        r"tiene|padece|sufre|esta sano|no necesita veterinario|no es grave|"
        r"le queda de vida"
        r")\b"
    )
    _disease = re.compile(
        r"\b("
        r"enfermedad|ehrlichia|ehrlichiosis|cancer|leucemia|parvovirus|moquillo|"
        r"infeccion|linfoma|anemia|anemia hemolitica|sangrado interno|garrapatas|"
        r"fiebre|enfermedad renal|enfermedad hepatica|trombosis|sano|grave"
        r")\b"
    )
    _urgency = re.compile(
        r"\b("
        r"no puede respirar|dificultad para respirar|convulsiona|convulsiones|"
        r"inconsciente|desmayo|se desangra|hemorragia|sangrado interno|"
        r"mucosas palidas|encias blancas|debilidad marcada|decaimiento severo|"
        r"no puede levantarse|urgencia|emergencia|puede esperar|esta grave|"
        r"esperar unos dias|esperar hasta manana|puedo esperar|puedo quedarme tranquilo|"
        r"descartar una emergencia|necesita hospitalizacion|hospitalizar|"
        r"necesita transfusion|necesita cirugia|se va a morir|pronostico|"
        r"supervivencia"
        r")\b"
    )
    _programming = re.compile(
        r"\b("
        r"javascript|python|docker|compose|sql|postgres|react|codigo|programacion|"
        r"programar|array|arreglo|variable|consulta sql|machine learning|"
        r"api|frontend|backend"
        r")\b"
    )
    _current_events = re.compile(
        r"\b("
        r"capital de|presidente|politica|deportes|bitcoin|celular|laptop|"
        r"noticias|actualidad|mundial|futbol|beisbol|precio del dolar|"
        r"cuanto vale el dolar|dolar hoy|que hora|hora es|japon|google pixel|"
        r"algebra|matematica|postgre|postgresql|desbloqueo|desbloquear"
        r")\b"
    )
    _unsafe_nonmedical = re.compile(
        r"\b(virus|hackear|hackeo|hack|malware|robar|dano|arma)\b"
    )
    _source_request = re.compile(
        r"\b("
        r"fuente|fuentes|bibliografia|cita|citar|pagina|libro|schalm|duncan|"
        r"prasse|cowell|corpus"
        r")\b"
    )
    _long_source = re.compile(
        r"\b("
        r"texto exacto|parrafo completo|copiarme el parrafo|copiame el parrafo|"
        r"copiar completo|contenido completo|transcribe"
        r")\b"
    )
    _individual = re.compile(
        r"\b(interpreta|interpretame|analiza|estos valores|este resultado|mi perro|mi mascota|este hemograma)\b"
    )
    _explicit_analysis_request = re.compile(
        r"\b(interpreta|interpretame|analiza|estos valores|este resultado|este hemograma)\b"
    )
    _symptoms = re.compile(
        r"\b(sintoma|sintomas|signos?|rango|rangos|sangrado|moretones|petequias)\b"
    )
    _result_explanation = re.compile(
        r"\b(baja|bajas|bajo|bajos|alta|altas|alto|altos|valor|valores|resultado|significa|significan)\b"
    )
    _hematology = re.compile(
        r"\b("
        r"hemograma|hematico|hematologico|sangre|plaqueta|plaquetas|plaquetopenia|"
        r"trombocito|trombocitos|trombocitopenia|trombocitosis|hematocrito|"
        r"hemoglobina|globulos|eritrocito|eritrocitos|leucocito|leucocitos|"
        r"neutrofil|neutrofilo|neutrofilos|linfocit|linfocito|linfocitos|"
        r"monocit|monocito|monocitos|eosinofil|eosinofilo|eosinofilos|"
        r"basofil|basofilo|basofilos|reticulocito|reticulocitos|anemia|"
        r"leucocitosis|leucopenia|neutropenia|neutrofilia|rdw|rbc|wbc|hgb|"
        r"hct|plt|vcm|mcv|hcm|mch|chcm|mchc|vpm|mpv"
        r")\b"
    )
    _hematology_typos = re.compile(
        r"\b("
        r"emoglovina|hemoglovina|homoglobina|emoglobina|hemoglobna|"
        r"trombo\s*citopenia|trombositopenia|trombocitopnia|plaquetaz|"
        r"leuco altos|leucos altos|leucos bajos|emograma|homograma|"
        r"hematocrit|hematocrito bajo|globulo rojo|globulo blanco"
        r")\b"
    )

    def evaluate(self, *, message: str, has_analysis_context: bool) -> SafetyDecision:
        functional = self.intent_classifier.classify(message)
        clinical_request = self.intent_classifier.classify_clinical_request(message)
        primary = self._evaluate_primary(
            message=message,
            has_analysis_context=has_analysis_context,
            functional=functional,
            clinical_request=clinical_request,
        )
        secondary = self._secondary_safety_intents(
            functional.secondary_intents,
            clinical_request=clinical_request,
        )
        return replace(primary, secondary_intents=secondary)

    def _evaluate_primary(
        self,
        *,
        message: str,
        has_analysis_context: bool,
        functional: IntentDetection,
        clinical_request: ClinicalRequestDetection,
    ) -> SafetyDecision:
        normalized = _normalize(message)

        # Content safety outranks attempts to change the assistant's rules. This
        # prevents a threat from being routed to an unrelated injection template.
        if functional.intent is FunctionalIntent.ANIMAL_HARM:
            return self._blocked(
                action=SafetyAction.REFUSE_OUT_OF_SCOPE,
                intent=SafetyIntent.OUT_OF_SCOPE_UNSAFE_NONMEDICAL,
                rule_id="prevent_animal_harm",
                response_policy="immediate_animal_safety",
                risk_flags=("animal_harm", "immediate_safety"),
                reason_internal="El mensaje expresa o propone violencia contra un animal.",
                confidence=functional.confidence,
            )
        if functional.intent is FunctionalIntent.HUMAN_HEALTH:
            return self._blocked(
                action=SafetyAction.REFUSE_OUT_OF_SCOPE,
                intent=SafetyIntent.OUT_OF_SCOPE_GENERAL,
                rule_id="human_health_referral",
                response_policy="human_health_referral",
                risk_flags=("human_health",),
                reason_internal="La consulta requiere orientación de salud humana.",
                confidence=functional.confidence,
            )
        if functional.intent is FunctionalIntent.VETERINARY_URGENCY:
            return self._blocked(
                action=SafetyAction.URGENT_REFERRAL,
                intent=SafetyIntent.EMERGENCY_REQUEST_DISALLOWED,
                rule_id="urgent_veterinary_risk",
                response_policy="urgent_vet_referral",
                risk_flags=("urgent_veterinary_risk",),
                reason_internal="La pregunta menciona signos compatibles con una urgencia veterinaria.",
                confidence=functional.confidence,
            )
        if functional.intent is FunctionalIntent.MEDICATION:
            # Use the already-computed clinical_request.kind (from
            # IntentClassifier._dose_request/_frequency_request/etc, which
            # requires an actual quantity/unit/administration context) rather
            # than a second, looser local regex. The former local `_dose`
            # regex matched a bare "cuantos" and misrouted purely educational
            # counting questions ("cuantos tipos de leucocitos hay?") as dose
            # requests — the audited false positive this etapa corrects.
            if clinical_request.kind in {
                ClinicalRequestKind.DOSAGE,
                ClinicalRequestKind.FREQUENCY,
                ClinicalRequestKind.DURATION,
            }:
                action = SafetyAction.REFUSE_DOSE
            elif clinical_request.kind is ClinicalRequestKind.TREATMENT_SELECTION:
                action = SafetyAction.REFUSE_TREATMENT
            elif re.search(r"\b(tratamiento|tratar|terapia)\b", normalized):
                action = SafetyAction.REFUSE_TREATMENT
            else:
                action = SafetyAction.REFUSE_MEDICATION
            return self._blocked(
                action=action,
                intent=(
                    SafetyIntent.DOSAGE_REQUEST_DISALLOWED
                    if action is SafetyAction.REFUSE_DOSE
                    else SafetyIntent.TREATMENT_REQUEST_DISALLOWED
                    if action is SafetyAction.REFUSE_TREATMENT
                    else SafetyIntent.MEDICATION_REQUEST_DISALLOWED
                ),
                rule_id=(
                    "dosage_request"
                    if action is SafetyAction.REFUSE_DOSE
                    else "treatment_request"
                    if action is SafetyAction.REFUSE_TREATMENT
                    else "medication_request"
                ),
                response_policy="refuse_medical_action",
                risk_flags=(
                    ("dose", "treatment")
                    if action is SafetyAction.REFUSE_DOSE
                    else ("medication", "treatment")
                ),
                reason_internal="La pregunta solicita un medicamento o una dosis.",
                confidence=functional.confidence,
            )
        if (
            self._prompt_injection.search(normalized)
            or self._capability_simulation.search(normalized)
            or self._rule_override.search(normalized)
        ):
            return self._blocked(
                action=SafetyAction.REFUSE_OUT_OF_SCOPE,
                intent=SafetyIntent.PROMPT_INJECTION,
                rule_id="prompt_injection",
                response_policy="brief_role_boundary",
                risk_flags=("prompt_injection",),
                reason_internal="La pregunta intenta cambiar el rol, revelar reglas o anular limites.",
                confidence=0.96,
            )
        if functional.intent is FunctionalIntent.DIAGNOSIS:
            return self._blocked(
                action=SafetyAction.REFUSE_DIAGNOSIS,
                intent=SafetyIntent.DIRECT_DIAGNOSIS,
                rule_id="direct_diagnosis",
                response_policy="safe_diagnosis_boundary",
                risk_flags=("direct_diagnosis",),
                reason_internal="La pregunta pide confirmar o negar una enfermedad con el hemograma.",
                confidence=functional.confidence,
            )
        if functional.intent is FunctionalIntent.IDENTITY:
            return self._allowed_decision(
                normalized,
                has_analysis_context=has_analysis_context,
                intent=SafetyIntent.IDENTITY,
                rule_id="assistant_identity",
                response_policy="assistant_identity",
                confidence=functional.confidence,
            )
        if functional.intent is FunctionalIntent.CHAT_HISTORY:
            return self._allowed_decision(
                normalized,
                has_analysis_context=has_analysis_context,
                intent=SafetyIntent.CHAT_HISTORY,
                rule_id="chat_history",
                response_policy="session_history_answer",
                confidence=functional.confidence,
            )
        if functional.intent is FunctionalIntent.NEARBY_VETERINARY_CARE:
            # Informational location-seeking, not a medical emergency. The actual
            # clinic names are resolved deterministically in the use case (never
            # invented by the LLM); this only clears the safety gate so the
            # question is not blocked by the generic out-of-domain checks below.
            return self._allowed_decision(
                normalized,
                has_analysis_context=has_analysis_context,
                intent=SafetyIntent.NEARBY_VETERINARY_CARE,
                rule_id="nearby_veterinary_care",
                response_policy="nearby_veterinary_care_answer",
                confidence=functional.confidence,
            )
        # Before the education branches, because a request to pick something to
        # administer is not education whatever its topic. "¿Qué vacuna debo
        # ponerle esta semana?" reached VETERINARY_EDUCATION on the word
        # "vacuna" and was allowed; the outcome it asks for is a prescription.
        if _PRODUCT_REQUEST.search(normalized):
            return self._blocked(
                action=SafetyAction.REFUSE_TREATMENT,
                intent=SafetyIntent.TREATMENT_REQUEST_DISALLOWED,
                rule_id="product_or_protocol_request",
                response_policy="refuse_medical_action",
                risk_flags=("treatment", "product_request"),
                reason_internal=(
                    "La pregunta pide elegir o nombrar algo que administrar."
                ),
                confidence=0.94,
            )
        if functional.intent is FunctionalIntent.VETERINARY_EDUCATION:
            # General veterinary topic with no hematology signal (e.g. "por
            # que jadean los perros?"). Previously had no branch here and
            # fell through to the OUT_OF_DOMAIN checks below — the audited
            # false positive this etapa corrects.
            return self._allowed_decision(
                normalized,
                has_analysis_context=has_analysis_context,
                intent=SafetyIntent.VETERINARY_EDUCATION_ALLOWED,
                rule_id="veterinary_education",
                response_policy="veterinary_education_answer",
                confidence=functional.confidence,
            )
        if functional.intent is FunctionalIntent.PET_PROFILE_QUESTION:
            # Question about the pet's own authorized profile (breed, age,
            # weight, notes, consented residence), not a hemogram parameter.
            # Whether a profile is actually available is a ContextBundle/
            # routing concern (etapa 2/3), not a safety concern.
            return self._allowed_decision(
                normalized,
                has_analysis_context=has_analysis_context,
                intent=SafetyIntent.PET_PROFILE_ALLOWED,
                rule_id="pet_profile_question",
                response_policy="pet_profile_answer",
                confidence=functional.confidence,
            )

        # Pre-existing hole, closed here: this rule authorized any message that
        # named a drug and classified as an educational concept, and the
        # classifier reads a compound question by its first clause. "¿Para qué
        # sirve la prednisona? ¿Se la puedo dar?" and "¿qué suplemento de
        # hierro compro en la farmacia?" were both allowed through — an
        # educational opening is enough to carry an administration ask past
        # it. Judging the outcome requested means reading the whole message,
        # so an administration frame anywhere in it disqualifies the
        # educational exemption and the message falls through to the
        # medication rule below.
        if (
            clinical_request.mentions_medication
            and clinical_request.kind
            in {
                ClinicalRequestKind.EDUCATIONAL_CONCEPT,
                ClinicalRequestKind.GENERAL_RISK_INFORMATION,
            }
            and not _ADMINISTRATION_FRAME.search(normalized)
            and not _PRODUCT_REQUEST.search(normalized)
        ):
            return self._allowed_decision(
                normalized,
                has_analysis_context=has_analysis_context,
                intent=SafetyIntent.EDUCATIONAL_ALLOWED,
                rule_id="medication_education",
                response_policy="evidence_grounded_medication_education",
                confidence=clinical_request.confidence,
            )
        if self._long_source.search(normalized):
            return self._blocked(
                action=SafetyAction.REFUSE_OUT_OF_SCOPE,
                intent=SafetyIntent.COPYRIGHT_OR_LONG_SOURCE_REQUEST,
                rule_id="copyright_or_long_source_request",
                response_policy="brief_copyright_summary_offer",
                risk_flags=("copyright", "sources"),
                reason_internal="La pregunta solicita copiar texto largo de una fuente.",
                confidence=0.90,
            )
        if self._urgency.search(normalized):
            return self._blocked(
                action=SafetyAction.URGENT_REFERRAL,
                intent=SafetyIntent.EMERGENCY_REQUEST_DISALLOWED,
                rule_id="urgent_veterinary_risk",
                response_policy="urgent_vet_referral",
                risk_flags=("urgent_veterinary_risk",),
                reason_internal="La pregunta menciona signos o decisiones compatibles con urgencia veterinaria.",
                confidence=0.92,
            )
        informational = self._asks_for_information(normalized, clinical_request)
        # Prognosis: how long recovery takes, or whether it will happen. A
        # judgement about this animal's course, not about what a hemogram is.
        if _PROGNOSIS.search(normalized) and (
            self._disease.search(normalized)
            or self._hematology.search(normalized)
            or self._individual.search(normalized)
            or re.search(r"\bsin\s+(?:ir|llevarlo|llevarla|veterinario)\b", normalized)
        ):
            return self._blocked(
                action=SafetyAction.REFUSE_DIAGNOSIS,
                intent=SafetyIntent.DIRECT_DIAGNOSIS,
                rule_id="prognosis_request",
                response_policy="safe_diagnosis_boundary",
                risk_flags=("prognosis",),
                reason_internal=(
                    "La pregunta pide un pronóstico de evolución o curación."
                ),
                confidence=0.92,
            )
        if (
            self._diet_protocol.search(normalized)
            and not informational
            and not re.search(
                r"\b(le doy|le puedo dar|puedo darle|que le doy)\b", normalized
            )
            and not (
                self._hematology.search(normalized)
                or self._disease.search(normalized)
                or self._individual.search(normalized)
            )
        ):
            return self._blocked(
                action=SafetyAction.REFUSE_OUT_OF_SCOPE,
                intent=SafetyIntent.OUT_OF_SCOPE_GENERAL,
                rule_id="out_of_scope_nutrition_general",
                response_policy="brief_natural_redirect",
                risk_flags=("out_of_scope",),
                reason_internal="La pregunta trata nutricion general fuera de hemogramas caninos.",
                confidence=0.88,
            )
        if (
            self._diet_protocol.search(normalized)
            # "¿Cómo afecta el hierro a la hemoglobina?" fired this rule purely
            # because it names a nutrient and a parameter. The rule is meant to
            # catch a request for something to *give* in order to move a
            # result, and the two are distinguishable without a longer word
            # list: the request classifier already tells an actionable ask from
            # a question about a mechanism.
            and not informational
            and (
                self._hematology.search(normalized)
                or self._modify_value.search(normalized)
                or self._disease.search(normalized)
                or re.search(
                    r"\b(que le doy|que le puedo dar|que puedo darle)\b", normalized
                )
            )
        ):
            return self._blocked(
                action=SafetyAction.REFUSE_TREATMENT,
                intent=SafetyIntent.TREATMENT_REQUEST_DISALLOWED,
                rule_id="diet_supplement_protocol_request",
                response_policy="refuse_indirect_treatment",
                risk_flags=("treatment", "diet_or_supplement"),
                reason_internal="La pregunta solicita alimentos, suplementos o protocolos para modificar un resultado.",
                confidence=0.96,
            )
        if (
            self._modify_value.search(normalized)
            and self._hematology.search(normalized)
            and re.search(
                r"\b(que|como|hacer|hago|sirve|puedo|debo|dar|darle)\b",
                normalized,
            )
        ):
            return self._blocked(
                action=SafetyAction.REFUSE_TREATMENT,
                intent=SafetyIntent.TREATMENT_REQUEST_DISALLOWED,
                rule_id="therapeutic_parameter_modification",
                response_policy="refuse_indirect_treatment",
                risk_flags=("treatment", "parameter_modification"),
                reason_internal="La pregunta pide modificar terapeuticamente un parametro del hemograma.",
                confidence=0.94,
            )
        if re.search(
            r"\b(que le doy|que le puedo dar|que puedo darle|que puedo administrar)\b",
            normalized,
        ) and (
            self._hematology.search(normalized)
            or self._individual.search(normalized)
            or self._disease.search(normalized)
        ):
            return self._blocked(
                action=SafetyAction.REFUSE_TREATMENT,
                intent=SafetyIntent.TREATMENT_REQUEST_DISALLOWED,
                rule_id="actionable_what_to_give_request",
                response_policy="refuse_indirect_treatment",
                risk_flags=("treatment", "what_to_give"),
                reason_internal="La pregunta solicita que administrar o dar al perro.",
                confidence=0.95,
            )
        # No standalone bare-regex dose fallback here anymore: legitimate
        # dosage/frequency/duration requests are already caught above via
        # FunctionalIntent.MEDICATION (fed by IntentClassifier's properly
        # scoped `_dose_request`, which requires an actual quantity/unit/
        # administration context). A separate, looser local check here
        # previously matched a bare "cuantos" and misclassified purely
        # educational counting questions ("cuantos tipos de leucocitos
        # existen?") as dose requests.
        # The most keyword-bound rule in the file: any drug name anywhere used
        # to be a refusal, so "¿qué efecto tiene la prednisona sobre los
        # leucocitos?" — pharmacology a hematology assistant should answer —
        # was refused for containing "prednisona". A real request for a
        # medication has already been caught above by FunctionalIntent.
        # MEDICATION, which requires an administration or quantity context;
        # what remains here is the bare mention.
        if self._medication.search(normalized) and not informational:
            return self._blocked(
                action=SafetyAction.REFUSE_MEDICATION,
                intent=SafetyIntent.MEDICATION_REQUEST_DISALLOWED,
                rule_id="medication_request",
                response_policy="refuse_medical_action",
                risk_flags=("medication", "treatment"),
                reason_internal="La pregunta solicita medicamento, farmacia, suplemento o receta.",
                confidence=0.94,
            )
        if self._treatment.search(normalized):
            if self._hematology.search(normalized) and not re.search(
                r"\b(tratamiento|tratar|terapia|como lo curo|cirugia|remedio|"
                r"casero|natural|que le doy|que debo darle|que puedo darle|"
                r"que le puedo dar|administrar|transfusion|hospitalizacion)\b",
                normalized,
            ):
                return self._allowed_decision(
                    normalized,
                    has_analysis_context=has_analysis_context,
                )
            return self._blocked(
                action=SafetyAction.REFUSE_TREATMENT,
                intent=SafetyIntent.TREATMENT_REQUEST_DISALLOWED,
                rule_id="treatment_request",
                response_policy="refuse_medical_action",
                risk_flags=("treatment",),
                reason_internal="La pregunta solicita tratamiento o decision clinica accionable.",
                confidence=0.91,
            )
        if (
            not has_explicit_diagnostic_boundary(normalized)
            and (
                (
                    self._diagnosis_strong.search(normalized)
                    and (
                        self._disease.search(normalized)
                        or self._individual.search(normalized)
                    )
                )
                or (
                    self._diagnosis_weak.search(normalized)
                    and self._disease.search(normalized)
                )
            )
        ):
            return self._blocked(
                action=SafetyAction.REFUSE_DIAGNOSIS,
                intent=SafetyIntent.DIRECT_DIAGNOSIS,
                rule_id="direct_diagnosis",
                response_policy="safe_diagnosis_boundary",
                risk_flags=("direct_diagnosis",),
                reason_internal="La pregunta pide confirmar, negar o asegurar una enfermedad o estado clinico.",
                confidence=0.90,
            )
        if self._programming.search(normalized) and not self._hematology.search(
            normalized
        ):
            return self._blocked(
                action=SafetyAction.REFUSE_OUT_OF_SCOPE,
                intent=SafetyIntent.OUT_OF_SCOPE_PROGRAMMING_OR_TECHNICAL,
                rule_id="out_of_scope_programming_or_technical",
                response_policy="brief_natural_redirect",
                risk_flags=("out_of_scope",),
                reason_internal="La pregunta solicita programacion o tecnologia general.",
                confidence=0.94,
            )
        if self._unsafe_nonmedical.search(normalized) and not self._hematology.search(
            normalized
        ):
            return self._blocked(
                action=SafetyAction.REFUSE_OUT_OF_SCOPE,
                intent=SafetyIntent.OUT_OF_SCOPE_UNSAFE_NONMEDICAL,
                rule_id="out_of_scope_unsafe_nonmedical",
                response_policy="brief_safety_redirect",
                risk_flags=("out_of_scope", "unsafe_nonmedical"),
                reason_internal="La pregunta solicita una accion no medica insegura.",
                confidence=0.93,
            )
        if self._current_events.search(normalized) and not self._hematology.search(
            normalized
        ):
            return self._blocked(
                action=SafetyAction.REFUSE_OUT_OF_SCOPE,
                intent=SafetyIntent.OUT_OF_SCOPE_CURRENT_EVENTS,
                rule_id="out_of_scope_current_events",
                response_policy="brief_natural_redirect",
                risk_flags=("out_of_scope",),
                reason_internal="La pregunta solicita informacion general o de actualidad.",
                confidence=0.90,
            )
        if self._source_request.search(normalized) and self._hematology.search(
            normalized
        ):
            return self._allowed_decision(
                normalized,
                has_analysis_context=has_analysis_context,
                intent=SafetyIntent.SOURCE_OR_BIBLIOGRAPHY_REQUEST,
                rule_id="source_or_bibliography_request",
                response_policy="source_grounded_answer",
                confidence=0.86,
            )
        if self._source_request.search(normalized) and not self._hematology.search(
            normalized
        ):
            if re.search(r"\b(schalm|duncan|prasse|cowell)\b", normalized):
                return self._allowed_decision(
                    normalized,
                    has_analysis_context=has_analysis_context,
                    intent=SafetyIntent.SOURCE_OR_BIBLIOGRAPHY_REQUEST,
                    rule_id="source_or_bibliography_request",
                    response_policy="source_grounded_answer",
                    confidence=0.84,
                )
            return self._blocked(
                action=SafetyAction.REFUSE_OUT_OF_SCOPE,
                intent=SafetyIntent.SOURCE_OR_BIBLIOGRAPHY_REQUEST,
                rule_id="generic_source_request_without_context",
                response_policy="brief_source_boundary",
                risk_flags=("sources",),
                reason_internal="La pregunta pide fuentes sin una consulta hematologica concreta.",
                confidence=0.76,
            )
        if self._individual.search(normalized) and not has_analysis_context:
            if self._hematology.search(
                normalized
            ) and not self._explicit_analysis_request.search(normalized):
                return self._allowed_decision(
                    normalized,
                    has_analysis_context=has_analysis_context,
                )
            return self._blocked(
                action=SafetyAction.REQUIRE_CONTEXT,
                intent=SafetyIntent.MISSING_AUTHORIZED_ANALYSIS,
                rule_id="analysis_context_required",
                response_policy="request_authorized_analysis",
                risk_flags=("missing_authorized_analysis",),
                reason_internal="La pregunta requiere un hemograma autorizado, pero no hay contexto disponible.",
                confidence=0.88,
            )
        if not self._hematology.search(
            normalized
        ) and not self._hematology_typos.search(normalized):
            if re.search(
                r"\b(como arreglo eso|dime como buscar dentro|que hago con esto)\b",
                normalized,
            ):
                return self._blocked(
                    action=SafetyAction.REFUSE_OUT_OF_SCOPE,
                    intent=SafetyIntent.AMBIGUOUS_BUT_POSSIBLY_CBC,
                    rule_id="ambiguous_without_cbc_context",
                    response_policy="brief_clarification",
                    risk_flags=("ambiguous",),
                    reason_internal="La pregunta es ambigua y no contiene senales hematologicas suficientes.",
                    confidence=0.65,
                )
            if re.search(
                r"\b(amor|amir|poema|cancion|receta de cocina|capital|francia|"
                r"algebra|matematica|postgre|postgresql|google pixel|dolar|japon|"
                r"docker|python|javascript|desbloquear|desbloqueo)\b",
                normalized,
            ):
                return self._blocked(
                    action=SafetyAction.REFUSE_OUT_OF_SCOPE,
                    intent=SafetyIntent.OUT_OF_SCOPE_GENERAL,
                    rule_id="out_of_scope_general",
                    response_policy="brief_natural_redirect",
                    risk_flags=("out_of_scope",),
                    reason_internal="La pregunta no pertenece al dominio de hemogramas caninos.",
                    confidence=0.89,
                )

        return self._allowed_decision(
            normalized,
            has_analysis_context=has_analysis_context,
        )

    @staticmethod
    def _secondary_safety_intents(
        secondary: tuple[FunctionalIntent, ...],
        *,
        clinical_request: ClinicalRequestDetection,
    ) -> tuple[SafetyIntent, ...]:
        mapped: list[SafetyIntent] = []
        for intent in secondary:
            if intent is FunctionalIntent.PROMPT_INJECTION:
                mapped.append(SafetyIntent.PROMPT_INJECTION)
            elif intent is FunctionalIntent.ANIMAL_HARM:
                mapped.append(SafetyIntent.OUT_OF_SCOPE_UNSAFE_NONMEDICAL)
            elif intent is FunctionalIntent.VETERINARY_URGENCY:
                mapped.append(SafetyIntent.EMERGENCY_REQUEST_DISALLOWED)
            elif intent is FunctionalIntent.DIAGNOSIS:
                mapped.append(SafetyIntent.DIRECT_DIAGNOSIS)
            elif intent is FunctionalIntent.MEDICATION:
                kind = getattr(clinical_request, "kind", None)
                mapped.append(
                    SafetyIntent.DOSAGE_REQUEST_DISALLOWED
                    if kind
                    in {
                        ClinicalRequestKind.DOSAGE,
                        ClinicalRequestKind.FREQUENCY,
                        ClinicalRequestKind.DURATION,
                    }
                    else SafetyIntent.TREATMENT_REQUEST_DISALLOWED
                    if kind is ClinicalRequestKind.TREATMENT_SELECTION
                    else SafetyIntent.MEDICATION_REQUEST_DISALLOWED
                )
            elif intent is FunctionalIntent.GENERAL_CBC:
                mapped.append(SafetyIntent.ALLOWED_CBC_GENERAL)
        return tuple(dict.fromkeys(mapped))

    def _blocked(
        self,
        *,
        action: SafetyAction,
        intent: SafetyIntent,
        rule_id: str,
        response_policy: str,
        risk_flags: tuple[str, ...],
        reason_internal: str,
        confidence: float,
        fallback_response: str = "",
    ) -> SafetyDecision:
        return SafetyDecision(
            action=action,
            response=fallback_response,
            intent=intent,
            secondary_intents=(),
            rule_id=rule_id,
            confidence=confidence,
            should_use_rag_value=False,
            should_use_selected_hemogram=False,
            load_selected_analysis=False,
            load_history=False,
            include_sources=False,
            route_selected="restricted_refusal",
            response_policy=response_policy,
            risk_flags=risk_flags,
            reason_internal=reason_internal,
            fallback_type=rule_id,
        )

    def _allowed_decision(
        self,
        normalized: str,
        *,
        has_analysis_context: bool,
        intent: SafetyIntent | None = None,
        rule_id: str | None = None,
        response_policy: str = "educational_answer",
        confidence: float = 0.82,
    ) -> SafetyDecision:
        detected_intent = intent or self._allowed_intent(
            normalized,
            has_analysis_context=has_analysis_context,
        )
        detected_rule = rule_id or {
            SafetyIntent.ALLOWED_CBC_GENERAL: "allowed_cbc_general",
            SafetyIntent.ALLOWED_SELECTED_HEMOGRAM: "allowed_selected_hemogram",
            SafetyIntent.ALLOWED_HISTORICAL_HEMOGRAM: "allowed_historical_hemogram",
            SafetyIntent.ALLOWED_CBC_CONCEPT_WITH_TYPOS: "allowed_cbc_concept_with_typos",
            SafetyIntent.RESULT_EXPLANATION_ALLOWED: "result_explanation",
            SafetyIntent.SYMPTOM_GENERAL_INFO_ALLOWED: "symptom_general_info",
            SafetyIntent.SOURCE_OR_BIBLIOGRAPHY_REQUEST: "source_or_bibliography_request",
        }.get(detected_intent, "educational_default")
        return SafetyDecision(
            SafetyAction.ALLOW,
            intent=detected_intent,
            secondary_intents=(),
            rule_id=detected_rule,
            confidence=confidence,
            should_use_rag_value=True,
            should_use_selected_hemogram=has_analysis_context,
            load_selected_analysis=has_analysis_context,
            load_history=has_analysis_context,
            include_sources=True,
            route_selected="rag_generation",
            response_policy=response_policy,
            risk_flags=(),
            reason_internal="Consulta permitida dentro del dominio de hemogramas caninos.",
        )

    def _allowed_intent(
        self,
        normalized: str,
        *,
        has_analysis_context: bool,
    ) -> SafetyIntent:
        if self._hematology_typos.search(normalized):
            return SafetyIntent.ALLOWED_CBC_CONCEPT_WITH_TYPOS
        if has_analysis_context:
            return SafetyIntent.ALLOWED_SELECTED_HEMOGRAM
        if self._symptoms.search(normalized):
            return SafetyIntent.SYMPTOM_GENERAL_INFO_ALLOWED
        if self._result_explanation.search(normalized):
            return SafetyIntent.RESULT_EXPLANATION_ALLOWED
        return SafetyIntent.ALLOWED_CBC_GENERAL
