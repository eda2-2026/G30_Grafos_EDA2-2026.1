"""
Grafo não-dirigido ponderado em LISTA DE ADJACÊNCIA.

Modelagem (ver README):
    V = ingredientes (normalizados)
    E = pares de ingredientes que co-ocorrem em >= 1 receita
    w({u,v}) = nº de receitas em que o par co-ocorre

Representação:
    self._adj : dict[ id -> dict[ vizinho -> peso ] ]

    O dicionário interno É a lista de adjacência do vértice: suas CHAVES são
    os vizinhos (o que BFS/DFS percorrem) e os VALORES guardam o peso da aresta.
    Usar dict-de-dict mantém a iteração de vizinhos em O(grau) — idêntico a uma
    lista encadeada de adjacência — e ainda dá acúmulo de peso O(1) por par.

Grafo SIMPLES: sem laços (u != v) e no máximo uma aresta por par (o peso conta
as repetições). A ordem de inserção das chaves é preservada (dicts do Python
>= 3.7), tornando BFS/DFS determinísticos sem custo extra de ordenação.
"""


class Graph:
    def __init__(self):
        # id -> {vizinho: peso}
        self._adj = {}

    # ------------------------------------------------------------------ nós
    def add_node(self, u):
        """Garante a existência do vértice u. O(1)."""
        if u not in self._adj:
            self._adj[u] = {}

    def has_node(self, u):
        return u in self._adj

    def nodes(self):
        """Itera sobre os ids de vértice (ordem de inserção)."""
        return self._adj.keys()

    def num_nodes(self):
        return len(self._adj)

    # --------------------------------------------------------------- arestas
    def add_edge(self, u, v):
        """
        Adiciona/reforça a aresta não-dirigida {u, v}, acumulando peso (+1).

        - Ignora laços (u == v): grafo sem laços.
        - Cria u e v automaticamente se ainda não existirem.
        O(1) amortizado.
        """
        if u == v:
            return  # sem laços
        self.add_node(u)
        self.add_node(v)
        self._adj[u][v] = self._adj[u].get(v, 0) + 1
        self._adj[v][u] = self._adj[v].get(u, 0) + 1

    def neighbors(self, u):
        """
        Vizinhos de u (a lista de adjacência propriamente dita).
        É isto que os algoritmos percorrem. O(1) para obter o iterável.
        """
        return self._adj[u].keys()

    def weight(self, u, v):
        """Peso da aresta {u, v} (0 se não existir)."""
        return self._adj.get(u, {}).get(v, 0)

    def degree(self, u):
        """
        Grau (não-ponderado) de u = nº de vizinhos distintos.
        É o campo 'degree' do contrato graph.json. O(1).
        """
        return len(self._adj[u])

    def weighted_degree(self, u):
        """Grau ponderado = soma dos pesos das arestas incidentes (co-ocorrências)."""
        return sum(self._adj[u].values())

    def num_edges(self):
        """Nº de arestas não-dirigidas (cada par contado uma vez). O(V)."""
        return sum(len(viz) for viz in self._adj.values()) // 2

    def edges_sorted(self):
        """
        Gera cada aresta não-dirigida UMA vez, como (u, v, peso), com u < v,
        em ordem determinística. Usado pelo exporter. O(E log E).
        """
        seen = []
        for u in sorted(self._adj):
            for v in sorted(self._adj[u]):
                if u < v:
                    seen.append((u, v, self._adj[u][v]))
        return seen

    # ------------------------------------------------------- (de)serialização
    @classmethod
    def from_export(cls, data):
        """
        Reconstrói um Graph a partir de um dict no formato graph.json
        (apenas nós e arestas), permitindo consultas (ex.: caminho) sem
        rebaixar a API. Os pesos são restaurados diretamente.
        """
        g = cls()
        for node in data.get("nodes", []):
            g.add_node(node["id"])
        for e in data.get("edges", []):
            u, v, w = e["source"], e["target"], e.get("weight", 1)
            if u == v:
                continue
            g.add_node(u)
            g.add_node(v)
            g._adj[u][v] = w
            g._adj[v][u] = w
        return g
