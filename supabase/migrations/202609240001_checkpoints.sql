-- Server-only immutable backup storage. No anonymous or user access.
create table public.simulation_checkpoints (
    id uuid primary key,
    schema_version integer not null check (schema_version = 1),
    label text not null check (char_length(label) between 1 and 120),
    tick bigint not null check (tick >= 0),
    payload jsonb not null check (jsonb_typeof(payload) = 'object'
        and payload ? 'world' and payload ? 'calendar' and payload ? 'tick_rate'),
    created_at timestamptz not null default now()
);
create index simulation_checkpoints_created_at_idx
    on public.simulation_checkpoints (created_at desc);
alter table public.simulation_checkpoints enable row level security;
revoke all on public.simulation_checkpoints from anon, authenticated;
grant select, insert on public.simulation_checkpoints to service_role;
