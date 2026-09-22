# Sharing / Передача друзьям

Репозиторий проекта: [yemelinart/locus](https://github.com/yemelinart/locus) — Public. [Выпуски](https://github.com/yemelinart/locus/releases).

## What to share

Locus is public: share https://github.com/yemelinart/locus or the presentation at https://yemelinart.github.io/locus/. Anyone can download the source without an invitation. Use a clean source ZIP when sharing files directly. Do not upload the working directory wholesale. `data/` contains research, settings and database backups; `.qa/` contains local checks. `.venv/`, `node_modules/`, credentials and model weights must not be included.

A source ZIP from a reviewed Git commit can be produced with `git archive --format=zip --prefix=Locus/ HEAD -o /path/outside/repository/Locus-source.zip`. It includes tracked files only. Review the tracked file list and history before the first push. The recipient installs dependencies and a model separately, following [START-HERE](../START-HERE.md).

The app does not run on GitHub Pages: it requires a local Python service and a local model. Each recipient runs their own installation. A research ZIP exported from Locus is an offline results archive, not an application installer.

## Если позже понадобится приватный GitHub

1. В своём аккаунте создайте репозиторий `locus` с видимостью **Private**. Не переключайте его в Public для удобства скачивания.
2. Загрузите проверенные исходники. README станет первой страницей проекта.
3. Для друга: Settings → Collaborators → Add people → его GitHub-логин. После принятия приглашения он сможет открыть репозиторий и скачать Code → Download ZIP.
4. Для версионированных выпусков используйте Releases с тегами и описанием изменений. Доступ к приватным выпускам требует входа и разрешения на репозиторий.

**Одной ссылки недостаточно:** GitHub не предоставляет режим приватного репозитория «доступ любому по секретной ссылке». Приглашённому нужен аккаунт. Приватные репозитории и участники доступны на GitHub Free.

**Уровень доступа:** в личном приватном репозитории приглашённый collaborator получает чтение и запись. Если нужен доступ только для чтения, используйте репозиторий организации с ролью Read либо передавайте чистый ZIP отдельно. Внешних участников не приглашайте до выбора нужного уровня доступа.

Приватность репозитория ограничивает доступ на GitHub. Она не отзывает уже скачанные копии. В проекте сохранена лицензия MIT, разрешающая получателю дальнейшее распространение кода с условиями лицензии; приватный репозиторий не является запретом копирования. Для публичного open-source выпуска можно позже осознанно открыть репозиторий.

[GitHub: приглашения](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository) · [GitHub: уровни доступа](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository)

## Updates

Stop the server and back up `data/` before updating. ZIP users should extract the new version into a new folder and carry over their own data. Git users can update their existing checkout. In both cases run setup again. No automatic updater, signed installer or bundled model is provided in this alpha.
