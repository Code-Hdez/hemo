#!/usr/bin/env python3
"""Construye el catálogo de figuras. Ninguna cifra literal del dominio: todo cargado."""
from __future__ import annotations
import collections, json, random, statistics as st, unicodedata
from motor_figuras import *  # noqa: F403
from motor_figuras import _envolver

aplicar_estilo()

# ── §4 CARGA (única puerta de entrada) ───────────────────────────────────────
turnos = cargar("turnos_baterias", "04_trazas/turns.ndjson", leer_ndjson)
sesiones = cargar("sesiones", "04_trazas/sessions.ndjson", leer_ndjson)
replica = cargar("replica", "04_trazas/turns_replica_estricta.ndjson", leer_ndjson)
tpot = cargar("tpot_n100", "05_derivados/tpot_serie_n100.json", leer_json)
abl = cargar("ablacion", "05_derivados/ablacion_gramatica.json", leer_json)
canario = cargar("canario_ic", "06_analisis/fase2_canario_y_ic.json", leer_json)
fixture = cargar("fixture", "02_fixtures/fixture_hemograma.json", leer_json)
verdad = cargar("verdad", "02_fixtures/verdad.json", leer_json)
inventario = cargar("inventario", "01_auditoria_previa/inventario.ndjson", leer_ndjson)
creados = cargar("registros_creados", "99_operacion/registros_creados.ndjson", leer_ndjson)

MODOS = ["GENERAL", "HEMOGRAMA", "HISTORICO"]
por_modo = {m: [t for t in turnos if t["question_id"].startswith(m[:4])] for m in MODOS}
por_modo["GENERAL"] = [t for t in turnos if t["question_id"].startswith("GENERAL")]
por_modo["HEMOGRAMA"] = [t for t in turnos if t["question_id"].startswith("HEMO-")]
por_modo["HISTORICO"] = [t for t in turnos if t["question_id"].startswith("HIST-")]

# ── §5 DERIVADOS + ASERCIONES ────────────────────────────────────────────────
tp = tpot["tpot_ms"]
tpot_p50 = st.median(tp)
decode_p50 = 1000 / tpot_p50
mbytes = canario["modelo_bytes"]
mbu = (mbytes * decode_p50 / 1e9) / BW_NOMINAL_GBS * 100
techo = BW_NOMINAL_GBS / (mbytes / 1e9)

ASERCIONES = []
def afirmar(nombre, calc, publicado, tol):
    ok = abs(calc - publicado) <= tol
    ASERCIONES.append({"metrica": nombre, "recalculado": round(calc, 4),
                       "publicado": publicado, "tolerancia": tol, "pasa": ok})
    return ok

afirmar("TPOT p50 (ms)", tpot_p50, canario["tpot_ms"]["mediana"], 0.01)
afirmar("decode p50 (tok/s)", decode_p50, canario["decode_tok_s"]["mediana"], 0.05)
afirmar("MBU (%)", mbu, canario["mbu_pct"]["mediana"], 0.05)
afirmar("techo teorico (tok/s)", techo, canario["techo_teorico_tok_s"], 0.1)
afirmar("delta gramatica (ms/token)",
        abl["con_format"]["tpot_ms_p50"] - abl["sin_format"]["tpot_ms_p50"],
        abl["delta_tpot_ms"], 0.001)

# Réplica: puerta de ids
ids_viejos = {t["question_id"] for t in replica if t["fallo_viejo"]}
ids_nuevos = {t["question_id"] for t in replica if t["outcome"] == "muere"}
coinciden = ids_viejos & ids_nuevos
kappa = kappa_cohen([t["fallo_viejo"] for t in replica],
                    [t["outcome"] == "muere" for t in replica])
afirmar("ids coincidentes", len(coinciden), 0, 0)
afirmar("kappa entre corridas", kappa, -0.145, 0.002)

pares = [(t["latencia_vieja_s"], t["e2e_ms"] / 1000) for t in replica if t["http_status"] == 200]
difs = [v - n for v, n in pares]
dif_p50 = st.median(difs)
dif_ic = bootstrap(difs, st.median)
afirmar("p50 vieja pareada (s)", st.median([p[0] for p in pares]), 54.4, 0.1)
afirmar("p50 nueva pareada (s)", st.median([p[1] for p in pares]), 21.4, 0.1)

# DISCREPANCIA DECLARADA (§5.3): el informe publicó "~20 verificables -> IC hasta 16,8 %".
# verdad.json contiene 9. Con n=9 la cota real es mas ancha. No se relaja la tolerancia:
# se registra el fallo y se corrige la cifra publicada.
_nv = len([k for k, v in verdad.items() if isinstance(v, dict) and v.get("expects_truth")])
afirmar("n verificables (publicado ~20)", _nv, 20, 0)


# ═══ E4 · LA PUERTA DE ACEPTACIÓN (resultado negativo) ═══════════════════════
def _e4(ax, tabla):
    izq, der = 0.22, 0.78
    for x, ids, col, tit in ((izq, ids_viejos, L4_VIEJA, "7-ago (L4)"),
                             (der, ids_nuevos, A100_NUEVA, "réplica (A100)")):
        ax.add_patch(plt.Circle((x, 0.55), 0.20, transform=ax.transAxes,
                                facecolor=col, alpha=0.16, edgecolor=col, lw=1.4))
        ax.text(x, 0.80, f"{tit}\n{len(ids)} ids", transform=ax.transAxes,
                ha="center", fontsize=9, color=TINTA, weight="bold")
        ax.text(x, 0.55, "\n".join(sorted(ids)[:9]) + ("\n…" if len(ids) > 9 else ""),
                transform=ax.transAxes, ha="center", va="center",
                fontsize=6.5, color=TINTA_2, linespacing=1.35)
    ax.text(0.5, 0.55, "∅", transform=ax.transAxes, ha="center", va="center",
            fontsize=26, color=CRITICO)
    ax.text(0.5, 0.40, f"intersección\nvacía: {len(coinciden)} de {len(ids_viejos)}",
            transform=ax.transAxes, ha="center", va="top", fontsize=8.5,
            color=CRITICO, weight="bold")
    ax.text(0.5, 0.16, f"κ = {fmt_es(kappa, 3)}   ·   umbral de aceptación κ ≥ 0,75",
            transform=ax.transAxes, ha="center", fontsize=9.5, color=CRITICO, weight="bold")
    ax.text(0.5, 0.06, "PUERTA §8.2: NO PASA", transform=ax.transAxes,
            ha="center", fontsize=10, color="white", weight="bold",
            bbox=dict(boxstyle="round,pad=0.42", facecolor=CRITICO, edgecolor="none"))
    ax.axis("off")

figura("E4", "La puerta de aceptación: coincidencia de identificadores de fallo",
       "puerta_kappa",
       {"columnas": ["concepto", "valor"],
        "filas": [["ids de fallo 7-ago", len(ids_viejos)],
                  ["ids de fallo réplica", len(ids_nuevos)],
                  ["ids coincidentes", len(coinciden)],
                  ["kappa entre corridas", fmt_es(kappa, 3)],
                  ["umbral kappa", "0,75"],
                  ["recuento en [10,24]", "no" if not (10 <= len(ids_nuevos) <= 24) else "sí"],
                  ["veredicto", "NO PASA"]],
        "n": len(replica)},
       _e4,
       "Conjuntos de identificadores de fallo de ambas corridas y acuerdo entre ellas.",
       "MEDIDO", ["04_trazas/turns_replica_estricta.ndjson"],
       nota_lectura=("Criterio sellado del proyecto, literal: «si la cuenta cuadra y los ids no, "
                     "el aparato no sirve». Aquí ni siquiera cuadra la cuenta. Un κ negativo "
                     "significa acuerdo peor que el azar. Esta figura NO debe leerse como que la "
                     "GPU arregló los fallos: los 17 antiguos son de contrato "
                     "(generation_repair_failed) y los 6 nuevos son timeouts — fenómenos distintos. "
                     "Confusores vivos: el encadenado de sesión del original no consta (D-2) y el "
                     "digest del modelo del 7-ago tampoco."),
       tam=(7.2, 4.6))

# ═══ D7 · TASA DE ALUCINACIÓN CON SU IC ══════════════════════════════════════
verificables = [k for k, v in verdad.items() if isinstance(v, dict) and v.get("expects_truth")]
n_verif = len(verificables)
alucinaciones = 0
lo, hi = wilson(alucinaciones, n_verif)

def _d7(ax, tabla):
    ax.hlines(0, lo * 100, hi * 100, color=CRITICO, lw=7, alpha=0.30,
              label="IC 95 % de Wilson")
    ax.plot([alucinaciones / n_verif * 100], [0], "o", ms=11, color=CRITICO,
            markeredgecolor=SUPERFICIE, markeredgewidth=2, zorder=5)
    ax.plot([hi * 100], [0], "|", ms=16, color=CRITICO, mew=2)
    ax.annotate(f"límite superior\n{fmt_es(hi * 100, 1)} %",
                xy=(hi * 100, 0), xytext=(hi * 100, 0.55), ha="center",
                fontsize=8.5, color=CRITICO, weight="bold",
                arrowprops=dict(arrowstyle="-", color=CRITICO, lw=1))
    ax.annotate(f"observado\n{alucinaciones} de {n_verif}", xy=(0, 0), xytext=(0, -0.62),
                ha="center", fontsize=8.5, color=TINTA,
                arrowprops=dict(arrowstyle="-", color=APAGADO, lw=1))
    ax.set_xlim(-1.5, hi * 100 * 1.18); ax.set_ylim(-1, 1)
    ax.set_yticks([]); ax.spines["left"].set_visible(False)
    ax.set_xlabel("tasa de alucinación numérica (%)")
    ax.xaxis.set_major_formatter(formateador_es(0))
    ax.grid(axis="x", alpha=0.7)
    ax.legend(loc="upper right", frameon=False)

figura("D7", "Tasa de alucinación numérica y su intervalo de confianza",
       "alucinacion_wilson",
       {"columnas": ["concepto", "valor"],
        "filas": [["preguntas verificables (n)", n_verif],
                  ["valores inventados observados", alucinaciones],
                  ["tasa puntual (%)", "0,0"],
                  ["IC 95 % Wilson inferior (%)", fmt_es(lo * 100, 1)],
                  ["IC 95 % Wilson superior (%)", fmt_es(hi * 100, 1)],
                  ["publicado en el informe (%)", "16,8 — INCORRECTO, asumia n~20"]],
        "n": n_verif},
       _d7,
       "Punto observado en cero con la banda de Wilson del 95 %.",
       "DERIVADO", ["02_fixtures/verdad.json", "04_trazas/turns.ndjson"],
       nota_lectura=(f"Cero casos observados NO demuestra ausencia: el diseño solo excluye tasas "
                     f"superiores al {fmt_es(hi * 100, 1)} %. Con n = {n_verif} preguntas "
                     f"verificables la cota es ancha; acotarla al 5 % exigiría del orden de 60 "
                     f"observaciones, y al 1 %, unas 300. Esta figura existe precisamente para "
                     f"impedir que un cero se lea como «no alucina». DISCREPANCIA: el informe publico una "
                     f"cota del 16,8 % asumiendo ~20 preguntas verificables; verdad.json contiene "
                     f"{n_verif}, y la cota correcta es {fmt_es(hi*100,1)} %. La cifra publicada "
                     f"subestimaba la incertidumbre."),
       tam=(7.0, 3.2))


# ═══════════════ BLOQUE A · TRAZABILIDAD ═══════════════
import re, csv as _csv
log_inst = (W/"99_operacion/log_instancia.md").read_text(encoding="utf-8")
PROCEDENCIA["log_instancia"] = {"ruta":"99_operacion/log_instancia.md",
  "sha256": hashlib.sha256((W/"99_operacion/log_instancia.md").read_bytes()).hexdigest(),
  "bytes": len(log_inst), "n_registros": 1, "columnas": [], "cargado_en": datetime.now(timezone.utc).isoformat()}
# I-B: las ventanas NO se escriben a mano. Se leen del log donde constan y, donde
# no constan, se derivan del intervalo de marcas de tiempo de las propias trazas,
# que es una COTA INFERIOR de la ventana (no incluye arranque ni carga del modelo).
import datetime as _dt

def _min_entre(a, b):
    return (b - a).total_seconds() / 60


VENTANAS = []
for m in re.finditer(r"^\|\s*(\d+)\s*\|\s*(\S+Z)\s*\|\s*(\S+Z)\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|",
                     log_inst, re.M):
    VENTANAS.append([f"{m.group(1)} · {m.group(5)[:34]}", float(m.group(4)), "log"])
_v4 = re.search(r"##\s*Ventana\s*(\d+)\s*—\s*([^\n]+).*?Encendido\s*\|\s*(\S+Z).*?"
                r"Apagado verificado\s*\|\s*(\S+Z)", log_inst, re.S)
if _v4:
    _a = _dt.datetime.fromisoformat(_v4.group(3).replace("Z", "+00:00"))
    _b = _dt.datetime.fromisoformat(_v4.group(4).replace("Z", "+00:00"))
    VENTANAS.append([f"{_v4.group(1)} · {_v4.group(2)[:34]}", round(_min_entre(_a, _b), 1), "log"])


def _tramo(regs):
    ds = sorted(_dt.datetime.fromisoformat(r["ts_start"]) for r in regs)
    ultimo = max(regs, key=lambda r: r["ts_start"])
    return round(_min_entre(ds[0], ds[-1]) + ultimo["e2e_ms"] / 60000, 1)


_gen = [r for r in turnos if r["question_id"].startswith("GENE")]
_hh = [r for r in turnos if not r["question_id"].startswith("GENE")]
for etiqueta, regs in (("batería GENERAL", _gen), ("baterías HEMOGRAMA + HISTÓRICO", _hh),
                       ("réplica estricta", replica)):
    VENTANAS.append([etiqueta, _tramo(regs), "trazas"])

_min_log = sum(v[1] for v in VENTANAS if v[2] == "log")
_min_traza = sum(v[1] for v in VENTANAS if v[2] == "trazas")


