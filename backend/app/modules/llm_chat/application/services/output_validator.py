from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.modules.llm_chat.application.services.clinical_facts import (
    ClinicalFactIndex,
    LabFact,
    temporal_fact_index,
)
from app.modules.llm_chat.application.services.output_claim_validator import (
    ClinicalClaimIssue,
    OutputClaimValidator,
)
from app.modules.llm_chat.claim_validation import (
    contains_english_passage,
    contains_non_spanish_passage,
)


@dataclass(frozen=True, slots=True)
class OutputValidation:
    is_safe: bool
    text: str
    # Invalid output may be repaired by bounded LLM attempts and otherwise
    # becomes a typed, retryable failure. Validators deliberately do not author
    # user-visible clinical prose.
    safe_fallback: str = ""
    reason: str = "ok"
    removed_invalid_citations: bool = False
    detail: str | None = None
    claim_text: str = ""
    parameter_code: str | None = None
    analysis_id: str | None = None
    meets_intent: bool = True
    coverage: int = 0
    required_coverage: int = 0

    @property
    def disposition(self) -> str:
        """Separate hard validation failures from correctable answer coverage.

        Safety and clinical-fidelity validators continue to return ``is_safe=False``.
        Intent checks may retain a safe candidate while requesting one controlled
        rewrite, so wording variation cannot masquerade as a clinical failure.
        """

        if not self.is_safe:
            return "invalid"
        if not self.meets_intent:
            return "repairable"
        return "valid"


