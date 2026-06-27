"""
Testes da construção do grafo a partir de receitas:
  - geração das C(k,2) arestas;
  - acúmulo de peso em pares repetidos;
  - ausência de laços e dedup de ingredientes (mesmo normalizado);
  - normalização (caixa/espacos) colapsando vértices;
  - extração de ingredientes ignorando slots vazios ("" e None).

Roda com:  python -m unittest discover -s tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingredient_graph.builder import build_graph, extract_ingredients  # noqa: E402
from ingredient_graph.normalize import normalize_name  # noqa: E402


class TestNormalize(unittest.TestCase):
    def test_lower_trim_collapse(self):
        self.assertEqual(normalize_name("  Soy   Sauce "), "soy sauce")

    def test_none_and_empty(self):
        self.assertEqual(normalize_name(None), "")
        self.assertEqual(normalize_name("   "), "")


class TestExtractIngredients(unittest.TestCase):
    def test_skips_empty_and_none_slots(self):
        meal = {f"strIngredient{i}": "" for i in range(1, 21)}
        meal["strIngredient1"] = "Egg"
        meal["strIngredient2"] = "  Milk "
        meal["strIngredient3"] = None
        meal["strIngredient4"] = "egg"  # duplicata normalizada -> deve sumir
        ings = extract_ingredients(meal)
        self.assertEqual(ings, ["egg", "milk"])


class TestBuildGraph(unittest.TestCase):
    def test_ck2_edges(self):
        # receita com 3 ingredientes -> C(3,2)=3 arestas, todas peso 1
        recipes = [{"id": "1", "name": "r1", "ingredients": ["a", "b", "c"]}]
        g = build_graph(recipes)
        self.assertEqual(g.num_nodes(), 3)
        self.assertEqual(g.num_edges(), 3)
        for u, v in [("a", "b"), ("a", "c"), ("b", "c")]:
            self.assertEqual(g.weight(u, v), 1)

    def test_weight_accumulation(self):
        # par (a,b) aparece em 2 receitas -> peso 2
        recipes = [
            {"id": "1", "name": "r1", "ingredients": ["a", "b", "c"]},
            {"id": "2", "name": "r2", "ingredients": ["a", "b"]},
        ]
        g = build_graph(recipes)
        self.assertEqual(g.weight("a", "b"), 2)
        self.assertEqual(g.weight("a", "c"), 1)
        self.assertEqual(g.weight("b", "c"), 1)

    def test_no_self_loops_on_duplicate(self):
        # ingrediente repetido dentro da receita não pode virar laço
        recipes = [{"id": "1", "name": "r1", "ingredients": ["a", "a", "b"]}]
        g = build_graph(recipes)
        self.assertEqual(g.weight("a", "a"), 0)
        self.assertEqual(g.weight("a", "b"), 1)
        self.assertEqual(g.num_edges(), 1)

    def test_single_ingredient_recipe_has_node_no_edge(self):
        recipes = [{"id": "1", "name": "r1", "ingredients": ["lonely"]}]
        g = build_graph(recipes)
        self.assertTrue(g.has_node("lonely"))
        self.assertEqual(g.num_edges(), 0)
        self.assertEqual(g.degree("lonely"), 0)

    def test_degree(self):
        recipes = [{"id": "1", "name": "r1", "ingredients": ["a", "b", "c", "d"]}]
        g = build_graph(recipes)
        # grafo completo K4 -> grau 3 para cada vértice
        for n in ("a", "b", "c", "d"):
            self.assertEqual(g.degree(n), 3)
        self.assertEqual(g.num_edges(), 6)  # C(4,2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