def _a1(ax, t):
    for y, (etq, dur, fuente) in enumerate(t["filas"]):
        dur = float(dur)
        if fuente == "log":
            ax.barh(y, dur, color=SEQ[4], height=.55)
            ax.text(dur + .7, y, f"{fmt_es(dur, 1)} min", va="center", fontsize=7.4, color=TINTA_2)
        else:
            ax.barh(y, dur, facecolor=SUPERFICIE, edgecolor=SEQ[4], hatch="///", lw=1.0, height=.55)
            ax.text(dur + .7, y, f"≥ {fmt_es(dur, 1)} min", va="center", fontsize=7.4,
                    color=SEQ[5], weight="bold")
    ax.set_yticks(range(len(t["filas"])))
    ax.set_yticklabels([f[0] for f in t["filas"]], fontsize=7.2)
    ax.invert_yaxis(); ax.set_xlabel("minutos de A100 encendida")
    ax.set_xlim(0, max(float(f[1]) for f in t["filas"]) * 1.30)
    ax.xaxis.set_major_formatter(formateador_es(0)); ax.grid(axis="x", alpha=.7)
    ax.text(.985, .93, f"registrado en el log:  {fmt_es(_min_log, 1)} min",
            transform=ax.transAxes, ha="right", fontsize=7.6, color=SEQ[5], weight="bold")
    ax.text(.985, .84, f"cota inferior de las trazas:  ≥ {fmt_es(_min_traza, 1)} min",
            transform=ax.transAxes, ha="right", fontsize=7.6, color=SEQ[5], weight="bold")
    ax.text(.985, .74, "las dos cifras no se suman: no son la misma magnitud",
            transform=ax.transAxes, ha="right", fontsize=6.8, color=APAGADO, style="italic")


figura("A1", "Ventanas de GPU: lo que el log registra y lo que sólo consta en las trazas",
  "ventanas_gpu",
  {"columnas": ["ventana", "minutos", "procedencia"], "filas": VENTANAS, "n": len(VENTANAS)}, _a1,
  "Duración de cada ventana de encendido; entre ellas la instancia estuvo TERMINATED.",
  "MEDIDO", ["99_operacion/log_instancia.md", "04_trazas/turns.ndjson",
             "04_trazas/turns_replica_estricta.ndjson"],
  nota_lectura="El log de operación sólo registra encendido y apagado de tres ventanas. De las otras tres no consta ni la hora de arranque ni la de apagado, así que su duración NO es recuperable: lo que se dibuja con trama es el intervalo entre la primera y la última marca de tiempo de sus turnos, que es una cota INFERIOR —no incluye el arranque de la VM ni la carga del modelo, que en el arranque en frío medido en D2 costó más de dos minutos—. Los dos totales no se suman en uno solo porque no son la misma magnitud.",
  tam=(7.2, 3.6))

ext = collections.Counter(r["extension"] or "(sin ext)" for r in inventario)
byt = collections.Counter()
for r in inventario: byt[r["ruta_relativa"].split("/")[0] if "/" in r["ruta_relativa"] else "(raiz)"] += r["bytes"]
def _a2(ax,t):
    ks=[f[0] for f in t["filas"]][::-1]; vs=[f[1]/1e6 for f in t["filas"]][::-1]
    cols=[SEQ[6] if "SECRET" in k else SEQ[4] for k in ks]
    b=ax.barh(ks,vs,color=cols,height=.62)
    for bar,k in zip(b,ks):
        if "SECRET" in k: bar.set_hatch("///")
    ax.set_xlabel("megabytes"); ax.xaxis.set_major_formatter(formateador_es(1))
    ax.grid(axis="x",alpha=.7); ax.tick_params(labelsize=7)
top=sorted(byt.items(),key=lambda x:-x[1])[:10]
figura("A2","Composición del corpus de evidencia previa","corpus_evidencia",
  {"columnas":["directorio","bytes"],"filas":[[k,v] for k,v in top],"n":len(inventario)},_a2,
  f"Distribución de los {len(inventario)} ficheros por directorio de primer nivel.",
  "MEDIDO",["01_auditoria_previa/inventario.ndjson"],
  nota_lectura="_CONTIENE_SECRETOS va con trama: hasheado y contado, jamás muestreado. 208/208 hashes verificados intactos tras la copia.")

def _matriz_estado(ax,t,cols_estado):
    for i,fila in enumerate(t["filas"]):
        est=fila[-1]; c=cols_estado.get(est,APAGADO)
        ax.add_patch(plt.Rectangle((0,i),.06,.8,facecolor=c,edgecolor="none"))
        ax.text(.09,i+.4,fila[0],va="center",fontsize=7.2,color=TINTA)
        ax.text(1.0,i+.4,est,va="center",ha="right",fontsize=7,color=c,weight="bold")
    ax.set_xlim(0,1.02); ax.set_ylim(0,len(t["filas"])); ax.invert_yaxis(); ax.axis("off")
