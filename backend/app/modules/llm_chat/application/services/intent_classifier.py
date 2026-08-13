from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from enum import StrEnum

from app.modules.llm_chat.application.services.clinical_code_registry import (
    extract_parameter_code,
)
from app.modules.llm_chat.domain.value_objects import (
    FunctionalIntent,
    IntentDetection,
)


class ClinicalRequestKind(StrEnum):
    EDUCATIONAL_CONCEPT = "educational_concept"
    GENERAL_RISK_INFORMATION = "general_risk_information"
    RESULT_EXPLANATION = "result_explanation"
    PERSONALIZED_RECOMMENDATION = "personalized_recommendation"
    DOSAGE = "dosage"
    FREQUENCY = "frequency"
    DURATION = "duration"
    TREATMENT_SELECTION = "treatment_selection"
    DIAGNOSIS_CONFIRMATION = "diagnosis_confirmation"
    URGENT_REFERRAL = "urgent_referral"
    NOT_CLINICAL = "not_clinical"

    @property
    def is_actionable(self) -> bool:
        return self in {
            self.PERSONALIZED_RECOMMENDATION,
            self.DOSAGE,
            self.FREQUENCY,
            self.DURATION,
            self.TREATMENT_SELECTION,
            self.DIAGNOSIS_CONFIRMATION,
            self.URGENT_REFERRAL,
        }


@dataclass(frozen=True, slots=True)
class ClinicalRequestDetection:
    kind: ClinicalRequestKind
    confidence: float
    mentions_medication: bool = False


def normalize_intent_text(value: str) -> str:
    folded = unicodedata.normalize("NFKD", str(value or "").casefold())
    plain = "".join(char for char in folded if not unicodedata.combining(char))
    plain = re.sub(r"[^a-z0-9%/.,\s-]+", " ", plain)
    return re.sub(r"\s+", " ", plain).strip()


_EXPLICIT_DIAGNOSTIC_BOUNDARY = re.compile(
    r"\b(?:sin|no)\s+(?:emitir|dar|hacer|realizar|establecer|confirmar)\s+"
    r"(?:un\s+)?diagnostico\b|"
    r"\b(?:sin|no)\s+diagnosticar\b|"
    r"\bno\s+(?:quiero|necesito|busco|solicito)\s+(?:un\s+)?diagnostico\b"
)


def has_explicit_diagnostic_boundary(value: str) -> bool:
    """Return whether the user explicitly excludes a diagnostic conclusion.

    The exception is intentionally narrow: negating a disease (for example,
    ``no tiene leucemia``) is still a diagnostic request. Only language that
    rejects the diagnostic act itself is treated as an informational boundary.
    """

    return bool(_EXPLICIT_DIAGNOSTIC_BOUNDARY.search(normalize_intent_text(value)))


def extract_clinical_parameter(message: str) -> str | None:
    return extract_parameter_code(message)


