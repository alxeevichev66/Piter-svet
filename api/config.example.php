<?php
// Образец настроек. Настоящий api/config.php создаётся автоматически при деплое
// из секретов GitHub (TG_BOT_TOKEN, TG_CHAT_ID, MAIL_TO, MAX_BOT_TOKEN, MAX_USER_ID). В репозиторий его не кладём.
return [
    'telegram_token'   => '123456789:AA...',   // токен бота от @BotFather
    'telegram_chat_id' => '123456789',         // ваш chat id (или id группы)
    'mail_to'          => '',                  // почта для копии заявок (необязательно)
    'max_token'        => '',                  // токен бота MAX (business.max.ru)
    'max_user_id'      => '',                  // ваш user_id в MAX (узнать: Actions → «MAX: узнать мой ID»)
];
