-- Apply after the checkpoint and research archive migrations.
-- Entire save rolls back if any insert fails. Existing checkpoints remain valid.
alter table public.simulation_checkpoints
    add column if not exists research_run_id uuid references public.simulation_runs(id);

create or replace function public.save_complete_world(p_checkpoint jsonb, p_archive jsonb)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_run_id uuid;
    v_record public.simulation_checkpoints;
begin
    if (p_checkpoint->>'tick')::bigint is distinct from (p_archive->>'current_tick')::bigint then
        raise exception 'Checkpoint and archive ticks must match';
    end if;
    v_run_id := public.archive_simulation(p_archive);
    insert into public.simulation_checkpoints
        (id, schema_version, label, tick, payload, research_run_id)
    values ((p_checkpoint->>'id')::uuid, (p_checkpoint->>'schema_version')::integer,
        p_checkpoint->>'label', (p_checkpoint->>'tick')::bigint,
        p_checkpoint->'payload', v_run_id)
    returning * into v_record;
    return (to_jsonb(v_record) - 'payload') || jsonb_build_object('archive_saved', true,
        'events', jsonb_array_length(coalesce(p_archive->'events', '[]'::jsonb)),
        'metrics', jsonb_array_length(coalesce(p_archive->'metrics', '[]'::jsonb)),
        'experiments', jsonb_array_length(coalesce(p_archive->'experiments', '[]'::jsonb)));
end;
$$;
revoke all on function public.save_complete_world(jsonb, jsonb) from public, anon, authenticated;
grant execute on function public.save_complete_world(jsonb, jsonb) to service_role;
