# ADR-002 — Vistoria atômica em dispositivo móvel

| Status | Aceito |
|---|---|

`POST /api/vistorias/registrar/` persiste vistoria, 5 fotos e mudança de status da reserva/veículo numa transação. Endpoints `iniciar`/`finalizar` ficaram legados (docstring nas views).

Mobile: redução de check-in “de mesa”. Limitação: cabeçalhos forjáveis.

Check-out na mesma unidade histórica (`unidade_checkin`) evita devolução em campus diferente do combinado.
