<?php
/**
 * Питер-Свет — приём заявок с сайта.
 * Отправляет заявку в Telegram (и на почту, если указана), сохраняет копию в data/leads.csv.
 * Настройки — в api/config.php (создаётся при автодеплое из секретов GitHub, в репозиторий не попадает).
 */
declare(strict_types=1);

date_default_timezone_set('Europe/Moscow');

header('Content-Type: application/json; charset=utf-8');
header('X-Robots-Tag: noindex');

function respond(bool $ok, string $error = '', int $code = 200): void {
    http_response_code($code);
    echo json_encode($ok ? ['ok' => true] : ['ok' => false, 'error' => $error], JSON_UNESCAPED_UNICODE);
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    respond(false, 'Метод не поддерживается', 405);
}

$configFile = __DIR__ . '/config.php';
$config = is_file($configFile) ? require $configFile : [];
$tgToken = (string)($config['telegram_token'] ?? '');
$tgChat  = (string)($config['telegram_chat_id'] ?? '');
$mailTo  = (string)($config['mail_to'] ?? '');

$dataDir = __DIR__ . '/data';
if (!is_dir($dataDir)) {
    @mkdir($dataDir, 0750, true);
}

/* --- защита от ботов --- */
if (trim((string)($_POST['website'] ?? '')) !== '') {
    respond(true); // ловушка заполнена — тихо игнорируем
}
$ts = (int)($_POST['ts'] ?? 0);
if ($ts > 0 && (microtime(true) * 1000 - $ts) < 3000) {
    respond(false, 'Слишком быстро. Попробуйте ещё раз.', 429);
}

/* --- ограничение частоты: не больше 5 заявок в час с одного IP --- */
$ip = $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
$rlFile = $dataDir . '/ratelimit.json';
$rl = is_file($rlFile) ? (json_decode((string)file_get_contents($rlFile), true) ?: []) : [];
$now = time();
foreach ($rl as $k => $list) {
    $rl[$k] = array_values(array_filter((array)$list, fn($t) => $now - (int)$t < 3600));
    if (!$rl[$k]) unset($rl[$k]);
}
$key = hash('sha256', $ip);
if (count($rl[$key] ?? []) >= 5) {
    respond(false, 'Слишком много заявок. Позвоните: +7 960 160-44-25', 429);
}
$rl[$key][] = $now;
@file_put_contents($rlFile, json_encode($rl), LOCK_EX);

/* --- данные формы --- */
function clean(string $v, int $max): string {
    $v = trim(preg_replace('/\s+/u', ' ', strip_tags($v)) ?? '');
    return mb_substr($v, 0, $max);
}
$name    = clean((string)($_POST['name'] ?? ''), 80);
$phone   = clean((string)($_POST['phone'] ?? ''), 20);
$area    = clean((string)($_POST['area'] ?? ''), 120);
$calc    = clean((string)($_POST['calc'] ?? ''), 160);
$consent = ($_POST['consent'] ?? '') === '1';

$digits = preg_replace('/\D/', '', $phone) ?? '';
if (strlen($digits) !== 11) {
    respond(false, 'Проверьте номер телефона — нужно 11 цифр.', 422);
}
if (!$consent) {
    respond(false, 'Нужно согласие на обработку данных.', 422);
}
$phonePretty = '+7 ' . substr($digits, 1, 3) . ' ' . substr($digits, 4, 3) . '-' . substr($digits, 7, 2) . '-' . substr($digits, 9, 2);
$page = clean((string)($_SERVER['HTTP_REFERER'] ?? ''), 200);
$date = date('d.m.Y H:i');

/* --- копия в CSV (для статистики заявок) --- */
$csv = $dataDir . '/leads.csv';
$isNew = !is_file($csv);
if ($fh = @fopen($csv, 'ab')) {
    if (flock($fh, LOCK_EX)) {
        if ($isNew) fwrite($fh, "\xEF\xBB\xBF");
        if ($isNew) fputcsv($fh, ['дата', 'имя', 'телефон', 'площадь/район', 'калькулятор', 'страница'], ';');
        fputcsv($fh, [$date, $name, $phonePretty, $area, $calc, $page], ';');
        flock($fh, LOCK_UN);
    }
    fclose($fh);
}

/* --- текст уведомления --- */
$lines = ["⚡ Заявка с сайта Питер-Свет", "Имя: " . ($name ?: '—'), "Телефон: $phonePretty"];
if ($area !== '') $lines[] = "Объект: $area";
if ($calc !== '') $lines[] = "Калькулятор: $calc";
$lines[] = "Время: $date";
if ($page !== '') $lines[] = "Страница: $page";
$text = implode("\n", $lines);

$sent = false;

/* --- Telegram --- */
if ($tgToken !== '' && $tgChat !== '') {
    $payload = http_build_query(['chat_id' => $tgChat, 'text' => $text, 'disable_web_page_preview' => 'true']);
    $url = 'https://api.telegram.org/bot' . $tgToken . '/sendMessage';
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => $payload, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 10]);
        $res = curl_exec($ch);
        $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
    } else {
        $ctx = stream_context_create(['http' => ['method' => 'POST', 'header' => "Content-Type: application/x-www-form-urlencoded\r\n", 'content' => $payload, 'timeout' => 10]]);
        $res = @file_get_contents($url, false, $ctx);
        $code = $res === false ? 0 : 200;
    }
    $sent = $code === 200 && is_string($res) && str_contains($res, '"ok":true');
}

/* --- почта (запасной канал) --- */
if ($mailTo !== '') {
    $subject = '=?UTF-8?B?' . base64_encode('Заявка с сайта: ' . $phonePretty) . '?=';
    $headers = "Content-Type: text/plain; charset=utf-8\r\nFrom: noreply@" . ($_SERVER['HTTP_HOST'] ?? 'localhost');
    $sent = @mail($mailTo, $subject, $text, $headers) || $sent;
}

if (!$sent) {
    // Уведомление не ушло (не настроен бот или нет связи), но заявка сохранена в data/leads.csv
    error_log('Piter-Svet lead: notification not delivered, saved to CSV');
}
respond(true);
