"""
Testes dos algoritmos sobre um GRAFO PEQUENO FEITO À MÃO, com resultados
esperados conhecidos (calculados manualmente).

Grafo de teste (não-dirigido):

        a
        |
        b
       / \
      e   c
          |
          d

      f --- g           h  (isolado)

  Arestas: a-b, b-c, b-e, c-d, f-g.   Vértice h sem arestas.

  Componentes esperados:
      {a, b, c, d, e}  -> 5 vértices
      {f, g}           -> 2 vértices
      {h}              -> 1 vértice
  => 3 componentes, maior = 5.

  BFS a partir de 'a' (níveis):
      a:0, b:1, e:2, c:2, d:3   (f,g,h inalcançáveis)

  Caminho mínimo a -> d:  a, b, c, d  (3 arestas)
  Caminho a -> h:         None (componentes diferentes)

Roda com:  python -m unittest discover -s tests
      ou:  python tests/test_algorithms.py
"""

import os
import sys
import unittest

# permite rodar o arquivo diretamente (python tests/test_algorithms.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingredient_graph.algorithms import (  # noqa: E402
    bfs_levels,
    connected_components,
    dfs_preorder,
    shortest_path,
)
from ingredient_graph.graph import Graph  # noqa: E402


def make_hand_graph():
    g = Graph()
    for u, v in [("a", "b"), ("b", "c"), ("b", "e"), ("c", "d"), ("f", "g")]:
        g.add_edge(u, v)
    g.add_node("h")  # isolado
    return g


class TestBFS(unittest.TestCase):
    def setUp(self):
        self.g = make_hand_graph()

    def test_levels(self):
        levels = bfs_levels(self.g, "a")
        self.assertEqual(levels, {"a": 0, "b": 1, "e": 2, "c": 2, "d": 3})

    def test_unreachable_not_included(self):
        levels = bfs_levels(self.g, "a")
        for n in ("f", "g", "h"):
            self.assertNotIn(n, levels)

    def test_source_level_zero(self):
        self.assertEqual(bfs_levels(self.g, "f"), {"f": 0, "g": 1})


class TestShortestPath(unittest.TestCase):
    def setUp(self):
        self.g = make_hand_graph()

    def test_path_a_to_d(self):
        self.assertEqual(shortest_path(self.g, "a", "d"), ["a", "b", "c", "d"])

    def test_path_length(self):
        path = shortest_path(self.g, "a", "d")
        self.assertEqual(len(path) - 1, 3)  # 3 arestas

    def test_same_node(self):
        self.assertEqual(shortest_path(self.g, "a", "a"), ["a"])

    def test_no_path_between_components(self):
        self.assertIsNone(shortest_path(self.g, "a", "h"))
        self.assertIsNone(shortest_path(self.g, "a", "f"))

    def test_symmetry(self):
        fwd = shortest_path(self.g, "a", "d")
        bwd = shortest_path(self.g, "d", "a")
        self.assertEqual(fwd, list(reversed(bwd)))


class TestComponents(unittest.TestCase):
    def setUp(self):
        self.g = make_hand_graph()

    def test_count(self):
        _, num = connected_components(self.g)
        self.assertEqual(num, 3)

    def test_membership(self):
        comp, _ = connected_components(self.g)
        # a,b,c,d,e no mesmo componente
        self.assertEqual(comp["a"], comp["b"])
        self.assertEqual(comp["a"], comp["c"])
        self.assertEqual(comp["a"], comp["d"])
        self.assertEqual(comp["a"], comp["e"])
        # f,g juntos, mas != do componente de a
        self.assertEqual(comp["f"], comp["g"])
        self.assertNotEqual(comp["a"], comp["f"])
        # h sozinho
        self.assertNotEqual(comp["h"], comp["a"])
        self.assertNotEqual(comp["h"], comp["f"])

    def test_largest_size(self):
        comp, _ = connected_components(self.g)
        from collections import Counter
        sizes = Counter(comp.values())
        self.assertEqual(max(sizes.values()), 5)


class TestDFS(unittest.TestCase):
    def setUp(self):
        self.g = make_hand_graph()

    def test_dfs_visits_whole_component(self):
        order = dfs_preorder(self.g, "a")
        self.assertEqual(set(order), {"a", "b", "c", "d", "e"})

    def test_dfs_starts_at_source(self):
        self.assertEqual(dfs_preorder(self.g, "a")[0], "a")

    def test_dfs_and_bfs_same_reachable_set(self):
        bfs_set = set(bfs_levels(self.g, "a").keys())
        dfs_set = set(dfs_preorder(self.g, "a"))
        self.assertEqual(bfs_set, dfs_set)


if __name__ == "__main__":
    unittest.main(verbosity=2)
