"""
Construtor do grafo: orquestra a API e materializa o grafo de ingredientes.

Pipeline:
  1. list_ingredients()            -> sementes (ingredientes normalizados)
  2. para cada semente: filter.php -> ids de receita (dedup por idMeal)
  3. para cada receita única: lookup.php -> ingredientes normalizados/dedup
  4. para cada receita com k ingredientes: adiciona as C(k,2) arestas,
     acumulando peso em pares repetidos.

Deduplicação:
  - receitas: por idMeal (uma receita conta no máximo 1 por par de ingredientes);
  - ingredientes dentro da receita: por nome normalizado (evita laços/duplo peso).
"""

from .graph import Graph
from .normalize import normalize_name


def extract_ingredients(meal):
    """
    Extrai a lista de ingredientes normalizados e SEM repetição de uma receita
    (dict de lookup.php). Ignora slots vazios ("" ou None).

    A deduplicação interna é essencial: se "garlic" aparecer 2x na mesma receita
    não pode virar laço nem dobrar peso indevidamente.
    """
    seen = set()
    out = []
    for i in range(1, 21):  # TheMealDB tem strIngredient1..20
        nv = normalize_name(meal.get(f"strIngredient{i}"))
        if nv and nv not in seen:
            seen.add(nv)
            out.append(nv)
    return out


def collect_recipes(client, seed_limit=80, use_all_seeds=False,
                    max_recipes=None, verbose=True):
    """
    Executa os passos 1-3 do pipeline e devolve a lista de receitas:
        [ {"id": idMeal, "name": strMeal, "ingredients": [...normalizados...]} ]

    Parâmetros:
      seed_limit    : nº de ingredientes-semente (os 1ºs da lista, ~por
                      popularidade). 80 já cobre quase todas as receitas do DB.
      use_all_seeds : se True, usa TODAS as ~935 sementes (mais chamadas).
      max_recipes   : limite opcional de receitas (para runs rápidos/demo).
    """
    ingredients = client.list_ingredients()
    seeds = []
    seen_seed = set()
    for item in ingredients:
        nv = normalize_name(item.get("strIngredient"))
        if nv and nv not in seen_seed:
            seen_seed.add(nv)
            seeds.append(nv)
    if not use_all_seeds:
        seeds = seeds[:seed_limit]
    if verbose:
        print(f"[1/3] {len(seeds)} ingredientes-semente")

    # 2) filter -> ids de receita (dedup, preservando ordem de descoberta)
    meal_ids = {}  # idMeal -> True (dict como conjunto ordenado)
    for idx, seed in enumerate(seeds, 1):
        for meal in client.filter_by_ingredient(seed):
            meal_ids.setdefault(meal["idMeal"], True)
        if verbose and idx % 20 == 0:
            print(f"      sementes processadas: {idx}/{len(seeds)} | receitas únicas: {len(meal_ids)}")
    ids = list(meal_ids)
    if max_recipes is not None:
        ids = ids[:max_recipes]
    if verbose:
        print(f"[2/3] {len(ids)} receitas únicas a detalhar")

    # 3) lookup -> ingredientes de cada receita
    recipes = []
    for idx, mid in enumerate(ids, 1):
        meal = client.lookup_meal(mid)
        if not meal:
            continue
        ings = extract_ingredients(meal)
        if ings:  # ignora receitas sem ingrediente válido
            recipes.append({"id": mid, "name": meal.get("strMeal", mid), "ingredients": ings})
        if verbose and idx % 50 == 0:
            print(f"      receitas detalhadas: {idx}/{len(ids)}")
    if verbose:
        print(f"[3/3] {len(recipes)} receitas válidas coletadas")
    return recipes


def _dedup_preserving_order(items):
    """Remove repetições mantendo a 1ª ocorrência (robustez: 1 receita -> +1/par)."""
    seen = set()
    out = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


def build_graph(recipes):
    """
    Passo 4: constrói o Graph a partir das receitas.

    Para cada receita com ingredientes [i0, i1, ..., i(k-1)] gera as C(k,2)
    arestas entre todos os pares; `add_edge` acumula o peso de pares repetidos
    e ignora laços. Custo: O(soma de k_r^2) sobre as receitas.

    Os ingredientes são deduplicados POR RECEITA antes de gerar os pares, de
    modo que uma única receita contribui com no máximo +1 ao peso de cada par
    (mesmo que o ingrediente apareça repetido na receita) — fiel à definição
    w({u,v}) = nº de RECEITAS em que o par co-ocorre.
    """
    g = Graph()
    for r in recipes:
        ings = _dedup_preserving_order(r["ingredients"])
        for ing in ings:           # garante o vértice mesmo se k == 1 (isolado)
            g.add_node(ing)
        for i in range(len(ings)):
            for j in range(i + 1, len(ings)):
                g.add_edge(ings[i], ings[j])
    return g
