#!/usr/bin/env bash
# Собирает файл доверенных сертификатов: системные + НУЦ Минцифры (нужно для API MAX).
set -e
bundle="$1"
: > "$bundle.tmp"
cat /etc/ssl/certs/ca-certificates.crt >> "$bundle.tmp"; echo >> "$bundle.tmp"
for name in root sub; do
  curl -fsS -m 30 -o /tmp/ru_$name.crt "https://gu-st.ru/content/lending/russian_trusted_${name}_ca_pem.crt"
  if grep -q "BEGIN CERTIFICATE" /tmp/ru_$name.crt; then
    tr -d '\r' < /tmp/ru_$name.crt >> "$bundle.tmp"
  else
    openssl x509 -inform DER -in /tmp/ru_$name.crt >> "$bundle.tmp"
  fi
  echo >> "$bundle.tmp"
done
openssl x509 -in /tmp/ru_root.crt -noout -subject 2>/dev/null || openssl x509 -inform DER -in /tmp/ru_root.crt -noout -subject
mv "$bundle.tmp" "$bundle"
