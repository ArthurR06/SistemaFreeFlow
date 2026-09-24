-- Privilegios de execucao da aplicacao Free Flow.
-- A funcao com LOGIN e sua senha sao criadas fora da migracao para que nenhum
-- segredo seja versionado. Esta funcao NOLOGIN concentra apenas os privilegios
-- necessarios para o backend operar as tabelas atuais.
do $$
begin
  if not exists (
    select 1 from pg_roles where rolname = 'freeflow_backend'
  ) then
    create role freeflow_backend
      nologin
      nosuperuser
      nocreatedb
      nocreaterole
      noinherit
      nobypassrls;
  end if;
end
$$;

revoke all on table
  public.proprietarios,
  public.veiculos,
  public.eventos_passagem,
  public.cobrancas,
  public.usuarios_concessionarias
from public;

revoke all on table
  public.proprietarios,
  public.veiculos,
  public.eventos_passagem,
  public.cobrancas,
  public.usuarios_concessionarias
from freeflow_backend;

grant select, insert, update on table
  public.proprietarios,
  public.veiculos,
  public.eventos_passagem,
  public.cobrancas,
  public.usuarios_concessionarias
to freeflow_backend;

revoke all on sequence
  public.proprietarios_id_seq,
  public.veiculos_id_seq,
  public.eventos_passagem_id_seq,
  public.cobrancas_id_seq,
  public.usuarios_concessionarias_id_seq
from freeflow_backend;

grant usage, select on sequence
  public.proprietarios_id_seq,
  public.veiculos_id_seq,
  public.eventos_passagem_id_seq,
  public.cobrancas_id_seq,
  public.usuarios_concessionarias_id_seq
to freeflow_backend;

grant usage on schema public to freeflow_backend;
revoke create on schema public from freeflow_backend;

drop policy if exists freeflow_backend_select on public.proprietarios;
drop policy if exists freeflow_backend_insert on public.proprietarios;
drop policy if exists freeflow_backend_update on public.proprietarios;
create policy freeflow_backend_select on public.proprietarios
  for select to freeflow_backend using (true);
create policy freeflow_backend_insert on public.proprietarios
  for insert to freeflow_backend with check (true);
create policy freeflow_backend_update on public.proprietarios
  for update to freeflow_backend using (true) with check (true);

drop policy if exists freeflow_backend_select on public.veiculos;
drop policy if exists freeflow_backend_insert on public.veiculos;
drop policy if exists freeflow_backend_update on public.veiculos;
create policy freeflow_backend_select on public.veiculos
  for select to freeflow_backend using (true);
create policy freeflow_backend_insert on public.veiculos
  for insert to freeflow_backend with check (true);
create policy freeflow_backend_update on public.veiculos
  for update to freeflow_backend using (true) with check (true);

drop policy if exists freeflow_backend_select on public.eventos_passagem;
drop policy if exists freeflow_backend_insert on public.eventos_passagem;
drop policy if exists freeflow_backend_update on public.eventos_passagem;
create policy freeflow_backend_select on public.eventos_passagem
  for select to freeflow_backend using (true);
create policy freeflow_backend_insert on public.eventos_passagem
  for insert to freeflow_backend with check (true);
create policy freeflow_backend_update on public.eventos_passagem
  for update to freeflow_backend using (true) with check (true);

drop policy if exists freeflow_backend_select on public.cobrancas;
drop policy if exists freeflow_backend_insert on public.cobrancas;
drop policy if exists freeflow_backend_update on public.cobrancas;
create policy freeflow_backend_select on public.cobrancas
  for select to freeflow_backend using (true);
create policy freeflow_backend_insert on public.cobrancas
  for insert to freeflow_backend with check (true);
create policy freeflow_backend_update on public.cobrancas
  for update to freeflow_backend using (true) with check (true);

drop policy if exists freeflow_backend_select on public.usuarios_concessionarias;
drop policy if exists freeflow_backend_insert on public.usuarios_concessionarias;
drop policy if exists freeflow_backend_update on public.usuarios_concessionarias;
create policy freeflow_backend_select on public.usuarios_concessionarias
  for select to freeflow_backend using (true);
create policy freeflow_backend_insert on public.usuarios_concessionarias
  for insert to freeflow_backend with check (true);
create policy freeflow_backend_update on public.usuarios_concessionarias
  for update to freeflow_backend using (true) with check (true);
