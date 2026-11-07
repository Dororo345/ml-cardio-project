"""Import LZ4 backlog + security tasks via GitHub CLI. Default: DRY RUN.

Requires: gh auth login, permission to write issues in target repo.
Run with --apply to perform remote changes (creates labels and issues).
"""
import argparse
import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def gh(*args, check=True):
    p = subprocess.run(['gh', *args], text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError(f"gh {' '.join(args[:2])} failed: {p.stderr.strip()}")
    return p.stdout


def create_issues(repo, apply):
    with (ROOT/'docs/backlog_LZ4.csv').open(encoding='utf-8-sig', newline='') as f:
        items = list(csv.DictReader(f))
    with (ROOT/'docs/security_issues.csv').open(encoding='utf-8-sig', newline='') as f:
        security = list(csv.DictReader(f))

    if apply:
        gh('repo','view',repo, '--json','name')
        existing = {x['title'] for x in json.loads(gh('issue','list','--repo',repo,
            '--state','all','--limit','500','--json','title'))}
        for name, color, desc in [
            ('type:story','1d76db','Пользовательская история'),
            ('type:security','d73a4a','Контроль безопасности'),
            ('release:mvp','0e8a16','Релиз MVP'),
            ('release:v2','fbca04','Версия 2'),
            ('release:v3','c2e0c6','Версия 3'),
            ('needs-verification','ededed','Нужна проверка фактического выполнения'),
        ]:
            gh('label','create',name,'--repo',repo,'--color',color,'--description',desc,'--force')
    else:
        existing = set()

    count = 0
    for row in items:
        issue_id = row['ID']
        title = f"{issue_id}: {row['Summary']}"
        if title in existing:
            print('SKIP existing:', title)
            continue
        body = (f"## Пользовательская история\n"
                f"Как {row['As a']}, я хочу {row['I want']}, чтобы {row['So that']}.\n\n"
                f"**Epic:** {row['Epic']}  \n**Release:** {row['Release']}  \n"
                f"**Story Points:** {row['Story Points']}\n\n"
                f"## Критерии приёмки (из ЛЗ4)\n{row['Acceptance criteria Given-When-Then']}\n\n"
                "## Подтверждение выполнения\n- [ ] Ссылка на commit/PR\n"
                "- [ ] Свидетельство тестирования\n\n"
                "Статус первоначально не подтверждён; не закрывать историю без проверки.\n")
        release=row['Release'].strip().lower().replace('версия ','v')
        release = release if release in ('mvp','v2','v3') else 'mvp'
        labels=['type:story',f'release:{release}','needs-verification']
        if apply:
            gh('issue','create','--repo',repo,'--title',title,'--body',body,
               *sum((['--label',label] for label in labels),[]))
        print('CREATE' if apply else 'PREVIEW',title)
        count+=1
    for row in security:
        title = f"{row['ID']}: {row['Summary']}"
        if title in existing:
            print('SKIP existing:', title)
            continue
        body = (f"**Плановый срок:** {row['Week']}\n\n"
                f"**Критерии приёмки:** {row['Acceptance']}\n\n"
                "- [ ] Проверить код и тесты\n- [ ] Приложить результаты/логи\n"
                "- [ ] Закрыть задачу только после подтверждения\n")
        if apply:
            gh('issue','create','--repo',repo,'--title',title,'--body',body,
               '--label','type:security','--label','needs-verification')
        print('CREATE' if apply else 'PREVIEW',title)
        count+=1
    print(f"Total candidate issues: {count}; mode: {'APPLY' if apply else 'DRY RUN'}")


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',default='Dororo345/ml-cardio-project')
    parser.add_argument('--apply',action='store_true',help='Actually create remote issues')
    args=parser.parse_args()
    create_issues(args.repo,args.apply)
