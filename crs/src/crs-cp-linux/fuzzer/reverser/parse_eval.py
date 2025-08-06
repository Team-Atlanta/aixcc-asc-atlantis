import json
import sys
from pathlib import Path
sys.path.append('tools/')
from tools.hash_equivalence import is_equivalent

log_file = 'log/evaluation-0501-230827.json'
if len(sys.argv) > 1:
    log_file = sys.argv[1]

with open(log_file) as f:
    text = f.read()
res = json.loads(text)
counter = 0
for r in res:
    for h in r['result'].keys():
        a = r['result'][h]
        succ = a['success_count']
        uniq = a['unique_count']
        if succ * 2 < uniq:
            counter += 1
            print(f'{h} ========================')
            print(f'Successful {succ} Unique {uniq}')
            print('Answer ========================')
            if (Path(__file__).parent / f'answers/{h}-ext.txt').is_file():
                with open(Path(__file__).parent / f'answers/{h}-ext.txt') as f:
                    ans = f.read()
            else:
                with open(Path(__file__).parent / f'answers/{h}.txt') as f:
                    ans = f.read()
            print(ans)
            print('Generated ========================')
            for g in a['generated']:
                print(g)
            print('========================')
print(counter)
# NOTE following code is for checking a specific target
# for r in res:
#     h = 'CVE-2022-32250-2'
#     a = r['result'][h]
#     succ = a['success_count']
#     uniq = a['unique_count']
#     # if succ * 2 < uniq:
#     print(f'{h} ========================')
#     print('Answer ========================')
#     with open(Path(__file__).parent / f'answers/{h}.txt') as f:
#         ans = f.read()
#         print(ans)
#     print('Generated ========================')
#     for g in a['generated']:
#         try:
#             iseq = is_equivalent(ans, g)
#             print(iseq)
#         except:
#             print('Parse error')
#         print(g)
#     print('========================')
