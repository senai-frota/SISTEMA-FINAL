# Frota SENAI — Frontend

Interface web (React + Vite) para o backend `projeto-frota-senai`, com a paleta institucional do SENAI.

## Como rodar

```bash
# 1. Instale as dependências
npm install

# 2. Configure a URL da API (se o backend não estiver em localhost:8000)
cp .env.example .env

# 3. Rode em modo desenvolvimento
npm run dev
```

O app abre em `http://localhost:5173`. Certifique-se de que o backend Django está rodando em
`http://localhost:8000` (ou ajuste `VITE_API_URL` no `.env`) e que `CORS_ALLOWED_ORIGINS` no `.env`
do backend inclui `http://localhost:5173` (já vem assim por padrão).

Para gerar a versão de produção:

```bash
npm run build
```

Os arquivos ficam em `dist/` prontos para servir por qualquer servidor estático (Nginx, etc).

## O que tem pronto

- **Login** com matrícula + senha (JWT, refresh automático de token)
- **Painel** com indicadores rápidos (veículos disponíveis, pendências, reserva ativa)
- **Veículos**: busca/filtro por status, cadastro e edição (administrador), solicitação de reserva
- **Minhas reservas**: acompanhamento de status, cancelamento, check-in e check-out
- **Vistoria**: upload de fotos (até 5) no check-in/check-out, com campo de ângulo/observação
- **Aprovações** (administrador): aprovar ou negar solicitações pendentes
- **Usuários** (administrador): cadastro e edição de funcionários

Perfis de administrador e funcionário têm menus diferentes automaticamente, conforme o campo
`is_admin` retornado por `/api/usuarios/perfil/`.

## Estrutura

```
src/
├── components/     # Layout, modais, badges, formulários reutilizáveis
├── context/        # AuthContext (login, JWT, usuário atual)
├── pages/          # Login, Dashboard, Veiculos, Reservas, Aprovacoes, Usuarios
├── services/       # Cliente axios com refresh automático de token
├── styles/         # tokens.css (paleta SENAI) + app.css (componentes)
└── utils/          # Formatação de datas
```

## Paleta SENAI usada

| Cor | Hex |
|---|---|
| Vermelho (primária) | `#E30613` |
| Preto | `#000000` / `#1A1A1A` |
| Cinza | `#878787` |
| Branco | `#FFFFFF` |

## Observações

- O cadastro de veículo aceita foto apenas pelo Django Admin por enquanto (a API espera o campo
  `foto` como arquivo; o formulário atual do frontend cobre os demais campos via JSON).
- Edição de usuário não permite alterar senha ou perfil (admin/funcionário) — isso é uma limitação
  da API atual (`UsuarioUpdateSerializer`), que só aceita nome, e-mail, telefone, setor e status
  ativo. Para trocar senha ou perfil, remova e recadastre o usuário, ou ajuste o serializer no
  backend se quiser habilitar isso pela interface.
