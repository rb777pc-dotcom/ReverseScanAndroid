# Скачать и установить ReverseScan 3D

## Скачать готовое приложение

1. Откройте [последнюю успешную полную сборку](https://github.com/rb777pc-dotcom/ReverseScanAndroid/actions/runs/45489640048).
2. Внизу страницы найдите блок **Artifacts**.
3. Скачайте архив **ReverseScan-full**.
4. Распакуйте ZIP и установите файл `app-debug.apk`.

**Важно:** `ReverseScan-native` — вспомогательная внутренняя сборка, а не полный сканер. Архивы **Source code** также не являются установочными файлами.

Для последующих версий откройте [список сборок](https://github.com/rb777pc-dotcom/ReverseScanAndroid/actions/workflows/reversescan-full-build.yml), выберите последний успешный запуск workflow **Build ReverseScan 3D scanner** и скачайте артефакт **ReverseScan-full**.

Артефакты GitHub Actions временные и удаляются по истечении срока хранения. Постоянный раздел Releases пока не настроен.

## Установка на Android

1. Перенесите `app-debug.apk` на телефон или скачайте его непосредственно на телефон.
2. Откройте APK через файловый менеджер.
3. Если Android запросит разрешение, разрешите установку приложений из этого источника.
4. Запустите ReverseScan 3D и предоставьте доступ к камере.
5. Дождитесь инициализации Google Play Services for AR.

Для работы требуется Android-устройство с поддержкой ARCore Depth API. Эмулятор не позволяет полноценно проверить камеру и захват глубины.

## Если возникла проблема

Создайте обращение в [Issues](https://github.com/rb777pc-dotcom/ReverseScanAndroid/issues/new/choose). Укажите модель телефона, версию Android, номер сборки и последовательность действий, после которой возникла ошибка.

## Для разработчиков

Полный сканер собирается workflow [Build ReverseScan 3D scanner](.github/workflows/reversescan-full-build.yml). В корневом каталоге `app/` находится вспомогательная нативная цель для предварительной сборки и JVM-тестов; её APK не является полной версией сканера.
