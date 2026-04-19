################################################################################
# Автоматическое исправление типовых ошибок после установки
################################################################################

log_step "Применение финальных патчей..."

# 1. Исправление прав на фронтенд для Nginx
if [[ -d "$INSTALL_DIR/frontend/build" ]]; then
    chown -R www-data:www-data "$INSTALL_DIR/frontend/build" 2>/dev/null || true
    log_info "✓ Права на фронтенд исправлены"
fi

# 2. Установка email-validator если не установлен
source "$INSTALL_DIR/venv/bin/activate"
if ! python3 -c "import email_validator" 2>/dev/null; then
    pip install email-validator --quiet
    log_info "✓ email-validator установлен"
fi

# 3. Создание пользователя admin через pgcrypto (если не создан)
PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;" 2>/dev/null

ADMIN_EXISTS=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM users WHERE username='admin';" 2>/dev/null | xargs)

if [[ "$ADMIN_EXISTS" == "0" ]]; then
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" << EOF 2>/dev/null
INSERT INTO users (email, username, full_name, hashed_password, role, is_superuser, is_active) 
VALUES ('admin@gochs.local', 'admin', 'Администратор', crypt('Admin123!', gen_salt('bf')), 'admin', TRUE, TRUE);
EOF
    log_info "✓ Пользователь admin создан"
else
    log_info "✓ Пользователь admin уже существует"
fi
deactivate

# 4. Исправление gochs-worker.service
if ! systemctl is-active --quiet gochs-worker; then
    # Упрощаем конфигурацию worker
    cat > /etc/systemd/system/gochs-worker.service << EOF
[Unit]
Description=ГО-ЧС Celery Worker
After=network.target redis-server.service postgresql.service

[Service]
Type=simple
User=$GOCHS_USER
Group=$GOCHS_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
ExecStart=$INSTALL_DIR/venv/bin/celery -A app.tasks.celery_app worker --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl restart gochs-worker
    log_info "✓ gochs-worker.service исправлен и перезапущен"
fi

# 5. Перезапуск API если не работает
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    systemctl restart gochs-api
    sleep 3
    log_info "✓ gochs-api перезапущен"
fi

log_info "Финальные патчи применены"
