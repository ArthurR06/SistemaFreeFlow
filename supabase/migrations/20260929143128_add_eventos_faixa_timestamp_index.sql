create index if not exists eventos_passagem_faixa_timestamp_idx
  on public.eventos_passagem (faixa, timestamp_evento);
