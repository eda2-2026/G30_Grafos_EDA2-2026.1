"""
Normalização de nomes de ingredientes.

A API devolve nomes com caixa e espaçamento inconsistentes (ex.: "Soy Sauce",
"  garlic ", "Chicken  Breast"). Para que o mesmo ingrediente vire um único
vértice, normalizamos todos os nomes da mesma forma antes de criar nós/arestas.

Regra de normalização (id do vértice):
    lowercase  ->  strip  ->  colapsa espaços internos repetidos
"""

import re

# Compilado uma única vez: qualquer sequência de espaços em branco vira " ".
_WHITESPACE = re.compile(r"\s+")


def normalize_name(raw):
    """
    Converte um nome cru de ingrediente no id canônico do vértice.

    Retorna string vazia para entradas inúteis (None, "", "   "), que o
    chamador deve descartar — os slots de ingrediente não usados de TheMealDB
    chegam ora como "" ora como None.

    >>> normalize_name("  Soy   Sauce ")
    'soy sauce'
    >>> normalize_name(None)
    ''
    """
    if raw is None:
        return ""
    return _WHITESPACE.sub(" ", raw.strip().lower())


def display_name(node_id):
    """
    Versão amigável (Title Case) do id para exibição na UI / relatório.

    >>> display_name("soy sauce")
    'Soy Sauce'
    """
    return " ".join(word.capitalize() for word in node_id.split())


def edges_word(n):
    """Pluralização PT-BR de 'aresta': 1 -> 'aresta', caso contrário 'arestas'."""
    return "aresta" if n == 1 else "arestas"
