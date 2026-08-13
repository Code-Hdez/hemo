"""Repara el arnes de aceptacion: los parametros de generacion viven ahora en el
perfil, no en el cliente. Se ENRUTAN, no se descartan."""
import pathlib, sys
ruta = pathlib.Path(sys.argv[1])
t = ruta.read_text()
viejo = '''    http_client = httpx.AsyncClient()
    llm = AcceptanceOllamaClient(
        http_client=http_client,
        base_url=base_url,
        model_name=model,
        temperature=float(os.getenv("OLLAMA_ACCEPTANCE_TEMPERATURE", "0.1")),
        max_tokens=int(os.getenv("OLLAMA_ACCEPTANCE_MAX_TOKENS", "384")),
        timeout_seconds=float(os.getenv("OLLAMA_ACCEPTANCE_TIMEOUT", "90")),
        keep_alive=os.getenv("OLLAMA_ACCEPTANCE_KEEP_ALIVE", "10m"),
        context_length=int(os.getenv("OLLAMA_ACCEPTANCE_CONTEXT", "4096")),
        think=False,
        top_p=0.9,
        top_k=40,
        repeat_penalty=1.1,
    )'''
nuevo = '''    http_client = httpx.AsyncClient()
    # Los parametros de generacion se movieron del cliente al perfil: hoy el caso
    # de uso construye el ModelRequest desde `generation_settings`, y el cliente
    # solo transporta lo que el request trae. Filtrarlos del constructor los
    # descartaria en silencio, asi que se ENRUTAN al perfil, que es donde surten
    # efecto. El arnes sigue midiendo con los valores que declara.
    _ctx = int(os.getenv("OLLAMA_ACCEPTANCE_CONTEXT", "4096"))
    _ka = os.getenv("OLLAMA_ACCEPTANCE_KEEP_ALIVE", "10m")
    acceptance_settings = dataclasses.replace(
        _TEST_CHAT_SETTINGS,
        model=model,
        temperature=float(os.getenv("OLLAMA_ACCEPTANCE_TEMPERATURE", "0.1")),
        num_predict=int(os.getenv("OLLAMA_ACCEPTANCE_MAX_TOKENS", "384")),
        context_length=_ctx,
        general_context_length=_ctx,
        selected_context_length=_ctx,
        history_context_length=_ctx,
        keep_alive=(int(_ka) if _ka.lstrip("-").isdigit() else _ka),
        thinking=False,
        top_p=0.9,
        top_k=40,
        repeat_penalty=1.1,
    )
    llm = AcceptanceOllamaClient(
        http_client=http_client,
        base_url=base_url,
        model_name=model,
        timeout_seconds=float(os.getenv("OLLAMA_ACCEPTANCE_TIMEOUT", "90")),
        warmup_profile=acceptance_settings.main_profile(
            name="warmup", context_scope="general"
        ),
    )'''
assert t.count(viejo) == 1, f"ancla no encontrada en {ruta}"
t = t.replace(viejo, nuevo)
# dentro de _run_acceptance, el caso de uso debe usar los ajustes del arnes
ini = t.index("        use_case = SendChatMessageUseCase(")
fin = t.index("\n        )", ini)
bloque = t[ini:fin]
t = t[:ini] + bloque.replace("_TEST_CHAT_SETTINGS", "acceptance_settings") + t[fin:]
ruta.write_text(t)
print(f"reparado: {ruta}")
