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
$maxToken = (string)($config['max_token'] ?? '');
$maxUser  = (string)($config['max_user_id'] ?? '');

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
$area    = clean((string)($_POST['area'] ?? ''), 40);
$district = clean((string)($_POST['district'] ?? ''), 60);
$type    = clean((string)($_POST['type'] ?? ''), 30);
$comment = trim(mb_substr(strip_tags((string)($_POST['comment'] ?? '')), 0, 1000));
if ($area !== '' && preg_match('/^\d+([.,]\d+)?$/', $area)) $area .= ' м²';
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
        if ($isNew) fputcsv($fh, ['дата', 'имя', 'телефон', 'тип помещения', 'площадь', 'район', 'комментарий', 'калькулятор', 'страница'], ';');
        fputcsv($fh, [$date, $name, $phonePretty, $type, $area, $district, $comment, $calc, $page], ';');
        flock($fh, LOCK_UN);
    }
    fclose($fh);
}

/* --- текст уведомления --- */
$lines = ["⚡ Заявка с сайта Питер-Свет", "Имя: " . ($name ?: '—'), "Телефон: $phonePretty"];
if ($type !== '') $lines[] = "Помещение: $type";
if ($area !== '') $lines[] = "Площадь: $area";
if ($district !== '') $lines[] = "Район: $district";
if ($comment !== '') $lines[] = "Комментарий: $comment";
if ($calc !== '') $lines[] = "Калькулятор: $calc";
$lines[] = "Время: $date";
if ($page !== '') $lines[] = "Страница: $page";
$text = implode("\n", $lines);

$sent = false;

/* --- HTTP POST (curl, с запасным вариантом без curl) --- */
function http_post(string $url, string $body, array $headers, string $caFile = ''): array {
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        $opts = [CURLOPT_POST => true, CURLOPT_POSTFIELDS => $body, CURLOPT_RETURNTRANSFER => true,
                 CURLOPT_TIMEOUT => 10, CURLOPT_HTTPHEADER => $headers];
        if ($caFile !== '' && is_file($caFile)) $opts[CURLOPT_CAINFO] = $caFile;
        curl_setopt_array($ch, $opts);
        $res = curl_exec($ch);
        $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $err = curl_error($ch);
        curl_close($ch);
        return [$code, is_string($res) ? $res : '', $err];
    }
    $ssl = ($caFile !== '' && is_file($caFile)) ? ['cafile' => $caFile] : [];
    $ctx = stream_context_create(['http' => ['method' => 'POST', 'header' => implode("\r\n", $headers), 'content' => $body, 'timeout' => 10, 'ignore_errors' => true], 'ssl' => $ssl]);
    $res = @file_get_contents($url, false, $ctx);
    $code = 0;
    foreach ($http_response_header ?? [] as $h) if (preg_match('#^HTTP/\S+\s+(\d{3})#', $h, $m)) $code = (int)$m[1];
    return [$code, $res === false ? '' : $res, $res === false ? 'request failed' : ''];
}

/* --- Telegram --- */
if ($tgToken !== '' && $tgChat !== '') {
    $payload = http_build_query(['chat_id' => $tgChat, 'text' => $text, 'disable_web_page_preview' => 'true']);
    [$code, $res] = http_post('https://api.telegram.org/bot' . $tgToken . '/sendMessage', $payload, ['Content-Type: application/x-www-form-urlencoded']);
    $sent = ($code === 200 && str_contains($res, '"ok":true')) || $sent;
}

/* --- MAX --- */
if ($maxToken !== '' && $maxUser !== '') {
    // Основной домен API — platform-api2.max.ru с сертификатом НУЦ Минцифры (файл certs/cacert.pem кладётся при деплое).
    // Если он недоступен, пробуем прежний домен.
    $caFile = __DIR__ . '/certs/cacert.pem';
    $body = json_encode(['text' => $text, 'notify' => true], JSON_UNESCAPED_UNICODE);
    $headers = ['Authorization: ' . $maxToken, 'Content-Type: application/json'];
    $maxOk = false;
    foreach (['https://platform-api2.max.ru', 'https://platform-api.max.ru'] as $base) {
        [$code, $res, $err] = http_post($base . '/messages?user_id=' . rawurlencode($maxUser), (string)$body, $headers, $caFile);
        if ($code === 200) { $maxOk = true; break; }
        error_log("Piter-Svet lead: MAX $base -> HTTP $code $err " . mb_substr($res, 0, 200));
    }
    $sent = $maxOk || $sent;
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
