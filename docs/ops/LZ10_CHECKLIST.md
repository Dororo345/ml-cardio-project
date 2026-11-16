# Лабораторная №10 — журнал фактов, артефактов и приёмки

Актуализация: 16 ноября 2026 г. Репозиторий: `Dororo345/ml-cardio-project`.

## Реально подтверждённые пункты
- [x] Два существовавших workflow проекта: GitHub run [43604189612](https://github.com/Dororo345/ml-cardio-project/actions/runs/43604189612) и [43604189619](https://github.com/Dororo345/ml-cardio-project/actions/runs/43604189619), success 14.11.2026.
- [x] Настроен LZ10 workflow с Ruff (E4/E9), pytest-cov ≥50%, gitleaks и Docker build/smoke.
- [x] Новый LZ10 workflow успешно завершён на main: [run 43860704653](https://github.com/Dororo345/ml-cardio-project/actions/runs/43860704653) (16.11.2026).
- [x] В LZ10 quality job пройдено **117 тестов**, покрытие **86,53%** при пороге 50%.
- [x] Готовы **3 артефакта этого запуска**: `lz10-v3-coverage` (XML), `gitleaks-results.sarif` (сканирование), `lz10-dora-dashboard` (JSON/CSV/PNG).
- [x] LZ10 PR [#39](https://github.com/Dororo345/ml-cardio-project/pull/39) объединён в main.
- [x] На основании GitHub Deployment ID `7823103737`, статус `success`, измерен первый baseline за 30 дней: DF 0,233/нед., LT 0,034 ч, CFR 0% (0/1), TTR N/A.
- [x] Созданы файл инцидентов, DORA-скрипт, план релиза и отката, понятные определения метрик.
- [x] Исправлен CFR с учётом связанных пострелизных `fix`/`rollback` (24 ч), добавлены 6 синтетических unit tests. [PR #41](https://github.com/Dororo345/ml-cardio-project/pull/41) объединён в `main` 16.11.2026.
- [x] В `docs/ops/TEAM_PROCESS.md` подготовлена инструкция о сроке жизни ветки ≤3 дней и текст для Wiki.

## Дополнительно проверено через GitHub UI 16 ноября 2026
- [x] Создан активный [Ruleset 27372146](https://github.com/Dororo345/ml-cardio-project/settings/rules/27372146), target `main`, без bypass actors.
- [x] Обязательны PR, 1 approving review от участника с write, сброс устаревших одобрений и актуальная ветка относительно main. Прямой коммит в main недоступен в веб-редакторе.
- [x] Required checks от GitHub Actions: `LZ10 quality and coverage`, `Scan Git history for secrets`, `Build and smoke-test ephemeral staging`. Заблокированы force push и удаление main.
- [x] Создан [тестовый PR #43](https://github.com/Dororo345/ml-cardio-project/pull/43) с намеренным `assert False`. [PR run 43867157856](https://github.com/Dororo345/ml-cardio-project/actions/runs/43867157856) завершил quality с ошибкой: 1 failed, 117 passed, 86,53% coverage. GitHub показал `Merging is blocked`, Merge disabled. Одновременно отсутствовало required review: отдельный опыт после уже полученного approval не выполнялся.
- [x] Намеренная ошибка заменена реальной проверкой HTTP 200 и HTML страницы /login в той же тестовой ветке. Ошибочный вариант не объединялся с main.
- [x] В [Wiki Home](https://github.com/Dororo345/ml-cardio-project/wiki) опубликованы определения четырёх DORA, определение deployment и правило жизни ветки не более трёх календарных дней. Это публикация правила, не доказательство его согласования всей командой.
- [x] Создана Wiki-страница [Журнал сдач](https://github.com/Dororo345/ml-cardio-project/wiki/%D0%96%D1%83%D1%80%D0%BD%D0%B0%D0%BB-%D1%81%D0%B4%D0%B0%D1%87) с записью ЛЗ 10, датой, исполнителем и ссылками.
- [x] План релиза дополнен протоколом готовности, явными несогласованными полями, предложенным датированным окном и текстом для согласования. Текст не отправлялся заказчику.

## Требует реального решения
- [ ] Получить независимый approving review итоговых изменений и объединить документацию в main; защиту не отключать ради сдачи.
- [ ] Назначить по ФИО единоличного владельца отката и подтвердить принятие ответственности.
- [ ] Получить от заказчика реальное согласование окна и сохранить ссылку/дату ответа.
- [ ] Утвердить итоговый релизный SHA, предыдущую версию и выполнить релизный чек-лист до согласованного выпуска.

Исторический снимок [main run 43864055516](https://github.com/Dororo345/ml-cardio-project/actions/runs/43864055516): 117 тестов приложения + 6 DORA-тестов; покрытие 86,53%; два успешных staging deployments за 30 дней, DF 0,467/нед., LT 0,034 ч, CFR 0/2, TTR N/A. Не считать этот снимок текущей статистикой всех последующих запусков. Падение тестового PR не является production-инцидентом и не добавляется в INCIDENTS.csv.

[Issue #40](https://github.com/Dororo345/ml-cardio-project/issues/40) остаётся открыт до реальной приёмки. Новые материалы проходят PR; пока он не объединён, актуальная версия находится в ветке PR, а main содержит предыдущую редакцию.


## Завершение демонстрационного опыта
- [x] [Повторный PR run 43867721426](https://github.com/Dororo345/ml-cardio-project/actions/runs/43867721426): quality, secrets и container smoke success; **118 passed** приложения, **6 passed** DORA, coverage **86,53%**. В интерфейсе наблюдались 12 успешных и 2 skipped checks; DORA job пропущен на PR по условию workflow.
- [x] PR #43 закрыт без слияния, тестовая ветка удалена 16.11.2026; коммиты и результаты доступны по ссылкам PR.
- [x] Issue #40 актуализирован и оставлен открытым для независимого review и реальных организационных решений.

Итоговая редакция документов и Word-отчёт со снимками собраны в [PR #44](https://github.com/Dororo345/ml-cardio-project/pull/44), ветка `lz10/final-work-evidence-20261116`. Объединение требует независимого одобрения; это требование не обходилось. До merge main содержит предыдущую редакцию документации.
