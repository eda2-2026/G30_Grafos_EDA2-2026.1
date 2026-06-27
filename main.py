#!/usr/bin/env python3
"""
CLI da Rede de Ingredientes (Entrega 1).

Uso:
  python main.py build [opções]      baixa, constrói e gera graph.json + analysis.txt
  python main.py path  <a> <b>       caminho mínimo entre 2 ingredientes (lê graph.json)
  python main.py info                imprime as estatísticas do graph.json

Exemplos:
  python main.py build
  python main.py build --seed-limit 120 --out output
  python main.py build --all                 # usa todas as ~935 sementes
  python main.py build --max-recipes 150     # run rápido / demo
  python main.py path egg saffron
  python main.py info

Não usa nenhuma dependência externa — só a biblioteca padrão do Python 3.
"""

import argparse
import json
import os
import sys

# Garante saída UTF-8 (emojis) mesmo em consoles Windows, cujo padrão é cp1252
# e quebraria ao imprimir 🥄/🍗. errors="replace" degrada com elegância.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from ingredient_graph.algorithms import shortest_path
from ingredient_graph.api_client import MealDBClient
from ingredient_graph.builder import build_graph, collect_recipes
from ingredient_graph.emoji_map import emoji_for
from ingredient_graph.exporter import (
    build_analysis,
    build_export,
    write_analysis,
    write_graph_json,
)
from ingredient_graph.graph import Graph
from ingredient_graph.normalize import display_name, edges_word, normalize_name


def cmd_build(args):
    client = MealDBClient(
        cache_dir=args.cache_dir,
        use_cache=not args.no_cache,
        verbose=not args.quiet,
    )
    print(">> Coletando receitas de TheMealDB ...")
    recipes = collect_recipes(
        client,
        seed_limit=args.seed_limit,
        use_all_seeds=args.all,
        max_recipes=args.max_recipes,
        verbose=not args.quiet,
    )
    if not recipes:
        print("ERRO: nenhuma receita coletada (rede indisponível?).", file=sys.stderr)
        return 1

    print(">> Construindo o grafo (arestas C(k,2)) ...")
    graph = build_graph(recipes)

    print(">> Rodando análise (componentes, graus, caminho) e exportando ...")
    export, component = build_export(graph, num_recipes=len(recipes))

    os.makedirs(args.out, exist_ok=True)
    graph_path = os.path.join(args.out, "graph.json")
    analysis_path = os.path.join(args.out, "analysis.txt")

    write_graph_json(export, graph_path)
    analysis = build_analysis(graph, export, component, client_stats=client.stats)
    write_analysis(analysis, analysis_path)

    s = export["stats"]
    print("")
    print(f"   V={s['num_vertices']}  E={s['num_edges']}  "
          f"componentes={s['num_components']}  maior={s['largest_component_size']}")
    print(f"   graph.json  -> {graph_path}")
    print(f"   analysis.txt-> {analysis_path}")
    return 0


def _load_graph(out_dir):
    path = os.path.join(out_dir, "graph.json")
    if not os.path.exists(path):
        print(f"ERRO: {path} não existe. Rode 'python main.py build' antes.", file=sys.stderr)
        return None, None
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return Graph.from_export(data), data


def cmd_path(args):
    graph, _ = _load_graph(args.out)
    if graph is None:
        return 1
    a, b = normalize_name(args.a), normalize_name(args.b)
    for name in (a, b):
        if not graph.has_node(name):
            print(f"ERRO: ingrediente '{name}' não está no grafo.", file=sys.stderr)
            return 1
    path = shortest_path(graph, a, b)
    if path is None:
        print(f"Sem caminho entre '{a}' e '{b}' (componentes diferentes).")
        return 0
    pretty = "  ->  ".join(f"{emoji_for(n)} {display_name(n)}" for n in path)
    n_edges = len(path) - 1
    print(f"Caminho mínimo ({n_edges} {edges_word(n_edges)}):")
    print(f"  {pretty}")
    return 0


def cmd_info(args):
    graph, data = _load_graph(args.out)
    if graph is None:
        return 1
    s = data["stats"]
    m = data["meta"]
    print(f"Fonte: {m['source']} | gerado em {m['generated_at']} | receitas: {m['num_recipes']}")
    print(f"Vértices: {s['num_vertices']}  Arestas: {s['num_edges']}")
    print(f"Componentes: {s['num_components']}  Maior componente: {s['largest_component_size']}")
    top = sorted(data["nodes"], key=lambda n: n["degree"], reverse=True)[:10]
    print("Top-10 por grau:")
    for i, n in enumerate(top, 1):
        print(f"  {i:>2}. {n['emoji']} {n['name']} ({n['degree']})")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="main.py",
        description="Rede de Ingredientes — engine de dados e análise (Entrega 1).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="baixa, constrói e exporta graph.json + analysis.txt")
    b.add_argument("--seed-limit", type=int, default=80,
                   help="nº de ingredientes-semente (padrão: 80)")
    b.add_argument("--all", action="store_true",
                   help="usa TODAS as ~935 sementes (mais lento)")
    b.add_argument("--max-recipes", type=int, default=None,
                   help="limita o nº de receitas (run rápido/demo)")
    b.add_argument("--out", default="output", help="diretório de saída (padrão: output)")
    b.add_argument("--cache-dir", default=".cache", help="diretório de cache (padrão: .cache)")
    b.add_argument("--no-cache", action="store_true", help="desliga o cache em disco")
    b.add_argument("--quiet", action="store_true", help="menos logs")
    b.set_defaults(func=cmd_build)

    pa = sub.add_parser("path", help="caminho mínimo entre dois ingredientes")
    pa.add_argument("a", help="ingrediente de origem (ex.: egg)")
    pa.add_argument("b", help="ingrediente de destino (ex.: saffron)")
    pa.add_argument("--out", default="output", help="diretório com graph.json")
    pa.set_defaults(func=cmd_path)

    inf = sub.add_parser("info", help="imprime estatísticas do graph.json")
    inf.add_argument("--out", default="output", help="diretório com graph.json")
    inf.set_defaults(func=cmd_info)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
