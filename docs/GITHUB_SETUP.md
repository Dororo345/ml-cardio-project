# Перенос проекта в GitHub без потери истории

Репозиторий: https://github.com/Dororo345/ml-cardio-project

**Важно:** этот пакет собран после проверки предоставленного архива `ml-cardio-project-main.zip`, в котором было только четыре файла (три документа и короткий README). Исходная история коммитов `.git` в ZIP отсутствует, поэтому она не проверена. Перед публикацией рекомендуется сравнить с актуальной веткой GitHub; если после экспорта репозиторий обновлялся, сначала объедините изменения.

## 1. Клонирование и отдельная ветка

```powershell
git clone https://github.com/Dororo345/ml-cardio-project.git
cd ml-cardio-project
git switch -c chore/cardio-week9-hardening
```

## 2. Сравните и перенесите изменения

Из предоставленного ZIP скопируйте **содержимое** папки `ml-cardio-project` внутрь свежего клона, в том числе папку `.github` (в Windows она может быть скрыта). Историю `.git` никогда не перезаписывайте. В предоставленном снимке кода не было, но если в GitHub уже появились новые файлы, не затирайте их без проверки.

Пример PowerShell из папки клона (замените путь распаковки):

```powershell
$from = "C:\path\to\ml-cardio-project"
Get-ChildItem -LiteralPath $from -Force | Copy-Item -Destination . -Recurse -Force
```

Проверьте `git status`, `git diff`, не допустите секретов, `.env` и реальных пациентских данных.

```powershell
python -m pytest -q
git status
git diff --check
git add .
git commit -m "Harden Flask MVP and add GitHub project tooling"
git push -u origin chore/cardio-week9-hardening
```

Создайте Pull Request из ветки в `main` после успешного тестирования и проверки кода.

## 3. Issues из ЛЗ4 + безопасности

Установите GitHub CLI (`gh`) и выполните `gh auth login`, затем:

```powershell
python scripts/create_github_issues.py --repo Dororo345/ml-cardio-project
# Это preview (dry run), без создания
python scripts/create_github_issues.py --repo Dororo345/ml-cardio-project --apply
```

Скрипт пытается не дублировать Issues с одинаковым заголовком; сначала создаёт нужные labels. Чтобы проверить права, выполните `gh repo view Dororo345/ml-cardio-project`.

## 4. GitHub Projects

В GitHub откройте Projects -> New project -> Board. Назовите `КардиоПрогноз — 15 недель` и создайте поля `Status`, `Release`, `SP`, `Week`. Колонки: `Todo`, `In Progress`, `In Review`, `Done`. Добавьте Issues `CARD-*` и `SEC-*` в доску, связывайте их с PR/commit и показывайте реальные статусы.

## 5. CI и безопасность

После push откройте вкладку Actions и проверьте результаты `CI (tests)` и `Security scans`. Файл workflow **не равен** успешному сканированию. Ошибки исправляются по фактическим логам, а не по симулированным CVE.

При отсутствии доступа к репозиторию можно передать ZIP архива текущей версии для точного сравнения.
