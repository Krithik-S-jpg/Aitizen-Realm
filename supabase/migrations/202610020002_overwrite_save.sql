-- Requires 202610020001_complete_save.sql. No existing data is deleted.
create or replace function public.overwrite_world_save(p_checkpoint jsonb, p_archive jsonb)
returns jsonb language plpgsql security definer set search_path = public
as $$
declare
    v_record public.simulation_checkpoints;
    v_run_id uuid;
begin
    select * into v_record from public.simulation_checkpoints
        where id = (p_checkpoint->>'id')::uuid for update;
    if not found then
        raise exception 'Selected save does not exist' using errcode = 'P0002';
    end if;
    if p_archive is not null and p_archive <> 'null'::jsonb then
        if (p_checkpoint->>'tick')::bigint is distinct from (p_archive->>'current_tick')::bigint then
            raise exception 'Checkpoint and archive ticks must match';
        end if;
        v_run_id := public.archive_simulation(p_archive);
    end if;
    update public.simulation_checkpoints set
        schema_version = (p_checkpoint->>'schema_version')::integer,
        tick = (p_checkpoint->>'tick')::bigint,
        payload = p_checkpoint->'payload',
        research_run_id = v_run_id
    where id = v_record.id returning * into v_record;
    -- Keep the slot's name and creation time. Older research archives remain historical.
    return (to_jsonb(v_record) - 'payload') || jsonb_build_object(
        'overwritten', true, 'archive_saved', v_run_id is not null,
        'events', jsonb_array_length(coalesce(p_archive->'events', '[]'::jsonb)),
        'metrics', jsonb_array_length(coalesce(p_archive->'metrics', '[]'::jsonb)),
        'experiments', jsonb_array_length(coalesce(p_archive->'experiments', '[]'::jsonb)));
end;
$$;
revoke all on function public.overwrite_world_save(jsonb, jsonb) from public, anon, authenticated;
grant execute on function public.overwrite_world_save(jsonb, jsonb) to service_role;
