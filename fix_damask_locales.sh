cat > ~/fix_damask_locales.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

APP_ID="app.drey.Damask"

echo "==> Verificando que ${APP_ID} esté instalado…"
if ! flatpak info "${APP_ID}" >/dev/null 2>&1; then
  echo "ERROR: ${APP_ID} no está instalado. Instálalo así:"
  echo "  flatpak install --user flathub ${APP_ID}"
  exit 1
fi

echo "==> Asegurando Flathub en scope usuario…"
flatpak remote-add --if-not-exists --user flathub https://flathub.org/repo/flathub.flatpakrepo

echo "==> Detectando runtime de Damask…"
RT="$(flatpak info --show-runtime ${APP_ID})"       # ej: org.gnome.Platform/x86_64/48
BASE="$(echo "$RT" | cut -d/ -f1)"                  # org.gnome.Platform
BRANCH="$(echo "$RT" | cut -d/ -f3)"                # 48
echo "    Runtime: $RT"
echo "    Locale pkg: ${BASE}.Locale//${BRANCH}"

echo "==> Configurando idiomas preferidos en Flatpak (scope usuario)…"
flatpak config --user --set languages "es_CL;es;en" || true

echo "==> Instalando locales del runtime (user)…"
flatpak install -y --user flathub "${BASE}.Locale//${BRANCH}" es_CL || true
flatpak install -y --user flathub "${BASE}.Locale//${BRANCH}" es    || true

echo "==> (Opcional) Intentando locales Freedesktop 24.08 (por dependencias)…"
flatpak install -y --user flathub org.freedesktop.Platform.Locale//24.08 es_CL || true
flatpak install -y --user flathub org.freedesktop.Platform.Locale//24.08 es    || true

echo "==> Forzando variables de entorno de locale SOLO para Damask…"
flatpak override --user \
  --env=LANG=es_CL.UTF-8 \
  --env=LC_ALL=es_CL.UTF-8 \
  --env=LC_MESSAGES=es_CL.UTF-8 \
  ${APP_ID}

echo "==> Reiniciando xdg-desktop-portal (integración Pantheon)…"
systemctl --user restart xdg-desktop-portal.service  || true
systemctl --user restart xdg-desktop-portal-gtk.service || true

echo "==> Limpiando config/cache de Damask (por si quedó estado inválido)…"
rm -rf ~/.var/app/${APP_ID}/config/damask || true
rm -rf ~/.var/app/${APP_ID}/cache/damask  || true

echo "==> Verificando locales dentro del sandbox…"
flatpak run --command=sh ${APP_ID} -c 'locale -a | sort | grep -i es_cl || true'

echo
echo ">> Si ves 'es_CL.utf8' arriba, el locale ya está DISPONIBLE dentro del sandbox."
echo ">> Recomendado: cierra sesión y vuelve a entrar si aún ves warnings de GTK en la app."
echo
echo "==> Uso correcto de Damask para evitar 'web_url NULL':"
echo "   1) Abrir Damask: flatpak run ${APP_ID}"
echo "   2) En 'Sources', elegir Unsplash/Bing"
echo "   3) Buscar o abrir una categoría"
echo "   4) CLIC en una miniatura (que quede seleccionada)"
echo "   5) Recién ahí, 'Set Wallpaper'"
EOF
