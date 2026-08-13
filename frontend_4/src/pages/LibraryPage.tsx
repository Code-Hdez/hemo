import { Link } from "@tanstack/react-router";
import { ArrowRight, BookOpen, Search } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { glossaryTerms } from "../domain/glossary";

const categories = [
  "Todos",
  "Serie roja",
  "Serie blanca",
  "Plaquetas",
  "Patrones",
  "Calidad",
] as const;

export function LibraryPage(): React.JSX.Element {
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const [category, setCategory] = useState<(typeof categories)[number]>("Todos");
  const normalized = deferredQuery.trim().toLowerCase();
  const filtered = glossaryTerms.filter(
    (term) =>
      (category === "Todos" || term.category === category) &&
      (!normalized ||
        term.term.toLowerCase().includes(normalized) ||
        term.aliases.some((alias) => alias.toLowerCase().includes(normalized)) ||
        term.short.toLowerCase().includes(normalized)),
  );

  return (
    <div className="library-page page-flow">
      <PageHeader
        eyebrow="Biblioteca hematológica"
        title="Definiciones en lenguaje sencillo"
        description="Consulta términos del CBC y prepara preguntas concretas para tu veterinario."
      />

      <div className="library-tools">
        <label className="search-field" data-tour="biblioteca-buscar">
          <Search size={18} aria-hidden="true" />
          <span className="sr-only">Buscar término</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar leucocitos, HCT, plaquetas..."
          />
        </label>
        <fieldset className="category-tabs">
          <legend className="sr-only">Filtrar por categoría</legend>
          {categories.map((item) => (
            <button
              type="button"
              key={item}
              data-active={category === item}
              onClick={() => setCategory(item)}
            >
              {item}
            </button>
          ))}
        </fieldset>
      </div>

      <div className="definition-list">
        {filtered.map((term) => (
          <Link key={term.slug} to="/biblioteca/$slug" params={{ slug: term.slug }}>
            <span className="definition-list__icon">
              <BookOpen size={19} aria-hidden="true" />
            </span>
            <div>
              <div>
                <h2>{term.term}</h2>
                <span>{term.category}</span>
              </div>
              <p>{term.short}</p>
              <small>{term.aliases.join(" · ")}</small>
            </div>
            <ArrowRight size={18} aria-hidden="true" />
          </Link>
        ))}
        {filtered.length === 0 && (
          <div className="empty-inline">No encontramos una definición con esos filtros.</div>
        )}
      </div>
    </div>
  );
}
