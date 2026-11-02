"""Read-only citizen conversation; dialogue never executes game actions."""
import json
import httpx

_busy = False


async def reply(entity, message, model):
    global _busy
    needs = entity.needs.model_dump() if entity.needs else {}
    context = {"name": entity.name, "diet": entity.diet,
               "needs": needs, "state": entity.metadata.get("state", "idle"),
               "reason": entity.metadata.get("last_decision_reason", "Not recorded")}
    fallback = (f"I'm {entity.name}. I'm currently {context['state']}. "
                f"My hunger is {needs.get('hunger', 0):.0f}/100 and energy is "
                f"{needs.get('energy', 0):.0f}/100. {context['reason']}")
    if not model or _busy:
        return {"reply": fallback, "source": "Simulation status fallback"}
    _busy = True
    try:
        async with httpx.AsyncClient(timeout=25, trust_env=False) as client:
            response = await client.post("http://127.0.0.1:11434/api/chat", json={
                "model": model, "stream": False,
                "options": {"num_predict": 150, "num_ctx": 2048},
                "messages": [{"role": "system", "content":
                    "Speak briefly in English as this simulated citizen. Use only supplied facts. "
                    "Dialogue cannot execute commands; never claim to give items or change the world. "
                    "If unknown, say so. Context: " + json.dumps(context)},
                    *entity.metadata.get("player_chat", [])[-6:],
                    {"role": "user", "content": message}]})
            response.raise_for_status()
            answer = response.json()["message"]["content"].strip()[:2000]
            if not answer:
                raise ValueError("Empty reply")
            return {"reply": answer, "source": "Local LLM · generated dialogue"}
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return {"reply": fallback, "source": "Model unavailable · simulation status fallback"}
    finally:
        _busy = False