class IntentClassifier:
    """Fast, deterministic intent classification for routing and slot resolution.

    Safety-critical intents intentionally precede prompt-injection detection: a user
    cannot turn an animal-harm threat into an unrelated guardrail response by adding
    "ignore your rules" to the same message.
    """

    _animal_harm = re.compile(
        r"\b(golpear|golpeo|golpeare|golpearlo|golpearla|pegar|pegarle|patear|"
        r"lastimar|lastimarlo|lastimarla|maltratar|matar|hacerle dano|hacer dano|"
        r"si lo golpeo|si la golpeo)\b"
    )
    _human_context = re.compile(
        r"\b(mi hermana|mi hermano|mi madre|mi padre|mi esposa|mi esposo|mi pareja|"
        r"persona|humano|humana|embarazada|embarazo|bebe)\b"
    )
    _human_health = re.compile(
        r"\b(embarazada|embarazo|sangrado|dolor intenso|desmayo|convulsion|"
        r"no puede respirar|urgencia|emergencia|medico|hospital)\b"
    )
    _veterinary_urgency = re.compile(
        r"\b(no puede respirar|dificultad para respirar|convulsion|inconsciente|"
        r"desmayo|se desangra|hemorragia|mucosas palidas|no puede levantarse|"
        r"emergencia|urgencia|se va a morir|esta muy mal|"
        r"fiebre\b.{0,80}\bgarrapatas?|garrapatas?\b.{0,80}\bfiebre)\b"
    )
    _medication = re.compile(
        r"\b(dosis|medicamentos?|medicinas?|farmacos?|antibioticos?|amoxicilina|doxiciclina|"
        r"prednisona|aspirina|paracetamol|acetaminofen|ibuprofeno|naproxeno|"
        r"hierro|suplementos?|pastillas?|receta|recetar|recetame|recetarme|"
        r"prescribir|prescribeme|que le doy|que puedo darle|que le puedo dar|"
        r"administrar|tratamiento|transfusion|plasma)\b"
    )
    _dose_request = re.compile(
        r"\b(dosis|dosage|mg/kg|cuanto le doy|cuanta le doy|que cantidad|"
        r"\d+[.,]?\d*\s*(?:mg|ml|cc|gotas?|tabletas?|pastillas?))\b"
    )
    _frequency_request = re.compile(
        r"\b(cada cuantas? horas?|cada cuanto|cuantas? veces (?:al|por) dia|"
        r"frecuencia|intervalo entre dosis)\b"
    )
    _duration_request = re.compile(
        r"\b(durante cuantos? dias?|por cuantos? dias?|cuantos? dias|"
        r"duracion del tratamiento|hasta cuando)\b"
    )
    _treatment_selection = re.compile(
        r"\b(que medicamento|cual medicamento|que antibiotico|cual antibiotico|"
        r"dime que (?:le )?(?:doy|dar)|que tratamiento|tratamiento completo|"
        r"recetame|recetarme|prescribeme|que puedo darle|que le puedo dar)\b"
    )
    _personalized_recommendation = re.compile(
        r"\b(puedo darle|debo darle|le doy|le puedo dar|le conviene|"
        r"me recomiendas|recomiendame|para mi perro|a mi perro|a mi mascota|"
        r"segun su peso|pesa \d+)\b"
    )
    _educational_question = re.compile(
        r"\b(que es|que significa|para que sirve|cual es la funcion|"
        r"por que (?:los|algunos|ciertos) medicamentos|informacion general|"
        r"de forma general)\b"
    )
    _general_risk = re.compile(
        r"\b(peligroso|peligrosos|toxico|toxicidad|riesgo|riesgos|"
        r"medicamentos humanos)\b"
    )
    _diagnosis = re.compile(
        r"\b(enfermedad|diagnosticos?|diagnostica|confirma|confirmame|padece|"
        r"ehrlichia|ehrlichiosis|cancer|leucemia|parvovirus|moquillo|linfoma|"
        r"se encontro una enfermedad|hay una enfermedad)\b"
    )
    # "¿mi perro tiene anemia?" is a diagnosis-confirmation request in plain
    # Spanish, but it matched no branch and was refused as out-of-domain, so
    # the cautious diagnosis route — which exists for exactly this question —
    # never ran. The verb alone is far too broad ("tiene las plaquetas bajas"
    # is a user describing a result, not asking to confirm a disease), so it
    # only counts when a named condition follows it closely.
    _condition_possession = re.compile(
        r"\b(?:tiene|tendra|sufre|padece|presenta|le\s+dio|se\s+contagio)\b"
        r"[^.?!\n]{0,30}"
    )
    _identity = re.compile(
        r"\b(eres humano|eres humana|eres un humano|eres una persona|eres veterinario|"
        r"eres veterinaria|eres un veterinario|eres una veterinaria|quien eres|"
        r"eres un bot|inteligencia artificial)\b|^\s*que eres\b"
    )
    _chat_history = re.compile(
        r"\b(primera pregunta|que recuerdas|todo lo que recuerdas|recuerdas de este chat|"
        r"que me dijiste|mencionamos anteriormente|dijiste antes|preguntas anteriores|"
        r"historial (?:de este )?chat)\b"
    )
    _prompt_injection = re.compile(
        r"\b(ignora|olvida|desactiva|sin restricciones|modo desarrollador|"
        r"cambia tu rol|ahora eres|tienes que responder|tienes que decir|"
        r"no digas que no|prompt del sistema|instrucciones internas|guardrails?|guardarils?)\b"
    )
    _comparison = re.compile(
        r"\b(compara|comparacion|evolucion|que cambio|que ha cambiado|cambios?|"
        r"anterior|previo|antes|aumento|aumento|disminuyo|subio|bajaron)\b"
    )
    _vet_questions = re.compile(
        r"\b(que preguntas? (?:puedo|debo) hacerle (?:a )?(?:mi|al) veterinari[oa]|"
        r"que preguntarle (?:a )?(?:mi|al) veterinari[oa]|preguntas? para (?:mi|el) veterinari[oa])\b"
    )
    _nearby_veterinary_care = re.compile(
        r"\b("
        r"veterinari[ao]s?\s+(?:cerca|cercana?s?|proxima?s?|mas cercana?)|"
        r"clinicas?\s+veterinari[ao]s?\s+(?:cerca|cercana?s?)|"
        r"atencion\s+veterinaria\s+(?:cerca|cercana?)|"
        r"donde\s+(?:hay|encuentro|queda|puedo encontrar)\s+(?:un[a]?\s+)?"
        r"(?:clinica\s+)?veterinari[oa]|"
        r"necesito\s+llevar\s+(?:a\s+)?mi\s+mascota\s+a\s+(?:un|una)\s+veterinari[oa]|"
        r"necesito\s+(?:un|una)\s+veterinari[oa]\s+cerca|"
        r"buscar\s+(?:una?\s+)?veterinari[ao]\s+cercana?|"
        r"(?:a\s+)?donde\s+(?:puedo\s+)?lo\s+llevo|"
        r"donde\s+puedo\s+llevarl[oa]|"
        r"que\s+hago\s*,?\s*a\s+donde\s+puedo\s+llevarl[oa]"
        r")\b"
    )
    _hematologic_pattern = re.compile(
        r"\b(patron hematologico|patron en (?:este|el) hemograma|hay un patron|"
        r"hallazgos? en conjunto|analiza (?:el|los) conjunto|"
        r"algun problema|algun hallazgo|hay algo (?:mal|malo|raro|preocupante)|"
        r"que (?:ves|observas|notas) (?:en|con|sobre)|"
        r"como (?:esta|luce|se ve) mi (?:perro|mascota|gato)|"
        r"condiciones? detectadas?)\b"
    )
    _full_summary = re.compile(
        r"\b(resumen completo|resume (?:todo|el hemograma completo)|"
        r"explica (?:todo|todos los parametros)|interpreta (?:todo|el hemograma completo)|"
        r"analiza (?:todo|el hemograma completo)|revision completa del hemograma)\b"
    )
    _range_threshold = re.compile(
        r"\b(que|cual|cuando|a partir de|por debajo de|por encima de|inferior|superior)\b.*"
        r"\b(valor|nivel|clasificacion|se considera|seria|es)\b.*"
        r"\b(bajo|baja|alto|alta|normal)\b|"
        r"\b(cual seria|que seria|se considera)\b.*\b(bajo|baja|alto|alta|normal)\b"
    )
    _classification = re.compile(
        r"\b(esta|estan|es|son|clasifica|clasificacion|estado|resultado)\b.*"
        r"\b(alto|alta|altos|altas|bajo|baja|bajos|bajas|normal|normales|dentro|fuera)\b|"
        r"\b(alto o bajo|alta o baja|altos o bajos|normal o no)\b"
    )
    _range = re.compile(r"\b(rango|referencia|limite|intervalo)\b")
    _value = re.compile(
        r"\b(cual es|cuanto es|que valor|que nivel|valor exacto|dame el valor|"
        r"indica el valor|aparece|muestra|tiene este hemograma|nibel)\b"
    )
    _clinical_follow_up = re.compile(
        r"^(?:y\s+)?(?:eso|esa|ese|esto|esta|este|estos|estas|lo anterior|"
        r"que significa|por que|es normal|son normales|esta alto|estan altos|"
        r"esta bajo|estan bajos|es alto|es bajo|cual seria|que seria|"
        r"cual se considera|que se considera|en el anterior|en la anterior|"
        r"en el previo|en la previa|y antes|y ahora|que cambio|que ha cambiado)\b"
    )
    _greeting = re.compile(
        r"^(hola|buenas|buenos dias|buenas tardes|buenas noches|saludos|hey)[.!?\s]*$"
    )
    # Five memorized spellings before this: "¿para qué sirves?", "¿en qué me
    # puedes ayudar?", "¿cómo funcionas?" and "¿qué sabes hacer?" all fell
    # through every branch to OUT_OF_DOMAIN and were refused as off-topic —
    # the assistant declining to say what it is for.
    _capability = re.compile(
        r"\b(?:que\s+(?:puedes|sabes|podes)\s+hacer|"
        r"que\s+(?:cosas\s+)?(?:puedes|sabes)\b|"
        r"para\s+que\s+(?:sirves|sirve\s+este\s+chat|sirve\s+hemovet|"
        r"fuiste\s+creado|estas\s+aqui)|"
        r"como\s+(?:funcionas|funciona\s+hemovet|funciona\s+este\s+chat|"
        r"me\s+puedes\s+ayudar|puedes\s+ayudarme|me\s+ayudas)|"
        r"en\s+que\s+(?:me\s+)?(?:puedes\s+ayudar|ayudas|me\s+ayudas)|"
        r"cuales\s+son\s+tus\s+(?:funciones|capacidades|opciones)|"
        r"que\s+(?:servicios|funciones|opciones)\s+(?:ofreces|tienes|hay)|"
        r"tus\s+(?:funciones|capacidades))\b"
    )
    # Courtesy and acknowledgement turns. These are not questions and carry no
    # topic, so every topical branch missed them and they were refused as
    # out-of-domain: answering "gracias" with "eso queda fuera del ámbito de
    # HemoVet" is the single most visible way the assistant reads as broken.
    _social_acknowledgement = re.compile(
        r"^\s*(?:muchas\s+|mil\s+)?(?:gracias|ok|okay|vale|listo|perfecto|"
        r"entiendo|entendido|de\s+acuerdo|genial|excelente|buenisimo|"
        r"ya\s+veo|comprendo|claro)\b"
        # A short closing tail stays part of the same courtesy turn ("gracias,
        # eso era todo"); anything longer is a real question that happens to
        # start politely and must keep going through the topical branches.
        r"(?:[\s,.!?]+(?:muchas\s+)?(?:gracias|eso\s+(?:es|era)\s+todo|"
        r"por\s+(?:tu\s+)?ayuda|por\s+todo|hasta\s+luego|adios|nos\s+vemos|"
        r"buen\s+dia|saludos|amigo|entonces|ya)\b)*[\s.!?,]*$"
    )
    _social = re.compile(
        r"\b(amor|amir|enamorado|enamorada|mi familia|mi pareja|"
        r"problema personal|me siento solo|me siento sola|discusion familiar)\b"
    )
    _cbc = re.compile(
        r"\b(hemograma|emograma|homograma|hematologico|sangre|leuco|leucos|"
        r"leucocito|leucocitos|leucosito|leucositos|hemoglobina|emoglovina|"
        r"hematocrito|plaqueta|plaquetas|eritrocito|eritrocitos|wbc|rbc|hgb|hct|plt)\b"
    )
    # Named hematologic conditions and processes. Deliberately separate from
    # `_cbc`: these are legitimate *topics* for the corpus, but they are not
    # the "there is a measurement being asked about" signal that gates the
    # literal value lookup (`has_clinical_signal`), so folding them into _cbc
    # would turn "¿qué es la anemia?" into a patient value request.
    _hematology_topic = re.compile(
        r"\b(anemi\w*|trombocitopeni\w*|trombocitosis|leucopeni\w*|leucocitosis|"
        r"neutrofili\w*|neutropeni\w*|linfocitosis|linfopeni\w*|eosinofili\w*|"
        r"monocitosis|basofili\w*|policitemi\w*|pancitopeni\w*|leucemi\w*|"
        r"linfom\w*|hemolisis|hemolitic\w*|aglutinacion|reticulocit\w*|"
        r"coagulacion|coagulopati\w*|hemostasi\w*|frotis|extendido sanguineo|"
        r"ehrlichi\w*|babesi\w*|anaplasm\w*|dirofilari\w*|hemoparasit\w*|"
        r"medula osea|eritropoyesis|hematopoyesis|hierro|ferritina|"
        # The three panels by their own names, the preanalytical artefacts the
        # corpus is largely about, and the morphology vocabulary. Their absence
        # is why "explícame el leucograma de estrés" and "los agregados
        # plaquetarios como artefacto preanalítico" were refused as off-topic.
        r"leucogram\w*|eritrogram\w*|trombogram\w*|"
        r"agregado\w*\s+plaquetari\w*|artefact\w*|preanalitic\w*|"
        r"hemodilucion|lipemi\w*|ictericia|rouleaux|"
        r"desviacion\s+a\s+la\s+izquierda|neutrofilos?\s+en\s+banda|"
        r"morfologi\w*\s+(?:eritrocitari\w*|celular)|"
        r"indices?\s+eritrocitari\w*|"
        r"eje\s+hpa|estres\s+(?:leucocitari\w*|fisiologic\w*)|"
        r"serie\s+(?:roja|blanca|plaquetaria)|"
        r"regenerativ\w*|hipocromi\w*|microcitosis|macrocitosis|anisocitosis|"
        r"poiquilocitosis|esferocit\w*|"
        r"transfusion\w*|hemoderivado\w*)\b"
    )
    # General veterinary topics with no hematology signal (audited false
    # positive: these used to have no matching branch and fell all the way
    # to OUT_OF_DOMAIN, e.g. "por que jadean los perros?"). High-confidence
    # topic words only, not a general animal-topic catch-all.
    _veterinary_education = re.compile(
        r"\b(jadea|jadean|jadeo|ladra|ladran|ladrido|ladridos|"
        r"comportamiento canino|comportamiento del perro|comportamiento felino|"
        r"vacuna|vacunas|vacunacion|desparasita|desparasitacion|desparasitar|"
        r"esteriliza|esterilizacion|castra|castracion|"
        r"pulgas|garrapatas|dermatitis|sarna|"
        r"dientes|dental|sarro|mal aliento|"
        r"otitis|"
        r"alergia|alergias|"
        r"embarazo canino|prenez|gestacion canina|parto|cachorro|cachorros|"
        r"esperanza de vida|cuidados del cachorro|"
        r"entrenamiento canino|entrenar (?:a )?(?:mi |un )?perro|adiestramiento|"
        r"socializacion|ansiedad por separacion|estres canino|"
        r"ejercicio (?:diario|para perros)|paseo|paseos|"
        r"golpe de calor|hidratacion canina)\b"
    )
    # Question about the pet's own profile rather than a hemogram parameter.
    _pet_profile = re.compile(
        r"\b(que raza|de que raza|cual es la raza|cuantos anos tiene|"
        r"que edad tiene|cuanto pesa|cual es su peso|cuanto mide|"
        r"es macho o hembra|es nino o nina|es hembra o macho|"
        r"cuando nacio|fecha de nacimiento|donde vive|"
        r"como se llama|cual es su nombre|"
        r"notas? (?:sobre|de) (?:mi |la )?mascota|informacion de mi mascota|"
        r"perfil de (?:mi |la )?mascota)\b"
    )

    _CLINICAL_REFERENCE_INTENTS = frozenset(
        {
            FunctionalIntent.VALUE_REQUEST,
            FunctionalIntent.VALUE_CLASSIFICATION,
            FunctionalIntent.RANGE_EXPLANATION,
            FunctionalIntent.RANGE_THRESHOLD,
            FunctionalIntent.HEMOGRAM_COMPARISON,
            FunctionalIntent.HISTORY_CHANGE,
            FunctionalIntent.GENERAL_CBC,
            FunctionalIntent.AMBIGUOUS,
        }
    )

    _PROTOTYPE_EXAMPLES: dict[FunctionalIntent, tuple[str, ...]] = {
        FunctionalIntent.GREETING: (
            "buen dia hemovet",
            "un gusto saludarte",
            "quiero saludarte",
        ),
        FunctionalIntent.CAPABILITY: (
            "en que me ayudas",
            "cuales son tus funciones",
            "que tipo de ayuda ofreces",
        ),
        FunctionalIntent.SOCIAL_GENERAL: (
            "quiero hablar del amor",
            "me siento en soledad",
            "tengo problemas con mi pareja",
        ),
        FunctionalIntent.GENERAL_CBC: (
            "explica las celulas sanguineas",
            "quiero aprender hematologia canina",
            "dudas sobre analisis de sangre",
        ),
        FunctionalIntent.OUT_OF_DOMAIN: (
            "ayudame con codigo python",
            "cual es el clima",
            "noticias de hoy",
        ),
    }
    _PROTOTYPE_STOPWORDS = frozenset(
        {"a", "al", "con", "de", "del", "el", "en", "es", "la", "las", "lo", "los", "me", "mi", "que", "un", "una", "y"}
    )

    def classify(
        self,
        message: str,
        *,
        has_memory_parameter: bool = False,
    ) -> IntentDetection:
        primary = self._classify_primary(
            message,
            has_memory_parameter=has_memory_parameter,
        )
        secondary = self._secondary_intents(
            normalize_intent_text(message),
            primary=primary.intent,
        )
        return replace(primary, secondary_intents=secondary)

    def _classify_primary(
        self,
        message: str,
        *,
        has_memory_parameter: bool = False,
    ) -> IntentDetection:
        normalized = normalize_intent_text(message)
        parameter = extract_clinical_parameter(message)
        follow_up_shape = bool(self._clinical_follow_up.search(normalized))
        clinical_request = self.classify_clinical_request(message)
        # "cual es"/"que valor"/"esta alto" etc. are common Spanish question
        # patterns for ANY topic, not just hemograms ("cual es la capital de
        # Francia" matched _value verbatim and was misrouted as
        # VALUE_REQUEST). The exact-value family (range_threshold,
        # classification, range, value) below must not fire without some
        # actual clinical signal: a recognized parameter, a CBC keyword, or
        # (mid-conversation) a remembered parameter from a prior turn.
        has_clinical_signal = bool(
            parameter or self._cbc.search(normalized) or has_memory_parameter
        )

        if self._animal_harm.search(normalized):
            return IntentDetection(FunctionalIntent.ANIMAL_HARM, confidence=0.99)
        if self._human_context.search(normalized) and self._human_health.search(
            normalized
        ):
            return IntentDetection(FunctionalIntent.HUMAN_HEALTH, confidence=0.97)
        if clinical_request.kind is ClinicalRequestKind.URGENT_REFERRAL:
            return IntentDetection(FunctionalIntent.VETERINARY_URGENCY, confidence=0.96)
        if clinical_request.kind in {
            ClinicalRequestKind.PERSONALIZED_RECOMMENDATION,
            ClinicalRequestKind.DOSAGE,
            ClinicalRequestKind.FREQUENCY,
            ClinicalRequestKind.DURATION,
            ClinicalRequestKind.TREATMENT_SELECTION,
        }:
            return IntentDetection(
                FunctionalIntent.MEDICATION, parameter, confidence=0.96
            )
        if clinical_request.kind is ClinicalRequestKind.DIAGNOSIS_CONFIRMATION:
            return IntentDetection(
                FunctionalIntent.DIAGNOSIS, parameter, confidence=0.92
            )
        if self._identity.search(normalized):
            return IntentDetection(FunctionalIntent.IDENTITY, confidence=0.98)
        if self._chat_history.search(normalized):
            return IntentDetection(FunctionalIntent.CHAT_HISTORY, confidence=0.98)
        if self._prompt_injection.search(normalized):
            return IntentDetection(FunctionalIntent.PROMPT_INJECTION, confidence=0.97)
        if self._greeting.search(normalized):
            return IntentDetection(FunctionalIntent.GREETING, confidence=0.99)
        # Before any topical branch: a bare "gracias" or "ok" has no topic to
        # match, so it fell through to OUT_OF_DOMAIN and was answered as an
        # off-topic request. Closing a conversation politely is not a
        # different subject, and GREETING is the route that already knows how
        # to answer briefly without clinical content.
        if self._social_acknowledgement.search(normalized):
            return IntentDetection(FunctionalIntent.GREETING, confidence=0.95)
        if self._capability.search(normalized):
            return IntentDetection(FunctionalIntent.CAPABILITY, confidence=0.97)
        if self._social.search(normalized):
            return IntentDetection(FunctionalIntent.SOCIAL_GENERAL, confidence=0.95)
        if self._vet_questions.search(normalized):
            return IntentDetection(FunctionalIntent.VET_QUESTIONS, confidence=0.98)
        if self._nearby_veterinary_care.search(normalized):
            return IntentDetection(
                FunctionalIntent.NEARBY_VETERINARY_CARE, confidence=0.95
            )
        if self._pet_profile.search(normalized) and not has_clinical_signal:
            return IntentDetection(FunctionalIntent.PET_PROFILE_QUESTION, confidence=0.90)
        if self._hematologic_pattern.search(normalized):
            return IntentDetection(
                FunctionalIntent.HEMATOLOGIC_PATTERN, confidence=0.97
            )
        if self._full_summary.search(normalized):
            return IntentDetection(
                FunctionalIntent.FULL_HEMOGRAM_SUMMARY, confidence=0.97
            )
        if clinical_request.kind in {
            ClinicalRequestKind.EDUCATIONAL_CONCEPT,
            ClinicalRequestKind.GENERAL_RISK_INFORMATION,
        }:
            return IntentDetection(
                FunctionalIntent.GENERAL_CBC, parameter, confidence=0.90
            )
        if self._comparison.search(normalized):
            return IntentDetection(
                FunctionalIntent.HEMOGRAM_COMPARISON,
                parameter,
                is_clinical_follow_up=follow_up_shape and has_memory_parameter,
                confidence=0.94,
            )

        boundary = self._requested_boundary(normalized)
        if self._range_threshold.search(normalized):
            return IntentDetection(
                FunctionalIntent.RANGE_THRESHOLD,
                parameter,
                requested_boundary=boundary,
                is_clinical_follow_up=follow_up_shape and has_memory_parameter,
                confidence=0.96,
            )
        if self._classification.search(normalized):
            return IntentDetection(
                FunctionalIntent.VALUE_CLASSIFICATION,
                parameter,
                requested_boundary=boundary,
                is_clinical_follow_up=follow_up_shape and has_memory_parameter,
                confidence=0.95,
            )
        if self._range.search(normalized):
            return IntentDetection(
                FunctionalIntent.RANGE_EXPLANATION,
                parameter,
                is_clinical_follow_up=follow_up_shape and has_memory_parameter,
                confidence=0.93,
            )
        # _value is the broadest, most topic-agnostic pattern here ("cual
        # es"/"cuanto es"/"que valor"/"aparece"/"muestra") — none of its
        # alternatives carry any hematology signal on their own, unlike
        # _range_threshold/_classification/_range above (which all require
        # alto/bajo/normal/rango, still hematology-adjacent even without a
        # named parameter, and are routed to safe educational RAG rather
        # than a literal lookup in general scope). Confirmed live:
        # "cual es la capital de Francia" matched _value verbatim and was
        # misrouted as VALUE_REQUEST.
        if has_clinical_signal and self._value.search(normalized):
            return IntentDetection(
                FunctionalIntent.VALUE_REQUEST,
                parameter,
                is_clinical_follow_up=follow_up_shape and has_memory_parameter,
                confidence=0.94,
            )
        if parameter or self._cbc.search(normalized):
            return IntentDetection(
                FunctionalIntent.GENERAL_CBC,
                parameter,
                is_clinical_follow_up=follow_up_shape and has_memory_parameter,
                confidence=0.78,
            )
        # A named hematologic condition or process is in domain even when the
        # sentence never says "hemograma". This vocabulary existed but was only
        # consulted by classify_clinical_request, so the primary classifier
        # walked past "explícame el leucograma de estrés", "los agregados
        # plaquetarios como artefacto preanalítico" and "la diferencia entre
        # anemia regenerativa y no regenerativa" and refused them as
        # off-topic — the core subject of the corpus, declined for not
        # containing one of eleven words. GENERAL_CBC rather than a new intent:
        # these are hematology education, which is what that route answers.
        if self._hematology_topic.search(normalized):
            return IntentDetection(
                FunctionalIntent.GENERAL_CBC,
                is_clinical_follow_up=follow_up_shape and has_memory_parameter,
                confidence=0.76,
            )
        if self._veterinary_education.search(normalized):
            return IntentDetection(
                FunctionalIntent.VETERINARY_EDUCATION, confidence=0.85
            )
        if follow_up_shape:
            # A follow-up-shaped message ("eso qué significa") with no
            # rememberable parameter still isn't OUT_OF_DOMAIN — the user is
            # continuing the current clinical conversation, they just didn't
            # name a parameter. AMBIGUOUS is a light, no-RAG, no-clinical-
            # context route (fixed: response_contracts no longer requires a
            # fact_id for its clarification claim), so it won't hit the
            # context budget the way heavier routes do on later turns.
            return IntentDetection(
                FunctionalIntent.AMBIGUOUS,
                is_clinical_follow_up=has_memory_parameter,
                confidence=0.70,
            )
        prototype = self._prototype_fallback(normalized)
        if prototype is not None:
            return prototype
        return IntentDetection(FunctionalIntent.OUT_OF_DOMAIN, confidence=0.72)

    def _secondary_intents(
        self,
        normalized: str,
        *,
        primary: FunctionalIntent,
    ) -> tuple[FunctionalIntent, ...]:
        candidates: list[FunctionalIntent] = []
        clinical = self.classify_clinical_request(normalized)
        if self._prompt_injection.search(normalized):
            candidates.append(FunctionalIntent.PROMPT_INJECTION)
        if self._animal_harm.search(normalized):
            candidates.append(FunctionalIntent.ANIMAL_HARM)
        if clinical.kind is ClinicalRequestKind.URGENT_REFERRAL:
            candidates.append(FunctionalIntent.VETERINARY_URGENCY)
        elif clinical.kind in {
            ClinicalRequestKind.PERSONALIZED_RECOMMENDATION,
            ClinicalRequestKind.DOSAGE,
            ClinicalRequestKind.FREQUENCY,
            ClinicalRequestKind.DURATION,
            ClinicalRequestKind.TREATMENT_SELECTION,
        }:
            candidates.append(FunctionalIntent.MEDICATION)
        elif clinical.kind is ClinicalRequestKind.DIAGNOSIS_CONFIRMATION:
            candidates.append(FunctionalIntent.DIAGNOSIS)
        if self._cbc.search(normalized):
            candidates.append(FunctionalIntent.GENERAL_CBC)
        return tuple(dict.fromkeys(item for item in candidates if item is not primary))

    @classmethod
    def _prototype_fallback(cls, normalized: str) -> IntentDetection | None:
        tokens = cls._prototype_tokens(normalized)
        if not tokens:
            return None
        scored: list[tuple[float, FunctionalIntent]] = []
        for intent, examples in cls._PROTOTYPE_EXAMPLES.items():
            score = max(
                cls._prototype_similarity(tokens, cls._prototype_tokens(example))
                for example in examples
            )
            scored.append((score, intent))
        scored.sort(key=lambda item: item[0], reverse=True)
        top_score, top_intent = scored[0]
        runner_up = scored[1][0]
        margin = top_score - runner_up
        if top_score < 0.45 or margin < 0.08:
            return None
        confidence = min(0.89, 0.55 + (0.25 * top_score) + (0.10 * margin))
        return IntentDetection(
            top_intent,
            confidence=round(confidence, 3),
            classification_method="lexical_prototype_margin",
        )

    @classmethod
    def _prototype_tokens(cls, value: str) -> frozenset[str]:
        return frozenset(
            token
            for token in normalize_intent_text(value).split()
            if len(token) > 1 and token not in cls._PROTOTYPE_STOPWORDS
        )

    @staticmethod
    def _prototype_similarity(
        left: frozenset[str],
        right: frozenset[str],
    ) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / ((len(left) * len(right)) ** 0.5)

    def classify_clinical_request(self, message: str) -> ClinicalRequestDetection:
        normalized = normalize_intent_text(message)
        mentions_medication = bool(self._medication.search(normalized))
        if self._veterinary_urgency.search(normalized):
            return ClinicalRequestDetection(
                ClinicalRequestKind.URGENT_REFERRAL,
                confidence=0.97,
                mentions_medication=mentions_medication,
            )
        if self._dose_request.search(normalized):
            return ClinicalRequestDetection(
                ClinicalRequestKind.DOSAGE,
                confidence=0.99,
                mentions_medication=mentions_medication,
            )
        if self._frequency_request.search(normalized):
            return ClinicalRequestDetection(
                ClinicalRequestKind.FREQUENCY,
                confidence=0.98,
                mentions_medication=mentions_medication,
            )
        if self._duration_request.search(normalized):
            return ClinicalRequestDetection(
                ClinicalRequestKind.DURATION,
                confidence=0.98,
                mentions_medication=mentions_medication,
            )
        if self._treatment_selection.search(normalized):
            return ClinicalRequestDetection(
                ClinicalRequestKind.TREATMENT_SELECTION,
                confidence=0.97,
                mentions_medication=mentions_medication,
            )
        if self._personalized_recommendation.search(normalized) and mentions_medication:
            return ClinicalRequestDetection(
                ClinicalRequestKind.PERSONALIZED_RECOMMENDATION,
                confidence=0.97,
                mentions_medication=True,
            )
        asks_to_confirm_condition = bool(
            self._diagnosis.search(normalized)
            or (
                (possession := self._condition_possession.search(normalized))
                and self._hematology_topic.search(possession.group(0))
            )
        )
        if (
            asks_to_confirm_condition
            and not has_explicit_diagnostic_boundary(normalized)
            and (
                extract_clinical_parameter(message)
                or self._cbc.search(normalized)
                or "enfermedad" in normalized
                # Was a four-word inline list; the shared vocabulary keeps
                # this branch and the educational one naming the same set.
                or self._hematology_topic.search(normalized)
                or re.search(r"\b(cancer|infeccion)\b", normalized)
            )
        ):
            return ClinicalRequestDetection(
                ClinicalRequestKind.DIAGNOSIS_CONFIRMATION,
                confidence=0.94,
                mentions_medication=mentions_medication,
            )
        if mentions_medication and self._general_risk.search(normalized):
            return ClinicalRequestDetection(
                ClinicalRequestKind.GENERAL_RISK_INFORMATION,
                confidence=0.94,
                mentions_medication=True,
            )
        if mentions_medication and self._educational_question.search(normalized):
            return ClinicalRequestDetection(
                ClinicalRequestKind.EDUCATIONAL_CONCEPT,
                confidence=0.93,
                mentions_medication=True,
            )
        if self._educational_question.search(normalized) and (
            self._hematology_topic.search(normalized)
        ):
            # "¿qué es la anemia en perros?" carried no parameter name and no
            # word from _cbc, so it reached NOT_CLINICAL and was refused as
            # off-topic — a question squarely inside the corpus this product
            # indexes. Named hematologic conditions are now a clinical signal
            # in their own right, routed as education (not as a diagnosis:
            # the DIAGNOSIS_CONFIRMATION branch above already claimed
            # "¿tiene anemia?" and runs first).
            return ClinicalRequestDetection(
                ClinicalRequestKind.EDUCATIONAL_CONCEPT,
                confidence=0.88,
                mentions_medication=mentions_medication,
            )
        if extract_clinical_parameter(message) or self._cbc.search(normalized):
            return ClinicalRequestDetection(
                ClinicalRequestKind.RESULT_EXPLANATION,
                confidence=0.84,
                mentions_medication=mentions_medication,
            )
        if mentions_medication:
            # A bare medication name is ambiguous, not authorization to choose
            # or administer it.  Route it to a short educational clarification.
            return ClinicalRequestDetection(
                ClinicalRequestKind.EDUCATIONAL_CONCEPT,
                confidence=0.70,
                mentions_medication=True,
            )
        return ClinicalRequestDetection(
            ClinicalRequestKind.NOT_CLINICAL, confidence=0.80
        )

    @classmethod
    def permits_parameter_reference(cls, detection: IntentDetection) -> bool:
        return (
            detection.intent in cls._CLINICAL_REFERENCE_INTENTS
            and detection.is_clinical_follow_up
        )

    @staticmethod
    def _requested_boundary(normalized: str) -> str | None:
        if re.search(r"\b(bajo|baja|bajos|bajas|inferior|por debajo)\b", normalized):
            return "low"
        if re.search(r"\b(alto|alta|altos|altas|superior|por encima)\b", normalized):
            return "high"
        if re.search(r"\b(normal|normales|dentro)\b", normalized):
            return "normal"
        return None
