"""
Cliente HTTP de TheMealDB (API aberta, sem chave — usa a key pública "1").

Responsabilidades:
  - falar com os 3 endpoints do enunciado;
  - CACHE em disco (uma resposta por URL, em JSON) para não re-baixar a cada run;
  - RETRY com BACKOFF exponencial em falhas de rede / rate limit (429) / 5xx;
  - DELAY educado entre chamadas que realmente vão à rede.

Edge cases tratados (verificados na própria API):
  - filter.php devolve {"meals": null} quando não há receita -> vira [].
  - slots de ingrediente não usados vêm como "" ou None (tratado no builder).
  - timeouts e erros transitórios -> retry; erro 4xx (exceto 429) -> não insiste.

Só usa a stdlib: urllib (HTTP) + json + hashlib (chave de cache) + time.
"""

import hashlib
import json
import os
import socket
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://www.themealdb.com/api/json/v1/1"
USER_AGENT = "EDA2-RedeDeIngredientes/1.0 (academic; UnB)"


class MealDBClient:
    def __init__(
        self,
        cache_dir=".cache",
        base_url=BASE_URL,
        use_cache=True,
        max_retries=4,
        backoff_base=0.5,   # 1ª espera ~0.5s, depois 1s, 2s, 4s ...
        polite_delay=0.05,  # pausa entre chamadas reais à rede
        timeout=20,
        verbose=True,
    ):
        self.base_url = base_url.rstrip("/")
        self.cache_dir = cache_dir
        self.use_cache = use_cache
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.polite_delay = polite_delay
        self.timeout = timeout
        self.verbose = verbose
        # estatísticas simples (úteis no log/relatório)
        self.stats = {"cache_hits": 0, "network_calls": 0, "retries": 0}
        if self.use_cache:
            os.makedirs(self.cache_dir, exist_ok=True)

    # ------------------------------------------------------------- infra HTTP
    def _cache_path(self, url):
        key = hashlib.sha1(url.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, key + ".json")

    def _log(self, msg):
        if self.verbose:
            print(msg)

    def _write_cache_atomic(self, path, data):
        """
        Grava o cache de forma ATÔMICA: escreve num arquivo temporário no mesmo
        diretório e faz os.replace (atômico em POSIX e Windows). Assim, se o
        processo for interrompido no meio da escrita, o arquivo final nunca fica
        truncado — ou existe completo, ou não existe. Cache é best-effort: uma
        falha de escrita é logada mas não derruba o build.
        """
        fd, tmp = tempfile.mkstemp(dir=self.cache_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        except OSError as e:
            self._log(f"  ~ não foi possível gravar cache em {path} ({e})")
            try:
                os.remove(tmp)
            except OSError:
                pass

    def _get(self, url):
        """
        GET com cache + retry/backoff. Retorna o JSON já desserializado (dict).

        Fluxo:
          1. se houver cache válido em disco, devolve na hora;
          2. senão, tenta a rede até max_retries vezes, dobrando o backoff a
             cada falha transitória (timeout, URLError, 429, 5xx);
          3. em sucesso, grava no cache.
        """
        # 1) cache (auto-cura: uma entrada corrompida é tratada como MISS, e não
        #    como falha fatal — uma escrita interrompida poderia deixar o arquivo
        #    truncado; nesse caso removemos e refazemos pela rede).
        if self.use_cache:
            path = self._cache_path(url)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    self.stats["cache_hits"] += 1
                    return data
                except (json.JSONDecodeError, OSError, ValueError) as e:
                    self._log(f"  ~ cache inválido em {path} ({e}); buscando na rede")
                    try:
                        os.remove(path)
                    except OSError:
                        pass

        # 2) rede com retry/backoff
        last_err = None
        for attempt in range(self.max_retries):
            try:
                if self.polite_delay:
                    time.sleep(self.polite_delay)
                self.stats["network_calls"] += 1
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                # 3) grava cache de forma atômica (nunca deixa arquivo truncado)
                if self.use_cache:
                    self._write_cache_atomic(self._cache_path(url), data)
                return data
            except urllib.error.HTTPError as e:
                last_err = e
                # 429 (rate limit) e 5xx são transitórios -> retry;
                # demais 4xx são definitivos -> aborta.
                if e.code != 429 and not (500 <= e.code < 600):
                    self._log(f"  ! HTTP {e.code} definitivo em {url} — abortando")
                    break
            except (urllib.error.URLError, TimeoutError, socket.timeout, json.JSONDecodeError) as e:
                # rede caiu / timeout / JSON corrompido -> retry.
                # socket.timeout é incluído explicitamente porque em Python < 3.10
                # ele NÃO é subclasse de TimeoutError (em 3.10+ é apenas um alias).
                last_err = e

            # backoff exponencial antes da próxima tentativa
            if attempt < self.max_retries - 1:
                wait = self.backoff_base * (2 ** attempt)
                self.stats["retries"] += 1
                self._log(f"  ~ falha ({last_err}); retry {attempt + 1}/{self.max_retries - 1} em {wait:.1f}s")
                time.sleep(wait)

        raise RuntimeError(f"Falha ao buscar {url} após {self.max_retries} tentativas: {last_err}")

    # ------------------------------------------------------------- endpoints
    def list_ingredients(self):
        """
        GET list.php?i=list -> lista de dicts de ingrediente (idIngredient,
        strIngredient, strDescription, strType, strThumb). Usados como SEMENTES.
        """
        url = f"{self.base_url}/list.php?i=list"
        data = self._get(url)
        return data.get("meals") or []

    def filter_by_ingredient(self, ingredient):
        """
        GET filter.php?i=<ingrediente> -> lista de {idMeal, strMeal, ...}.
        Devolve [] quando a API responde {"meals": null}.
        """
        url = f"{self.base_url}/filter.php?i={urllib.parse.quote(ingredient.strip())}"
        data = self._get(url)
        return data.get("meals") or []

    def lookup_meal(self, meal_id):
        """
        GET lookup.php?i=<idMeal> -> dict completo da receita (com
        strIngredient1..20 / strMeasure1..20), ou None se não existir.
        """
        url = f"{self.base_url}/lookup.php?i={urllib.parse.quote(str(meal_id))}"
        data = self._get(url)
        meals = data.get("meals") or []
        return meals[0] if meals else None
