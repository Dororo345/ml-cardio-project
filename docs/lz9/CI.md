# Проверки изменений

CI выполняет compileall и pytest на Python 3.11, затем DOM-тесты формы на Node 22. npm ci использует package-lock.json. JUnit XML сохраняется через upload-artifact даже при неуспешном тесте. Проверка не является клинической валидацией модели.

Команды: `python -m compileall -q app.py validation.py xai.py tests scripts/lz9`; `python -m pytest -q --junitxml=test-results/pytest.xml`; `npm ci && npm test`.
