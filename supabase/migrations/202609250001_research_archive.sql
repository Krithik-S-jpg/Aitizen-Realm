-- Normalized, immutable research archives for systems implemented by the backend.
create table public.simulation_runs (
    id uuid primary key,
    world_seed bigint,
    world_width integer not null check (world_width > 0),
    world_height integer not null check (world_height > 0),
    current_tick bigint not null check (current_tick >= 0),
    tick_rate double precision not null check (tick_rate > 0),
    calendar jsonb not null check (jsonb_typeof(calendar) = 'object'),
    created_at timestamptz not null default now()
);

create table public.research_experiments (
    run_id uuid not null references public.simulation_runs(id) on delete cascade,
    id uuid not null,
    name text not null check (char_length(name) between 1 and 120),
    seed bigint not null check (seed between 0 and 2147483647),
    parameters jsonb not null default '{}'::jsonb,
    status text not null check (status in ('DRAFT', 'ACTIVE', 'COMPLETED')),
    created_at_tick bigint not null check (created_at_tick >= 0),
    primary key (run_id, id)
);

create table public.metrics_snapshots (
    run_id uuid not null references public.simulation_runs(id) on delete cascade,
    tick bigint not null check (tick >= 0),
    population integer not null check (population >= 0),
    average_health double precision not null check (average_health between 0 and 100),
    average_hunger double precision not null check (average_hunger between 0 and 100),
    resources_available double precision not null check (resources_available >= 0),
    structures integer not null check (structures >= 0),
    completed_structures integer not null check (completed_structures >= 0),
    groups integer not null check (groups >= 0),
    communications integer not null check (communications >= 0),
    wildlife_by_species jsonb not null default '{}'::jsonb,
    births integer not null check (births >= 0),
    deaths integer not null check (deaths >= 0),
    primary key (run_id, tick)
);

create table public.world_events (
    run_id uuid not null references public.simulation_runs(id) on delete cascade,
    id uuid not null,
    sequence bigint not null check (sequence >= 0),
    tick bigint not null check (tick >= 0),
    event_type text not null check (char_length(event_type) between 1 and 40),
    severity text not null check (severity in ('INFO', 'SUCCESS', 'WARNING', 'DANGER')),
    title text not null check (char_length(title) between 1 and 80),
    summary text not null check (char_length(summary) between 1 and 240),
    entity_id uuid,
    x integer,
    y integer,
    data jsonb not null default '{}'::jsonb,
    primary key (run_id, id),
    unique (run_id, sequence)
);

create index simulation_runs_created_at_idx on public.simulation_runs (created_at desc);
create index research_experiments_status_idx on public.research_experiments (run_id, status);
create index world_events_tick_idx on public.world_events (run_id, tick, sequence);

alter table public.simulation_runs enable row level security;
alter table public.research_experiments enable row level security;
alter table public.metrics_snapshots enable row level security;
alter table public.world_events enable row level security;
revoke all on public.simulation_runs, public.research_experiments,
    public.metrics_snapshots, public.world_events from anon, authenticated;
grant select, insert on public.simulation_runs, public.research_experiments,
    public.metrics_snapshots, public.world_events to service_role;

create or replace function public.archive_simulation(p_archive jsonb)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
    v_run_id uuid := (p_archive->>'id')::uuid;
begin
    insert into public.simulation_runs (
        id, world_seed, world_width, world_height, current_tick, tick_rate, calendar
    ) values (
        v_run_id, nullif(p_archive->>'world_seed', '')::bigint,
        (p_archive->>'world_width')::integer, (p_archive->>'world_height')::integer,
        (p_archive->>'current_tick')::bigint, (p_archive->>'tick_rate')::double precision,
        p_archive->'calendar'
    );

    insert into public.research_experiments
        (run_id, id, name, seed, parameters, status, created_at_tick)
    select v_run_id, x.id, x.name, x.seed, x.parameters, x.status, x.created_at_tick
    from jsonb_to_recordset(coalesce(p_archive->'experiments', '[]'::jsonb)) as x(
        id uuid, name text, seed bigint, parameters jsonb, status text, created_at_tick bigint
    );

    insert into public.metrics_snapshots
        (run_id, tick, population, average_health, average_hunger,
         resources_available, structures, completed_structures, groups,
         communications, wildlife_by_species, births, deaths)
    select v_run_id, x.tick, x.population, x.average_health, x.average_hunger,
        x.resources_available, x.structures, x.completed_structures, x.groups,
        x.communications, x.wildlife_by_species, x.births, x.deaths
    from jsonb_to_recordset(coalesce(p_archive->'metrics', '[]'::jsonb)) as x(
        tick bigint, population integer, average_health double precision,
        average_hunger double precision, resources_available double precision,
        structures integer, completed_structures integer, groups integer,
        communications integer, wildlife_by_species jsonb, births integer, deaths integer
    );

    insert into public.world_events
        (run_id, id, sequence, tick, event_type, severity, title, summary,
         entity_id, x, y, data)
    select v_run_id, x.id, x.sequence, x.tick, x.event_type, x.severity,
        x.title, x.summary, x.entity_id, x.x, x.y, x.data
    from jsonb_to_recordset(coalesce(p_archive->'events', '[]'::jsonb)) as x(
        id uuid, sequence bigint, tick bigint, event_type text, severity text,
        title text, summary text, entity_id uuid, x integer, y integer, data jsonb
    );
    return v_run_id;
end;
$$;

revoke all on function public.archive_simulation(jsonb) from public, anon, authenticated;
grant execute on function public.archive_simulation(jsonb) to service_role;
