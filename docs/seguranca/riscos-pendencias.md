# Riscos e pendências

| Campo | Valor |
|---|---|
| Versão | 1.0 |
| Data | 26 de outubro de 2026 |
| Classificação | Uso interno |

Probabilidade e impacto são estimativas de engenharia, não análise quantitativa.

| ID | Descrição | Impacto | Prob. | Evidência | Prioridade | Mitigação | Status |
|---|---|---|---|---|---|---|---|
| R01 | Tráfego HTTP sem TLS no Compose | Credenciais em claro | Alta em LAN aberta | `listen 80` | Alta | Proxy TLS | Confirmado |
| R02 | Arquivos em `/media/` sem autenticação no Nginx | Vazamento de CNH/fotos se URL vazar | Média | `nginx/default.conf` | Alta | URLs assinadas ou auth no proxy | Confirmado |
| R03 | Sem backup automático | Perda de dados | Média | Compose sem cron | Alta | Job + ensaio de restore | Confirmado |
| R04 | FIPE indisponível | Cadastro assistido pela FIPE falha; cadastro manual permanece | Baixa | `veiculos/services.py` responde 503 | Baixa | Cadastro manual | Mitigado (503 + mensagem) |
| R05 | `DEBUG=True` default no settings se env omitido | Vazamento de traceback | Baixa no Compose (False) | `settings.py` | Média | Nunca omitir DEBUG em prod | Confirmado |
| R06 | Cabeçalho mobile forjável | Check-in via script | Baixa/média | `dispositivo.py` | Média | Aceitar como política ou 2FA operacional | Confirmado |
| R07 | Unicidade CPF/CNH só no serializer | Duplicidade concorrente | Baixa | models vs serializers termos | Baixa | unique constraint | Confirmado |
| R08 | E-mail desligado | Alertas só na UI | — | `FROTA_EMAIL_ENABLED` | Baixa | Ativar com TI | Confirmado (intencional) |
| R09 | Sem CI | Regressão não detectada no push | Média | ausência de workflows | Média | pipeline test+build | Confirmado |
| R10 | Relato de alerta visível a usuário que não é o dono | Falso alarme | — | investigação 26/10/2026 | — | Filtro original `usuario=usuario` restaurado | Hipótese encerrada |
| R11 | LGPD / retenção de documentos | Jurídico | — | dados pessoais no banco e media | Alta institucional | Política e RIPD | Pendente de validação (não afirmada) |
| R12 | Restore de dump não ensaiado | RTO desconhecido | — | docs de backup | Alta operacional | Drill em ambiente isolado | Pendente de validação (não ensaiado) |
| R13 | Dois `.env.example` (raiz vs BACKEND) | Operador usar o arquivo errado | Média | arquivos no repo | Baixa | Seguir o da raiz no Compose | Confirmado |
| R14 | Check-out sem teto temporal | Devolução possível muito após o fim da reserva | Média | `validar_checkout_horario_reserva` só bloqueia cedo demais; `MSG_CHECKOUT_DEPOIS` não é chamada | Média | Decidir se o teto deve ser implementado | Confirmado no código; **não** é pentest |
