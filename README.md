Структра проета
```bont
/opt/gochs-informing/
├── app/                # Бэкенд (FastAPI)
│   ├── main.py         # Точка входа
│   ├── core/           # Конфигурация, безопасность
│   ├── api/            # Эндпоинты API
│   ├── services/       # Бизнес-логика (звонки, контакты, сценарии)
│   ├── tasks/          # Фоновые задачи (Celery/RQ)
│   ├── models/         # Модели БД (SQLAlchemy)
│   ├── schemas/        # Pydantic-схемы
│   └── utils/          # Вспомогательные функции
├── frontend/           # Фронтенд (React)
├── recordings/         # Аудиозаписи разговоров
├── generated_voice/    # Сгенерированные TTS-файлы
├── playbooks/          # Приветствия для входящих звонков
├── logs/               # Логи приложения
├── backups/            # Резервные копии БД и конфигураций
├── installer/          # Скрипты для установки (install.sh)
└── exports/            # Файлы для импорта/экспорта данных
```
