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

## Не выполнено / требует реального подтверждения
- [ ] Реально включить защиту `main`: GitHub Settings → Rules → Rulesets; обязательный PR, успешные required CI checks и **1 независимый approving review**. Доступный для проверки список rulesets пуст.
- [ ] Сделать **намеренно красный** PR с неуспешным CI, убедиться, что GitHub запрещает Merge, и сохранить ссылку/снимок. **Нельзя считать выполненным без включённой защиты.**
- [ ] Подтвердить публикацию в GitHub Wiki правил жизни веток ≤3 дней и определений всех четырёх DORA. Markdown-файлы в `docs/` сами по себе не означают обновлённую Wiki.
- [ ] Назначить конкретного ответственного за откат (ФИО) и получить согласование окна релиза от заказчика; пока они не подтверждены, назначения и согласования нет.
- [x] После слияния поправок CFR: [main run 43864055516](https://github.com/Dororo345/ml-cardio-project/actions/runs/43864055516) завершён успешно (117 тестов приложения + 6 DORA-тестов; покрытие 86,53%; gitleaks и Docker smoke успешны). На момент этого запуска за 30 дней зафиксированы 2 успешных staging deployments: DF 0,467/нед., LT 0,034 ч, CFR 0/2, TTR N/A. Это **снимок на время указанного запуска**, а не статистически надёжная оценка.

Список доступных действий коннектора GitHub не включает изменение rulesets, branch protection и GitHub Wiki. Для этих операций необходим GitHub UI с правами владельца; заменять их фиктивной отметкой [x] нельзя.

Обратная ссылка на отслеживание незавершённых пунктов: [issue #40](https://github.com/Dororo345/ml-cardio-project/issues/40).
