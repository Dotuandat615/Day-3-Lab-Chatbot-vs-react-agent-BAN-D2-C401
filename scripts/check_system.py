"""Full system check - import all modules and test tools."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')
os.environ['HOSPITAL_DB_PATH'] = 'data/hospital.db'

print('=== FULL IMPORT CHECK ===')
errors = []

mods_to_test = [
    'src.telemetry.logger',
    'src.telemetry.metrics',
    'src.providers.base',
    'src.providers.local_llm',
    'src.chatbot.baseline_chatbot',
    'src.tools.tool_schema',
    'src.tools.tool_registry',
    'src.agent.agent',
    'src.core.openai_provider',
    'src.core.gemini_provider',
]

for mod in mods_to_test:
    try:
        __import__(mod)
        print(f'OK  {mod}')
    except Exception as e:
        errors.append(f'FAIL {mod} - {e}')
        print(f'ERR {mod} - {e}')

print()
print('=== TOOL TESTS ===')

try:
    from src.tools.tool_registry import run_tool, get_tool_names
    print('Tools registered:', get_tool_names())

    # Test 1: search with correct specialty name
    r = run_tool('search_available_slots', {'specialty': 'Tim mạch', 'date': '2026-06-09'})
    print(f'search Tim mach 2026-06-09: {r["status"]} | slots={len(r.get("slots", []))} | err={r.get("error_code")}')

    # Test 2: hallucinated tool
    r2 = run_tool('fake_tool', {})
    print(f'fake_tool: {r2["status"]} | {r2["error_code"]}')

    # Test 3: missing required field
    r3 = run_tool('search_available_slots', {'specialty': 'Da liễu'})
    print(f'missing date: {r3["status"]} | {r3["error_code"]}')

    # Test 4: bad date format
    r4 = run_tool('search_available_slots', {'specialty': 'Da liễu', 'date': '09/06/2026'})
    print(f'bad date format: {r4["status"]} | {r4["error_code"]}')

    # Test 5: suggest_alternative_dates
    r5 = run_tool('suggest_alternative_dates', {'specialty': 'Tim mạch', 'from_date': '2026-06-01'})
    alts = r5.get('alternatives', [])
    print(f'suggest_alternative_dates: {r5["status"]} | {len(alts)} alternatives')
    for a in alts[:2]:
        print(f'  -> {a["date"]} {a.get("time","?")} {a.get("doctor_name","?")}')

    # Test 6: rank_slots
    if r.get('slots'):
        r6 = run_tool('rank_slots', {'slots': r['slots'][:5]})
        best = r6.get('best_slot', {})
        print(f'rank_slots: best={best.get("slot_id")} doctor={best.get("doctor_name")} wait={best.get("estimated_wait_time")}')

except Exception as e:
    import traceback
    errors.append(f'FAIL tool tests - {e}')
    print(f'ERR tool tests:')
    traceback.print_exc()

print()
if errors:
    print(f'ERRORS ({len(errors)}):')
    for e in errors:
        print(f'  {e}')
else:
    print('ALL CHECKS PASSED!')
