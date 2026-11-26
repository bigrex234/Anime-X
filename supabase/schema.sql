-- AnimeX Mega Update: run this whole script in Supabase SQL Editor.
-- User-owned tables are protected by RLS. Do not disable these policies.
create extension if not exists pgcrypto;

create table if not exists public.anime_library (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  anime_id bigint not null,
  title text not null,
  image text,
  status text not null default 'plan_to_watch'
    check (status in ('watching','completed','on_hold','dropped','plan_to_watch')),
  progress integer not null default 0 check (progress >= 0),
  is_favorite boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, anime_id)
);

create table if not exists public.recently_viewed (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  anime_id bigint not null,
  title text not null,
  image text,
  viewed_at timestamptz not null default now(),
  unique (user_id, anime_id)
);

-- Only administrator-curated assets with explicit permission belong here.
-- This table is not writable by public/authenticated clients.
create table if not exists public.downloadable_assets (
  id uuid primary key default gen_random_uuid(),
  anime_id bigint not null,
  title text not null,
  description text,
  source_url text not null,
  file_name text,
  mime_type text,
  rights_note text not null,
  is_active boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists anime_library_user_updated_idx
  on public.anime_library(user_id, updated_at desc);
create index if not exists recently_viewed_user_viewed_idx
  on public.recently_viewed(user_id, viewed_at desc);
create index if not exists downloadable_assets_anime_active_idx
  on public.downloadable_assets(anime_id, is_active);

alter table public.anime_library enable row level security;
alter table public.recently_viewed enable row level security;
alter table public.downloadable_assets enable row level security;

revoke all on public.anime_library from anon;
revoke all on public.recently_viewed from anon;
revoke all on public.downloadable_assets from anon;

grant select, insert, update, delete on public.anime_library to authenticated;
grant select, insert, update, delete on public.recently_viewed to authenticated;
grant select on public.downloadable_assets to anon, authenticated;

drop policy if exists "users manage their own anime library" on public.anime_library;
create policy "users manage their own anime library"
on public.anime_library for all to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "users manage their own recently viewed" on public.recently_viewed;
create policy "users manage their own recently viewed"
on public.recently_viewed for all to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "public can read active approved downloads" on public.downloadable_assets;
create policy "public can read active approved downloads"
on public.downloadable_assets for select to anon, authenticated
using (is_active = true);

-- Keep updated_at current for library upserts.
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists anime_library_set_updated_at on public.anime_library;
create trigger anime_library_set_updated_at
before update on public.anime_library
for each row execute function public.set_updated_at();

-- recently_viewed upserts update the timestamp.
create or replace function public.set_viewed_at()
returns trigger language plpgsql as $$
begin
  new.viewed_at = now();
  return new;
end;
$$;

drop trigger if exists recently_viewed_set_viewed_at on public.recently_viewed;
create trigger recently_viewed_set_viewed_at
before update on public.recently_viewed
for each row execute function public.set_viewed_at();

-- Example: only add an asset here when you have explicit distribution rights.
-- insert into public.downloadable_assets
--   (anime_id, title, source_url, rights_note, is_active)
-- values
--   (12345, 'Public-domain short film', 'https://your-authorized-host/file.mp4',
--    'Public domain / written distribution permission on file', true);
