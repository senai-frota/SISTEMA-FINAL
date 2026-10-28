# Frontend — FROTA-SENAI

Interface React (Vite) do sistema de frota.

Documentação: [docs/](../docs/) — em especial [guia de desenvolvimento](../docs/desenvolvimento/guia-desenvolvimento.md) e [configuração](../docs/operacao/configuracao.md).

## Comandos

```bash
npm ci
npm run dev
npm run build
npm run preview
```

Sem `VITE_API_URL`, a base da API é resolvida automaticamente (localhost `:8000/api` ou o mesmo host na porta `8000`). No Docker Compose o build usa `VITE_API_URL=/api`.
