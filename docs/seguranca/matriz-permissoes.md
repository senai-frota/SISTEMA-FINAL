# Matriz de permissões

| Campo | Valor |
|---|---|
| Versão | 1.0 |
| Data | 26 de outubro de 2026 |
| Perfis | Anônimo, funcionário (`is_admin=False`), administrador (`is_admin=True`) |
| Evidência | `permissions.py`, views, `App.jsx` `adminOnly` |

Legenda: Sim = permitido; Não = recusado; Próprio = só registros do usuário.

## Autenticação

| Operação | Anônimo | Funcionário | Admin |
|---|---|---|---|
| Login / refresh | Sim | Sim | Sim |
| Definir senha (1º acesso) | Não (precisa token) | Sim | Sim |
| Usar API sem senha definida | Não | Não (exceto perfil/definir-senha) | Não |

## Contas e documentos

| Operação | Funcionário | Admin |
|---|---|---|
| Ver próprio perfil | Sim | Sim |
| Listar usuários | Não | Sim |
| Criar usuário | Não | Sim |
| Editar próprio nome/contato | Sim | Sim |
| Alterar `is_active` de terceiros | Não | Sim |
| Inativar usuário | Não | Sim (não a si) |
| Upload CNH/termo | Sim (próprio) | Sim (próprio; não aprova o próprio) |
| Decidir CNH/termo | Não | Sim |
| Pendências agregadas | Não | Sim |

## Frota e reservas

| Operação | Funcionário | Admin |
|---|---|---|
| Listar veículos (não inativos) | Sim | Sim + inativos |
| Cadastrar/editar/inativar veículo | Não | Sim |
| Fotos do veículo | Não | Sim |
| Consultar FIPE | Sim | Sim |
| Criar reserva | Sim | **Não** |
| Ver reservas | Próprias | Todas |
| Aprovar/negar reserva | Não | Sim |
| Cancelar pendente/aprovada | Própria | Qualquer (com justificativa) |
| Check-in/out registrar | Própria, mobile | API: sim (admin não é bloqueado pelo serializer). UI: o botão exige `reserva.usuario ===` usuário logado, então o admin não registra vistoria de terceiros pela interface |
| Check-in antecipado solicitar | Própria | Não |
| Decidir antecipado | Não | Sim |
| Alertas operacionais | Próprios críticos | Frota + avisos |
| Calendário / indicadores / Excel | Não | Sim |
| Auditoria | Não | Sim (somente GET) |

## Frontend

Rotas `adminOnly` redirecionam funcionário para `/`. Isso **não** é autorização.

## Evidência no código

As respostas 403 são emitidas por `IsAdmin`, `ExigeSenhaDefinida` e pelos filtros de queryset nas views de usuários, veículos, reservas, relatórios, auditoria e termos.
