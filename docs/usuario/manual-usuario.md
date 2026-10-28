# Manual do usuário — FROTA-SENAI

| Campo | Valor |
|---|---|
| Versão | 1.0 |
| Data | 26 de outubro de 2026 |
| Público | Funcionários (`is_admin=False`) com conta ativa |
| Classificação | Uso interno |

## Objetivo

Orientar o acesso à interface web para solicitar veículos, cumprir CNH e termo, e realizar check-in/check-out.

Administradores devem usar também o [manual do administrador](../administrador/manual-administrador.md). Administradores **não** solicitam reservas (a API recusa).

## Acesso e autenticação

1. Abra o endereço informado pela TI (em Docker: a origem do Nginx, por exemplo `http://servidor/`).
2. Informe a **matrícula** e a senha.
3. **Primeiro acesso:** se o administrador criou a conta sem senha, use o modo “Primeiro acesso (sem senha)” só com a matrícula e defina a senha em seguida (`/definir-senha`).
4. A sessão usa JWT armazenado no navegador (token de acesso com validade de 8 horas; refresh de 7 dias, com rotação). Ao expirar, a tela volta ao login.

Conta inativa: o login ainda é aceito pela API (`user_authentication_rule`), mas reservar é bloqueado até regularizar o termo.

## Navegação

Após o login, o painel (`/`) mostra veículos disponíveis e as suas reservas.

Menu (funcionário): Painel, Veículos, Minhas reservas, Minha CNH, Meu termo. No celular há barra inferior com atalhos e “Mais” para o menu lateral.

Tema claro/escuro: botão no canto superior direito.

## Pré-requisitos para reservar

Todos verificados no backend ao criar a reserva:

| Requisito | Evidência |
|---|---|
| Conta ativa | `ReservaCreateSerializer` |
| Termo aprovado e dentro da validade (365 dias após aprovação) | `usuario_possui_termo_valido` |
| CNH aprovada com `data_validade` ≥ hoje | `usuario_pode_reservar_com_cnh` |
| Veículo não em manutenção/inativo | serializer |
| Sem conflito de horário com outra reserva ativa | `existem_conflitos` |
| Retirada não no passado; no máximo **14 dias** à frente | `ANTECEDENCIA_MAXIMA_DIAS` |
| Sem pernoite: início e fim no **mesmo dia** civil | `validar_intervalo_dias` |
| Com pernoite: modalidade horário personalizado e unidade informada | `validar_pernoite` |

## CNH (`/minha-cnh`)

1. Envie PDF ou imagem da CNH.
2. Status: pendente → aprovado ou rejeitado pelo administrador.
3. Só uma CNH pendente por vez.
4. Com CNH aprovada a **30 dias** ou menos do vencimento, o painel alerta (`CNH_DIAS_ALERTA_VENCIMENTO`).
5. CNH vencida impede nova reserva.

## Termo (`/meu-termo`)

1. Preencha entidade (FIBRA, SESI, SENAI, IEL), CPF, número da CNH e anexe o PDF.
2. Aguarde aprovação. Rejeição exige justificativa visível.
3. Validade: 365 dias a partir da aprovação. Vencido: a conta do funcionário pode ser inativada pela sincronização de termo (`sincronizar_status_conta`).

## Solicitar reserva (`/veiculos` → reservar)

Modalidades:

- **Horário personalizado:** data/hora de início e fim.
- **Turno:** manhã 06:00–12:00, tarde 12:00–18:00, noite 18:00–22:00 (fuso local).

Pernoite: somente em horário personalizado; informe onde o veículo permanece à noite. Pernoite **não** dispensa o check-in.

Textos de motivo e destino são gravados em maiúsculas.

## Estados da reserva

```text
pendente → aprovada → em_andamento → concluida
    │          │
    └──────────┴→ cancelada
pendente → negada
```

| Status | Significado |
|---|---|
| Pendente | Aguardando o administrador |
| Aprovada | Pode fazer check-in na janela |
| Negada | Recusada (há justificativa) |
| Em andamento | Check-in feito; veículo em uso |
| Concluída | Check-out feito |
| Cancelada | Pelo solicitante, pelo admin ou automaticamente (falta de check-in) |

Edição: só reserva **pendente**. Cancelamento pelo solicitante: **pendente** ou **aprovada** (não em andamento).

## Check-in e check-out

**Somente em smartphone ou tablet.** O sistema combina o cabeçalho `X-Client-Form-Factor`, Client Hints e User-Agent. Desktop é recusado.

- Cinco fotos obrigatórias: frente, traseira, laterais e painel.
- Unidade: Taguatinga, Gama, Sobradinho ou SIG.
- Check-in: reserva **aprovada**; janela da reserva ±30 minutos; horário operacional **06:00–22:00**.
- Check-in antecipado: solicite em `/reservas` com justificativa; o admin aprova ou recusa. Mesmo autorizado, o check-in noturno (fora 06:00–22:00) continua bloqueado.
- Check-out: na **mesma unidade** do check-in; permitido após o horário previsto (atraso). O código só recusa check-out **antes** da janela de início da reserva (±30 min). Não há teto de 24 h implementado em `validar_checkout_horario_reserva` (a constante `MSG_CHECKOUT_DEPOIS` existe e não é usada).
- Um check-in e um check-out por reserva (unicidade no banco). Reenvio idêntico pode ser tratado como idempotente (HTTP 200) se a vistoria já existe.

## Alertas

A barra no topo lista alertas **da sua reserva** (check-out atrasado, check-in perto do cancelamento, cancelamento automático recente). Administradores veem a frota. Toasts de “nova solicitação” são só para admin.

Cancelamento automático: se não houver check-in, na **meia-noite civil do dia seguinte** ao fim da janela de check-in a reserva aprovada é cancelada. O serviço `rotina` no Compose executa isso em loop.

## Desktop e celular

| | Desktop | Celular |
|---|---|---|
| Reservar, CNH, termo | Sim | Sim |
| Check-in / check-out | Não | Sim |
| Menu | Barra lateral | Botão ☰ + navegação inferior |

## Problemas comuns

| Sintoma | O que fazer |
|---|---|
| “Usuário ou senha inválidos” | Confira matrícula; no 1º acesso não envie senha se ainda não foi definida |
| Não consegue reservar | Verifique termo, CNH e se a conta está ativa |
| Check-in recusado no computador | Use o celular |
| Check-in fora do horário | Espere a janela ±30 min ou solicite antecipação; não opera 22:00–06:00 |
| Check-out em outra unidade | Volte à unidade do check-in |
| Sessão caiu | Entre novamente; o token dura 8 horas |

## Segurança

Não compartilhe a senha nem deixe a sessão aberta em computador público. Use Sair no menu.
