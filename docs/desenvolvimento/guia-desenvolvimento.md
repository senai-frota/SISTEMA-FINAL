# Guia de desenvolvimento — FROTA-SENAI

| Campo | Valor |
|---|---|
| Versão | 1.0 |
| Data | 26 de outubro de 2026 |
| Público | Desenvolvedores |
| Classificação | Uso interno |

## Ambiente

Recomendado: Debian/Ubuntu, Python 3.12, Node 20. Backend em `BACKEND/`, frontend em `SISTEMA-FINAL/`.

Os testes **não** usam o PostgreSQL de desenvolvimento: `config.test_settings` força SQLite (`BACKEND/test_db.sqlite3`).

## Backend

```bash
cd BACKEND
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Ajuste DB_* se for rodar runserver contra PostgreSQL
python manage.py migrate
python manage.py createsuperuser   # matrícula, nome, senha
python manage.py runserver 0.0.0.0:8000
python manage.py check
python manage.py test --settings=config.test_settings
```

Atalhos Windows no repositório: `run.bat`, `create_superuser.bat` (não exercitados neste ambiente Debian).

Rotina local: `python manage.py rotina_operacional` ou `--loop --intervalo 60`.

Limpeza de vistorias órfãs (comando existente): `python manage.py limpar_vistorias_orfas` — use só com entendimento do efeito; não faz parte do boot Docker.

## Frontend

```bash
cd SISTEMA-FINAL
npm ci
npm run dev      # :5173, host true (LAN)
npm run build
npm run preview
```

Sem `VITE_API_URL`: localhost → `http://localhost:8000/api`; outro hostname → `http://<host>:8000/api`. CORS em DEBUG libera LAN nas portas 3000 e 5173.

## Variáveis

Ver [configuração](../operacao/configuracao.md). Nunca commitar `.env`.

## Organização

| Pacote | Responsabilidade |
|---|---|
| `usuarios` | Auth JWT, perfil, CNH, contas |
| `veiculos` | Frota, imagens, FIPE |
| `reservas` | Reservas, alertas, rotina, e-mail stub |
| `vistorias` | Check-in/out, fotos, dispositivo |
| `termos` | Termo e validade da conta |
| `auditoria` | Trilha HMAC |
| `relatorios` | Indicadores e xlsx |
| `SISTEMA-FINAL/src/pages` | Telas |
| `SISTEMA-FINAL/src/components` | Layout, modais, alertas |
| `SISTEMA-FINAL/src/context` | Auth, feedback |

Textos de negócio de reserva/CNH/termo são normalizados para maiúsculas no backend (`aplicar_maiusculas`).

## Convenções

- Idioma da UI e mensagens de API: português.
- Fuso: `TIME_ZONE=America/Sao_Paulo`, `USE_TZ=True`.
- Não alterar regras de janela (±30 min, 06:00–22:00) sem testes em `vistorias/tests.py` e `reservas/tests_operacoes.py`.
- Novas views: reutilizar `AuthenticatedAndPasswordSet` e filtrar queryset por dono se não for admin.
- Autorização **sempre** no backend.

## Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

Não edite migrations já aplicadas em produção. Não execute `flush`/`reset_db` contra dados reais.

## Dependências

Backend: pinado em `requirements.txt`. Frontend: `package-lock.json` (`npm ci`).

Atualização: altere o arquivo de lock, rode testes/build, registre risco de licença em [inventário](../governanca/inventario-dependencias.md).

## Revisão de alteração (recomendado)

1. Escopo mínimo; sem “limpeza” não pedida.
2. Testes do módulo + `npm run build` se o frontend mudou.
3. Conferir permissões (matriz).
4. Não incluir `.env`, mídia nem `dist/`.
5. Documentar endpoints novos em `api.md`.

Não há pipeline CI neste repositório (**lacuna**).
