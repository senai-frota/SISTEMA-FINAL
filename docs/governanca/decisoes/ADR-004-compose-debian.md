# ADR-004 — Docker Compose em Debian

Empacotamento `db` + `backend` + `rotina` + `web`. PostgreSQL sem porta no host. Storage local. Settings ainda aceitam Supabase/Render via env (`BACKEND/.env.example`).

Consequência: dois modelos de env; o da **raiz** é o do Compose.
