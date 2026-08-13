import { Link, useParams } from "@tanstack/react-router";
import { ArrowLeft, ArrowRight, MessageCircleQuestion } from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { glossaryTerms } from "../domain/glossary";

export function DefinitionPage(): React.JSX.Element {
  const { slug } = useParams({ strict: false }) as { slug: string };
  const term = glossaryTerms.find((item) => item.slug === slug);

  if (!term) return <div className="form-error">La definición solicitada no está disponible.</div>;

  return (
    <div className="definition-page page-flow">
      <Link className="back-link" to="/biblioteca">
        <ArrowLeft size={16} aria-hidden="true" /> Volver a la biblioteca
      </Link>
      <PageHeader eyebrow={term.category} title={term.term} description={term.short} />
      <div className="definition-layout">
        <article className="definition-content">
          <section>
            <h2>Qué significa</h2>
            <p>{term.explanation}</p>
          </section>
          {(term.high || term.low) && (
            <div className="definition-comparison">
              {term.high && (
                <section>
                  <span>Cuando está alto</span>
                  <p>{term.high}</p>
                </section>
              )}
              {term.low && (
                <section>
                  <span>Cuando está bajo</span>
                  <p>{term.low}</p>
                </section>
              )}
            </div>
          )}
          <section className="question-prompt">
            <MessageCircleQuestion size={21} aria-hidden="true" />
            <div>
              <span>Pregunta útil para la consulta</span>
              <strong>{term.ask_vet}</strong>
            </div>
          </section>
        </article>
        <aside className="dashboard-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Continuar aprendiendo</p>
              <h2>Términos relacionados</h2>
            </div>
          </div>
          <div className="related-links">
            {term.related.map((related) => {
              const item = glossaryTerms.find((candidate) => candidate.slug === related);
              if (!item) return null;
              return (
                <Link key={item.slug} to="/biblioteca/$slug" params={{ slug: item.slug }}>
                  {item.term} <ArrowRight size={15} />
                </Link>
              );
            })}
          </div>
        </aside>
      </div>
    </div>
  );
}