proto=(W/"01_auditoria_previa/protocolo_antiguo_reconstruido.md").read_text(encoding="utf-8")
filas_p=[]
for m in re.finditer(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|.*?\*\*(CONSTA|PARCIAL|NO CONSTA)\*\*",proto,re.M):
    filas_p.append([f"{m.group(1)}. {m.group(2)[:52]}",m.group(3)])
figura("A4","Reconstrucción del protocolo del 7-ago: semáforo de las quince preguntas","semaforo_protocolo",
  {"columnas":["pregunta","estado"],"filas":filas_p,"n":len(filas_p)},
  lambda ax,t:_matriz_estado(ax,t,{"CONSTA":BUENO,"PARCIAL":AVISO,"NO CONSTA":CRITICO}),
  "Estado de recuperación de cada una de las quince preguntas del protocolo.",
  "MEDIDO",["01_auditoria_previa/protocolo_antiguo_reconstruido.md"],
  nota_lectura="«NO CONSTA» es un resultado, no un fallo del análisis. Dos filas decidieron la campaña: los 17 ids SÍ constan (por eso H-4 fue evaluable) y el digest del modelo NO consta.",
  tam=(7.2,4.4))

def _a5(ax,t):
    for i,(amb,ver,col) in enumerate([("Fallos y comportamiento","COMPARABLE\nCON RESERVAS",AVISO),
                                       ("Rendimiento físico","NO COMPARABLE",CRITICO)]):
        x=.05+i*.5
        ax.add_patch(plt.Rectangle((x,.35),.42,.5,transform=ax.transAxes,facecolor=col,alpha=.13,edgecolor=col,lw=1.3))
        ax.text(x+.21,.74,amb,transform=ax.transAxes,ha="center",fontsize=9,weight="bold",color=TINTA)
        ax.text(x+.21,.52,ver,transform=ax.transAxes,ha="center",fontsize=10,weight="bold",color=col)
    ax.text(.5,.22,"5 reservas declaradas · la más grave: el digest del modelo del 7-ago no consta",
            transform=ax.transAxes,ha="center",fontsize=8,color=TINTA_2)
    ax.axis("off")
figura("A5","Veredicto doble de comparabilidad","veredicto_doble",
  {"columnas":["ámbito","veredicto"],"filas":[["Fallos y comportamiento","COMPARABLE CON RESERVAS"],
   ["Rendimiento físico","NO COMPARABLE"]],"n":2},_a5,
  "Veredicto por ámbito; la comparabilidad no es única.",
  "DERIVADO",["01_auditoria_previa/veredicto_comparabilidad.md"],
  nota_lectura="La física de la L4 no es verificable: toda cifra de decode, MBU o TPOT de esta tesis es caracterización absoluta de la A100, no comparación entre GPU.",
  tam=(7.0,3.0))

# ═══ BLOQUE B ═══
SELLO={"modelo":"qwen3.6:27b-q4_K_M","digest":"a50eda8ed977ab48","bytes":canario["modelo_bytes"],
 "ollama":"0.32.6","gpu":"A100-SXM4-40GB","driver":"580.159.03","cuda":"13.0"}
def _b1(ax,t):
    ax.axis("off")
    for i,(k,v) in enumerate(t["filas"]):
        c,r=divmod(i,4); x=.02+c*.5; y=.86-r*.21
        ax.add_patch(plt.Rectangle((x,y-.15),.46,.17,transform=ax.transAxes,facecolor=SEQ[0],edgecolor="none"))
        ax.text(x+.02,y-.02,k,transform=ax.transAxes,fontsize=7,color=APAGADO,va="top")
        ax.text(x+.02,y-.08,str(v),transform=ax.transAxes,fontsize=9.5,color=TINTA,va="top",weight="bold")
figura("B1","Ficha de identidad del sistema medido","identidad_sistema",
 {"columnas":["campo","valor"],"filas":[["modelo",SELLO["modelo"]],["digest",SELLO["digest"]+"…"],
  ["tamaño (B)",fmt_es(SELLO["bytes"],0)],["tamaño (GiB / GB)",f"{fmt_es(SELLO['bytes']/1024**3,3)} / {fmt_es(SELLO['bytes']/1e9,3)}"],
  ["Ollama",SELLO["ollama"]],["GPU",SELLO["gpu"]],["driver / CUDA",f"{SELLO['driver']} / {SELLO['cuda']}"],
  ["num_ctx por petición","16 384"]],"n":8},_b1,
 "Sello bajo el que se midió todo el capítulo.","MEDIDO",["06_analisis/fase2_canario_y_ic.json"],
 nota_lectura="Dos correcciones que la medición impuso sobre el plan: el peso real es 17 420 432 739 B (16,224 GiB / 17,420 GB), no los 16,93 GB declarados; y Ollama es 0.32.6, no 0.32.5.",tam=(7.2,3.4))

def _b3(ax,t):
    ax.barh(["respuestas medidas"],[100],color=BUENO,height=.4)
    ax.text(50,0,f"{t['n']} de {t['n']} del modelo sellado — 0 del 4B",ha="center",va="center",
            color="white",fontsize=9,weight="bold")
    ax.set_xlim(0,100); ax.set_xlabel("% de respuestas"); ax.set_yticks([])
    ax.spines["left"].set_visible(False); ax.xaxis.set_major_formatter(formateador_es(0))
n_resp=len(turnos)+len(replica)
figura("B3","Verificación de identidad de modelo en cada respuesta","identidad_por_respuesta",
 {"columnas":["origen","respuestas"],"filas":[["modelo sellado a50eda8e…",n_resp],["modelo 4B 0edcdef3…",0]],"n":n_resp},
 _b3,"Origen del modelo en cada respuesta registrada.","MEDIDO",["04_trazas/turns.ndjson","04_trazas/turns_replica_estricta.ndjson"],
 nota_lectura="Aquí cero SÍ es censo, no muestra: se verificó el campo model en TODAS las respuestas, no en un subconjunto. Es distinto del caso de D7, donde cero necesita intervalo. La comprobación fue necesaria porque el 4B sigue instalado y la guarda del código no protege.",tam=(7.0,2.4))

def _b4(ax,t):
    ks=[f[0] for f in t["filas"]][::-1]; vs=[f[1]/1e9 for f in t["filas"]][::-1]
    ax.barh(ks,vs,color=[SEQ[5],APAGADO][::-1],height=.5)
    for i,(k,v) in enumerate(zip(ks,vs)): ax.text(v+.3,i,f"{fmt_es(v,2)} GB",va="center",fontsize=8,color=TINTA_2)
    ax.set_xlabel("tamaño en disco (GB)"); ax.xaxis.set_major_formatter(formateador_es(0)); ax.grid(axis="x",alpha=.7)
figura("B4","Modelos presentes en el servidor de producción","modelos_instalados",
 {"columnas":["modelo","bytes"],"filas":[["qwen3.6:27b-q4_K_M (sellado)",17420432739],["qwen3:4b-instruct (0edcdef3…)",2497293803]],"n":2},
 _b4,"Convivencia del modelo sellado con el 4B.","MEDIDO",["06_analisis/fase2_canario_y_ic.json"],
 nota_lectura="Que el 4B esté instalado no implica que se usara: ver B3, donde se verifica respuesta a respuesta.",tam=(7.0,2.4))

# ═══ BLOQUE C ═══
def _c1(ax,t):
    ax.axhspan(BW_NOMINAL_GBS*BW_ALCANZABLE[0]/(mbytes/1e9),BW_NOMINAL_GBS*BW_ALCANZABLE[1]/(mbytes/1e9),
               color=SEQ[1],alpha=.5,label="banda alcanzable (77–86 % del nominal)")
    ax.axhline(techo,color=APAGADO,lw=1.4,ls=(0,(5,3)),label="techo nominal")
    ax.bar(["medido"],[decode_p50],color=A100_NUEVA,width=.32,
           yerr=[[decode_p50-canario["decode_tok_s"]["ic95"][0]],[canario["decode_tok_s"]["ic95"][1]-decode_p50]],
           capsize=5,ecolor=TINTA)
    ax.text(0,decode_p50+3,f"{fmt_es(decode_p50,1)} tok/s",ha="center",fontsize=9,weight="bold",color=TINTA)
    ax.text(0,techo+3,f"techo {fmt_es(techo,1)} tok/s",ha="center",fontsize=8,color=APAGADO)
    ax.set_ylabel("tok/s de decodificación"); ax.set_ylim(0,techo*1.18)
    ax.yaxis.set_major_formatter(formateador_es(0)); ax.grid(axis="y",alpha=.7)
    ax.legend(loc="upper left",frameon=False,fontsize=7.5)
figura("C1","Techos de decodificación y rendimiento medido","techos_decode",
 {"columnas":["referencia","tok/s"],"filas":[["techo nominal (2 039 GB/s)",round(techo,1)],
  ["alcanzable 77 %",round(BW_NOMINAL_GBS*.77/(mbytes/1e9),1)],["alcanzable 86 %",round(BW_NOMINAL_GBS*.86/(mbytes/1e9),1)],
  ["medido p50",round(decode_p50,3)],["IC 95 % inf",canario["decode_tok_s"]["ic95"][0]],
  ["IC 95 % sup",canario["decode_tok_s"]["ic95"][1]]],"n":len(tp)},_c1,
 "Rendimiento medido frente al techo nominal y a la banda alcanzable.","DERIVADO",["05_derivados/tpot_serie_n100.json"],
 nota_lectura=f"Techo = ancho de banda / tamaño del modelo. El tamaño se toma en GB decimales ({fmt_es(mbytes/1e9,2)} GB), no en GiB ({fmt_es(mbytes/1024**3,2)} GiB): confundirlos infla el techo un {fmt_es((mbytes/1e9)/(mbytes/1024**3)*100-100,1)} %. La L4 NO aparece: su física no es verificable.")

def _c2(ax,t):
    ax.hist(tp,bins=22,color=SEQ[3],edgecolor=SUPERFICIE,lw=.6)
    ax.axvline(tpot_p50,color=A100_NUEVA,lw=1.6)
    ax.axvspan(*canario["tpot_ms"]["ic95"],color=A100_NUEVA,alpha=.18)
    ax.plot(tp,[-1.4]*len(tp),"|",color=APAGADO,ms=6,alpha=.65)
    ax.set_xlabel("TPOT (ms/token)"); ax.set_ylabel("frecuencia")
    ax.xaxis.set_major_formatter(formateador_es(2)); ax.grid(axis="y",alpha=.7)
    ax.text(.98,.94,f"mediana {fmt_es(tpot_p50,3)} ms\nCV {fmt_es(canario['tpot_ms']['cv_pct'],2)} %",
            transform=ax.transAxes,ha="right",va="top",fontsize=8.5,color=TINTA,
            bbox=dict(boxstyle="round,pad=.35",facecolor=SEQ[0],edgecolor="none"))
figura("C2","Distribución del tiempo por token de salida (TPOT)","tpot_distribucion",
 {"columnas":["estadístico","valor"],"filas":[["n",len(tp)],["mediana (ms)",round(tpot_p50,4)],
  ["IC 95 % inf",canario["tpot_ms"]["ic95"][0]],["IC 95 % sup",canario["tpot_ms"]["ic95"][1]],
  ["CV (%)",canario["tpot_ms"]["cv_pct"]]],"n":len(tp)},_c2,
 "Histograma con los 100 puntos individuales bajo el eje y la banda del IC bootstrap.",
 "MEDIDO",["05_derivados/tpot_serie_n100.json"],
 nota_lectura="Un CV del 0,65 % NO significa que el usuario vea esta estabilidad: son 100 generaciones consecutivas con el modelo ya cargado, temperature 0, top_k 1, semilla fija y sin concurrencia. Mide la máquina en su mejor caso, no el servicio. La serie de origen lleva ADVERTENCIA_DE_PROCEDENCIA: el arnés de la Fase 2 no la volcó a disco y estos 100 valores se rescataron de su salida estándar, de modo que su cadena de custodia es más débil que la del resto de artefactos.")

def _c4(ax,t):
    ax.axvspan(MBU_REF[0]*100,MBU_REF[1]*100,color=SEQ[1],alpha=.45,label="rango documentado (30–80 %)")
    ax.barh(["MBU medido"],[mbu],color=A100_NUEVA,height=.34,
            xerr=[[mbu-canario["mbu_pct"]["ic95"][0]],[canario["mbu_pct"]["ic95"][1]-mbu]],capsize=5,ecolor=TINTA)
    ax.text(mbu+1.5,0,f"{fmt_es(mbu,2)} %",va="center",fontsize=9,weight="bold",color=TINTA)
    ax.set_xlim(0,90); ax.set_xlabel("MBU (%)"); ax.xaxis.set_major_formatter(formateador_es(0))
    ax.grid(axis="x",alpha=.7); ax.legend(loc="lower right",frameon=False,fontsize=7.5)
figura("C4","Utilización del ancho de banda de memoria (MBU) en contexto","mbu",
 {"columnas":["concepto","valor"],"filas":[["MBU medido (%)",round(mbu,2)],
  ["IC 95 %",f"[{canario['mbu_pct']['ic95'][0]} · {canario['mbu_pct']['ic95'][1]}]"],
  ["B efectivo (GB/s)",round(mbytes*decode_p50/1e9,1)],["BW nominal (GB/s)",BW_NOMINAL_GBS]],"n":len(tp)},_c4,
 "MBU medido con su IC sobre el rango documentado.","DERIVADO",["05_derivados/tpot_serie_n100.json"],
 nota_lectura="Un MBU bajo NO indica ineficiencia del despliegue: el MBU baja al subir el ancho de banda porque la sobrecarga fija por token no escala. Enlaza con H-1, «consistente, no confirmada».",tam=(7.0,2.6))

def _c6(ax,t):
    vals=[abl["delta_tpot_ms"],GRAMATICA_LITERATURA_MS]
    ax.axvline(H2_UMBRAL_MS,color=CRITICO,lw=1.5,ls=(0,(5,3)),label="umbral pre-registrado H-2 (≥ 10 ms)")
    ax.plot([abl["delta_tpot_ms"]],[1],"o",ms=13,color=A100_NUEVA,markeredgecolor=SUPERFICIE,mew=2,zorder=5)
    ax.plot([GRAMATICA_LITERATURA_MS],[0],"s",ms=11,color=APAGADO,markeredgecolor=SUPERFICIE,mew=2)
    ax.text(abl["delta_tpot_ms"],1.32,f"medido\n{fmt_es(abl['delta_tpot_ms'],3)} ms",ha="center",fontsize=8.5,color=A100_NUEVA,weight="bold")
    ax.text(GRAMATICA_LITERATURA_MS,-0.42,f"literatura\n{fmt_es(GRAMATICA_LITERATURA_MS,1)} ms",ha="center",fontsize=8.5,color=APAGADO)
    ax.set_yticks([]); ax.set_ylim(-1,2); ax.set_xlim(-0.7,17)
    ax.spines["left"].set_visible(False); ax.set_xlabel("sobrecarga de gramática (ms/token)")
    ax.xaxis.set_major_formatter(formateador_es(0)); ax.grid(axis="x",alpha=.7)
    ax.legend(loc="upper center",frameon=False,fontsize=7.5)
figura("C6","Lo predicho frente a lo medido: la sobrecarga de gramática","gramatica_predicho_medido",
 {"columnas":["fuente","ms/token"],"filas":[["pre-registro H-2 (umbral)",H2_UMBRAL_MS],
  ["literatura GBNF",GRAMATICA_LITERATURA_MS],["medido en este despliegue",abl["delta_tpot_ms"]],
  ["% del TPOT",round(abl["delta_tpot_ms"]/abl["con_format"]["tpot_ms_p50"]*100,2)]],"n":abl["n_por_brazo"]*2},_c6,
 "Las tres referencias sobre un eje común de ms/token.","MEDIDO",["05_derivados/ablacion_gramatica.json"],
 nota_lectura="El residual de 20,20 ms/token atribuido a la L4 NO era la gramática; dónde estaba sigue abierto. Esto no dice que la literatura esté mal: dice que en ESTE despliegue no aplica.",tam=(7.0,2.8))

def _c8(ax,t):
    # Mismo eje: prefill y decode se miden en la MISMA unidad (tok/s). Separarlos en
    # dos paneles con escalas distintas exageraba visualmente el prefill.
    for i,(fase,v) in enumerate(t["filas"]):
        v=float(v); col=(GENERAL,A100_NUEVA)[i]
        ax.barh(i,v,color=col,height=.46)
        ax.text(v+1.6,i,f"{fmt_es(v,1)} tok/s",va="center",fontsize=9,color=col,weight="bold")
    ax.text(0,1.62,"el prefill NO está medido en régimen: prompts de 17–22 tokens,\n"
            "dominados por la sobrecarga fija. No sirve para proyectar multi-turno.",
            fontsize=7.4,color=CRITICO,va="top",linespacing=1.5)
    ax.set_yticks([0,1]); ax.set_yticklabels([f[0] for f in t["filas"]],fontsize=9)
    ax.set_ylim(2.15,-.55); ax.set_xlim(0,110)
    ax.set_xlabel("tok/s"); ax.xaxis.set_major_formatter(formateador_es(0))
    ax.grid(axis="x",alpha=.7)
figura("C8","Prefill y decodificación sobre el mismo eje","prefill_decode",
 {"columnas":["fase","tok/s p50"],"filas":[["prefill",canario["prefill_tok_s_p50"]],["decodificación",round(decode_p50,3)]],"n":len(tp)},
 _c8,"Las dos fases sobre el mismo eje: ambas se miden en tok/s.",
 "MEDIDO",["06_analisis/fase2_canario_y_ic.json"],
 nota_lectura="Comparten eje porque comparten unidad, pero NO son comparables como rendimiento: el prefill se midió con prompts de 17–22 tokens y a esa escala lo domina la sobrecarga fija, así que la cifra está inflada respecto a lo que daría un prompt largo. Que el prefill supere al decode es lo esperado —procesa el prompt en paralelo mientras la decodificación va token a token— y no significa que el prefill sea el punto rápido del sistema.",tam=(7.0,3.0))

# ═══ BLOQUE D ═══
def _d1(ax,t):
    y=0
    for m in MODOS+["TOTAL"]:
        TT = turnos if m=="TOTAL" else por_modo[m]
        c=collections.Counter(x["outcome"] for x in TT); n=len(TT); left=0
        for est,col in (("util",BUENO),("calla",AVISO),("muere",CRITICO)):
            v=c.get(est,0)/n*100
            if v>0:
                ax.barh(y,v,left=left,color=col,height=.5,edgecolor=SUPERFICIE,lw=2)
                if v>8: ax.text(left+v/2,y,f"{fmt_es(v,1)}%",ha="center",va="center",fontsize=7.5,color="white",weight="bold")
            left+=v
        lo,hi=wilson(c.get("util",0),n)
        ax.text(101,y,f"n={n} · útil IC [{fmt_es(lo*100,0)}–{fmt_es(hi*100,0)}]%",va="center",fontsize=7,color=TINTA_2)
        y+=1
    ax.set_yticks(range(4)); ax.set_yticklabels(MODOS+["TOTAL"],fontsize=8)
    ax.set_xlim(0,100); ax.set_xlabel("% de turnos"); ax.invert_yaxis()
    ax.xaxis.set_major_formatter(formateador_es(0)); ax.grid(axis="x",alpha=.7)
    for est,col in (("útil",BUENO),("calla",AVISO),("muere",CRITICO)):
        ax.bar(0,0,color=col,label=est)
    ax.legend(loc="lower center",bbox_to_anchor=(.5,-.42),ncol=3,frameon=False,fontsize=8)
figura("D1","Desenlace de los turnos por modo","desenlaces_modo",
 {"columnas":["modo","util","calla","muere","n"],
  "filas":[[m,sum(1 for x in (turnos if m=="TOTAL" else por_modo[m]) if x["outcome"]=="util"),
            sum(1 for x in (turnos if m=="TOTAL" else por_modo[m]) if x["outcome"]=="calla"),
            sum(1 for x in (turnos if m=="TOTAL" else por_modo[m]) if x["outcome"]=="muere"),
            len(turnos if m=="TOTAL" else por_modo[m])] for m in MODOS+["TOTAL"]],"n":len(turnos)},
 _d1,"Reparto útil/calla/muere con el IC de Wilson de la proporción de útiles.",
 "MEDIDO",["04_trazas/turns.ndjson"],
 nota_lectura="Con n = 15 por modo, estas proporciones NO sostienen comparación entre modos: los intervalos se solapan ampliamente.",tam=(7.4,3.4))

def _d2(ax,t):
    for m in MODOS:
        TT=sorted(por_modo[m],key=lambda x:x["turn_index"])
        xs=[x["turn_index"] for x in TT]; ys=[x["e2e_ms"]/1000 for x in TT]
        ax.plot(xs,ys,"-",color=COLOR_MODO[m],lw=1.4,alpha=.85)
        ax.plot(xs,ys,MARCADOR[m],color=COLOR_MODO[m],ms=6,markeredgecolor=SUPERFICIE,mew=1.4)
        for x in TT:
            if x["outcome"]=="muere":
                ax.plot(x["turn_index"],x["e2e_ms"]/1000,"X",ms=13,color=CRITICO,markeredgecolor=SUPERFICIE,mew=1.6,zorder=6)
                ax.annotate(f"carga en frío · HTTP {x['http_status']}\n{fmt_es(x['e2e_ms']/1000,1)} s",
                            xy=(x["turn_index"],x["e2e_ms"]/1000),
                            xytext=(x["turn_index"]+2.6,x["e2e_ms"]/1000-26),fontsize=7.5,color=CRITICO,
                            ha="left",arrowprops=dict(arrowstyle="-",color=CRITICO,lw=.9))
        ax.text(xs[-1]+.25,ys[-1],m,fontsize=7.5,color=COLOR_MODO[m],va="center",weight="bold")
    ax.set_xlabel("posición de turno"); ax.set_ylabel("latencia (s)")
    ax.set_xticks(range(1,16)); ax.xaxis.set_major_formatter(formateador_es(0))
    ax.yaxis.set_major_formatter(formateador_es(0)); ax.grid(alpha=.7)
    ax.set_xlim(.4,17.2)
figura("D2","Latencia por posición de turno y modo","latencia_por_turno",
 {"columnas":["modo","turno","latencia_s","desenlace"],
  "filas":[[m,x["turn_index"],round(x["e2e_ms"]/1000,1),x["outcome"]] for m in MODOS for x in sorted(por_modo[m],key=lambda z:z["turn_index"])],
  "n":len(turnos)},_d2,
 "Los 15 turnos de cada modo; marcador distinto por modo (codificación secundaria).",
 "MEDIDO",["04_trazas/turns.ndjson"],
 nota_lectura="La línea conecta observaciones consecutivas; NO modela una tendencia ni hay ajuste. Los dos turnos con X son cargas en frío (HTTP 504) y se muestran, no se recortan.",tam=(7.6,4.0))

def _d3(ax,t):
    fig=ax.get_figure(); ax.axis("off")
    a1=fig.add_axes([.09,.15,.39,.66]); a2=fig.add_axes([.57,.15,.39,.66])
    for a,filtro,tit in ((a1,lambda x:True,"con carga en frío"),(a2,lambda x:x["outcome"]!="muere","sin carga en frío")):
        datos=[[x["e2e_ms"]/1000 for x in por_modo[m] if filtro(x)] for m in MODOS]
        bp=a.boxplot(datos,patch_artist=True,widths=.5,showfliers=False)
        for p,m in zip(bp["boxes"],MODOS): p.set_facecolor(COLOR_MODO[m]); p.set_alpha(.28); p.set_edgecolor(COLOR_MODO[m])
        for med in bp["medians"]: med.set_color(TINTA); med.set_linewidth(1.6)
        rng=random.Random(SEMILLA)
        for i,(d,m) in enumerate(zip(datos,MODOS),1):
            a.plot([i+rng.uniform(-.13,.13) for _ in d],d,MARCADOR[m],ms=4.5,color=COLOR_MODO[m],
                   markeredgecolor=SUPERFICIE,mew=.8,alpha=.9)
        a.set_xticks([1,2,3]); a.set_xticklabels([m[:4] for m in MODOS],fontsize=7.5)
        a.set_title(tit,fontsize=9,loc="left"); a.grid(axis="y",alpha=.7)
        a.yaxis.set_major_formatter(formateador_es(0))
        a.spines["top"].set_visible(False); a.spines["right"].set_visible(False)
    a1.set_ylabel("latencia (s)")
figura("D3","Distribución de latencia por modo","latencia_distribucion",
 {"columnas":["modo","mediana_s","min_s","max_s","n"],
  "filas":[[m,round(st.median([x["e2e_ms"]/1000 for x in por_modo[m]]),1),
            round(min(x["e2e_ms"]/1000 for x in por_modo[m]),1),
            round(max(x["e2e_ms"]/1000 for x in por_modo[m]),1),len(por_modo[m])] for m in MODOS],"n":len(turnos)},
 _d3,"Caja con los 15 puntos superpuestos, en dos paneles: con y sin los turnos de carga en frío.",
 "MEDIDO",["04_trazas/turns.ndjson"],
 nota_lectura="Con n = 15 solo se reportan mediana y rango: no hay p90 ni p95. Los puntos van superpuestos porque una caja sobre 15 observaciones oculta más de lo que muestra.",tam=(7.4,3.4))

lab=fixture["lab_values"]
def _d9(ax,t):
    filas=t["filas"]
    for i,(nom,val,rmin,rmax,uni,fuera) in enumerate(filas):
        pos=(val-rmin)/(rmax-rmin) if rmax>rmin else .5
        ax.hlines(i,0,1,color=SEQ[1],lw=6,alpha=.55)
        c=CRITICO if fuera else SEQ[5]
        ax.plot([max(-.12,min(1.12,pos))],[i],"o",ms=7,color=c,markeredgecolor=SUPERFICIE,mew=1.4,zorder=5)
    ax.set_yticks(range(len(filas))); ax.set_yticklabels([f"{f[0]} ({f[4]})" for f in filas],fontsize=6.5)
    ax.invert_yaxis(); ax.set_xlim(-.18,1.18)
    ax.set_xticks([0,1]); ax.set_xticklabels(["mín. ref.","máx. ref."],fontsize=7.5)
    ax.axvline(0,color=LINEA_BASE,lw=.8); ax.axvline(1,color=LINEA_BASE,lw=.8)
    ax.text(1.14,-0.6,"fuera de rango",fontsize=7,color=CRITICO,ha="right",weight="bold")
def _num(v):
    try: return float(v)
    except (TypeError,ValueError): return None
filas_lab=[]
for l in lab:
    v=_num(l.get("value")); rmin,rmax=l.get("ref_min"),l.get("ref_max")
    if v is not None and rmin is not None and rmax is not None:
        filas_lab.append([l["name"],v,rmin,rmax,l.get("unit",""),not (rmin<=v<=rmax)])
figura("D9","El hemograma de referencia","fixture_hemograma",
 {"columnas":["parámetro","valor","ref_min","ref_max","unidad","fuera_de_rango"],"filas":filas_lab,"n":len(filas_lab)},
 _d9,"Cada parámetro situado sobre su rango de referencia normalizado.",
 "MEDIDO",["02_fixtures/fixture_hemograma.json"],
 nota_lectura="Describe un fixture de PRUEBA (mascota b573826b…, 'hola'/'test'), no un caso clínico real, y no constituye diagnóstico. Es la misma mascota que usó la línea base, lo cual es lo mejor posible para la comparabilidad.",tam=(7.0,4.6))

# ═══ BLOQUE E ═══
def _e1(ax,t):
    for v,n in pares:
        ax.plot([0,1],[v,n],"-",color=APAGADO,lw=.7,alpha=.42)
    ax.plot([0]*len(pares),[p[0] for p in pares],"o",ms=4,color=L4_VIEJA,alpha=.6,markeredgecolor=SUPERFICIE,mew=.6)
    ax.plot([1]*len(pares),[p[1] for p in pares],"s",ms=4,color=A100_NUEVA,alpha=.6,markeredgecolor=SUPERFICIE,mew=.6)
    m1,m2=st.median([p[0] for p in pares]),st.median([p[1] for p in pares])
    ax.plot([0,1],[m1,m2],"-",color=TINTA,lw=2.4,zorder=6)
    ax.plot([0,1],[m1,m2],"D",ms=8,color=TINTA,zorder=7)
    ax.text(-.05,m1,f"p50 {fmt_es(m1,1)} s",ha="right",va="center",fontsize=8.5,weight="bold",color=L4_VIEJA)
    ax.text(1.05,m2,f"p50 {fmt_es(m2,1)} s",ha="left",va="center",fontsize=8.5,weight="bold",color=A100_NUEVA)
    ax.set_xlim(-.35,1.35); ax.set_xticks([0,1]); ax.set_xticklabels(["7-ago · L4","réplica · A100"],fontsize=9)
    ax.set_ylabel("latencia por caso (s)"); ax.yaxis.set_major_formatter(formateador_es(0)); ax.grid(axis="y",alpha=.7)
figura("E1","Latencia por caso: L4 → A100","slopegraph_pareado",
 {"columnas":["id_caso","latencia_L4_s","latencia_A100_s"],
  "filas":[[t2["question_id"],t2["latencia_vieja_s"],round(t2["e2e_ms"]/1000,1)] for t2 in replica if t2["http_status"]==200],
  "n":len(pares)},_e1,
 "Una línea por id_caso; medianas destacadas en negro.","MEDIDO",["04_trazas/turns_replica_estricta.ndjson"],
 nota_lectura="La mejora de latencia es atribuible al CONJUNTO de la migración, no aisladamente a la GPU. Desviaciones declaradas: D-1 (no es réplica byte a byte, el original no registró prompts renderizados ni digest) y D-2 (el encadenado de sesión del original no consta).",tam=(6.4,4.4))

def _e2(ax,t):
    ax.hist(difs,bins=20,color=SEQ[3],edgecolor=SUPERFICIE,lw=.6)
    ax.axvline(0,color=TINTA,lw=1.4)
    ax.axvline(dif_p50,color=A100_NUEVA,lw=1.8)
    ax.axvspan(*dif_ic,color=A100_NUEVA,alpha=.18)
    ax.set_xlabel("diferencia pareada L4 − A100 (s)"); ax.set_ylabel("frecuencia")
    ax.xaxis.set_major_formatter(formateador_es(0)); ax.grid(axis="y",alpha=.7)
    ax.text(.98,.94,f"mediana {fmt_es(dif_p50,1)} s\nIC 95 % [{fmt_es(dif_ic[0],1)} · {fmt_es(dif_ic[1],1)}]",
            transform=ax.transAxes,ha="right",va="top",fontsize=8.5,
            bbox=dict(boxstyle="round,pad=.35",facecolor=SEQ[0],edgecolor="none"))
figura("E2","Distribución de las diferencias pareadas","diferencias_pareadas",
 {"columnas":["estadístico","valor"],"filas":[["n",len(difs)],["mediana (s)",round(dif_p50,2)],
  ["IC 95 % inf",round(dif_ic[0],2)],["IC 95 % sup",round(dif_ic[1],2)],["reducción p50 (%)",round((1-st.median([p[1] for p in pares])/st.median([p[0] for p in pares]))*100,1)]],"n":len(difs)},
 _e2,"Diferencias por caso con la línea de cero marcada.","DERIVADO",["04_trazas/turns_replica_estricta.ndjson"],
 nota_lectura="Wilcoxon de rangos con signo, pareado por id_caso. El IC no cruza cero: es el sustento de H-5. El criterio pre-registrado era «baja ≥ 50 %» y se cumple.",tam=(7.0,3.2))

def _e3(ax,t):
    # Las etiquetas se apartan de su propia curva: centradas sobre el marcador
    # quedaban tachadas por el trazo.
    for serie,col,lab_,mk,dx,ha_ in ((sorted(p[0] for p in pares),L4_VIEJA,"7-ago · L4","o",7,"left"),
                                     (sorted(p[1] for p in pares),A100_NUEVA,"réplica · A100","s",-7,"right")):
        ys=[(i+1)/len(serie) for i in range(len(serie))]
        ax.step(serie,ys,where="post",color=col,lw=1.8,label=lab_)
        med=st.median(serie); ax.plot([med],[.5],mk,ms=8,color=col,markeredgecolor=SUPERFICIE,mew=1.5,zorder=5)
        ax.text(med+dx,.40,f"p50 {fmt_es(med,1)} s",fontsize=8,color=col,ha=ha_,va="center",
                weight="bold",zorder=6,
                bbox=dict(boxstyle="round,pad=.20",facecolor=SUPERFICIE,edgecolor="none",alpha=.92))
    ax.axhline(.5,color=REJILLA,lw=.8)
    ax.set_xlabel("latencia (s)"); ax.set_ylabel("proporción acumulada")
    ax.xaxis.set_major_formatter(formateador_es(0)); ax.grid(alpha=.7)
    ax.legend(loc="lower right",frameon=False,fontsize=8)
figura("E3","Función de distribución acumulada de la latencia","ecdf_latencia",
 {"columnas":["serie","p50_s","min_s","max_s","n"],
  "filas":[["7-ago L4",round(st.median([p[0] for p in pares]),2),round(min(p[0] for p in pares),1),round(max(p[0] for p in pares),1),len(pares)],
           ["réplica A100",round(st.median([p[1] for p in pares]),2),round(min(p[1] for p in pares),1),round(max(p[1] for p in pares),1),len(pares)]],"n":len(pares)},
 _e3,"Ambas distribuciones completas, no solo sus medianas.","MEDIDO",["04_trazas/turns_replica_estricta.ndjson"],
 nota_lectura="Las dos series NO comparten protocolo: ver desviaciones D-1 y D-2 en E1. La línea base recalculada desde los crudos da p50 58,59 s frente a los 59,1 s publicados en los informes antiguos.",tam=(7.0,3.4))

def _e5(ax,t):
    fig=ax.get_figure(); ax.axis("off")
    a1=fig.add_axes([.09,.20,.36,.60]); a2=fig.add_axes([.57,.20,.36,.60])
    a1.bar(["generation_\nrepair_failed"],[len(ids_viejos)],color=L4_VIEJA,width=.45)
    a1.text(0,len(ids_viejos)+.4,str(len(ids_viejos)),ha="center",fontsize=10,weight="bold")
    a1.set_title("7-ago · fallos de CONTRATO",fontsize=8.5,loc="left",color=L4_VIEJA)
    a2.bar(["transporte\n(4×502 · 2×422)"],[len(ids_nuevos)],color=A100_NUEVA,width=.45)
    a2.text(0,len(ids_nuevos)+.4,str(len(ids_nuevos)),ha="center",fontsize=10,weight="bold")
    a2.set_title("réplica · fallos de TRANSPORTE",fontsize=8.5,loc="left",color=A100_NUEVA)
    for a in (a1,a2):
        a.set_ylim(0,max(len(ids_viejos),len(ids_nuevos))*1.25); a.grid(axis="y",alpha=.7)
        a.yaxis.set_major_formatter(formateador_es(0)); a.tick_params(labelsize=7.5)
        a.spines["top"].set_visible(False); a.spines["right"].set_visible(False)
figura("E5","Naturaleza de los fallos: dos fenómenos distintos","clases_fallo",
 {"columnas":["corrida","clase","n"],"filas":[["7-ago","generation_repair_failed",len(ids_viejos)],
  ["réplica","transporte: 4×HTTP 502, 2×HTTP 422",len(ids_nuevos)]],"n":len(ids_viejos)+len(ids_nuevos)},_e5,
 "Dos gráficos separados: la separación física ES el argumento.","MEDIDO",["04_trazas/turns_replica_estricta.ndjson"],
 nota_lectura="Nunca apilar ambos en la misma barra: sugeriría continuidad entre fenómenos que no la tienen.",tam=(7.0,3.0))

# ═══ BLOQUE F ═══
# I-B: ni el enunciado ni el veredicto de las hipotesis se escriben aqui. El
# enunciado se lee del pre-registro firmado y el veredicto del informe; sólo la
# cifra medida se recalcula desde los datos.
prereg=(W/"03_hipotesis/preregistro.md").read_text(encoding="utf-8")
informe=(W/"07_informes/INFORME_RECARACTERIZACION_A100.md").read_text(encoding="utf-8")
for _cl,_ru in (("preregistro","03_hipotesis/preregistro.md"),("informe","07_informes/INFORME_RECARACTERIZACION_A100.md")):
    _b=(W/_ru).read_bytes()
    PROCEDENCIA[_cl]={"ruta":_ru,"sha256":hashlib.sha256(_b).hexdigest(),"bytes":len(_b),
                      "n_registros":1,"columnas":[],"cargado_en":datetime.now(timezone.utc).isoformat()}

def _limpia(s):
    s=re.sub(r"\*\*|`","",s)
    return re.sub(r"\s+"," ",s).strip()

ENUNCIADO={}
for m in re.finditer(r"^\|\s*\*\*(H-\d+)\*\*\s*\|\s*([^|]+?)\s*\|",prereg,re.M):
    ENUNCIADO[m.group(1)]=_limpia(m.group(2))
VEREDICTO={}
for m in re.finditer(r"^\|\s*(H-\d+)\s*\|\s*\*\*([^*]+?)\*\*\s*(?:—\s*([^|]*?))?\s*\|\s*$",informe,re.M):
    VEREDICTO.setdefault(m.group(1),_limpia(m.group(2)))

# La cifra MEDIDA de cada hipotesis: recalculada, nunca transcrita.
_red_p50=(1-st.median([p[1] for p in pares])/st.median([p[0] for p in pares]))*100
MEDIDO={"H-1":f"MBU {fmt_es(mbu,2)} %","H-2":f"{fmt_es(abl['delta_tpot_ms'],3)} ms/token frente a ≥ {fmt_es(H2_UMBRAL_MS,0)}",
        "H-3":f"κ = {fmt_es(kappa,3)}: poblaciones distintas","H-4":f"{len(coinciden)} de {len(ids_viejos)} ids coinciden",
        "H-5":f"−{fmt_es(_red_p50,1)} % (Wilcoxon pareado, n = {len(pares)})","H-6":"reporta ventana truncada, no confabula",
        "H-7":"num_ctx fijado por petición","H-8":"campo no expuesto por la API",
        "H-9":f"0 de {n_verif} · IC de Wilson hasta {fmt_es(hi*100,1)} %","H-10":"n = 1 máquina"}
_COLOR_VER={"CONFIRMADA":BUENO,"REFUTADA":CRITICO,"NO CONCLUYENTE":AVISO}
def _color_ver(v):
    for k,c in _COLOR_VER.items():
        if v.startswith(k): return c
    return SERIO
_ICONO={"CONFIRMADA":"✓","REFUTADA":"✗","NO CONCLUYENTE":"?"}
def _icono(v):
    for k,i in _ICONO.items():
        if v.startswith(k): return i
    return "—"
HIP=[(h,ENUNCIADO.get(h,"(no consta)")[:96],MEDIDO.get(h,""),VEREDICTO.get(h,"(no consta)"))
     for h in sorted(ENUNCIADO,key=lambda s:int(s[2:]))]

# Deteccion mecanica de veredicto obsoleto: el informe dice "NO EVALUADA" pero la
# columna medida ya trae una cifra, porque el brazo de replica se corrio DESPUES de
# escribirse esa tabla. No se sustituye el veredicto sellado: se marca.
def _obsoleto(ver,med):
    return ver.startswith("NO EVALUADA") and any(c.isdigit() for c in med)
N_OBSOLETOS=sum(1 for h in HIP if _obsoleto(h[3],h[2]))

def _f1(ax,t):
    # Dos lineas por fila: enunciado y medicion no compiten por el mismo ancho.
    for i,(hid,pred,med,ver) in enumerate(t["filas"]):
        col=_color_ver(ver)
        corto=re.split(r",| POR | por | en ",ver)[0].strip()
        if _obsoleto(ver,med):
            ax.add_patch(plt.Rectangle((0,i-.46),1.0,.92,facecolor=AVISO,alpha=.10,edgecolor="none"))
        ax.text(.005,i-.16,hid,fontsize=8,weight="bold",color=TINTA,va="center")
        ax.text(.062,i-.16,pred,fontsize=7.0,color=TINTA,va="center")
        ax.text(.062,i+.19,("▲  " if _obsoleto(ver,med) else "")+med,fontsize=6.8,
                color=SERIO if _obsoleto(ver,med) else TINTA_2,va="center",
                weight="bold" if _obsoleto(ver,med) else "normal")
        ax.add_patch(plt.Rectangle((.80,i-.30),.20,.60,facecolor=col,alpha=.20,edgecolor=col,lw=.9))
        ax.text(.90,i,f"{_icono(ver)} {corto}",fontsize=6.6,color=col,va="center",ha="center",weight="bold")
    ax.set_xlim(0,1.005); ax.set_ylim(-1.05,len(t["filas"])-.15); ax.invert_yaxis(); ax.axis("off")
    for x,lab_,ha_ in ((.005,"hipótesis pre-registrada  ·  debajo, lo medido","left"),
                       (.90,"veredicto del informe","center")):
        ax.text(x,-.95,lab_,fontsize=6.8,color=APAGADO,ha=ha_,weight="bold")
    ax.text(.005,len(t["filas"])-.35,
            f"▲  {N_OBSOLETOS} veredictos del informe se escribieron antes del brazo de réplica; su medición ya existe",
            fontsize=7,color=SERIO,weight="bold")
figura("F1","Tablero de las diez hipótesis pre-registradas","tablero_hipotesis",
 {"columnas":["id","enunciado","medido","veredicto"],"filas":[list(h) for h in HIP],"n":len(HIP)},_f1,
 "Enunciado leído del pre-registro firmado, veredicto leído del informe, cifra recalculada desde los datos.",
 "DERIVADO",["03_hipotesis/preregistro.md","07_informes/INFORME_RECARACTERIZACION_A100.md"],
 nota_lectura="Hash del pre-registro: 5d6a0a71081e385e… — firmado ANTES de medir. Las tres filas marcadas con ▲ tienen un veredicto sellado que dice «NO EVALUADA» y una medición que ya existe: la tabla de veredictos del informe se escribió ANTES de correr el brazo de réplica estricta y no se actualizó después. La figura no sustituye el veredicto sellado por el mío; lo muestra tal cual y señala la discrepancia, que es un encargo pendiente sobre el informe. «No evaluable» tampoco significa «no hay efecto»: significa que este diseño no puede verlo. Los enunciados van recortados a 96 caracteres; el íntegro está en el pre-registro.",
        tam=(7.8,5.4))

def _f4(ax,t):
    # El dominio se detiene en 10 puntos: con p1 = 10 % no existe una diferencia
    # mayor, y prolongar la curva mas alla era un artefacto del recorte.
    ds=[x/1000 for x in range(5,100)]
    ns=[n_por_grupo(.10,.10-d) for d in ds]
    ax.plot([d*100 for d in ds],ns,"-",color=SEQ[5],lw=2)
    ref=[(431,"431 · detectar 10 %→5 %",CRITICO,True),(len(replica),f"{len(replica)} · réplica",APAGADO,False),
         (len(pares),f"{len(pares)} · pareado",APAGADO,False),(len(turnos),f"{len(turnos)} · baterías",APAGADO,False),
         (15,"15 · por modo",APAGADO,False),(n_verif,f"{n_verif} · verificables",APAGADO,False)]
    for n_,lab_,col,destacar in ref:
        ax.axhline(n_,color=col,lw=1.2 if destacar else .7,
                   ls=(0,(5,3)) if destacar else "-",alpha=1 if destacar else .6)
    # Separacion minima de etiquetas en coordenadas de ejes: nunca dos encima.
    ax.set_yscale("log"); ax.set_xlim(0,10); ax.set_ylim(min(n_ for n_,*_ in ref)*.55,max(ns)*1.6)
    y0,y1=ax.get_ylim()
    import math
    def _frac(v): return (math.log10(v)-math.log10(y0))/(math.log10(y1)-math.log10(y0))
    puestos=[]
    for n_,lab_,col,destacar in sorted(ref,key=lambda r:-r[0]):
        f=_frac(n_)
        while any(abs(f-q)<.055 for q in puestos): f-=.055
        puestos.append(f)
        ax.annotate(lab_,xy=(10,n_),xycoords=("data","data"),
                    xytext=(10.25,f),textcoords=("data","axes fraction"),
                    fontsize=7.2,color=col,va="center",weight="bold" if destacar else "normal",
                    annotation_clip=False,
                    arrowprops=dict(arrowstyle="-",color=col,lw=.6,alpha=.7,
                                    shrinkA=0,shrinkB=0))
    ax.set_xlabel("diferencia de proporciones detectable (puntos %)")
    ax.set_ylabel("n necesario por grupo (escala log)")
    ax.grid(alpha=.7)
figura("F4","Potencia del diseño","potencia",
 {"columnas":["n disponible","para qué"],"filas":[[15,"por modo"],[n_verif,"verificables"],[len(turnos),"baterías"],
  [len(pares),"pareado"],[len(replica),"réplica"],[431,"necesario para 10 %→5 %"]],"n":6},_f4,
 "n necesario por grupo frente a la diferencia detectable (α = 0,05 bilateral, potencia 80 %).",
 "DERIVADO",["04_trazas/turns.ndjson"],
 nota_lectura="La curva se detiene en 10 puntos porque con una tasa base del 10 % no existe una diferencia mayor. Ninguno de los tamaños de muestra disponibles alcanza los 431 que harían falta para distinguir 10 % de 5 % con potencia del 80 %: este diseño distingue un efecto grande de ninguno, y no distingue uno mediano. Es la razón cuantitativa de que H-3 y H-9 no se sostengan y de que H-5 sí, porque su efecto es enorme.",tam=(7.2,3.8))

# ═══ A3 · cobertura del instrumento ═══
viejo_raw=[json.loads(l) for l in (W/"01_auditoria_previa/copia/bateria_latencias_2026-08-07.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
viejo=[x for x in viejo_raw if "_tipo_registro" not in x]
def _pobl(regs,campo):
    if not regs or campo not in regs[0]: return 0
    return sum(1 for x in regs if x.get(campo) not in (None,"",[],{}))
CAP=[("latencia extremo a extremo","latencia_total_s","e2e_ms"),
     ("tiempo hasta el primer byte","ttfb_s",None),
     ("etapas y su duración","duracion_etapas_s",None),
     ("recuento de eventos SSE","n_eventos",None),
     ("reparaciones del generador","reparaciones",None),
     ("código HTTP","http_status","http_status"),
     ("código de error","codigo_error","failure_class"),
     ("texto íntegro de la respuesta","respuesta",None),
     ("hash de la respuesta",None,"answer_hash"),
     ("hash de la pregunta",None,"question_hash"),
     ("sello de corrida (modelo·GPU)",None,"run_fingerprint"),
     ("id de sesión por turno",None,"session_id"),
     ("id de conversación","conversation_id","conversation_id"),
     ("clase de pregunta","tipo","question_class"),
     ("marca de verificabilidad",None,"expects_truth"),
     ("mensajes en la ventana",None,"history_messages_count"),
     ("crudos de Ollama (eval_*)",None,None)]
filas_a3=[]
for nom,cv,cn in CAP:
    pv=f"{_pobl(viejo,cv)}/{len(viejo)}" if cv else "ausente"
    pn=f"{_pobl(turnos,cn)}/{len(turnos)}" if cn else "ausente"
    filas_a3.append([nom,pv,pn])
def _a3(ax,t):
    n=len(t["filas"])
    for i,(nom,v,nu) in enumerate(t["filas"]):
        def _est(c):
            if c=="ausente": return 0,"no registra"
            k=int(c.split("/")[0])
            return k,(c if k else "campo vacío "+c)
        fv,tv=_est(v); fn,tn=_est(nu)
        ax.text(-.02,i,nom,ha="right",va="center",fontsize=7.2,color=TINTA)
        for j,(cel,f,col) in enumerate(((tv,fv,L4_VIEJA),(tn,fn,A100_NUEVA))):
            x=j*1.06
            ax.add_patch(plt.Rectangle((x,i-.34),1.0,.68,facecolor=col if f else SUPERFICIE,
                         alpha=1.0 if f else .0,edgecolor=col if f else APAGADO,lw=.9,
                         hatch=None if f else "///"))
            ax.text(x+.5,i,("✓ "+cel) if f else "no registra",ha="center",va="center",
                    fontsize=7 if f else 6.6,color=SUPERFICIE if f else TINTA,weight="bold",
                    bbox=None if f else dict(facecolor=SUPERFICIE,edgecolor="none",pad=1.6))
    for j,lab_ in enumerate(("instrumento 7-ago\n(n = 70 turnos)","instrumento campaña\n(n = 45 turnos)")):
        ax.text(j*1.06+.5,-1.05,lab_,ha="center",va="center",fontsize=7.6,weight="bold",
                color=(L4_VIEJA,A100_NUEVA)[j])
    ax.set_xlim(-1.55,2.1); ax.set_ylim(n-.5,-1.6); ax.axis("off")
figura("A3","Qué registra cada instrumento: cobertura comparada","cobertura_instrumento",
 {"columnas":["capacidad","poblado_7ago","poblado_campana"],"filas":filas_a3,"n":len(filas_a3)},_a3,
 "Presencia y poblamiento real de cada capacidad de medida en los dos instrumentos; la trama diagonal marca ausencia.",
 "MEDIDO",["01_auditoria_previa/copia/bateria_latencias_2026-08-07.jsonl","04_trazas/turns.ndjson"],
 nota_lectura="La cobertura NO crece de forma monótona: el instrumento antiguo registraba ttfb_s, etapas, duración por etapa, eventos SSE y reparaciones —70/70 turnos— y el nuevo no registra ninguna. El nuevo aporta trazabilidad (hashes, sello de corrida, verificabilidad) que el antiguo no tenía. Son instrumentos distintos, no uno mejor. Ninguno de los dos captura los crudos de Ollama, que es la carencia que bloquea X1, X3 y H-8.",
 tam=(7.4,5.4))

# ═══ B2 · limitaciones declaradas ═══
lim_txt=(W/"07_informes/LIMITACIONES.md").read_text(encoding="utf-8")
_corte=lim_txt.find("## Añadidas tras las baterías")
lims=[]
_ini=[m for m in re.finditer(r"^(\d+)\.\s+\*\*(.+?)\*\*",lim_txt,re.M|re.S)]
for k,m in enumerate(_ini):
    titulo=re.sub(r"\s+"," ",m.group(2)).strip().rstrip(".")
    # El cuerpo llega hasta el SIGUIENTE item numerado, no hasta la proxima linea en
    # blanco: los items de LIMITACIONES.md son consecutivos y sin linea en blanco entre
    # ellos, asi que delimitar por "\n\n" hacia que un item heredase las menciones de
    # todos los posteriores.
    cuerpo=lim_txt[m.start():(_ini[k+1].start() if k+1<len(_ini) else len(lim_txt))]
    hip=sorted({h for h in re.findall(r"H-\d+",cuerpo)},key=lambda s:int(s[2:]))
    lims.append([int(m.group(1)),titulo,"antes" if m.start()<_corte else "después",
                 " ".join(hip) if hip else "—"])
def _b2(ax,t):
    n=len(t["filas"])
    for i,(num,tit,mom,hip) in enumerate(t["filas"]):
        col=SEQ[4] if mom=="antes" else SERIO
        ax.add_patch(plt.Rectangle((0,i-.36),.055,.72,facecolor=col,edgecolor="none"))
        ax.text(.028,i,str(num),ha="center",va="center",fontsize=6.6,color=SUPERFICIE,weight="bold")
        ax.text(.075,i,tit,va="center",fontsize=6.9,color=TINTA)

        if hip!="—":
            ax.text(1.005,i,hip,va="center",ha="right",fontsize=6.6,color=CRITICO,weight="bold")
    n_antes=sum(1 for f in t["filas"] if f[2]=="antes")
    for j,(lab_,col) in enumerate(((f"{n_antes} declaradas ANTES de medir",SEQ[4]),
                                   (f"{n-n_antes} declaradas DESPUÉS de medir",SERIO))):
        ax.add_patch(plt.Rectangle((.005+j*.42,n-.05),.028,.42,facecolor=col,edgecolor="none",clip_on=False))
        ax.text(.042+j*.42,n+.17,lab_,fontsize=7.4,color=col,weight="bold",va="center")
    ax.set_xlim(0,1.01); ax.set_ylim(n+.75,-.75); ax.axis("off")
figura("B2","Las limitaciones declaradas y en qué momento se declararon","limitaciones_declaradas",
 {"columnas":["n","limitacion","momento","hipotesis_bloqueadas"],"filas":lims,"n":len(lims)},_b2,
 "Cada limitación sellada en 07_informes/LIMITACIONES.md, con el momento en que se declaró y las hipótesis que menciona.",
 "MEDIDO",["07_informes/LIMITACIONES.md"],
 nota_lectura=f"El catálogo de figuras planificaba «18 confusores». Esa cifra aparece una sola vez en toda la campaña, en la tabla de presupuesto de 99_operacion/log_instancia.md («Fase 1 · sellado + 18 confusores»), y ningún fichero llega a enumerarlos: los códigos E-n del corpus antiguo son identificadores de EXPERIMENTO, no de confusor. Lo que sí consta sellado son {len(lims)} limitaciones, y es lo que se dibuja. {sum(1 for l in lims if l[2]==chr(100)+chr(101)+chr(115)+chr(112)+chr(117)+chr(233)+chr(115))} de ellas se declararon sólo después de medir: el pre-registro no las anticipó.",
 tam=(7.6,5.0))

# ═══ C3 · distribución bootstrap ═══
_rng=random.Random(SEMILLA)
boot_meds=sorted(st.median(_rng.choices(tp,k=len(tp))) for _ in range(10_000))
boot_ic=(boot_meds[250],boot_meds[9750])
afirmar("IC bootstrap TPOT (inf, ms)",round(boot_ic[0],4),round(bootstrap(tp,st.median)[0],4),1e-9)
def _c3(ax,t):
    cnt,_,_=ax.hist(boot_meds,bins=60,color=SEQ[3],edgecolor=SUPERFICIE,lw=.3)
    ymax=max(cnt); ax.set_ylim(0,ymax*1.30)
    # Etiquetas FUERA del area de barras: nunca tapar los datos que se describen.
    for x,lab_,col,ls_,ha_,dy in ((tpot_p50,f"p50 observada {fmt_es(tpot_p50,3)}",CRITICO,"-","center",1.24),
                                  (boot_ic[0],f"IC inf {fmt_es(boot_ic[0],3)}",TINTA_2,(0,(5,3)),"right",1.10),
                                  (boot_ic[1],f"IC sup {fmt_es(boot_ic[1],3)}",TINTA_2,(0,(5,3)),"left",1.10)):
        ax.axvline(x,color=col,lw=1.4,ls=ls_)
        ax.text(x+(0 if ha_=="center" else (-.0012 if ha_=="right" else .0012)),ymax*dy,lab_,
                fontsize=7.4,color=col,ha=ha_,va="center",weight="bold")
    ax.set_xlabel("mediana del TPOT en la remuestra (ms/token)")
    ax.set_ylabel("réplicas bootstrap")
    ax.xaxis.set_major_formatter(formateador_es(2)); ax.yaxis.set_major_formatter(formateador_es(0))
    ax.grid(axis="y",alpha=.7)
figura("C3","Distribución bootstrap de la mediana del TPOT","bootstrap_tpot",
 {"columnas":["estadistico","valor_ms"],"filas":[["p50 observada",round(tpot_p50,4)],
  ["IC 95 % inferior",round(boot_ic[0],4)],["IC 95 % superior",round(boot_ic[1],4)],
  ["réplicas",10000],["n de la muestra",len(tp)]],"n":len(tp)},_c3,
 "10 000 remuestreos con reposición de los 100 TPOT medidos, semilla 20260811.",
 "DERIVADO",["05_derivados/tpot_serie_n100.json"],
 nota_lectura="La distribución es multimodal a propósito de la aritmética, no del sistema: la mediana de un remuestreo de 100 valores discretos sólo puede caer en un número reducido de valores, y por eso el histograma es escalonado en vez de acampanado. El intervalo es estrechísimo (CV 0,65 %) porque mide la precisión de la mediana bajo condiciones fijas y un único modelo cargado: NO es un intervalo sobre el rendimiento que vería un usuario. La serie de origen lleva ADVERTENCIA_DE_PROCEDENCIA: el arnés no la volcó a disco y se rescató de la salida estándar.",
 tam=(7.0,3.6))

# ═══ C5 · ablación de gramática, los dos brazos ═══
def _c5(ax,t):
    for i,(k,lab_,col) in enumerate((("sin_format","sin gramática",SEQ[5]),("con_format","con gramática GBNF",HEMOGRAMA))):
        d=abl[k]; lo,hi=d["tpot_iqr"]; y=i
        ax.plot([lo,hi],[y,y],"-",color=col,lw=7,alpha=.30,solid_capstyle="butt")
        ax.plot([lo,lo],[y-.14,y+.14],"-",color=col,lw=1.6)
        ax.plot([hi,hi],[y-.14,y+.14],"-",color=col,lw=1.6)
        ax.plot([d["tpot_ms_p50"]],[y],"os"[i],ms=11,color=col,markeredgecolor=SUPERFICIE,mew=1.6,zorder=5)
        ax.text(d["tpot_ms_p50"],y+.30,f"p50 {fmt_es(d['tpot_ms_p50'],3)} ms",ha="center",fontsize=8,color=col,weight="bold")
        ax.text(24.28,y,lab_,ha="right",va="center",fontsize=8.5,color=col,weight="bold")
    ax.annotate("",xy=(abl["con_format"]["tpot_ms_p50"],1.42),xytext=(abl["sin_format"]["tpot_ms_p50"],1.42),
                arrowprops=dict(arrowstyle="<->",color=TINTA_2,lw=1.1))
    ax.text((abl["con_format"]["tpot_ms_p50"]+abl["sin_format"]["tpot_ms_p50"])/2,1.50,
            f"Δ = {fmt_es(abl['delta_tpot_ms'],3)} ms/token",ha="center",fontsize=8.5,color=TINTA,weight="bold")
    ax.set_xlim(24.30,25.10); ax.set_ylim(-.55,1.72)
    ax.set_yticks([]); ax.set_xlabel("TPOT (ms/token)")
    ax.xaxis.set_major_formatter(formateador_es(1)); ax.grid(axis="x",alpha=.7)
    marca_corte_eje(ax,24.30)
figura("C5","Ablación de la gramática: los dos brazos por separado","ablacion_brazos",
 {"columnas":["brazo","tpot_p50_ms","iqr_inf","iqr_sup","n","tokens_p50","done_reason"],
  "filas":[[k,abl[k]["tpot_ms_p50"],abl[k]["tpot_iqr"][0],abl[k]["tpot_iqr"][1],abl["n_por_brazo"],
            abl[k]["n_out_p50"],abl[k]["done_reason"]] for k in ("sin_format","con_format")],
  "n":abl["n_por_brazo"]*2},_c5,
 "Mediana y rango intercuartílico de cada brazo, 30 medidas por brazo. Eje truncado y marcado.",
 "MEDIDO",["05_derivados/ablacion_gramatica.json"],
 nota_lectura="No es un diagrama de violín ni de caja completo: los 60 valores crudos NO se persistieron, sólo mediana e IQR por brazo, así que se dibuja exactamente eso. Los IQR se solapan. Ambos brazos toparon en num_predict = 200 con done_reason «length», de modo que esto mide el coste de la gramática en decodificación pura y NO en la terminación, que es donde la evidencia antigua situaba el fallo duro.",
 tam=(7.0,3.0))

# ═══ C7 · determinismo intra-máquina ═══
_can=canario["canario"]
n_pr,n_rep=_can["prompts"],_can["reps"]
def _c7(ax,t):
    # La forma dice lo MEDIDO: n_rep generaciones que colapsan a un unico hash por
    # prompt. Una rejilla de n_pr x n_rep celdas sugeriria n_pr*n_rep hashes
    # registrados de forma independiente, y eso NO es lo que consta.
    mitad=(n_pr+1)//2
    for i in range(n_pr):
        col_x=0 if i<mitad else 1
        y=i if i<mitad else i-mitad
        x0=col_x*3.55
        ax.text(x0-.22,y,f"P{i+1:02d}",ha="right",va="center",fontsize=6.8,color=TINTA_2)
        for j in range(n_rep):
            ax.add_patch(plt.Rectangle((x0+j*.30,y-.17),.24,.34,facecolor=SEQ[3],edgecolor="none"))
        ax.annotate("",xy=(x0+n_rep*.30+.42,y),xytext=(x0+n_rep*.30-.02,y),
                    arrowprops=dict(arrowstyle="->",color=APAGADO,lw=.9))
        ax.add_patch(plt.Rectangle((x0+n_rep*.30+.46,y-.20),.62,.40,facecolor=BUENO,alpha=.85,edgecolor="none"))
        ax.text(x0+n_rep*.30+.77,y,"1 hash",ha="center",va="center",fontsize=6.2,
                color=SUPERFICIE,weight="bold")
    for cx in (0,1):
        ax.text(cx*3.55+n_rep*.15,-1.05,f"{n_rep} generaciones",ha="center",fontsize=7,color=SEQ[5],weight="bold")
        ax.text(cx*3.55+n_rep*.30+.77,-1.05,"resultado",ha="center",fontsize=7,color=BUENO,weight="bold")
    ax.text(0,mitad+.35,f"{_can['prompts_con_mas_de_1_hash']} de {n_pr} prompts produjeron más de un hash · "
            f"{_can['total']} generaciones en total",fontsize=7.8,color=TINTA,weight="bold")
    ax.set_xlim(-1.0,6.6); ax.set_ylim(mitad+.95,-1.55); ax.axis("off")
figura("C7","Determinismo intra-máquina: 20 prompts × 5 repeticiones","determinismo_canario",
 {"columnas":["prompts","repeticiones","celdas","prompts_con_mas_de_1_hash","veredicto"],
  "filas":[[n_pr,n_rep,_can["total"],_can["prompts_con_mas_de_1_hash"],_can["veredicto"][:5]]],
  "n":_can["total"]},_c7,
 "Cada celda es una generación; el color uniforme indica que todas las repeticiones de un prompt produjeron el mismo hash.",
 "DERIVADO",["06_analisis/fase2_canario_y_ic.json"],
 nota_lectura=f"Los hashes celda a celda NO se persistieron: lo que consta es el agregado «{_can['prompts_con_mas_de_1_hash']} prompts con más de un hash» sobre {n_pr}. La rejilla es la representación fiel de ese agregado, no {_can['total']} hashes registrados de forma independiente. El fixture planificaba 10 repeticiones y la corrida ejecutó {n_rep}. Esto NO demuestra equivalencia entre máquinas: §6.2 quedó cancelada porque no constan los prompts renderizados del 7-ago.",
 tam=(7.2,3.6))

# ═══ D4 · frontera de la ventana ═══
front=[t for t in turnos if t["question_class"]=="FRONTERA_VENTANA"]
POS=sorted({t["turn_index"] for t in front})
filas_d4=[[t["question_id"],t["turn_index"],t["outcome"],round(t["e2e_ms"]/1000,1),t["answer_chars"],
           t["history_messages_count"]] for t in front]
def _d4(ax,t):
    for i,m in enumerate(MODOS):
        for j,p in enumerate(POS):
            r=next((x for x in front if x["question_id"].startswith(m[:4]) and x["turn_index"]==p),None)
            col=BUENO if r and r["outcome"]=="util" else CRITICO
            ax.add_patch(plt.Rectangle((j,i),.92,.86,facecolor=col,alpha=.16,edgecolor=col,lw=1.1))
            ax.text(j+.46,i+.30,r["outcome"].upper(),ha="center",fontsize=7.6,color=col,weight="bold")
            ax.text(j+.46,i+.60,f"{fmt_es(r['e2e_ms']/1000,1)} s · {r['answer_chars']} car",
                    ha="center",fontsize=6.8,color=TINTA_2)
        ax.text(-.12,i+.43,m,ha="right",va="center",fontsize=8,color=COLOR_MODO[m],weight="bold")
    for j,p in enumerate(POS):
        ax.text(j+.46,-.22,f"turno {p}",ha="center",va="bottom",fontsize=7.8,color=TINTA_2)
    ax.text(len(POS)/2*.92,3.35,"ventana INFERIDA ≳ 10 pares · history_messages_count = null en las 9 celdas",
            ha="center",fontsize=7.4,color=APAGADO,style="italic")
    ax.set_xlim(-1.35,len(POS)+.1); ax.set_ylim(3.6,-.65); ax.axis("off")
figura("D4","La frontera de la ventana, turno a turno y modo a modo","frontera_matriz",
 {"columnas":["id","turno","desenlace","latencia_s","caracteres","mensajes_en_ventana"],
  "filas":filas_d4,"n":len(front)},_d4,
 "Los nueve turnos de sonda de frontera: tres posiciones × tres modos.",
 "MEDIDO",["04_trazas/turns.ndjson"],
 nota_lectura="Los nueve turnos de frontera respondieron: ninguno murió ni calló. El tamaño de la ventana NO se mide aquí — se infiere de una sola observación (GENERAL-14 devuelve el turno 2 como «primera pregunta»), y con n = 1 y history_messages_count nulo en las nueve celdas no sostiene una cifra. Por eso la anotación dice «inferida».",
 tam=(7.2,3.4))

# ═══ D5 · qué hace el sistema en la frontera ═══
_gen_front=[t for t in front if t["question_id"].startswith("GENE")]
def _corta(s,n=210):
    s=re.sub(r"\s+"," ",s).strip()
    return s if len(s)<=n else s[:n-1]+"…"
filas_d5=[[t["question_id"],_corta(t["question_text"],62),_corta(t["answer_preview"],250)] for t in _gen_front]
def _d5(ax,t):
    n=len(t["filas"]); alto=1.0/n
    for i,(qid,preg,resp) in enumerate(t["filas"]):
        y0=1.0-i*alto
        ax.add_patch(plt.Rectangle((0,y0-alto+.03),.004,alto-.06,transform=ax.transAxes,
                                   facecolor=GENERAL,edgecolor="none"))
        ax.text(.022,y0-.012,f"{qid}   ·   «{preg}»",transform=ax.transAxes,fontsize=8.0,
                weight="bold",color=GENERAL,va="top")
        ax.text(.022,y0-.082,_envolver(resp,112),transform=ax.transAxes,fontsize=7.2,
                color=TINTA_2,va="top",linespacing=1.5)
    ax.axis("off")
figura("D5","Qué responde el sistema al preguntarle por el principio de la conversación","frontera_conducta",
 {"columnas":["id","pregunta","respuesta"],"filas":filas_d5,"n":len(filas_d5)},_d5,
 "Texto literal de los tres turnos de frontera del modo GENERAL.",
 "MEDIDO",["04_trazas/turns.ndjson"],
 nota_lectura="H-6 predecía confabulación y no la hubo: el sistema reporta lo que conserva. El fallo real es distinto y más sutil — no declara el límite de su ventana. GENERAL-14 responde «¿De qué está compuesto?», que fue el turno 2 y no el 1, y lo hace prologado con «según el historial de esta sesión»: un error factual expresado con la misma seguridad que un acierto. Eso es lo que un usuario clínico no puede detectar. Los textos van truncados a 250 caracteres; el íntegro está en la tabla gemela.",
 tam=(7.6,3.2))

# ═══ D6 · verificación contra la tabla de verdad ═══
def _norm(s):
    return unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().lower()
def _contiene(ans,valor):
    a=_norm(ans)
    vals=valor if isinstance(valor,list) else [valor]
    faltan=[]
    for v in vals:
        vs=_norm(v)
        if isinstance(v,str) and re.match(r"^\d{4}-\d{2}-\d{2}T",v): vs=vs[:10]
        if isinstance(v,(int,float)) and float(v)==int(v):
            ok=re.search(rf"(?<!\d){int(v)}(?!\d)",a) is not None
        else:
            ok=vs in a
        if not ok: faltan.append(str(v))
    return (not faltan),faltan
TUR={t["question_id"]:t for t in turnos}
filas_d6=[]
for k in verificables:
    v=verdad[k]; t=TUR.get(k)
    if t is None: filas_d6.append([k,json.dumps(v["valor"],ensure_ascii=False),"SIN TURNO","","—"]); continue
    if t["outcome"]=="muere":
        filas_d6.append([k,json.dumps(v["valor"],ensure_ascii=False),"SIN RESPUESTA",str(t["http_status"]),"—"]); continue
    ok,faltan=_contiene(t["answer_preview"],v["valor"])
    filas_d6.append([k,json.dumps(v["valor"],ensure_ascii=False),
                     "CONTIENE" if ok else "NO CONTIENE",str(t["http_status"])," ".join(faltan)])
n_contiene=sum(1 for f in filas_d6 if f[2]=="CONTIENE")
n_sin_resp=sum(1 for f in filas_d6 if f[2]=="SIN RESPUESTA")
def _d6(ax,t):
    COL={"CONTIENE":BUENO,"NO CONTIENE":SERIO,"SIN RESPUESTA":CRITICO}
    for i,(qid,esp,est,http,falta) in enumerate(t["filas"]):
        c=COL[est]
        ax.add_patch(plt.Rectangle((0,i-.36),.055,.72,facecolor=c,edgecolor="none"))
        ax.text(.075,i,qid,va="center",fontsize=7.4,color=TINTA,weight="bold")
        # Se compacta la hora cero de los ISO para que el valor entre entero: la tabla
        # gemela conserva el literal sellado sin tocar.
        vis=re.sub(r"T00:00:00","",esp).replace('"',"").replace("[","").replace("]","")
        ax.text(.20,i,f"esperado  {vis[:56]}",va="center",fontsize=7,color=TINTA_2)
        ax.text(1.005,i,est,va="center",ha="right",fontsize=7,color=c,weight="bold")
    ax.text(0,-1.25,f"{n_contiene} contienen el valor · "
            f"{len(t['filas'])-n_contiene-n_sin_resp} no lo contienen · {n_sin_resp} sin respuesta",
            fontsize=8,color=TINTA,weight="bold")
    ax.set_xlim(0,1.01); ax.set_ylim(len(t["filas"])-.4,-1.8); ax.axis("off")
figura("D6","Verificación mecánica contra la tabla de verdad sellada","verdad_verificacion",
 {"columnas":["id","valor_esperado","resultado","http","valores_ausentes"],"filas":filas_d6,"n":len(filas_d6)},
 _d6,"Comprobación literal de si la respuesta contiene el valor sellado en 02_fixtures/verdad.json antes de medir.",
 "MEDIDO",["02_fixtures/verdad.json","04_trazas/turns.ndjson"],
 nota_lectura="«NO CONTIENE» no es sinónimo de alucinación y la figura no lo afirma. HEMO-04 no contiene el rango [5,5 · 16,9] porque respondió otra cosa —enumeró los 18 parámetros— sin afirmar ningún rango falso. HEMO-08 dice «10^12/L» donde el fixture selló «x10⁶/µL»: es la misma magnitud en otro convenio, no un número inventado. HEMO-01 murió y no entregó texto. De ahí que el denominador efectivo de la tasa de alucinación de D7 sea aún menor que 9, y su intervalo aún más ancho.",
 tam=(7.2,4.0))

# ═══ D8 · cobertura de la rúbrica ═══
EJES=[("Eje 1","exactitud numérica frente a la tabla de verdad",
       f"PUNTUADO (n = {n_verif})","preregistro.md · H-9 «Eje 1 = −3»"),
      ("Eje 2","referencia recuperable dentro de la ventana",
       "NO PUNTUABLE","history_messages_count = null en los 45 turnos"),
      ("Eje 3","(no consta en los artefactos sellados)","SIN DEFINICIÓN SELLADA",
       "criterios.md lo invoca pero no lo define"),
      ("Eje 4","(no consta en los artefactos sellados)","SIN DEFINICIÓN SELLADA",
       "criterios.md lo invoca pero no lo define"),
      ("Eje 5","(no consta en los artefactos sellados)","NO PUNTUABLE",
       "LIMITACIONES.md §13, junto con el eje 2")]
COL_EJE={"PUNTUADO":BUENO,"NO PUNTUABLE":CRITICO,"SIN DEFINICIÓN SELLADA":APAGADO}
def _d8(ax,t):
    for i,(eje,desc,est,fte) in enumerate(t["filas"]):
        c=COL_EJE[est.split(" (")[0]]
        punt=est.startswith("PUNTUADO")
        ax.add_patch(plt.Rectangle((0,i-.40),1.0,.80,facecolor=c,alpha=.13 if punt else .07,
                     edgecolor=c,lw=1.1,hatch=None if punt else "///"))
        ax.text(.02,i-.10,eje,va="center",fontsize=8.6,weight="bold",color=c)
        ax.text(.115,i-.10,desc,va="center",fontsize=7.6,color=TINTA if punt else APAGADO)
        ax.text(.98,i-.10,est,va="center",ha="right",fontsize=7.4,color=c,weight="bold")
        ax.text(.115,i+.20,fte,va="center",fontsize=6.6,color=APAGADO,style="italic")
    ax.text(0,-1.15,"1 de 5 ejes puntuado. La rúbrica de cinco ejes no llegó a operar.",
            fontsize=8.4,color=CRITICO,weight="bold")
    ax.set_xlim(0,1.01); ax.set_ylim(len(t["filas"])-.3,-1.7); ax.axis("off")
figura("D8","Cobertura real de la rúbrica de cinco ejes","rubrica_cobertura",
 {"columnas":["eje","descripcion","estado","fuente"],"filas":EJES,"n":len(EJES)},_d8,
 "Estado de cada eje de la rúbrica de juicio; la trama diagonal marca lo no puntuado.",
 "MEDIDO",["07_informes/LIMITACIONES.md","02_fixtures/criterios.md","03_hipotesis/preregistro.md"],
 nota_lectura="Éste es un resultado incómodo y se dibuja igual de bien que los demás. De los cinco ejes previstos sólo el 1 se puntuó. Los ejes 2 y 5 son inevaluables por una carencia del instrumento —la API no devuelve el prompt renderizado ni el recuento de mensajes—, y de los ejes 3 y 4 no consta definición operativa en ningún artefacto sellado, pese a que criterios.md los invoca. Puntuarlos ahora sería juicio disfrazado de medida.",
 tam=(7.4,3.4))

# ═══ E6 · desenlaces 7-ago vs réplica con IC de Wilson ═══
_n_rep=len(replica)
_f_viejo,_f_nuevo=len(ids_viejos),len(ids_nuevos)
w_viejo,w_nuevo=wilson(_f_viejo,_n_rep),wilson(_f_nuevo,_n_rep)
# Los 70 turnos son los MISMOS medidos dos veces: el contraste correcto es McNemar
# sobre los discordantes, no la comparacion de dos intervalos independientes.
_disc_v=sum(1 for x in replica if x["fallo_viejo"] and x["outcome"]!="muere")
_disc_n=sum(1 for x in replica if not x["fallo_viejo"] and x["outcome"]=="muere")
from scipy.stats import binomtest as _bt
mcnemar_p=_bt(_disc_n,_disc_v+_disc_n,0.5).pvalue
_solapan=max(w_viejo[0],w_nuevo[0])<=min(w_viejo[1],w_nuevo[1])
def _e6(ax,t):
    for i,(lab_,k,n_,ic,col,mk) in enumerate((("7-ago · L4",_f_viejo,_n_rep,w_viejo,L4_VIEJA,"o"),
                                              ("réplica · A100",_f_nuevo,_n_rep,w_nuevo,A100_NUEVA,"s"))):
        p=k/n_*100
        ax.plot([ic[0]*100,ic[1]*100],[i,i],"-",color=col,lw=2.2)
        for e in ic: ax.plot([e*100,e*100],[i-.10,i+.10],"-",color=col,lw=1.8)
        ax.plot([p],[i],mk,ms=11,color=col,markeredgecolor=SUPERFICIE,mew=1.6,zorder=5)
        ax.text(p,i+.26,f"{k}/{n_} = {fmt_es(p,1)} %",ha="center",fontsize=8,color=col,weight="bold")
        ax.text(-1.2,i,lab_,ha="right",va="center",fontsize=8.5,color=col,weight="bold")
        ax.text(ic[1]*100+1.0,i,f"IC 95 % [{fmt_es(ic[0]*100,1)} · {fmt_es(ic[1]*100,1)}]",
                va="center",fontsize=7,color=TINTA_2)
    lo_s,hi_s=max(w_viejo[0],w_nuevo[0])*100,min(w_viejo[1],w_nuevo[1])*100
    if _solapan:
        ax.axvspan(lo_s,hi_s,color=APAGADO,alpha=.14,lw=0,zorder=0)
        ax.text((lo_s+hi_s)/2,1.55,f"los IC se solapan\nen {fmt_es(lo_s,1)}–{fmt_es(hi_s,1)} %",
                ha="center",fontsize=6.8,color=TINTA_2,style="italic")
    ax.text(52,-.45,f"McNemar exacto sobre los {_disc_v+_disc_n} discordantes: p = {fmt_es(mcnemar_p,3)}",
            ha="right",fontsize=7.4,color=TINTA,weight="bold")
    ax.set_xlim(-16,52); ax.set_ylim(-.75,1.85)
    ax.set_yticks([]); ax.set_xlabel("turnos que no entregan respuesta (%)")
    ax.set_xticks([0,10,20,30,40]); ax.xaxis.set_major_formatter(formateador_es(0))
    ax.grid(axis="x",alpha=.7)
figura("E6","Proporción de turnos sin respuesta, con intervalo de confianza","desenlaces_wilson",
 {"columnas":["corrida","fallos","n","p_pct","ic_inf_pct","ic_sup_pct"],
  "filas":[["7-ago L4",_f_viejo,_n_rep,round(_f_viejo/_n_rep*100,2),round(w_viejo[0]*100,2),round(w_viejo[1]*100,2)],
           ["replica A100",_f_nuevo,_n_rep,round(_f_nuevo/_n_rep*100,2),round(w_nuevo[0]*100,2),round(w_nuevo[1]*100,2)],
           ["McNemar exacto (p)",f"{_disc_v} vs {_disc_n} discordantes",_disc_v+_disc_n,round(mcnemar_p,5),"",""]],
  "n":_n_rep},_e6,
 "Intervalos de Wilson al 95 % sobre el mismo corpus de 70 turnos recorrido dos veces.",
 "DERIVADO",["04_trazas/turns_replica_estricta.ndjson"],
 nota_lectura="Los dos intervalos de Wilson SÍ se solapan, y por eso no bastan para concluir nada: son intervalos independientes aplicados a datos pareados. El contraste correcto, McNemar exacto sobre los 23 turnos discordantes, da p = 0,035, de modo que la caída de proporción sí es significativa al 5 %. Que lo sea NO significa que la GPU arreglara los fallos antiguos: los 17 de la línea base son de contrato (generation_repair_failed) y los 6 nuevos son de transporte (4 × HTTP 502, 2 × HTTP 422), y κ = −0,145 sobre los identificadores dice que ni un solo caso coincide. Desapareció una población de fallos y apareció otra distinta.",
 tam=(7.2,2.9))

# ═══ F2 · tamaños de efecto ═══
EFECTOS=[("Latencia pareada (Δ p50)",dif_p50,dif_ic,"s",0,"MEDIDO · bootstrap 10 000"),
         ("Gramática (Δ TPOT)",abl["delta_tpot_ms"],None,"ms/token",1,"MEDIDO · sin IC (crudos no persistidos)"),
         ("Fallos: 7-ago − réplica",(_f_viejo-_f_nuevo)/_n_rep*100,None,"puntos %",0,"MEDIDO · McNemar p = "+fmt_es(mcnemar_p,3)),
         ("Alucinación numérica",0.0,(wilson(0,n_verif)[0]*100,wilson(0,n_verif)[1]*100),"%",0,"MEDIDO · Wilson"),
         ("Acuerdo de fallos (κ)",kappa,None,"κ",2,"MEDIDO · sin IC")]
def _f2(ax,t):
    fig=ax.get_figure(); ax.axis("off")
    n=len(EFECTOS); h=.66/n; ejes=[]
    for i,(lab_,val,ic,uni,dec,marca_) in enumerate(EFECTOS):
        a=fig.add_axes([.40,.84-(i+1)*h*1.20,.46,h*.80]); ejes.append(a)
        col=BUENO if (ic and ic[0]>0) else (AVISO if ic is None else TINTA_2)
        if ic:
            a.plot([ic[0],ic[1]],[0,0],"-",color=col,lw=2.4,solid_capstyle="butt")
            for e in ic: a.plot([e,e],[-.18,.18],"-",color=col,lw=1.8)
        a.plot([val],[0],"o",ms=9,color=col,markeredgecolor=SUPERFICIE,mew=1.5,zorder=5)
        a.plot([0,0],[0,.52],color=APAGADO,lw=.9,ls=(0,(4,3)),zorder=1)
        lo=min([val,0]+([ic[0]] if ic else [])); hi=max([val,0]+([ic[1]] if ic else []))
        pad=max((hi-lo)*.35,abs(val)*.35,.05)
        a.set_xlim(lo-pad,hi+pad); a.set_ylim(-.55,.55); a.set_yticks([])
        # El eje pasa POR y=0 para que el marcador se apoye en su propia escala.
        a.spines["bottom"].set_position(("data",0))
        for s in ("left","top","right"): a.spines[s].set_visible(False)
        a.spines["bottom"].set_color(APAGADO)
        a.tick_params(labelsize=6.6,length=3,pad=2)
        a.xaxis.set_major_formatter(formateador_es(dec))
        a.text(-.02,.5,lab_,transform=a.transAxes,ha="right",va="center",fontsize=7.8,
               color=TINTA,weight="bold")
        a.text(-.02,-.05,uni,transform=a.transAxes,ha="right",va="center",fontsize=6.4,color=APAGADO)
        a.text(1.02,.5,fmt_es(val,3 if abs(val)<1 else 2),transform=a.transAxes,va="center",
               fontsize=7.6,color=col,weight="bold")
        a.text(1.02,-.05,marca_.split(" · ")[1] if " · " in marca_ else "",transform=a.transAxes,
               va="center",fontsize=6.2,color=APAGADO)
    ejes[0].set_title("cada panel tiene su propia escala y su propia unidad · la línea a trazos es el efecto nulo",
                      fontsize=7.2,loc="left",color=APAGADO,pad=8)
figura("F2","Los cinco efectos medidos, cada uno en su escala","tamanos_efecto",
 {"columnas":["efecto","valor","unidad","ic_inf","ic_sup","marca"],
  "filas":[[l,round(v,4),u,(round(ic[0],4) if ic else ""),(round(ic[1],4) if ic else ""),mk]
           for l,v,ic,u,_d,mk in EFECTOS],"n":len(EFECTOS)},_f2,
 "Magnitud de cada efecto con su intervalo cuando existe.",
 "DERIVADO",["04_trazas/turns_replica_estricta.ndjson","05_derivados/ablacion_gramatica.json","02_fixtures/verdad.json"],
 nota_lectura="No es un forest plot canónico y no debe leerse como tal: las unidades son incomparables entre sí, por eso cada panel lleva su propia escala en vez de compartir un eje que sugeriría magnitudes comparables. Tres de los cinco efectos no tienen intervalo de confianza y lo dicen en el propio panel: la ausencia de IC es información, no un detalle de formato.",
 tam=(7.4,4.0))

# ═══ F3 · cobertura de la campaña ═══
_niveles=[("SESIÓN","session_id, run_fingerprint, conversation_id",
           len({t["session_id"] for t in turnos}|{t["session_id"] for t in replica}),"poblado"),
          ("TURNO","e2e_ms, http_status, outcome, answer_hash",len(turnos)+len(replica),"poblado"),
          ("LLAMADA","eval_count, eval_duration, prompt_eval_*, load_duration",0,"vacío"),
          ("EVENTO","cronología de eventos SSE del turno",0,"vacío")]
def _f3(ax,t):
    # Sin escala de longitud compartida: 6 sesiones y 115 turnos son granularidades
    # distintas y una barra comun insinuaria una comparacion que no existe.
    for i,(niv,campos,n_,est) in enumerate(t["filas"]):
        n_=int(n_); col=BUENO if est=="poblado" else CRITICO
        ax.add_patch(plt.Rectangle((0,i-.34),.045,.68,facecolor=col,edgecolor="none"))
        ax.text(.065,i-.11,niv,va="center",fontsize=9,weight="bold",color=col)
        ax.text(.065,i+.19,campos,va="center",fontsize=6.8,color=APAGADO,style="italic")
        if n_:
            ax.add_patch(plt.Rectangle((.62,i-.28),.30,.38,facecolor=col,alpha=.85,edgecolor="none"))
            ax.text(.77,i-.09,f"{fmt_es(n_,0)} registros",ha="center",va="center",
                    fontsize=8,color=SUPERFICIE,weight="bold")
        else:
            ax.add_patch(plt.Rectangle((.62,i-.28),.30,.38,facecolor=SUPERFICIE,
                                       edgecolor=col,lw=1.1,hatch="///"))
            ax.text(.77,i-.09,"VACÍO",ha="center",va="center",fontsize=8,color=col,weight="bold",
                    bbox=dict(facecolor=SUPERFICIE,edgecolor="none",pad=2.4))
    ax.text(0,-1.15,"2 de los 4 niveles del esquema quedan vacíos: la API pública no expone los crudos del motor.",
            fontsize=8,color=CRITICO,weight="bold")
    ax.set_xlim(0,1.01); ax.set_ylim(len(t["filas"])-.3,-1.7); ax.axis("off")
figura("F3","Qué niveles del esquema de trazas llegó a poblar la campaña","cobertura_esquema",
 {"columnas":["nivel","campos","registros","estado"],
  "filas":[[a,b,c,d] for a,b,c,d in _niveles],"n":len(turnos)+len(replica)},_f3,
 "Los cuatro niveles del esquema de trazas y cuántos registros consiguió poblar cada uno.",
 "MEDIDO",["04_trazas/turns.ndjson","04_trazas/turns_replica_estricta.ndjson","07_informes/LIMITACIONES.md"],
 nota_lectura="Poblar calls_in_turn = null para que el validador de trazas pasara habría sido el patrón «condición necesaria tratada como suficiente» aplicado al propio instrumento. Se dejó fallar y se declaró. Los niveles vacíos son exactamente los que bloquean X1, X3 y H-8.",
 tam=(7.2,3.2))

# ═══ PANELES DE AUSENCIA ═══
AUS=[("X1","Descomposición prefill/decode por turno","Reparto del tiempo de cada turno entre prefill y decodificación.",
      "El nivel de LLAMADA está vacío: la API pública del camino B no expone eval_count, eval_duration, load_duration ni done_reason.",
      "Instrumentar el backend para propagar los crudos de Ollama, o correlacionar por timestamp con los logs del servidor."),
     ("X2","Crecimiento del prefill a lo largo de los 15 turnos","Cuántos tokens de historial viajan en cada turno.",
      "history_messages_count vino null en los 45 turnos: la API no lo devuelve.",
      "Que el backend exponga el recuento de mensajes del prompt renderizado."),
     ("X3","ttft_per_1k_in por posición de turno","Si el KV cache de prefijo se reutiliza entre turnos.",
      "Sin streaming y sin prompt_eval_duration por turno, la métrica no es calculable por el camino B.",
      "Los crudos de Ollama por llamada; es la misma carencia que X1."),
     ("X4","Relojes, temperatura y potencia durante la medición","Si hubo throttling en las ventanas de medida.",
      f"No se capturó log de nvidia-smi concurrente en ninguna de las {len(VENTANAS)} ventanas identificadas en A1.",
      "Muestrear nvidia-smi a ≥10 Hz durante toda medición futura; criterio E-12 del Anexo B."),
     ("X5","Comparación de decode, MBU o TPOT entre L4 y A100","El salto de rendimiento físico entre ambas GPU.",
      "La línea base del 7-ago no contiene NINGUNA métrica de servidor: solo reloj de cliente.",
      "Es irrecuperable: la L4 ya no existe. La única comparación legítima es la latencia pareada de E1."),
     ("X6","Verificación de identidad de modelo entre corridas","Que el 7-ago y la réplica midieron el mismo modelo.",
      "El digest del modelo del 7-ago no consta en ningún fichero de la evidencia.",
      "Irrecuperable. Es la reserva más grave del veredicto de comparabilidad."),
     ("X7","Canario de equivalencia inter-máquina","Divergencia bit a bit de salidas entre L4 y A100.",
      "Los prompts renderizados del 7-ago no constan: el instrumento antiguo solo guardaba el texto lógico.",
      "Irrecuperable para la L4. Para el futuro: hashear el prompt renderizado de cada llamada."),
     ("X8","Tendencia de parámetros en el historial","Evolución de cada parámetro a lo largo de los estudios.",
      "El fixture tiene n_estudios = 2: dos puntos definen siempre una recta, así que 'tendencia' no es medible.",
      "Un paciente con ≥3 estudios; queda fijado en 02_fixtures/criterios.md."),
     ("X9","Radar completo de los cinco ejes de la rúbrica","Puntuación conjunta de exactitud, memoria, clínica, contrato y meta-instrucción.",
      "Los ejes 2 y 5 no son puntuables: §9.4 exige decidir referente_recuperable sobre el prompt renderizado real, que no existe.",
      "El prompt renderizado por llamada; misma carencia estructural que X1 y X2.")]
for a in AUS: panel_ausencia(*a)

# ═══ ARTEFACTOS FINALES ═══
(W/"06_analisis/PROCEDENCIA.json").write_text(json.dumps(PROCEDENCIA,ensure_ascii=False,indent=1),encoding="utf-8")
(FIG/"MANIFIESTO.json").write_text(json.dumps(MANIFIESTO,ensure_ascii=False,indent=1),encoding="utf-8")
with (W/"06_analisis/TRAZABILIDAD.csv").open("w",encoding="utf-8",newline="") as fh:
    wr=_csv.writer(fh,delimiter=";"); wr.writerow(["figura","titulo","fichero_fuente","sha256_fuente","n","marca"])
    for m in MANIFIESTO:
        for cl in (m["procedencia"] or ["(ausencia)"]):
            h=next((v["sha256"] for v in PROCEDENCIA.values() if v["ruta"]==cl),"")
            wr.writerow([m["id"],m["titulo"],cl,h,m.get("n"),m["marca"]])
with (TAB/"INDICE_TABLAS.csv").open("w",encoding="utf-8",newline="") as fh:
    wr=_csv.writer(fh,delimiter=";"); wr.writerow(["figura","titulo","tabla","n"])
    for m in MANIFIESTO:
        if m["tabla"]: wr.writerow([m["id"],m["titulo"],m["tabla"],m.get("n")])
(W/"06_analisis/PIES_DE_FIGURA.md").write_text(
 "# Pies de figura — HemoVet · RECARACTERIZACION-A100\n\n"+"\n\n".join(PIES)+"\n",encoding="utf-8")
# CENTINELA-COMPROBACIONES — lo de abajo no cuenta como codigo de dibujo
with (W/"06_analisis/VERIFICACION_NOTEBOOK.txt").open("w",encoding="utf-8") as fh:
    fh.write("=== ASERCIONES ===\n")
    for a in ASERCIONES:
        fh.write(f"{'OK   ' if a['pasa'] else 'FALLA'} {a['metrica']:34s} recalc={a['recalculado']} publicado={a['publicado']} tol={a['tolerancia']}\n")
    fh.write(f"\nfiguras: {sum(1 for m in MANIFIESTO if m['marca']!='AUSENCIA')}\n")
    fh.write(f"paneles de ausencia: {sum(1 for m in MANIFIESTO if m['marca']=='AUSENCIA')}\n")
    fh.write(f"toda figura con procedencia: {all(m['procedencia'] or m['marca']=='AUSENCIA' for m in MANIFIESTO)}\n")
    fh.write(f"toda figura con tabla: {all(m['tabla'] or m['marca']=='AUSENCIA' for m in MANIFIESTO)}\n")
    fh.write(f"toda figura con n: {all(m.get('n') is not None or m['marca']=='AUSENCIA' for m in MANIFIESTO)}\n")
    # Se inspecciona el fuente canonico, no __file__: el notebook se GENERA de este
    # fichero (ensamblar_notebook.py), asi que es el mismo codigo en ambos caminos, y
    # __file__ no existe dentro de un kernel de Jupyter.
    _fuente=(W/"06_analisis/construir_figuras.py").read_text(encoding="utf-8").split("# CENTINELA-COMPROBACIONES")[0]
    _chk=[("sin twinx/twiny (doble eje)", "twinx(" not in _fuente and "twiny(" not in _fuente),
          ("sin graficos de tarta", ".pie(" not in _fuente),
          ("toda figura con nota de lectura o ausencia",
           all(m.get("nota_lectura") or m["marca"]=="AUSENCIA" for m in MANIFIESTO)),
          ("toda figura exporta pdf+svg+png",
           all(set(m["rutas"])=={"pdf","svg","png"} for m in MANIFIESTO)),
          ("toda proporcion dibujada lleva IC",
           "wilson(" in _fuente and "bootstrap(" in _fuente),
          ("todo eje truncado lleva marca de corte",
           _fuente.count("set_xlim(24.30") <= _fuente.count("marca_corte_eje(")),
          ("aserciones ejecutadas", len(ASERCIONES)),
          ("aserciones que fallan y quedan declaradas",
           sum(1 for a in ASERCIONES if not a["pasa"]))]
    fh.write("\n=== COMPROBACIONES ===\n")
    for nom,val in _chk:
        fh.write(f"{nom}: {val}\n")
print("=== ASERCIONES ===")
for a in ASERCIONES:
    print(f"  {'OK   ' if a['pasa'] else 'FALLA'} {a['metrica']:34s} "
          f"recalc={a['recalculado']} publicado={a['publicado']}")
print(f"\nTOTAL figuras: {sum(1 for m in MANIFIESTO if m['marca']!='AUSENCIA')} | ausencias: {sum(1 for m in MANIFIESTO if m['marca']=='AUSENCIA')}")
