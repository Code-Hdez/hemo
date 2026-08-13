import type { GlossaryTerm } from "./types";

/** Contenido educativo local: el backend aún no expone un contrato de glosario. */
export const glossaryTerms: GlossaryTerm[] = [
  {
    slug: "leucocitos",
    term: "Leucocitos",
    aliases: ["WBC", "glóbulos blancos"],
    category: "Serie blanca",
    short: "Células relacionadas con las defensas y distintas respuestas del organismo.",
    explanation:
      "El conteo total se interpreta junto con los tipos de leucocitos, el estado de la muestra y el contexto clínico.",
    high: "Puede aparecer en inflamación, estrés y otros escenarios que el hemograma por sí solo no distingue.",
    low: "Puede reflejar consumo, menor producción u otras causas que requieren evaluación profesional.",
    ask_vet: "¿Cómo se relaciona este valor con los signos y el examen de mi mascota?",
    related: ["neutrofilos", "patron-inflamatorio"],
  },
  {
    slug: "neutrofilos",
    term: "Neutrófilos",
    aliases: ["NEU"],
    category: "Serie blanca",
    short: "Tipo de leucocito que suele participar en respuestas inflamatorias.",
    explanation:
      "Su cantidad se interpreta junto con el resto del leucograma. Un cambio aislado no identifica una causa concreta.",
    high: "Puede acompañar inflamación o estrés, entre otros procesos.",
    low: "Puede necesitar revisión rápida dependiendo del grado y del estado clínico.",
    ask_vet: "¿El resto del leucograma ayuda a contextualizar este cambio?",
    related: ["leucocitos", "patron-inflamatorio"],
  },
  {
    slug: "hematocrito",
    term: "Hematocrito",
    aliases: ["HCT"],
    category: "Serie roja",
    short: "Porcentaje de sangre ocupado por los glóbulos rojos.",
    explanation:
      "Ayuda a valorar la serie roja junto con eritrocitos, hemoglobina e índices hematimétricos.",
    high: "Puede relacionarse con concentración sanguínea u otros escenarios.",
    low: "Forma parte de la evaluación de patrones anémicos.",
    ask_vet: "¿Los otros valores de la serie roja muestran un patrón coherente?",
    related: ["hemoglobina", "eritrocitos"],
  },
  {
    slug: "hemoglobina",
    term: "Hemoglobina",
    aliases: ["HGB"],
    category: "Serie roja",
    short: "Proteína de los glóbulos rojos que transporta oxígeno.",
    explanation:
      "Se analiza junto con hematocrito, eritrocitos y los índices de tamaño y concentración.",
    ask_vet: "¿Este resultado requiere pruebas complementarias?",
    related: ["hematocrito", "eritrocitos"],
  },
  {
    slug: "eritrocitos",
    term: "Eritrocitos",
    aliases: ["RBC", "glóbulos rojos"],
    category: "Serie roja",
    short: "Células encargadas de transportar oxígeno mediante la hemoglobina.",
    explanation: "Su conteo aislado no define un diagnóstico; debe leerse con HCT, HGB e índices.",
    ask_vet: "¿La serie roja completa sugiere que debo hacer seguimiento?",
    related: ["hematocrito", "hemoglobina"],
  },
  {
    slug: "plaquetas",
    term: "Plaquetas",
    aliases: ["PLT"],
    category: "Plaquetas",
    short: "Fragmentos celulares importantes para la coagulación.",
    explanation:
      "La agrupación de plaquetas puede hacer que el analizador reporte un valor artificialmente bajo.",
    high: "Debe interpretarse con el resto del hemograma y el contexto.",
    low: "Puede requerir confirmación de la muestra y evaluación veterinaria según el grado.",
    ask_vet: "¿El informe menciona agregados o recomienda confirmar el conteo?",
    related: ["agregados-plaquetarios", "frotis-sanguineo"],
  },
  {
    slug: "patron-inflamatorio",
    term: "Patrón inflamatorio",
    aliases: ["respuesta inflamatoria"],
    category: "Patrones",
    short: "Combinación de valores compatible con una respuesta inflamatoria.",
    explanation:
      "Es una señal multivariable. No confirma una infección ni determina por sí sola la causa del cambio.",
    ask_vet: "¿Qué signos o pruebas adicionales permiten contextualizar este patrón?",
    related: ["leucocitos", "neutrofilos"],
  },
  {
    slug: "agregados-plaquetarios",
    term: "Agregados plaquetarios",
    aliases: ["agrupación de plaquetas"],
    category: "Calidad",
    short: "Plaquetas agrupadas que pueden alterar el conteo automatizado.",
    explanation:
      "Es un fenómeno de calidad de muestra. El valor numérico puede subestimar la cantidad real.",
    ask_vet: "¿Conviene revisar el informe original o confirmar la muestra?",
    related: ["plaquetas", "frotis-sanguineo"],
  },
  {
    slug: "frotis-sanguineo",
    term: "Frotis sanguíneo",
    aliases: ["extensión sanguínea"],
    category: "Calidad",
    short: "Preparación microscópica que permite revisar células y artefactos.",
    explanation:
      "HemoVet no procesa imágenes de frotis. Cualquier revisión microscópica corresponde al profesional.",
    ask_vet: "¿La calidad de la muestra justifica una revisión microscópica?",
    related: ["agregados-plaquetarios", "plaquetas"],
  },
  {
    slug: "rangos-de-referencia",
    term: "Rangos de referencia",
    aliases: ["intervalos de referencia"],
    category: "Calidad",
    short: "Intervalos esperados definidos por el laboratorio o instrumento.",
    explanation:
      "Un valor fuera del intervalo no equivale automáticamente a enfermedad y uno dentro del rango no descarta problemas.",
    ask_vet: "¿Qué rango utiliza el laboratorio y cómo aplica a mi mascota?",
    related: ["hematocrito", "leucocitos"],
  },
];

function normalize(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

export function glossarySlugForFinding(label: string): string | undefined {
  const normalized = normalize(label);
  return glossaryTerms.find((term) =>
    [term.term, ...term.aliases].some((candidate) => normalized.includes(normalize(candidate))),
  )?.slug;
}