class OutputValidator:
    _citation = re.compile(r"\[\s*S\s*\d+(?:\s*,\s*S\s*\d+)*\s*\]", re.IGNORECASE)
    _reasoning_marker = re.compile(
        r"(<\s*/?\s*(think|thinking|reasoning|analysis)\b|"
        r"okay[, ]+let(?:'|’)?s|"
        r"the user (?:is asking|asks|wants)|"
        r"i need to (?:check|analy[sz]e|review|ensure)|"
        r"i should(?: not)?|"
        r"let me (?:analy[sz]e|check|think)|"
        r"according to (?:the )?(?:instructions|authorized facts|sources?|context)|"
        r"the authorized facts|"
        r"we need(?: to)? [a-z]+|"
        r"voy a (?:analizar|revisar)|"
        r"el usuario (?:pregunta|pide|solicita)|"
        r"seg[uú]n las instrucciones|"
        r"chain[- ]of[- ]thought|"
        r"razonamiento interno|"
        r"cadena de pensamiento)",
        re.IGNORECASE,
    )
    _unsafe = re.compile(
        r"\b(administra|administrar|dale|darle|receta|prescribe|"
        r"inicia tratamiento|iniciar tratamiento|dosis|mg/kg|"
        r"\d+[.,]?\d*\s*(mg|ml|cc|gotas?|tabletas?|pastillas?))\b",
        re.IGNORECASE,
    )
    _indirect_treatment = re.compile(
        r"\b("
        r"dieta rica|carne roja|frijoles|legumbres|verduras verdes|"
        r"alimentos fortificados|alimento fortificado|comida|alimentos?|"
        r"suplementos?|vitaminas?|minerales?|hierro|acido folico|folato|b12|"
        r"protocolo|protocolos|glucocorticoides?|corticoides?|"
        r"transfusion|plasma|crioprecipitado|terapia celular|"
        r"tratamiento natural|remedio casero"
        r")\b",
        re.IGNORECASE,
    )
    _actionable_indirect_treatment = re.compile(
        r"\b("
        r"dale|darle|debes?|puedes?|podrias?|conviene|recomiendo|recomendaria|"
        r"incluye|incluya|ofrece|ofrezca|anade|agrega|administra|suministra|"
        r"necesita|requiere|se indica|esta indicado|"
        r"para (?:subir|bajar|aumentar|disminuir|mejorar|corregir|normalizar)"
        r")\b",
        re.IGNORECASE,
    )
    _clinical_decision = re.compile(
        r"\b("
        r"puede esperar|puedes esperar|esperar unos dias|esperar hasta manana|"
        r"quedarte tranquilo|no hay urgencia|no es una urgencia|"
        r"necesita hospitalizacion|no necesita hospitalizacion|"
        r"necesita transfusion|no necesita transfusion|necesita cirugia|"
        r"no necesita cirugia|se va a morir|pronostico"
        r")\b",
        re.IGNORECASE,
    )
    _definitive = re.compile(
        r"\b("
        r"diagn[oó]stico definitivo|confirma que|confirmar que|no confirma que|"
        # "confirma que hay una infección" was covered; "confirma una
        # infección" was not, and it is the shorter, likelier phrasing.
        r"(?:confirma|confirman|demuestra|demuestran|diagnostica|diagnostican|"
        r"evidencia|evidencian)\s+(?:un[a]?\s+)?"
        r"(?:ehrlichia|ehrlichiosis|c[aá]ncer|leishmania|moquillo|parvovirus|"
        r"infecci[oó]n|enfermedad|anemia|linfoma|hem[oó]lisis|leucemia|"
        r"trombocitopenia|neutrofilia|leucocitosis|leucopenia)|"
        r"descarta|se descarta|queda descartado|est[aá] sano|no est[aá] sano|"
        r"sin duda|definitivamente|100% de certeza|claramente|"
        r"(?:tu perro|el perro|el paciente|mi perro|mi mascota)\s+"
        r"(?:tiene|no tiene|padece|no padece|sufre|no sufre)\s+"
        r"(?:ehrlichia|ehrlichiosis|c[aá]ncer|leishmania|moquillo|parvovirus|infecci[oó]n|"
        r"enfermedad|anemia|linfoma)"
        r")\b",
        re.IGNORECASE,
    )
    # The same definitive-diagnosis sentence with the pet's own name as the
    # subject. `_definitive` above enumerates the subject ("tu perro", "el
    # paciente", ...), so "Lucas tiene anemia." walked straight through the
    # last clinical safety net \u2014 and the assistant is deliberately authorized
    # to call the patient by name, which makes that phrasing the likely one.
    # Case-sensitive on purpose: in Spanish a capitalized word mid-sentence is
    # a proper noun, which is what separates "Lucas tiene anemia" from the
    # educational "un perro que tiene anemia".
    _definitive_named_subject = re.compile(
        r"\b[A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1][a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1]{1,30}\s+"
        r"(?:tiene|no tiene|padece|no padece|sufre|no sufre|"
        r"presenta|no presenta)\s+"
        r"(?:un[a]?\s+)?"
        r"(?:ehrlichia|ehrlichiosis|c[a\u00e1]ncer|leishmania|moquillo|parvovirus|"
        r"infecci[o\u00f3]n|enfermedad|anemia|linfoma|hem[o\u00f3]lisis|leucemia|"
        r"trombocitopenia|neutrofilia|leucocitosis|leucopenia)\b"
    )
    _unexpected_script = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
    _internal_material = re.compile(
        r"\b(system[_ -]?prompt|developer[_ -]?message|route[_ -]?trace|"
        r"context_revision|client_message_id|analysis_id|chunk_id|similarity[_ -]?score)\b|"
        r"(?:/backend/|/app/modules/|knowledge_base/)|"
        r"\{\s*[\"'](?:role|response_policy|clinical_context)[\"']\s*:",
        re.IGNORECASE,
    )

    def validate(
        self,
        text: str,
        *,
        allowed_source_ids: set[str] | None = None,
        case_facts: list[dict[str, Any]] | None = None,
        safety_decision: object | None = None,
        patient_in_scope: bool = True,
    ) -> OutputValidation:
        cleaned, removed_invalid_citations = self._remove_inline_citations(
            text, allowed_source_ids=allowed_source_ids
        )
        if not cleaned.strip():
            return OutputValidation(
                is_safe=False,
                text="",
                reason="empty_output",
                removed_invalid_citations=removed_invalid_citations,
            )
        reasoning_match = self._reasoning_marker.search(cleaned)
        if reasoning_match:
            return OutputValidation(
                is_safe=False,
                text="",
                reason="reasoning_marker",
                removed_invalid_citations=removed_invalid_citations,
                detail=reasoning_match.group(0).strip().lower(),
            )
        if self._looks_like_english_answer(cleaned):
            return OutputValidation(
                is_safe=False,
                text="",
                reason="english_answer",
                removed_invalid_citations=removed_invalid_citations,
            )
        if contains_non_spanish_passage(cleaned):
            # Etapa 4, Block F: language="es" is contractually required for
            # every visible answer. This is a positive Spanish-density check
            # (see contains_non_spanish_passage), so it also catches French/
            # German/Portuguese/other drift that the English-specific check
            # above would miss — triggers the same repair/regeneration path,
            # never a deterministic translation or fixed replacement.
            return OutputValidation(
                is_safe=False,
                text="",
                reason="non_spanish_answer",
                removed_invalid_citations=removed_invalid_citations,
            )
        if self._unexpected_script.search(cleaned):
            return OutputValidation(
                is_safe=False,
                text="",
                reason="unexpected_script",
                removed_invalid_citations=removed_invalid_citations,
            )
        internal_match = self._internal_material.search(cleaned)
        if internal_match:
            return OutputValidation(
                is_safe=False,
                text="",
                reason="internal_material_exposed",
                removed_invalid_citations=removed_invalid_citations,
                detail=internal_match.group(0)[:80],
            )
        indirect_reason = self._contains_indirect_treatment(cleaned)
        if indirect_reason and not self._is_safe_refusal(cleaned):
            return OutputValidation(
                is_safe=False,
                text="",
                reason=indirect_reason,
                removed_invalid_citations=removed_invalid_citations,
            )
        if self._unsafe.search(cleaned) and (
            self._contains_positive_dose_instruction(cleaned)
            or not self._is_safe_refusal(cleaned)
        ):
            return OutputValidation(
                is_safe=False,
                text="",
                reason="unsafe_instruction",
                removed_invalid_citations=removed_invalid_citations,
            )
        if self._contains_definitive_diagnosis(cleaned):
            return OutputValidation(
                is_safe=False,
                text="",
                reason="definitive_diagnosis",
                removed_invalid_citations=removed_invalid_citations,
            )
        safety_reason = self._validate_safety_contract(cleaned, safety_decision)
        if safety_reason:
            return OutputValidation(
                is_safe=False,
                text="",
                reason=safety_reason,
                removed_invalid_citations=removed_invalid_citations,
            )
        clinical_issue = self._validate_case_facts(
            cleaned,
            case_facts or [],
            patient_in_scope=patient_in_scope,
        )
        if clinical_issue:
            return OutputValidation(
                is_safe=False,
                text="",
                reason=clinical_issue.code,
                removed_invalid_citations=removed_invalid_citations,
                detail=clinical_issue.detail,
                claim_text=clinical_issue.claim_text,
                parameter_code=clinical_issue.parameter_code,
                analysis_id=clinical_issue.analysis_id,
            )
        return OutputValidation(
            is_safe=True,
            text=cleaned,
            removed_invalid_citations=removed_invalid_citations,
        )

    def _validate_safety_contract(
        self,
        text: str,
        decision: object | None,
    ) -> str | None:
        if decision is None:
            return None
        normalized = "".join(
            character
            for character in unicodedata.normalize("NFKD", text.casefold())
            if not unicodedata.combining(character)
        )
        risk_flags = set(getattr(decision, "risk_flags", ()) or ())
        action = str(getattr(decision, "action", ""))
        if "animal_harm" in risk_flags:
            refuses_harm = bool(
                re.search(
                    r"\b(no|nunca)\b.{0,70}\b(golpe|golpear|pegues|pegar|dano|lastim)",
                    normalized,
                )
            )
            separates = bool(re.search(r"\b(alej\w*|separ\w*|distancia)\b", normalized))
            seeks_help = bool(
                re.search(
                    r"\b(pide|pedir|busca|buscar|contacta|contactar)\b.{0,55}\b(ayuda|persona|veterinari|proteccion)\b",
                    normalized,
                )
            )
            if not refuses_harm or not separates or not seeks_help:
                return "animal_harm_safety_contract"
        if action in {
            "refuse_medication",
            "refuse_dose",
            "refuse_treatment",
        }:
            refuses_action = self._is_safe_refusal(normalized)
            refers_to_vet = bool(re.search(r"\bveterinari[oa]\b", normalized))
            if not refuses_action or not refers_to_vet:
                return "medical_refusal_contract"
        if "prompt_injection" in risk_flags and re.search(
            r"\b(aqui (?:esta|tienes)|mis reglas son|el prompt dice|instrucciones internas:)\b",
            normalized,
        ):
            return "prompt_injection_disclosure"
        return None

    def _remove_inline_citations(
        self, text: str, *, allowed_source_ids: set[str] | None
    ) -> tuple[str, bool]:
        cleaned, removed_count = self._citation.subn("", str(text or ""))
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\s+([.,;:])", r"\1", cleaned)
        return cleaned.strip(), bool(removed_count)

    def _contains_definitive_diagnosis(self, text: str) -> bool:
        # Uncertainty and negated implications are safety-compliant language,
        # not diagnoses ("no significa que tu perro tiene...").  Remove only
        # that bounded construction; absolute exclusions such as "no tiene una
        # enfermedad" remain definitive and are still rejected.
        protected = re.sub(
            r"\b(?:no\s+(?:significa(?:n)?|implica(?:n)?|demuestra(?:n)?|confirma(?:n)?)|"
            r"no\s+permite(?:n)?\s+(?:afirmar|confirmar)|"
            r"no\s+se\s+puede\s+(?:afirmar|confirmar)|"
            r"no\s+(?:puedo|podemos)\s+(?:confirmar|diagnosticar|establecer|"
            r"determinar|asegurar|descartar)|"
            r"no\s+es\s+posible\s+(?:confirmar|diagnosticar|establecer|"
            r"determinar|asegurar|descartar)|"
            r"no\s+(?:puedo|podemos|se\s+puede)\s+(?:proporcionar|emitir|dar|hacer)\s+"
            r"(?:un\s+)?diagn[oó]stico)\b"
            r"[^.!?\n]{0,120}",
            "",
            text,
            flags=re.IGNORECASE,
        )
        return bool(
            self._definitive.search(protected)
            or self._definitive_named_subject.search(protected)
        )

    def _contains_indirect_treatment(self, text: str) -> str | None:
        if self._clinical_decision.search(text):
            return "unsafe_clinical_decision"
        if self._indirect_treatment.search(
            text
        ) and self._actionable_indirect_treatment.search(text):
            return "indirect_treatment_recommendation"
        if re.search(
            r"\b(como|para|que)\s+(subir|bajar|aumentar|mejorar|corregir)\b",
            text,
            re.IGNORECASE,
        ):
            return "therapeutic_parameter_modification"
        return None

    def _is_safe_refusal(self, text: str) -> bool:
        """Recognize a prohibition without requiring one exact conjugation.

        Medication refusals naturally use forms such as ``no debes
        administrarlo`` or ``no se debe dar``.  Treating only ``no debo`` as a
        refusal made safe LLM answers fail intermittently, because the generic
        medication detector then saw ``administrar`` as an instruction.  Keep
        the match bounded to a negative construction and an action term so a
        refusal followed by a positive prescription is still rejected.
        """

        action = (
            r"(?:indic(?:ar|o|amos)|recomend(?:ar|aria|amos)|proponer|"
            r"administr(?:ar|es|e|arlo|arla|arle|aci[oó]n)|recet(?:ar|es|e)|"
            r"dar(?:le|lo|la)?|des|suministr(?:ar|es|e)|usar|uses|use|"
            r"uso|empleo|automedicaci[oó]n|dosis|medicamento|tratamiento|"
            r"determinar|evaluar|decidir|"
            r"diagnosticar|establecer|descartar)"
        )
        negative_lead = (
            r"(?:no\s+(?:puedo|puedes|puede|podemos|debo|debes|debe|debemos|se\s+debe|"
            r"es\s+seguro|es\s+recomendable|conviene|corresponde|"
            r"recomiendo)|no\s+se\s+(?:recomienda|debe|puede)|nunca|"
            r"evita|evite)"
        )
        if re.search(
            rf"\b{negative_lead}\b.{{0,100}}\b{action}\b",
            text,
            re.IGNORECASE,
        ):
            return True
        # Imperative prohibitions place the action immediately after ``no``
        # and do not contain an auxiliary verb: "no le des" / "no administres".
        return bool(
            re.search(
                rf"\bno\s+(?:(?:le|lo|la|se)\s+)?{action}\b",
                text,
                re.IGNORECASE,
            )
        )

    @staticmethod
    def _contains_positive_dose_instruction(text: str) -> bool:
        """Do not let an initial refusal mask a later concrete prescription."""

        return bool(
            re.search(
                r"\b(?:dale|administra(?:le)?|suministra(?:le)?|usa|aplica|inicia)\b"
                r"[^.!?\n]{0,80}\b(?:\d+(?:[.,]\d+)?\s*(?:mg|ml|cc|gotas?|"
                r"tabletas?|pastillas?)|una?\s+dosis)\b|"
                r"\b(?:la\s+)?dosis\s+(?:es|seria|recomendada)\b[^.!?\n]{0,60}\d",
                text,
                re.IGNORECASE,
            )
        )

    def _validate_case_facts(
        self,
        text: str,
        case_facts: list[dict[str, Any]],
        *,
        patient_in_scope: bool = True,
    ) -> ClinicalClaimIssue | None:
        if not case_facts and not patient_in_scope:
            # Educación general sin paciente en alcance: no existe un valor
            # del paciente que una cifra pudiera contradecir, y los rangos de
            # libro son exactamente el contenido pedido — GEN-12 pagó 122-125 s
            # de reparación por unsupported_numeric_claim en las dos baterías
            # rigurosas del 9-ago por decir «37 a 55 %» en una respuesta de
            # libro. Con paciente autorizado la puerta sigue entera aunque el
            # presupuesto haya dejado la lista de hechos vacía.
            return None
        index = temporal_fact_index(case_facts)
        normalized = text.lower()
        if index.by_key and self._all_values_called_normal(normalized, index):
            return ClinicalClaimIssue(
                code="unsupported_status_claim",
                detail="all_values_called_normal",
                claim_text=text[:240],
            )
        latest_facts = {
            code: fact
            for code in index.available_codes
            if (fact := index.latest(code)) is not None
        }
        if latest_facts and self._red_cell_high_called_anemia(
            normalized,
            latest_facts,
        ):
            return ClinicalClaimIssue(
                code="unsupported_status_claim",
                detail="red_cell_high_called_anemia",
                claim_text=text[:240],
            )
        if latest_facts.get("RDW") and "rdw" in normalized:
            if re.search(
                r"\brdw\b.{0,80}\b(inflamacion|infeccion|inflamatorio)\b",
                normalized,
            ):
                return ClinicalClaimIssue(
                    code="unsupported_clinical_interpretation",
                    detail="rdw_used_as_inflammation",
                    parameter_code="RDW",
                    claim_text=text[:240],
                )
        validation = OutputClaimValidator().validate(text, case_facts=case_facts)
        return validation.first_issue

    def _all_values_called_normal(
        self,
        text: str,
        index: ClinicalFactIndex,
    ) -> bool:
        # Do not reject a sentence that explicitly denies the global claim.
        if re.search(r"\bno\s+(?:todos|todas)\b.{0,40}\bnormal", text):
            return False
        for clause in re.split(r"(?<=[.;!?])\s+|\n+", text):
            scoped = self._facts_for_global_clause(clause, index)
            abnormal_facts = [
                (fact.code, fact.status)
                for fact in scoped
                if fact.status in {"high", "low"}
            ]
            if not abnormal_facts:
                continue
            absolute_normality = re.search(
                r"\b(?:todos|todas)\b.{0,70}\b(?:normal|normales|dentro del rango)\b|"
                r"\bning[uú]n valor\b.{0,40}\bfuera del rango\b|"
                r"\b(?:ambos|ambas|estos valores|estas mediciones|los valores|las mediciones)\b"
                r".{0,25}\bdentro\s+de\s+(?:los|sus)\s+rangos\b|"
                r"\bdentro\s+de\s+(?:los|sus)\s+rangos\s+"
                r"(?:normales|de referencia|autorizados)\b",
                clause,
            )
            if absolute_normality and not re.search(
                r"\b(?:salvo|excepto|a excepci[oó]n de)\b",
                absolute_normality.group(0),
            ):
                return True

            no_relevant_findings = re.search(
                r"\b(?:no (?:hay|se observan|muestra)|sin)\b.{0,55}\b"
                r"(?:alteraciones|hallazgos|valores fuera|cambios significativos)\b",
                clause,
            )
            if no_relevant_findings and not any(
                self._acknowledges_abnormal_fact(text, code, status)
                for code, status in abnormal_facts
            ):
                return True
        return False

    @staticmethod
    def _facts_for_global_clause(
        clause: str,
        index: ClinicalFactIndex,
    ) -> tuple[LabFact, ...]:
        studies = list(index.by_study.values())
        if re.search(r"\b(?:estudio\s+)?(?:anterior|previo)\b|\bantes\b", clause):
            return studies[-2] if len(studies) >= 2 else ()
        if re.search(
            r"\b(?:mas\s+reciente|reciente|[uú]ltimo|actual|ahora)\b",
            clause,
        ):
            return studies[-1] if studies else ()
        date = re.search(r"\b20\d{2}-\d{2}-\d{2}\b", clause)
        if date:
            return tuple(
                fact
                for fact in index.by_key.values()
                if fact.study_date.startswith(date.group(0))
            )
        for facts in studies:
            if any(
                fact.study_key
                and re.search(rf"\b{re.escape(fact.study_key.casefold())}\b", clause)
                for fact in facts
            ):
                return facts
        return tuple(index.by_key.values())

    def _acknowledges_abnormal_fact(self, text: str, code: str, status: str) -> bool:
        words = (
            {
                "alto",
                "alta",
                "altos",
                "altas",
                "elevado",
                "elevada",
                "elevados",
                "elevadas",
                "aumentado",
                "aumentada",
                "por encima",
            }
            if status == "high"
            else {
                "bajo",
                "baja",
                "bajos",
                "bajas",
                "disminuido",
                "disminuida",
                "reducido",
                "reducida",
                "por debajo",
            }
        )
        if self._mentions_status(text, code, words):
            return True
        named_statuses = {
            ("WBC", "high"): "leucocitosis",
            ("WBC", "low"): "leucopenia",
            ("NEU", "high"): "neutrofilia",
            ("NEU", "low"): "neutropenia",
            ("LYM", "high"): "linfocitosis",
            ("LYM", "low"): "linfopenia",
            ("MONO", "high"): "monocitosis",
            ("MONO", "low"): "monocitopenia",
            ("EOS", "high"): "eosinofilia",
            ("EOS", "low"): "eosinopenia",
            ("BASO", "high"): "basofilia",
            ("BASO", "low"): "basopenia",
            ("PLT", "high"): "trombocitosis",
            ("PLT", "low"): "trombocitopenia",
        }
        term = named_statuses.get((code, status))
        if not term:
            return False
        return bool(
            re.search(rf"\b{term}\b", text)
            and not re.search(rf"\bno\b.{{0,30}}\b{term}\b", text)
        )

    def _red_cell_high_called_anemia(self, text: str, facts: dict[str, Any]) -> bool:
        if not any(
            facts.get(code) and facts[code].status == "high"
            for code in ("HGB", "HCT", "RBC")
        ):
            return False
        if "anemia" not in text:
            return False
        if re.search(
            r"\b(no corresponde|no es|no indica|no sugiere)\b.{0,60}\banemia\b",
            text,
        ):
            return False
        return bool(
            re.search(
                r"\b(indica|signos de|compatible con|puede indicar|sugiere|"
                r"corresponde a|patron de)\b.{0,80}\banemia\b|"
                r"\banemia\b.{0,80}\b(indica|compatible|sugiere)\b",
                text,
            )
        )

    def _mentions_status(self, text: str, code: str, words: set[str]) -> bool:
        word = r"(?:" + "|".join(re.escape(item) for item in sorted(words)) + r")"
        named_statuses = {
            "WBC": {"leucocitosis", "leucopenia"},
            "NEU": {"neutrofilia", "neutropenia"},
            "LYM": {"linfocitosis", "linfopenia"},
            "MONO": {"monocitosis", "monocitopenia"},
            "EOS": {"eosinofilia", "eosinopenia"},
            "BASO": {"basofilia", "basopenia"},
            "PLT": {"trombocitosis", "trombocitopenia"},
        }
        for term in named_statuses.get(code, set()) & words:
            if re.search(rf"\bno\b.{{0,30}}\b{term}\b", text):
                continue
            if re.search(rf"\b{term}\b", text):
                return True
        for clause in self._parameter_forward_spans(text, code):
            if re.search(rf"\bno\b.{{0,30}}\b{word}\b", clause):
                continue
            if re.search(rf"\b{word}\b", clause):
                return True
        return False

    def _mentions_normal_status(self, text: str, code: str) -> bool:
        alias = self._parameter_alias(code)
        for clause in self._parameter_forward_spans(text, code):
            if re.search(
                rf"\b{alias}\b.{{0,80}}\b(?:dentro|en)\s+(?:de\s+)?(?:su\s+|el\s+)?rango\b",
                clause,
            ):
                return True
            if re.search(
                rf"\b{alias}\b.{{0,40}}\b(?:es|son|est[aá]|est[aá]n|"
                r"se encuentra|se encuentran|permanece|permanecen|resulta|resultan)\b"
                r".{0,18}\bnormal(?:es)?\b",
                clause,
            ):
                return True
            if re.search(rf"\b{alias}\b\s*[:=-]?\s*normal(?:es)?\b", clause):
                return True
            if re.search(
                r"\b(?:ambos|ambas|los dos|las dos)\b.{0,35}\b"
                r"(?:normal(?:es)?|dentro\s+(?:de\s+)?(?:los?\s+)?rangos?)\b",
                clause,
            ):
                return True
        return False

    def _parameter_forward_spans(self, text: str, code: str) -> list[str]:
        """Return text from a parameter mention up to the next parameter/clause.

        A whole sentence may compare several parameters ("NEU alto y PLT bajo").
        Sharing the complete sentence made the status for the second parameter
        look like a contradiction of the first. Forward, parameter-bounded spans
        associate each adjective only with its own measurement.
        """
        alias = self._parameter_alias(code)
        all_matches: list[tuple[int, int]] = []
        for candidate in (
            "WBC",
            "RBC",
            "HGB",
            "HCT",
            "PLT",
            "NEU",
            "LYM",
            "MONO",
            "EOS",
            "BASO",
            "MCV",
            "MCH",
            "MCHC",
            "RDW",
            "MPV",
        ):
            candidate_alias = self._parameter_alias(candidate)
            all_matches.extend(
                (match.start(), match.end())
                for match in re.finditer(rf"\b{candidate_alias}\b", text)
            )
        all_matches.sort()
        spans: list[str] = []
        for match in re.finditer(rf"\b{alias}\b", text):
            endings = [
                position
                for separator in ",;.!?\n"
                for position in [text.find(separator, match.end())]
                if position >= 0
            ]
            endings.extend(start for start, _ in all_matches if start > match.start())
            right = min(endings) if endings else len(text)
            spans.append(text[match.start() : right])
        return spans

    @staticmethod
    def _parameter_alias(code: str) -> str:
        aliases = {
            "WBC": r"(?:wbc|leucocitos?|gl[oó]bulos blancos)",
            "PLT": r"(?:plt|plaquetas?|trombocitos?)",
            "HGB": r"(?:hgb|hemoglobina)",
            "HCT": r"(?:hct|hematocrito)",
            "RBC": r"(?:rbc|eritrocitos?|gl[oó]bulos rojos)",
            "NEU": r"(?:neu|neut|neutr[oó]filos?)",
            "LYM": r"(?:lym|lymph|linfocitos?)",
            "MONO": r"(?:mono|monocitos?)",
            "EOS": r"(?:eos|eosin[oó]filos?)",
            "BASO": r"(?:baso|bas[oó]filos?)",
            "MCV": r"(?:mcv|vcm|volumen corpuscular medio)",
            "MCH": r"(?:mch|hcm|hemoglobina corpuscular media)",
            "MCHC": r"(?:mchc|chcm|concentraci[oó]n de hemoglobina corpuscular)",
            "RDW": r"(?:rdw|ancho de distribuci[oó]n eritrocitaria)",
            "MPV": r"(?:mpv|vpm|volumen plaquetario medio)",
        }
        return aliases.get(code, re.escape(code.lower()))

    def _mentioned_absent_parameter(
        self, text: str, facts: dict[str, Any]
    ) -> str | None:
        aliases = {
            "RBC": r"\b(rbc|eritrocitos?|globulos rojos)\b",
            "HGB": r"\b(hgb|hemoglobina)\b",
            "HCT": r"\b(hct|hematocrito)\b",
            "WBC": r"\b(wbc|leucocitos?|globulos blancos)\b",
            "PLT": r"\b(plt|plaquetas?|trombocitos?)\b",
            "RDW": r"\b(rdw)\b",
        }
        present = set(facts)
        for code, pattern in aliases.items():
            if code not in present and re.search(pattern, text):
                return code
        return None

    def _looks_like_english_answer(self, text: str) -> bool:
        return contains_english_passage(text)
