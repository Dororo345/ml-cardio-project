# ЛЗ 10 Подтверждения GitHub

Дата наблюдений 16.11.2026. Скриншоты сняты в браузере Work через интерфейс GitHub.

| Файл | Подтверждение | Источник |
| --- | --- | --- |
| 00_ruleset_active.jpg | Active, main, bypass list пуст | https://github.com/Dororo345/ml-cardio-project/settings/rules/27372146 |
| 01_ruleset.jpg | Обязательный PR, approvals 1 | тот же Ruleset |
| 01b_required_checks.jpg | quality, secrets, smoke required | тот же Ruleset |
| 02_direct_push_blocked.jpg | Веб-редактор запрещает прямой commit в main | зафиксирован при создании PR 43 |
| 03_red_pr_blocked.jpg | Неуспешные CI и disabled Merge; одновременно нет review | https://github.com/Dororo345/ml-cardio-project/pull/43 |
| 04_green_quality.jpg | 118 passed, coverage 86.53%, quality/secrets/smoke success | https://github.com/Dororo345/ml-cardio-project/actions/runs/43867721426/job/133300481078 |
| 05_wiki_dora.jpg | Определения четырёх DORA | https://github.com/Dororo345/ml-cardio-project/wiki |
| 05b_wiki_branch_policy.jpg | Правило ветки до трёх календарных дней | та же Wiki |
| 06_wiki_journal.jpg | Запись ЛЗ 10 | https://github.com/Dororo345/ml-cardio-project/wiki/%D0%96%D1%83%D1%80%D0%BD%D0%B0%D0%BB-%D1%81%D0%B4%D0%B0%D1%87 |
| 07_issue40.jpg | Реальные оставшиеся условия приёмки | https://github.com/Dororo345/ml-cardio-project/issues/40 |

Красный PR run: https://github.com/Dororo345/ml-cardio-project/actions/runs/43867157856

Исторический DORA run: https://github.com/Dororo345/ml-cardio-project/actions/runs/43864055516

Итоговый PR: https://github.com/Dororo345/ml-cardio-project/pull/44

PR 43 исправлен, закрыт без слияния, его тестовая ветка удалена. Ошибочный код в main не попадал. Проверка CI отдельно от review после уже полученного approval не выполнялась. Правило жизни веток опубликовано; согласие всех участников не заявляется. Отсутствующие ФИО владельца отката, согласование окна и независимый review перечислены в Issue 40. До merge PR 44 актуальная документация находится в его ветке.
