# Manual do administrador — FROTA-SENAI

| Campo | Valor |
|---|---|
| Versão | 1.0 |
| Data | 26 de outubro de 2026 |
| Público | Contas com `is_admin=True` |
| Classificação | Uso interno |

## Objetivo

Descrever as operações administrativas realmente disponíveis na interface e na API.

## Perfil

O campo `is_admin` no cadastro define o perfil. `is_staff` no Django Admin replica `is_admin`. Não há papéis intermediários (gestor de unidade, auditor somente leitura, etc.).

Administradores **não criam reservas**. A API responde 403: *“Administradores não podem solicitar reservas de veículos.”*

## Acesso

Login igual ao funcionário (matrícula + senha). Rotas exclusivas: Aprovações, Usuários, CNH pendentes, Termos pendentes, Relatórios, Calendário, Auditoria. O painel (`/`) mostra o dashboard administrativo (pendências, frota, alertas críticos).

Django Admin (`/admin/`): existe e exige superusuário/`is_admin`. Use com cuidado; a operação cotidiana é a SPA.

## Gestão de usuários (`/usuarios`)

- Criar: matrícula, nome, e-mail, telefone, setor, se é administrador, se está ativo. A conta nasce **sem senha** (`precisa_definir_senha=True`).
- Listar: por padrão só ativos; há opção de incluir inativos. Filtros de setor, situação de CNH e termo.
- Editar: nome, contato, setor. Só admin altera `is_active`.
- Remover: **inativação** (`is_active=False`), não exclusão física. Não é permitido remover a própria conta.
- Não é possível (nesta API) o admin aprovar a **própria** CNH ou o **próprio** termo.

## Gestão de veículos (`/veiculos`)

Cadastro e edição (placa única, marca, modelo, ano, cor, combustível, capacidade, RENAVAM, chassi, status, km, data de última manutenção **informativa** — não bloqueia reserva).

Status: disponível, em uso, manutenção, inativo. Inativar é exclusão lógica.

Fotos: até 8 por veículo (`VEICULO_IMAGEM_MAXIMO_FOTOS`), tamanho máximo configurável (padrão 5 MB), JPG/PNG/WebP.

Consulta FIPE (Parallelum) auxilia o preenchimento. Se a API externa falhar, o sistema responde HTTP 503 — cadastre marca, modelo e ano manualmente.

Aprovar reserva **não** coloca o veículo em uso; isso ocorre no check-in.

## Aprovações (`/aprovacoes`)

1. Reservas pendentes: aprovar ou negar (negação **exige** justificativa). Conflito de horário impede aprovação.
2. Pedidos de check-in antecipado: aprovar ou rejeitar (rejeição exige observação).

A tela atualiza periodicamente (polling ~25 s).

## CNH e termos

- `/cnh-pendentes` e `/termos-pendentes`.
- Aprovar CNH: informar `data_validade`.
- Rejeitar: justificativa obrigatória.
- Termo aprovado: `data_validade` = aprovação + 365 dias.

Pendências agregadas: `GET /api/usuarios/pendencias/` (somente admin).

## Acompanhamento operacional

Alertas no topo e no painel:

- Check-out atrasado (reserva em andamento após `data_fim` + 30 min).
- Check-in próximo do cancelamento automático.
- Cancelamento automático (últimos 7 dias na listagem).
- Novas solicitações e check-ins antecipados pendentes.

A rotina contínua (`rotina` no Compose, a cada 60 s) cancela reservas aprovadas sem check-in após a meia-noite do dia seguinte ao fim da janela e registra eventos de check-out atrasado.

## Relatórios (`/relatorios`, `/relatorio-calendario`)

Indicadores filtráveis (período, veículo, usuário, status, turno) e exportação `.xlsx`. Calendário mensal das reservas relevantes. Somente admin.

## Auditoria (`/auditoria`)

- Ações (filtros por tipo, ator, afetado, datas, busca).
- Arquivos (CNH, termo, fotos de vistoria e de veículo) **sem copiar o binário** — consulta metadados e URL.
- Integridade da cadeia HMAC (hash encadeado). Se `AUDITORIA_CHAVE_INTEGRIDADE` mudar, registros antigos falham na verificação.
- Registros são **imutáveis** (update/delete bloqueados no modelo).

## Cuidados e erros comuns

| Situação | Orientação |
|---|---|
| Recusar reserva/CNH/termo sem texto | A API exige justificativa |
| Aprovar com conflito de agenda | 400 — ajuste horários |
| Trocar a chave de auditoria | Quebra a verificação de integridade de todo o histórico |
| `docker compose down -v` | Apaga banco e mídia — **proibido** em produção |
| Ativar e-mail | Só com SMTP institucional e `FROTA_EMAIL_ENABLED=true` (hoje desligado) |
| Check-in pelo admin | O fluxo de vistoria é do **solicitante** no mobile |

## Permissões

Tabela completa: [matriz de permissões](../seguranca/matriz-permissoes.md).
