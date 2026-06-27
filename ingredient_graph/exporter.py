"""
Exportador: gera o contrato graph.json (consumido pela Entrega 2) e um
analysis.txt legível.

Contrato graph.json:
{
  "meta":  { "source", "generated_at", "num_recipes" },
  "nodes": [ { "id", "name", "emoji", "degree", "component" } ],
  "edges": [ { "source", "target", "weight" } ],
  "stats": { "num_vertices", "num_edges", "num_components", "largest_component_size" }
}
"""

import json
from collections import Counter
from datetime import datetime

from .algorithms import (
    approx_diameter_path,
    connected_components,
    shortest_path,
)
from .emoji_map import emoji_for
from .normalize import display_name, edges_word

STUDENT = "Patrick Anderson Carvalho dos Santos — 211030620"


def build_export(graph, num_recipes, source="TheMealDB"):
    """
    Monta o dict no formato graph.json e devolve (export_dict, component),
    onde `component` é o mapa vértice -> id_componente (reaproveitado no relatório).
    """
    component, num_components = connected_components(graph)

    nodes = [
        {
            "id": nid,
            "name": display_name(nid),
            "emoji": emoji_for(nid),
            "degree": graph.degree(nid),
            "component": component[nid],
        }
        for nid in sorted(graph.nodes())
    ]

    edges = [
        {"source": u, "target": v, "weight": w}
        for (u, v, w) in graph.edges_sorted()
    ]

    sizes = Counter(component.values())
    largest = max(sizes.values()) if sizes else 0

    export = {
        "meta": {
            "source": source,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "num_recipes": num_recipes,
        },
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "num_vertices": graph.num_nodes(),
            "num_edges": graph.num_edges(),
            "num_components": num_components,
            "largest_component_size": largest,
        },
    }
    return export, component


def write_graph_json(export, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(export, fh, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------- relatório
def _largest_component_nodes(graph, component):
    """Devolve a lista de vértices do maior componente."""
    sizes = Counter(component.values())
    if not sizes:
        return []
    biggest_cid = max(sizes, key=sizes.get)
    return [n for n, c in component.items() if c == biggest_cid]


def _format_path(graph, path):
    """Formata um caminho como 'emoji nome -> emoji nome -> ...'."""
    parts = [f"{emoji_for(n)} {display_name(n)}" for n in path]
    return "  ->  ".join(parts)


def build_analysis(graph, export, component, client_stats=None):
    """
    Gera o texto do analysis.txt:
      - cabeçalho/identificação + complexidade dos algoritmos;
      - nº de vértices/arestas, componentes, maior componente;
      - top-10 ingredientes por grau;
      - exemplo de caminho mínimo entre dois ingredientes DISTANTES.
    """
    stats = export["stats"]
    L = []
    add = L.append

    add("=" * 70)
    add("REDE DE INGREDIENTES — ANÁLISE (Entrega 1)")
    add("Estruturas de Dados 2 — UnB")
    add(f"Aluno: {STUDENT}")
    add(f"Fonte: {export['meta']['source']}  |  gerado em {export['meta']['generated_at']}")
    add("=" * 70)
    add("")
    add("MODELAGEM DO GRAFO (não-dirigido, simples, ponderado)")
    add("  V = ingredientes (nomes normalizados: lowercase + trim)")
    add("  E = pares de ingredientes que co-ocorrem em >= 1 receita")
    add("  w({u,v}) = nº de receitas em que o par u,v co-ocorre")
    add("  Para receita com k ingredientes -> C(k,2) arestas (peso acumulado).")
    add("")
    add("COMPLEXIDADE (lista de adjacência, V vértices e E arestas)")
    add("  BFS / DFS ................ O(V + E)")
    add("  Caminho mínimo (BFS) ..... O(V + E)")
    add("  Componentes conexas ...... O(V + E)  (total, cada vértice/aresta 1x)")
    add("")
    add("-" * 70)
    add("ESTATÍSTICAS GERAIS")
    add(f"  Receitas processadas ....... {export['meta']['num_recipes']}")
    add(f"  Vértices (ingredientes) .... {stats['num_vertices']}")
    add(f"  Arestas (co-ocorrências) ... {stats['num_edges']}")
    add(f"  Componentes conexas ........ {stats['num_components']}")
    add(f"  Maior componente ........... {stats['largest_component_size']} vértices")
    if stats["num_vertices"]:
        dens = 2 * stats["num_edges"] / (stats["num_vertices"] * (stats["num_vertices"] - 1)) if stats["num_vertices"] > 1 else 0
        add(f"  Densidade .................. {dens:.4f}")
    add("")

    # ---- top-10 por grau
    add("-" * 70)
    add("TOP-10 INGREDIENTES POR GRAU (nº de co-ingredientes distintos)")
    add(f"  {'#':>2}  {'ingrediente':<26} {'grau':>5} {'grau_pond.':>11}")
    ranked = sorted(
        graph.nodes(),
        key=lambda n: (graph.degree(n), graph.weighted_degree(n)),
        reverse=True,
    )
    for i, n in enumerate(ranked[:10], 1):
        label = f"{emoji_for(n)} {display_name(n)}"
        add(f"  {i:>2}  {label:<26} {graph.degree(n):>5} {graph.weighted_degree(n):>11}")
    add("")

    # ---- caminho mínimo entre dois ingredientes distantes
    add("-" * 70)
    add("EXEMPLO DE CAMINHO MÍNIMO (entre dois ingredientes distantes)")
    big = _largest_component_nodes(graph, component)
    if len(big) >= 2:
        # heurística da dupla BFS dentro do maior componente
        a, b, path = approx_diameter_path(graph, big[0])
        if path:
            d = len(path) - 1
            add(f"  De  {emoji_for(a)} {display_name(a)}  até  {emoji_for(b)} {display_name(b)}")
            add(f"  Distância: {d} {edges_word(d)}")
            add(f"  Caminho: {_format_path(graph, path)}")
    else:
        add("  (grafo pequeno demais para um exemplo significativo)")
    add("")

    # ---- exemplo nomeado do enunciado: "do ovo ao açafrão" (egg -> saffron)
    if graph.has_node("egg") and graph.has_node("saffron"):
        ep = shortest_path(graph, "egg", "saffron")
        if ep:
            d = len(ep) - 1
            add("  Exemplo nomeado (do ovo ao açafrão):")
            add(f"  {_format_path(graph, ep)}  [{d} {edges_word(d)}]")
            add("")

    if client_stats:
        add("-" * 70)
        add("CHAMADAS À API")
        add(f"  cache hits ..... {client_stats.get('cache_hits', 0)}")
        add(f"  network calls .. {client_stats.get('network_calls', 0)}")
        add(f"  retries ........ {client_stats.get('retries', 0)}")
        add("")

    add("=" * 70)
    return "\n".join(L) + "\n"


def write_analysis(text, path):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
