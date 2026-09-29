-- CASE 2027 — tabelas do banco (rodar UMA vez no Supabase: SQL Editor > New query > Run)
-- Segurança: RLS ligado e NENHUMA política => ninguém lê pela chave pública.
-- Só o app (com a chave SECRETA, guardada nos Secrets do Streamlit) acessa.

create table if not exists public.armazenamento (
  chave          text primary key,
  conteudo       text not null,
  atualizado_em  timestamptz not null default now(),
  atualizado_por text
);

create table if not exists public.auditoria (
  id      bigint generated always as identity primary key,
  quando  timestamptz not null default now(),
  quem    text,
  acao    text not null,
  detalhe jsonb
);
create index if not exists auditoria_quando_idx on public.auditoria (quando desc);

-- atualiza a data sozinho a cada gravação
create or replace function public.tocar_atualizado_em() returns trigger
language plpgsql set search_path = '' as $$
begin
  new.atualizado_em := now();
  return new;
end $$;

drop trigger if exists armazenamento_tocar on public.armazenamento;
create trigger armazenamento_tocar before update on public.armazenamento
  for each row execute function public.tocar_atualizado_em();

alter table public.armazenamento enable row level security;
alter table public.auditoria     enable row level security;
revoke all on public.armazenamento, public.auditoria from anon, authenticated;
