"""
Rede de Ingredientes — Engine de dados e análise (Entrega 1).

Trabalho de Estruturas de Dados 2 (UnB).
Aluno: Patrick Anderson Carvalho dos Santos — 211030620

Pacote modular:
  - api_client : cliente HTTP de TheMealDB (cache em disco + retry/backoff)
  - normalize  : normalização de nomes de ingredientes
  - graph      : grafo não-dirigido ponderado em lista de adjacência
  - builder    : orquestra a API e constrói o grafo (arestas C(k,2))
  - algorithms : BFS, DFS, caminho mínimo e componentes conexas (do zero)
  - emoji_map  : dicionário editável ingrediente -> emoji
  - exporter   : geração de graph.json (contrato) e analysis.txt
"""

__all__ = [
    "api_client",
    "normalize",
    "graph",
    "builder",
    "algorithms",
    "emoji_map",
    "exporter",
]

__version__ = "1.0.0"
