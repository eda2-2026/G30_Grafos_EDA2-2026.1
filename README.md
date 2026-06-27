# Rede de Ingredientes — Engine de Dados e Análise (Entrega 1)

Trabalho de **Estruturas de Dados 2** — Universidade de Brasília (UnB).
Tema: **grafos**. Construímos uma rede de ingredientes a partir de receitas
reais (API [TheMealDB](https://www.themealdb.com/)) e rodamos **BFS**, **DFS**,
**caminho mínimo** e **componentes conexas** sobre ela.

> Esta é a **Entrega 1 de 2**: a engine de dados e análise. Ela produz o
> contrato `graph.json` que a **Entrega 2** (visualização) irá consumir.

**Aluno responsável por esta entrega:** Patrick Anderson Carvalho dos Santos — **211030620**

---

## 1. Modelagem formal do grafo

Seja `R` o conjunto de receitas coletadas. Definimos o grafo **não-dirigido,
simples e ponderado** `G = (V, E, w)`:

| Elemento | Definição |
|---|---|
| **Vértice** `V` | Um ingrediente, identificado pelo nome **normalizado** (`lowercase` + `trim` + colapso de espaços). Ex.: `"  Soy   Sauce "` → `soy sauce`. |
| **Aresta** `E` | `E = { {u, v} : u ≠ v e existe r ∈ R contendo u e v }`. Ou seja, dois ingredientes são ligados se co-ocorrem em **pelo menos uma** receita. |
| **Peso** `w` | `w({u, v}) = |{ r ∈ R : u, v ∈ r }|` = número de receitas em que o par `u, v` co-ocorre. |

**Geração das arestas.** Para uma receita com `k` ingredientes distintos,
geram-se todas as `C(k, 2) = k·(k−1)/2` arestas entre seus pares. Pares que se
repetem em outras receitas **acumulam peso** (cada receita contribui no máximo
`+1` ao peso de um par).

**Propriedades garantidas:** sem laços (`u ≠ v`); no máximo uma aresta por par
(grafo simples — o peso conta as repetições); não-dirigido (`{u,v}` = `{v,u}`).

**Grau.** `grau(v)` = número de vizinhos distintos de `v` (grau **não-ponderado**;
é o campo `degree` do contrato). O relatório também mostra o **grau ponderado**
(soma dos pesos incidentes = total de co-ocorrências).

---

## 2. Algoritmos (implementados do zero)

Tudo em `ingredient_graph/algorithms.py`, sobre **lista de adjacência**, **sem
nenhuma biblioteca de grafos** (NetworkX, igraph etc.). A única importação é
`collections.deque` — apenas uma fila genérica, não um algoritmo pronto.

| Algoritmo | Função | O quê | Complexidade |
|---|---|---|---|
| **BFS** | `bfs_levels(g, s)` | nível (distância em arestas) de cada vértice alcançável | **O(V + E)** |
| **DFS** | `dfs_preorder(g, s)` | ordem de descoberta (pilha explícita, iterativa) | **O(V + E)** |
| **Caminho mínimo** | `shortest_path(g, a, b)` | menor caminho em nº de arestas, **com reconstrução** | **O(V + E)** |
| **Componentes conexas** | `connected_components(g)` | rotula cada vértice com o id do componente (flood-fill BFS) | **O(V + E)** total |

> **Por que componentes é O(V + E) no total** (e não `O(V·(V+E))`): cada vértice
> é rotulado uma única vez e cada aresta é examinada um número constante de vezes
> somando-se **todas** as buscas. Memória auxiliar: **O(V)**.

> **Peso ≠ distância.** O peso mede *força* de co-ocorrência, não custo de
> travessia. A BFS trata o grafo como **não-ponderado** e mede distância em
> **arestas (saltos)**, como pede o enunciado.

---

## 3. Setup

**Requisito único:** Python **3.8+**. **Não há dependências externas** — a engine
usa apenas a biblioteca padrão (`urllib`, `json`, `hashlib`, ...). Nada de `pip install`.

```bash
python --version   # 3.8 ou superior
```

> **Por que Python (só stdlib)?** O enunciado permite "só lib de HTTP/JSON". A
> stdlib do Python já entrega HTTP (`urllib`), JSON (`json`) e cache/hashing
> (`hashlib`) — então a engine roda com `python main.py` puro, sem instalar nada,
> o que simplifica a correção. Os algoritmos centrais são 100% próprios.

---

## 4. Como rodar

### Construir o grafo (baixa, constrói e exporta)

```bash
python main.py build
```

Gera dois arquivos em `output/`:
- **`graph.json`** — o contrato consumido pela Entrega 2;
- **`analysis.txt`** — relatório legível (estatísticas, top-10 por grau, caminho exemplo).

As respostas da API são **cacheadas em `.cache/`**; a partir da 2ª execução o
build é praticamente instantâneo e offline.

**Opções úteis:**

```bash
python main.py build --seed-limit 120   # mais ingredientes-semente (grafo maior)
python main.py build --all              # usa TODAS as ~935 sementes (mais lento)
python main.py build --max-recipes 150  # run rápido p/ demonstração
python main.py build --no-cache         # ignora o cache (força rede)
python main.py build --out saida        # muda o diretório de saída
```

### Consultar um caminho mínimo (lê o `graph.json`)

```bash
python main.py path egg saffron
# Caminho mínimo (1 aresta):
#   🥚 Egg  ->  🌸 Saffron

python main.py path salt redcurrants
# Caminho mínimo (2 arestas):
#   🧂 Salt  ->  🍞 Bread  ->  🍒 Redcurrants
```

### Resumo rápido do grafo

```bash
python main.py info
```

### Rodar os testes

```bash
python -m unittest discover -s tests -v
```

---

## 5. Contrato de saída: `graph.json`

```jsonc
{
  "meta":  { "source": "TheMealDB", "generated_at": "<ISO>", "num_recipes": 535 },
  "nodes": [
    { "id": "milk", "name": "Milk", "emoji": "🥛", "degree": 254, "component": 0 }
  ],
  "edges": [ { "source": "milk", "target": "egg", "weight": 8 } ],
  "stats": {
    "num_vertices": 766, "num_edges": 15804,
    "num_components": 1, "largest_component_size": 766
  }
}
```

- `nodes` e `edges` são ordenados de forma determinística; cada aresta aparece
  **uma vez** com `source < target` (não-dirigido).
- O **emoji** vem de um dicionário **editável** em
  [`ingredient_graph/emoji_map.py`](ingredient_graph/emoji_map.py): busca exata →
  fallback por palavra-chave → genérico `🥄`.

---

## 6. Arquitetura (modular)

```
eda2/
├── main.py                      # CLI: build / path / info
├── ingredient_graph/
│   ├── api_client.py            # cliente TheMealDB: cache em disco + retry/backoff
│   ├── normalize.py             # normalização de nomes
│   ├── graph.py                 # Graph: lista de adjacência ponderada
│   ├── builder.py               # orquestra a API e monta o grafo (C(k,2))
│   ├── algorithms.py            # BFS, DFS, caminho mínimo, componentes (DO ZERO)
│   ├── emoji_map.py             # dicionário editável ingrediente -> emoji
│   └── exporter.py              # graph.json (contrato) + analysis.txt
├── tests/
│   ├── test_algorithms.py       # grafo manual com resultados conhecidos
│   └── test_builder.py          # C(k,2), pesos, sem laços, normalização
└── output/                      # graph.json + analysis.txt (amostra versionada)
```

**Pipeline de dados (`builder.py`)** e endpoints usados:

1. `list.php?i=list` → ~935 ingredientes (sementes).
2. `filter.php?i=<ingrediente>` → ids de receita; **dedup** por `idMeal`.
3. `lookup.php?i=<idMeal>` → ingredientes completos da receita (`strIngredient1..20`).
4. monta as arestas `C(k, 2)` acumulando peso.

**Edge cases tratados (verificados na própria API):**
- `filter.php` devolve `{"meals": null}` (não `[]`) quando não há receita;
- slots de ingrediente não usados vêm como `""` **ou** `null` → descartados;
- nomes multi-palavra são URL-encodados;
- **retry com backoff exponencial** em `429` (rate limit), `5xx`, timeout e
  falha de rede; `4xx` definitivo não insiste;
- **cache em disco** (uma resposta por URL, chave = SHA-1 da URL);
- console **UTF-8** forçado para imprimir emojis no Windows (cp1252).

---

## 7. Resultados (amostra — `--seed-limit 80`, 535 receitas)

| Métrica | Valor |
|---|---|
| Vértices (ingredientes) | **766** |
| Arestas (co-ocorrências) | **15.804** |
| Componentes conexas | **1** |
| Maior componente | **766** (100%) |

O grafo real é um **único componente gigante**: ingredientes-hub (alho, cebola,
sal, manteiga, azeite) conectam praticamente tudo. Os **top-10 por grau**
refletem isso:

```
 1  🧄 Garlic      434      6  🥕 Carrots   296
 2  🧅 Onion       421      7  🥚 Egg       275
 3  🧂 Salt        388      8  🌶️ Pepper    262
 4  🧈 Butter      373      9  🍬 Sugar     258
 5  🫒 Olive Oil   365     10  🥛 Milk      254
```

> O algoritmo de componentes encontrar **1** componente aqui é um resultado
> legítimo; a capacidade de detectar **vários** componentes é exercitada nos
> testes (`tests/test_algorithms.py`), num grafo manual com 3 componentes.

Veja o relatório completo em [`output/analysis.txt`](output/analysis.txt).

---

## 8. Testes

`tests/test_algorithms.py` valida BFS, DFS, caminho mínimo e componentes sobre um
**grafo pequeno feito à mão** com resultado conhecido:

```
        a
        |                Componentes esperados:
        b                  {a,b,c,d,e}  (5)
       / \                 {f,g}        (2)
      e   c                {h}          (1)
          |              => 3 componentes, maior = 5
          d
   f — g     h(isolado)   BFS(a): a:0 b:1 c:2 e:2 d:3
                          caminho a→d: a,b,c,d (3 arestas)
                          caminho a→h: None
```

`tests/test_builder.py` valida a construção: geração `C(k,2)`, acúmulo de peso,
ausência de laços, dedup e normalização.

```bash
python -m unittest discover -s tests -v   # 22 testes, todos passam
```
