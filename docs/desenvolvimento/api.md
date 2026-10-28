# Referência da API — FROTA-SENAI

| Campo | Valor |
|---|---|
| Versão | 1.0 |
| Data | 26 de outubro de 2026 |
| Prefixo | `/api/` |
| Autenticação | `Authorization: Bearer <access>` salvo rotas públicas |
| Paginação | `PageNumberPagination`, `PAGE_SIZE=20` (`count`, `next`, `previous`, `results`) |
| Formato | JSON; uploads em `multipart/form-data` |
| OpenAPI | **Não há** esquema gerado no repositório; este documento foi extraído das `urls.py` e views |

## Convenções

- Permissão padrão: autenticado + senha definida. Mensagem 403 de senha: *“É necessário definir sua senha antes de continuar.”*
- Admin: `IsAdmin` → *“Apenas administradores podem realizar esta ação.”*
- Filtro típico: admin vê todos; funcionário vê os próprios registros.
- Exemplos abaixo usam matrícula `f12345` e dados fictícios.

## Públicos

### POST `/api/usuarios/login/`

AllowAny. Corpo: `{ "matricula": "f12345", "password": "********" }`.  
Primeiro acesso sem senha: `password` vazio e conta com `precisa_definir_senha` e senha não usável.

Resposta 200: `access`, `refresh`, `precisa_definir_senha`, `is_admin`, `matricula`, `nome`.  
400: *“Usuário ou senha inválidos.”*

### POST `/api/usuarios/refresh/`

SimpleJWT. Corpo: `{ "refresh": "..." }`. Rotação ativada; token antigo vai para blacklist.

## Usuários e perfil

| Método | Caminho | Quem |
|---|---|---|
| POST | `/usuarios/definir-senha/` | autenticado (1º acesso permitido) |
| GET | `/usuarios/perfil/` | próprio (1º acesso permitido) |
| GET | `/usuarios/pendencias/` | admin |
| GET POST | `/usuarios/cnh/` | lista: admin todas / user próprias; POST: própria |
| GET | `/usuarios/cnh/meu-status/` | próprio |
| GET | `/usuarios/cnh/<id>/` | dono ou admin |
| PATCH | `/usuarios/cnh/<id>/decisao/` | admin (`status`, `data_validade` ou `observacao_admin`) |
| GET POST | `/usuarios/` | admin |
| GET PATCH | `/usuarios/<id>/` | admin ou próprio |
| DELETE | `/usuarios/<id>/` | admin (inativa) |

Filtros de listagem de usuários: `incluir_inativos`, `ativo`, `setor`, `cnh_situacao`, `termo_situacao`.

## Veículos

| Método | Caminho | Quem |
|---|---|---|
| GET | `/veiculos/` | autenticado (oculta inativos, salvo admin com query) |
| POST PATCH DELETE | `/veiculos/`, `/veiculos/<id>/` | admin (DELETE = inativo) |
| GET | `/veiculos/<id>/` | autenticado |
| POST DELETE | `/veiculos/<id>/imagem/` | admin |
| GET | `/veiculos/marcas/` … `/anos/<codigo_ano>/` | autenticado (FIPE; 503 se a API externa falhar) |

Query GET veículos: `status`, `marca`, `tipo_combustivel`, `ano`, busca placa/modelo/marca.

## Reservas

| Método | Caminho | Quem |
|---|---|---|
| GET POST | `/reservas/` | GET: dono ou admin; POST: **não** admin |
| GET | `/reservas/disponibilidade/` | autenticado (`veiculo`, `data_inicio`, `data_fim`) |
| GET | `/reservas/relatorio/calendario/` | admin (`mes`, `ano`) |
| GET | `/reservas/alertas-operacionais/` | autenticado (conteúdo filtrado) |
| GET | `/reservas/autorizacoes-checkin/` | admin todas; user as que solicitou |
| PATCH | `/reservas/autorizacoes-checkin/<id>/` | admin |
| GET PATCH | `/reservas/<id>/` | dono ou admin; PATCH só pendente |
| DELETE | `/reservas/<id>/` | cancela pendente/aprovada; admin precisa `justificativa` |
| PATCH | `/reservas/<id>/aprovar/` | admin |
| POST | `/reservas/<id>/checkin-antecipado/` | dono (`justificativa`) |
| POST | `/reservas/<id>/iniciar/` | legado, dono, mobile |
| POST | `/reservas/<id>/finalizar/` | legado, dono, mobile |

Exemplo de criação (turno):

```http
POST /api/reservas/
Authorization: Bearer eyJhbGciOi...
Content-Type: application/json

{
  "veiculo": 1,
  "modalidade": "turno",
  "turno": "manha",
  "data": "2026-11-02",
  "motivo": "VISITA TECNICA",
  "destino": "TAGUATINGA",
  "passageiros": 2
}
```

## Vistorias

| Método | Caminho | Quem |
|---|---|---|
| GET POST | `/vistorias/` | GET filtrado; POST **não** altera status da reserva |
| POST | `/vistorias/registrar/` | dono, **mobile**, 5 fotos; altera status |
| GET | `/vistorias/ultima-quilometragem/?veiculo=` | autenticado |
| GET POST | `/vistorias/fotos/` | dono/admin |
| GET DELETE | `/vistorias/fotos/<id>/` | DELETE só admin |
| GET | `/vistorias/<id>/` | dono/admin |
| DELETE | `/vistorias/<id>/` | admin |
| POST | `/vistorias/<id>/upload-fotos/` | dono/admin |

`registrar` (fluxo atual da UI): `reserva`, `tipo` (`checkin`|`checkout`), `unidade`, `quilometragem`, `fotos` (5), `descricoes` alinhadas a frente/tras/lateral_esq/lateral_dir/painel. Cabeçalho `X-Client-Form-Factor: mobile`.

## Termos

| Método | Caminho | Quem |
|---|---|---|
| GET POST | `/termos/` | filtrado; POST próprio |
| GET | `/termos/meu-status/` | próprio |
| GET | `/termos/<id>/` | dono/admin |
| PUT/PATCH | `/termos/<id>/decisao/` | admin |

## Auditoria e relatórios (somente admin)

| Método | Caminho |
|---|---|
| GET | `/auditoria/acoes/` |
| GET | `/auditoria/arquivos/` |
| GET | `/auditoria/integridade/` |
| GET | `/auditoria/opcoes/` |
| GET | `/relatorios/indicadores/` |
| GET | `/relatorios/opcoes/` |
| GET | `/relatorios/exportar/` (xlsx) |

Filtros de relatório: `de`, `ate` (AAAA-MM-DD), `veiculo`, `usuario`, `status`, `turno`.

## Códigos HTTP frequentes

| Código | Uso |
|---|---|
| 200 | OK, inclusive registrar idempotente |
| 201 | Criação |
| 400 | Validação (janela, fotos, justificativa, datas) |
| 401 | Token ausente/inválido |
| 403 | Perfil insuficiente ou senha não definida |
| 404 | Recurso fora do queryset (outro usuário) |
| 405 | Métodos não permitidos (auditoria é só GET) |
| 503 | Consulta FIPE indisponível |

## Alertas operacionais (contrato)

`GET /reservas/alertas-operacionais/` devolve `criticos`, `comuns`, `contagens`, `gerado_em`.

- Não admin: reservas `usuario=request.user`.
- Admin: todas + comuns (pendentes e check-in antecipado pendente).

Tipos críticos: `checkin_proximo_cancelamento`, `checkout_atrasado`, `cancelamento_automatico`.
