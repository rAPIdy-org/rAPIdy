# rAPIdy server spikes A/B/C

Одноразовый код для проверки серверных рисков до реализации rAPIdy 2.0. Этот каталог не входит в пакет `rapidy`,
его код не переносится в production. После гейта переиспользуются только выводы из
`/Users/popkovdaniil/Documents/projects/opensource/roadmap/rapidy2/research/spikes-verdict.md`.

Окружение изолировано от workspace server member:

```bash
python3.12 -m venv spikes/.venv
spikes/.venv/bin/pip install -r spikes/requirements.txt
spikes/.venv/bin/python -m pytest spikes -q
spikes/.venv/bin/python spikes/spike_c_matcher/bench_resolve.py
```

`aiohttp` установлен только в `spikes/.venv` как поведенческий/benchmark-эталон. DI primitives импортируются из
editable workspace-пакета `rapidy_core.di`, а не напрямую из Dishka.
