#!/usr/bin/env python3
"""Apply the ReverseScan usability and reconstruction fixes to the pinned Strata checkout."""
from pathlib import Path
import base64
import re

ROOT = Path(__file__).resolve().parent.parent / "strata"

def replace_once(path, old, new):
    p = ROOT / path
    s = p.read_text()
    if old not in s:
        lines = s.splitlines()
        candidates = [i for i, line in enumerate(lines) if any(token in line for token in ("camera = cam", "imageCapture = capture", "bindToLifecycle", "unbindAll", "previewView = null"))]
        context = "\\n".join("\\n".join(lines[max(0, i-3):min(len(lines), i+7)]) for i in candidates[:8])
        raise SystemExit(
            f"Expected source block not found in {path}.\\n"
            f"Missing anchor: {old!r}\\n"
            f"Nearby source context:\\n{context}\\n"
            "Refusing partial patch"
        )
    p.write_text(s.replace(old, new, 1))

# The first MVE SfM run must be deterministic. The upstream code previously started
# with 2-4 threads, then retried single-threaded after the initial pair had already
# been selected and saved. That cannot repair a bad initial pair.
replace_once(
    "app/src/main/java/app/strata3d/capture/recon/ReconRunner.kt",
    "var sfmOk = exec(\"sfmrecon\", ReconPlan.Args.sfm(scene.path, settings.sfm), Stage.CAMERAS, settings.threads,\n            guardMb = if (settings.sfm == ReconPlan.SfmSetting.HIGH) ReconPlan.GUARD_MB else null)",
    "var sfmOk = exec(\"sfmrecon\", ReconPlan.Args.sfm(scene.path, settings.sfm), Stage.CAMERAS, threads = 1,\n            guardMb = if (settings.sfm == ReconPlan.SfmSetting.HIGH) ReconPlan.GUARD_MB else null)"
)

# Always start in automatic capture when motion sensors are available. Do not restore a
# previous manual selection silently; that was a common reason users had to tap every shot.
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "val mode = if (!sensors.available) Mode.MANUAL else Mode.entries.firstOrNull { it.name == prefs.getString(KEY_MODE, null) } ?: Mode.SMART",
    "val mode = if (!sensors.available) Mode.MANUAL else Mode.SMART"
)

# Russian capture/library strings. Keep Android format arguments unchanged.
capture_ru = {
"capture_entry":"Съёмки", "capture_object":"Отсканировать предмет",
"captures_title":"Мои съёмки", "capture_new":"Новая съёмка",
"captures_empty_title":"Сделайте первую съёмку",
"captures_empty_body":"Медленно обойдите неподвижный предмет с телефоном. Приложение автоматически делает резкие фотографии со всех сторон для построения 3D-модели.",
"capture_untitled":"Съёмка %1$s", "capture_stats":"%1$d фото · охват ракурсов %2$d%% · %3$s",
"capture_interrupted":"Прервано · сохранено фото: %1$d", "capture_rename":"Переименовать",
"capture_export":"Экспорт ZIP", "capture_delete":"Удалить",
"capture_delete_title":"Удалить эту съёмку?", "capture_delete_body":"Все %1$d фотографий будут удалены с телефона. Отменить это действие нельзя.",
"capture_rename_title":"Переименовать съёмку", "capture_name_hint":"Название",
"capture_exporting":"Экспорт: %1$d%%…", "capture_exported":"Съёмка экспортирована",
"capture_export_failed":"Не удалось экспортировать. Проверьте свободное место.",
"capture_more":"Дополнительно", "capture_device_report":"Сведения об устройстве",
"capture_back":"Назад", "capture_copy":"Копировать", "capture_copied":"Скопировано",
"cancel":"Отмена", "save":"Сохранить", "close":"Закрыть",
"capture_permission_title":"Нужен доступ к камере",
"capture_permission_body":"Камера используется только во время съёмки. Фотографии сохраняются на этом телефоне.",
"capture_permission_allow":"Разрешить камеру", "capture_permission_settings":"Открыть настройки",
"capture_close":"Закрыть съёмку", "capture_done":"Готово",
"capture_coverage_desc":"Охват ракурсов: %1$d%%",
"capture_leave_title":"Сохранить эту съёмку?", "capture_leave_body":"Сделано фотографий: %1$d.",
"capture_keep":"Сохранить", "capture_discard":"Удалить",
"capture_error_title":"Съёмка остановлена",
"guide_hot":"Телефон перегрелся. Съёмка приостановлена до охлаждения.",
"guide_low_storage":"Почти закончилось место. Съёмка приостановлена.",
"guide_paused":"Съёмка на паузе",
"capture_saved":"Съёмка сохранена", "capture_summary_photos":"Фотографии",
"capture_summary_covered":"Охват ракурсов", "capture_summary_size":"Размер",
"capture_summary_missing_low":"Не хватает ракурсов снизу.",
"capture_summary_missing_mid":"Не хватает ракурсов сверху.",
"capture_summary_complete":"Все стороны объекта охвачены.",
"capture_summary_next":"Можно запускать построение 3D-модели.",
"capture_tap_object":"Нажмите на предмет в кадре, чтобы начать съёмку",
"capture_keep_moving":"Продолжайте медленно обходить предмет",
"capture_hold_steady":"Остановите телефон на мгновение",
"capture_saving_photo":"Сохраняю фотографию…",
"capture_manual_hint":"Нажмите кнопку затвора для каждого снимка",
"capture_photo_failed":"Не удалось сохранить фото. Автосъёмка приостановлена.",
"capture_no_sensors":"Нет датчиков движения. Используйте ручную съёмку.",
"capture_count":"Фото: %1$d · рекомендуется 40 и более",
"capture_mode_smart":"Автосъёмка", "capture_mode_manual":"Вручную",
"capture_pause_short":"Пауза", "capture_resume":"Продолжить",
"capture_shutter_desc":"Сделать фото",
"capture_shutter_locked":"Сначала нажмите на объект в кадре",
"capture_shutter_setting":"Кнопка съёмки",
"capture_shutter_smart_desc":"Фото делается автоматически, когда вы меняете ракурс и на мгновение останавливаете телефон.",
"capture_shutter_manual_desc":"Каждое фото делается нажатием кнопки.",
"capture_guide_title":"Обойдите предмет по кругу",
"capture_guide_body":"Держите предмет в центре кадра. Автосъёмка делает фото сама, когда ракурс изменился и телефон неподвижен. Для верхних ракурсов слегка наклоните камеру вниз. Индикатор показывает охват ракурсов по наклону телефона, а не измеряет отснятые участки поверхности.",
"capture_guide_done":"Бирюзовый — снято",
"capture_object":"Сканировать предмет",
"capture_new":"Новая съёмка",
"capture_stats":"%1$d фото · охват ракурсов %2$d%% · %3$s",
"capture_rename":"Переименовать",
"capture_delete":"Удалить",
"capture_delete_body":"Все %1$d фотографий будут удалены с телефона. Отменить это действие нельзя.",
"capture_name_hint":"Название",
"capture_exported":"Съёмка экспортирована",
"capture_device_report":"Сведения об устройстве",
"capture_copy":"Копировать",
"capture_copied":"Скопировано",
"save":"Сохранить",
"close":"Закрыть",
"capture_permission_settings":"Открыть настройки",
"capture_done":"Готово",
"capture_leave_body":"Сделано фотографий: %1$d.",
"capture_discard":"Удалить",
"capture_summary_photos":"Фотографии",
"capture_summary_size":"Размер",
"capture_mode_manual":"Вручную",
"capture_resume":"Продолжить",
"capture_import":"Импортировать съёмку из ZIP",
"capture_import_short":"Импорт ZIP",
"capture_new_scan":"Начать новое сканирование",
"capture_torch_on":"Фонарик ВКЛ",
"capture_torch_off":"Фонарик ВЫКЛ",
"capture_coverage_title":"Карта ракурсов",
"capture_coverage_done":"Бирюзовый сектор — ракурс уже снят",
"capture_coverage_missing":"Серый сектор — ракурс ещё нужен",
"capture_coverage_bottom":"Нижнюю сторону под столом можно доснять отдельно, перевернув предмет",
"capture_guide_missing":"Серый — ещё не снято",
}
recon_ru = {
"recon_channel":"Построение 3D-модели", "recon_notification_title":"Строю 3D-модель",
"recon_notification_starting":"Подготовка…", "recon_stage_import":"Подготовка фотографий",
"recon_stage_cameras":"Сопоставление фотографий и ракурсов",
"recon_stage_box":"Определение границ предмета",
"recon_stage_depth":"Расчёт глубины", "recon_stage_points":"Построение облака точек",
"recon_stage_surface":"Построение поверхности", "recon_stage_ground":"Удаление поверхности под предметом",
"recon_stage_clean":"Очистка модели", "recon_stage_texture":"Перенос цвета и текстуры",
"recon_stage_steps":"%1$s (%2$d из %3$d)",
"recon_build_title":"Построить 3D-модель",
"recon_build_body":"Построение выполняется на телефоне и может занять 5–25 минут. Можно свернуть приложение — процесс продолжится.",
"recon_build":"Построить модель", "recon_building":"Идёт построение 3D-модели",
"recon_step":"Этап %1$d из %2$d · %3$s", "recon_elapsed":"Прошло %1$s",
"recon_leave_hint":"Можно выйти из приложения. Ход построения также виден в уведомлении.",
"recon_placed_detail":"%1$s · использовано %2$d из %3$d фото",
"recon_ready":"Модель готова", "recon_ready_time":"Построено за %1$s",
"recon_ready_stats":"Время: %1$s · использовано фото: %2$d из %3$d · точек: %4$s",
"recon_ready_gaps":"Не удалось сопоставить %1$d фото (возможно, из-за однотонных или блестящих поверхностей). В этих местах могут быть пробелы.",
"recon_open":"Открыть 3D-модель", "recon_build_again":"Построить заново",
"recon_failed":"Не удалось построить модель", "recon_try_again":"Повторить",
"recon_cancelled_note":"Предыдущее построение было отменено.",
"recon_minutes_seconds":"%1$d мин %2$d с", "recon_seconds":"%1$d с",
"recon_err_unsupported":"Процессор этого телефона не поддерживается для построения модели.",
"recon_err_storage":"Недостаточно свободного места. Освободите память и повторите попытку.",
"recon_err_memory":"Телефону не хватило оперативной памяти. Закройте другие приложения и повторите попытку.",
"recon_err_placed":"Фотографии не удалось надёжно сопоставить. Съёмка не подходит для построения модели. Повторите съёмку медленно, обходя предмет по кругу и сохраняя его в центре кадра.",
"recon_err_no_object":"Фотографии не показывают один и тот же предмет с разных сторон. Повторите съёмку, обходя предмет и удерживая его в центре кадра.",
"recon_err_tap":"Выбранная точка не совпадает с предметом на фотографиях. Повторите съёмку и нажмите именно на предмет.",
"recon_err_tool":"Ошибка на этапе построения модели. Подробности сохранены в журнале. Повторите попытку.",
"recon_err_interrupted":"Построение неожиданно остановилось. Повторите попытку.",
"recon_review_switch":"Проверить границы предмета перед построением",
"recon_review_switch_body":"Если выключено — приложение определит границы автоматически. Если включено — остановится после сопоставления фотографий, чтобы вы могли проверить рамку.",
"recon_review_title":"Проверьте рамку предмета",
"recon_review_body":"Сопоставлено фото: %1$d из %2$d. Проверьте, что рамка охватывает весь предмет, затем продолжите построение.",
"recon_review_notification":"Фотографии сопоставлены. Нажмите, чтобы проверить рамку и продолжить.",
"recon_review_photo":"Фото %1$d из %2$d", "recon_review_reset":"Сбросить",
"recon_review_unavailable":"Не удалось показать рамку на фотографиях.",
"size_row_label":"Реальный размер", "size_add_optional":"Добавить (необязательно)",
"size_row_height":"Высота %1$s", "size_row_width":"Ширина %1$s",
"size_title_height":"Какова высота предмета?", "size_title_width":"Какова ширина предмета?",
"size_body_height":"Измерьте от поверхности, на которой стоит предмет, до его верхней точки. Приблизительное значение подойдёт.",
"size_body_width":"Измерьте самую широкую часть предмета. Приблизительное значение подойдёт.",
"size_axis_height":"Высота", "size_axis_width":"Ширина",
"size_follow_height":"Ширина и глубина будут рассчитаны по фотографиям.",
"size_follow_width":"Высота и глубина будут рассчитаны по фотографиям.",
"size_value_label":"Размер", "size_skip":"Пропустить", "size_save":"Сохранить",
"size_error_number":"Введите число, например 25 или 12,5",
"size_error_range":"Введите размер от %1$s до %2$s",
"size_not_set":"Размер не задан", "size_add":"Добавить размер", "size_edit":"Изменить",
"size_failed":"Не удалось применить размер. Повторите попытку.",
"recon_preview_description":"Изображение построенной модели",
"export_model":"Экспорт модели", "export_glb":"GLB",
"export_glb_body":"Один файл со встроенными цветами и текстурами. Подходит для большинства 3D-программ и просмотрщиков.",
"export_obj":"OBJ (.zip)",
"export_obj_body":"Модель, материалы и текстуры для редакторов, например Blender.",
"export_about_size":"около %1$s", "export_sized":"Сохранено в реальном масштабе.",
"export_unsized":"Реальный размер модели не задан. Добавьте размер, чтобы экспортировать её в масштабе.",
"export_save":"Сохранить", "export_share":"Поделиться",
"export_writing":"Запись %1$s… %2$d%%", "export_saved":"Сохранено",
"export_open":"Открыть", "export_no_app":"На телефоне нет приложения для открытия этого типа файла.",
"recon_notification_title":"Строю 3D-модель",
"recon_stage_import":"Подготовка фотографий",
"recon_stage_points":"Построение облака точек",
"recon_stage_ground":"Удаление поверхности под предметом",
"recon_stage_texture":"Перенос цвета и текстуры",
"recon_building":"Идёт построение 3D-модели",
"recon_elapsed":"Прошло %1$s",
"recon_ready_time":"Построено за %1$s",
"recon_build_again":"Построить заново",
"recon_try_again":"Повторить",
"recon_seconds":"%1$d с",
"recon_review_reset":"Сбросить",
"size_add_optional":"Добавить (необязательно)",
"size_row_width":"Ширина %1$s",
"size_title_width":"Какова ширина предмета?",
"size_axis_width":"Ширина",
"size_skip":"Пропустить",
"size_save":"Сохранить",
"size_add":"Добавить размер",
"size_edit":"Изменить",
"export_glb":"GLB",
"export_sized":"Сохранено в реальном масштабе.",
"export_share":"Поделиться",
"export_saved":"Сохранено",
"export_no_app":"На телефоне нет приложения для открытия этого типа файла.",
"export_failed":"Не удалось завершить экспорт. Повторите попытку.",
}

def translate(path, mapping):
    p = ROOT / path
    s = p.read_text()
    for key, value in mapping.items():
        pattern = rf'(<string\s+name="{re.escape(key)}">).*?(</string>)'
        s, n = re.subn(pattern, lambda m: m.group(1) + value.replace("&", "&amp;").replace("'", "\\'") + m.group(2), s, count=1, flags=re.S)
        if n == 0:
            # New guidance labels are appended when the upstream resource does not define them yet.
            escaped = value.replace("&", "&amp;").replace("'", "\\'")
            line = '    <string name="' + key + '">' + escaped + '</string>\n'
            s = s.replace("</resources>", line + "</resources>")
        elif n != 1:
            raise SystemExit(f"String {key} appears more than once in {path}")
    p.write_text(s)


# Keep a real English resource pack before the default Russian resources are translated.
# German starts from the English pack, so any not-yet-translated technical term remains
# readable English rather than unexpectedly falling back to Russian.
from shutil import copyfile
base_values = ROOT / "app/src/main/res/values"
for locale_name in ("en", "de"):
    locale_dir = ROOT / f"app/src/main/res/values-{locale_name}"
    locale_dir.mkdir(parents=True, exist_ok=True)
    for resource_file in ("strings.xml", "strings_capture.xml", "strings_recon.xml", "strings_info.xml"):
        copyfile(base_values / resource_file, locale_dir / resource_file)
translate("app/src/main/res/values-en/strings.xml", {
    "app_name": "ReverseScan 3D",
    "language_title": "App language",
    "language_russian": "Russian",
    "language_english": "English",
    "language_german": "German",
})
translate("app/src/main/res/values-en/strings_info.xml", {
    "info_support": "Contact",
    "info_help": "Help",
    "info_about": "About ReverseScan 3D",
    "info_credits": "Components and acknowledgements",
    "info_license": "Licences",
    "support_body": "Contact the developer: rb-service@live.de\nSource code and issue tracker: https://github.com/rb777pc-dotcom/ReverseScanAndroid",
    "about_body": "ReverseScan 3D is an Android application for capturing, building and viewing 3D models.\n\nCAPTURE AND RECONSTRUCTION\n• Capture a stationary object with the phone camera using the automatic or manual shutter.\n• On-screen guidance helps keep the object in frame and collect overlapping viewpoints.\n• Save capture sessions and photos on the device; export or import a capture archive in ZIP format.\n• Reconstruct a 3D model from a set of photographs directly on the phone.\n• Transfer colour and texture from the photographs to the reconstructed model.\n\nMODEL VIEWING AND TOOLS\n• Import STL, OBJ, PLY, 3MF, glTF and GLB models.\n• Rotate, pan and zoom; use perspective or orthographic projection and standard top, front, side and isometric views.\n• Measure the distance between two selected surface points and inspect a section through the model.\n• Inspect model information and analyse mesh defects, including open or non-manifold edges and flipped or degenerate triangles.\n• Save a view snapshot and export the result as GLB or OBJ.\n\nCapture processing and reconstruction run on the device. Results depend on lighting, surface texture and reflectivity, viewpoint overlap and phone performance. The app is not a calibrated measuring instrument and does not guarantee a watertight or print-ready mesh.",
    "about_thanks": "Developer: Bähr. Copyright © 2026. Contact: rb-service@live.de. Project and source code: https://github.com/rb777pc-dotcom/ReverseScanAndroid.",
    "license_copyright": "Copyright © 2026 Bähr. ReverseScan 3D modifications.",
    "license_body": "ReverseScan 3D is distributed under the GNU Affero General Public License version 3 (AGPL-3.0). Developer of the ReverseScan modifications: Bähr. Contact: rb-service@live.de. Project and source code: https://github.com/rb777pc-dotcom/ReverseScanAndroid. Required upstream and third-party copyright notices remain in the full licence and third-party notices.",

    "plans_title": "Planned for future versions",
    "plans_body": "The following items are under consideration and are not features of this build:\n• Scale calibration and improved measurement accuracy.\n• Mesh editing tools, including hole filling and geometry repair.\n• Additional exchange formats, including STEP, subject to a full CAD converter.\n• Better reconstruction of difficult, plain and reflective surfaces.\n• Further model analysis and 3D-print preparation tools.\n\nScope and timing may change. Listing an item here does not mean it is already implemented.",
    "help_body": "1. OPEN OR IMPORT A MODEL\nTap Open 3D model and choose a file in Android's file picker. You can also open a supported file from a file manager using Open with or Share. Supported formats: STL, OBJ, PLY, 3MF, glTF and GLB. A ZIP archive can be opened when it contains a supported model. Recent files are shortcuts, not copies; if the original file has moved or been deleted, select it again.\n\n2. NAVIGATE THE 3D VIEW\n• Drag with one finger to rotate; drag with two fingers to pan; pinch to zoom.\n• Use the view controls for perspective or orthographic projection and top, front, side or isometric views.\n• Fit centres the model in the viewport. Display modes show a solid surface, edges or wireframe. Photo colours are available when the model contains them.\n\n3. MEASURE, SECTION AND CHECK THE MESH\n• Choose Measure and tap two points on the surface. The app reports the distance between the selected points. This is a measurement of model coordinates, not independent physical calibration.\n• Choose Section and move the cutting plane to inspect the inside of the model.\n• Run Mesh check to detect open or non-manifold edges, flipped or degenerate triangles and other geometry issues. The check reports defects; it does not repair them.\n• Snapshot saves an image of the current view. Model information shows file and geometry properties. STL, OBJ and PLY may not specify units, so verify units before relying on dimensions or volume.\n\n4. CAPTURE AN OBJECT\nOpen Captures, choose New capture and grant camera permission. Place a stationary object in even, bright light. Matte surfaces with visible texture work best. Glass, mirrors, shiny metal, transparent and plain surfaces are difficult to reconstruct.\nTap the object in the preview to begin. Smart shutter takes a photo after the phone has moved to a new angle and become steady; Manual shutter takes a photo when you press the shutter button. Walk slowly around the object, keeping it in frame, then capture additional higher and lower viewpoints. Consecutive photos must overlap. Around 40 or more photos is a useful starting point; complex objects may need more.\n\n5. SAVE AND BUILD\nTap Done to save the capture. It appears in My captures. You can rename it or export a ZIP backup. To transfer a capture to another phone, import its ZIP archive from the capture library.\nOpen a saved capture and choose Build 3D model. Reconstruction runs on the phone and may take several minutes. Time depends on photo count, scene complexity and device performance. Keep enough free storage and do not force-stop the app. If box review is available, check that the box encloses the whole object before continuing.\n\n6. REVIEW AND EXPORT\nOpen the completed model in the viewer and inspect every side. Areas without enough viewpoints may contain holes or distortions. GLB can package geometry, colour and textures in one file. OBJ is exported as a ZIP containing the model, materials and texture images. Choose a destination in Android's save dialog.\n\n7. TROUBLESHOOTING\n• Too few photos were aligned: retake the object with more overlap and stronger surface texture.\n• A side is missing: capture additional viewpoints of that area without moving the object during a capture session.\n• Holes remain: add photos of the missing areas and rebuild. Automatic guaranteed hole repair is not included in this version.\n• Not enough memory or storage: close other apps and free device storage."
})
translate("app/src/main/res/values-de/strings.xml", {
    "app_name": "ReverseScan 3D", "open_file": "3D-Modell öffnen", "model_info": "Modellinformationen",
    "settings": "Einstellungen", "settings_panel_title": "Optionen", "language_title": "App-Sprache",
    "language_russian": "Russisch", "language_english": "Englisch", "language_german": "Deutsch",
    "theme_switch_to_dark": "Dunkles Design aktivieren", "theme_switch_to_light": "Helles Design aktivieren",
    "view_rail": "Ansichten", "view_rail_collapse": "Ansichtsleiste ausblenden", "view_rail_expand": "Ansichtsleiste anzeigen",
    "view_persp": "Perspektive", "view_ortho": "Orthografisch", "view_top": "Oben", "view_front": "Vorne",
    "view_side": "Seite", "view_iso": "Isometrisch", "view_fit": "Einpassen", "snapshot_title": "Bildschirmaufnahme",
    "recent_models": "Zuletzt verwendete Modelle", "recent_view_all": "Alle anzeigen", "recent_files": "Zuletzt verwendete Dateien",
    "recent_reopen": "Erneut öffnen", "recent_remove": "Aus Liste entfernen", "recent_clear": "Leeren",
    "recent_empty": "Geöffnete Modelle werden hier angezeigt.", "recent_back": "Zurück",
    "snapshot_preview": "Vorschau", "snapshot_background": "Hintergrund", "snapshot_transparent": "Transparent",
    "snapshot_framed": "Mit Rahmen", "snapshot_grid": "Raster", "snapshot_save": "Speichern", "snapshot_share": "Teilen",
    "snapshot_saved": "Bild gespeichert", "show_grid": "Raster anzeigen", "model_color": "Modellfarbe",
    "close_model": "Modell schließen", "empty_title": "Kein Modell geladen",
    "empty_body": "Öffnen Sie eine STL-, OBJ-, PLY-, 3MF-, glTF- oder GLB-Datei von Ihrem Gerät.",
    "loading": "Wird geladen …", "measure": "Messen", "measure_title": "Messung", "measure_distance": "Abstand",
    "measure_instruction_p1": "Ersten Punkt antippen", "measure_instruction_p2": "Zweiten Punkt antippen",
    "measure_clear": "Löschen", "measure_done": "Fertig", "diag_title": "Netzprüfung", "diag_analyze": "Analysieren",
    "diag_analyzing": "Analyse läuft …", "diag_cancel": "Abbrechen", "diag_no_issues": "Keine Fehler erkannt",
    "diag_issues_found": "Fehler gefunden", "diag_failed": "Analyse fehlgeschlagen", "diag_retry": "Erneut versuchen",
    "section": "Schnitt", "section_title": "Schnitt", "section_flip": "Andere Seite anzeigen", "section_close": "Schnitt schließen",
    "file_location": "Dateispeicherort", "copy_path": "Pfad kopieren", "copy_uri": "URI kopieren",
    "download_as_new_file": "Als neue Datei speichern", "file_saved": "Gespeichert unter %1$s",
    "error_saving": "Datei konnte nicht gespeichert werden: %1$s", "view_photo": "Foto",
    "view_photo_show": "Fotofarben anzeigen", "view_photo_hide": "Einfarbige Darstellung anzeigen"
})
translate("app/src/main/res/values-de/strings_capture.xml", {
    "capture_entry": "Aufnahmen", "capture_object": "Objekt aufnehmen", "captures_title": "Aufnahmen",
    "capture_new": "Neue Aufnahme", "captures_empty_title": "Erstes Objekt aufnehmen",
    "capture_untitled": "Aufnahme %1$s", "capture_rename": "Umbenennen", "capture_export": "ZIP exportieren",
    "capture_delete": "Löschen", "capture_delete_title": "Diese Aufnahme löschen?", "capture_name_hint": "Name",
    "capture_exporting": "Export läuft %1$d%% …", "capture_exported": "Aufnahme exportiert", "capture_back": "Zurück",
    "capture_copy": "Kopieren", "capture_copied": "Kopiert", "cancel": "Abbrechen", "save": "Speichern", "close": "Schließen",
    "capture_permission_title": "Kamerazugriff erforderlich", "capture_permission_body": "ReverseScan 3D verwendet die Kamera nur während einer Aufnahme. Fotos werden auf diesem Gerät gespeichert.",
    "capture_permission_allow": "Kamera erlauben", "capture_permission_settings": "Einstellungen öffnen",
    "capture_done": "Fertig", "capture_leave_title": "Aufnahme behalten?", "capture_keep": "Behalten",
    "capture_discard": "Verwerfen", "capture_saved": "Aufnahme gespeichert", "capture_summary_photos": "Fotos",
    "capture_summary_covered": "Abdeckung", "capture_summary_size": "Speicher", "capture_tap_object": "Tippen Sie auf das Objekt, um zu beginnen",
    "capture_keep_moving": "Langsam weiter um das Objekt gehen", "capture_hold_steady": "Telefon ruhig halten",
    "capture_saving_photo": "Foto wird gespeichert …", "capture_manual_hint": "Für jedes Foto den Auslöser drücken",
    "capture_mode_smart": "Automatisch", "capture_mode_manual": "Manuell", "capture_pause_short": "Pause",
    "capture_resume": "Fortsetzen", "capture_shutter_desc": "Foto aufnehmen", "capture_shutter_setting": "Auslöser"
})
translate("app/src/main/res/values-de/strings_recon.xml", {
    "recon_step": "Schritt %1$d von %2$d · %3$s", "recon_elapsed": "Bisher %1$s",
    "recon_leave_hint": "Sie können die App verlassen. Der Fortschritt wird auch in der Benachrichtigung angezeigt.",
    "recon_ready": "Modell fertig", "recon_ready_time": "Erstellt in %1$s", "recon_open": "Im Viewer öffnen",
    "recon_build_again": "Erneut erstellen", "recon_failed": "Modell konnte nicht erstellt werden",
    "recon_try_again": "Erneut versuchen", "recon_cancelled_note": "Der letzte Vorgang wurde abgebrochen.",
    "recon_err_storage": "Nicht genügend freier Speicher. Geben Sie Speicherplatz frei und versuchen Sie es erneut.",
    "recon_err_memory": "Der Arbeitsspeicher war knapp; der Vorgang wurde beendet. Schließen Sie andere Apps und versuchen Sie es erneut.",
    "recon_err_placed": "Zu wenige Fotos konnten zugeordnet werden. Nehmen Sie das Objekt erneut langsam von allen Seiten auf.",
    "recon_err_no_object": "Die Fotos zeigen nicht durchgehend dasselbe Objekt. Nehmen Sie das Objekt erneut auf und halten Sie es mittig im Bild.",
    "recon_err_tool": "Beim Erstellen des Modells ist ein Fehler aufgetreten. Versuchen Sie es erneut.",
    "recon_review_title": "Begrenzungsrahmen prüfen", "recon_review_body": "%1$d von %2$d Fotos wurden zugeordnet. Prüfen Sie den Rahmen um das Objekt.",
    "recon_review_reset": "Zurücksetzen", "size_row_label": "Reale Größe", "size_add_optional": "Hinzufügen (optional)",
    "size_title_height": "Wie hoch ist das Objekt?", "size_title_width": "Wie breit ist das Objekt?",
    "size_skip": "Überspringen", "size_save": "Speichern", "size_error_number": "Geben Sie eine Zahl ein, z. B. 25 oder 12,5",
    "size_not_set": "Größe nicht festgelegt", "size_add": "Größe hinzufügen", "size_edit": "Bearbeiten",
    "export_model": "Modell exportieren", "export_glb_body": "Eine Datei mit eingebetteten Farben. Für die meisten 3D-Apps und Viewer geeignet.",
    "export_obj_body": "Modell, Materialien und Texturbilder, z. B. für Blender.", "export_save": "Speichern",
    "export_share": "Teilen", "export_writing": "%1$s wird geschrieben … %2$d%%", "export_saved": "Gespeichert",
    "export_open": "Öffnen", "export_failed": "Export nicht abgeschlossen. Versuchen Sie es erneut."
})
translate("app/src/main/res/values-de/strings_info.xml", {
    "info_support": "Kontakt", "info_help": "Hilfe", "info_about": "Über ReverseScan 3D",
    "info_credits": "Komponenten und Danksagungen", "info_license": "Lizenzen", "info_close": "Schließen",
    "info_version": "%1$s (Build %2$d)",
    "support_body": "Kontakt zum Entwickler: rb-service@live.de\nQuellcode und Fehlerberichte: https://github.com/rb777pc-dotcom/ReverseScanAndroid",
    "about_body": "ReverseScan 3D ist eine Android-App zum Aufnehmen, Erstellen und Anzeigen dreidimensionaler Modelle.\n\nAUFNAHME UND REKONSTRUKTION\n• Aufnahme eines unbeweglichen Objekts mit automatischem oder manuellem Kameraauslöser.\n• Bildschirmanleitungen helfen, das Objekt im Bild zu halten und überlappende Blickwinkel aufzunehmen.\n• Aufnahmesitzungen und Fotos auf dem Gerät speichern; ZIP-Archive exportieren und importieren.\n• 3D-Modelle direkt auf dem Telefon aus einer Fotoserie rekonstruieren.\n• Farbe und Textur aus den Fotos auf das Modell übertragen.\n\n3D-ANSICHT UND WERKZEUGE\n• STL, OBJ, PLY, 3MF, glTF und GLB importieren.\n• Modelle drehen, verschieben und zoomen; Perspektiv- und Orthogonalansicht sowie Standardansichten nutzen.\n• Abstände zwischen zwei Oberflächenpunkten messen und einen Schnitt durch das Modell anzeigen.\n• Modellinformationen anzeigen und Netzfehler wie offene oder nicht-mannigfaltige Kanten sowie fehlerhafte Dreiecke analysieren.\n• Ansichten speichern und Modelle als GLB oder OBJ exportieren.\n\nAufnahme und Rekonstruktion erfolgen auf dem Gerät. Das Ergebnis hängt von Beleuchtung, Oberflächenstruktur, Reflexionen, Bildüberlappung und Geräteleistung ab. Die App ist kein kalibriertes Messgerät und garantiert kein geschlossenes oder druckfertiges Netz.",
    "about_thanks": "Entwickler: Bähr. Copyright © 2026. Kontakt: rb-service@live.de. Projekt und Quellcode: https://github.com/rb777pc-dotcom/ReverseScanAndroid.",
    "license_copyright": "Copyright © 2026 Bähr. Änderungen für ReverseScan 3D.",
    "license_body": "ReverseScan 3D wird unter der GNU Affero General Public License Version 3 (AGPL-3.0) veröffentlicht. Entwickler der ReverseScan-Änderungen: Bähr. Kontakt: rb-service@live.de. Projekt und Quellcode: https://github.com/rb777pc-dotcom/ReverseScanAndroid. Erforderliche Urheberrechtshinweise des ursprünglichen Projekts und der Drittanbieter bleiben in den vollständigen Lizenz- und Hinweisdokumenten erhalten.",

    "plans_title": "Für zukünftige Versionen geplant",
    "plans_body": "Die folgenden Punkte werden geprüft und sind in dieser Version noch nicht verfügbar:\n• Maßstabskalibrierung und höhere Messgenauigkeit.\n• Werkzeuge zur Netzbearbeitung, zum Schließen von Löchern und zur Geometriekorrektur.\n• Weitere Austauschformate, einschließlich STEP, nach Entwicklung eines vollständigen CAD-Konverters.\n• Verbesserte Rekonstruktion schwieriger, einfarbiger und reflektierender Oberflächen.\n• Weitere Analysewerkzeuge und Funktionen zur Vorbereitung auf den 3D-Druck.\n\nUmfang und Zeitplan können sich ändern. Ein Eintrag bedeutet nicht, dass die Funktion bereits implementiert ist.",
    "help_body": "1. MODELL ÖFFNEN ODER IMPORTIEREN\nTippen Sie auf 3D-Modell öffnen und wählen Sie eine Datei im Android-Dateiauswahldialog. Unterstützt werden STL, OBJ, PLY, 3MF, glTF und GLB. ZIP-Archive können geöffnet werden, wenn sie ein unterstütztes Modell enthalten.\n\n2. 3D-ANSICHT STEUERN\n• Ein Finger dreht das Modell; zwei Finger verschieben es; Zusammenziehen und Spreizen ändert den Zoom.\n• Die Ansichtsleiste bietet Perspektive und Orthogonalprojektion sowie Ansichten von oben, vorne, seitlich und isometrisch.\n• Einpassen zentriert das Modell. Die Darstellungsmodi zeigen Oberfläche, Kanten oder Drahtmodell.\n\n3. MESSEN, SCHNEIDEN UND PRÜFEN\n• Wählen Sie Messen und tippen Sie zwei Punkte auf der Oberfläche an. Der Abstand wird anhand der Modellkoordinaten berechnet und ist keine unabhängige physische Kalibrierung.\n• Mit Schnitt und der verschiebbaren Ebene können Sie das Modellinnere untersuchen.\n• Die Netzprüfung erkennt unter anderem offene und nicht-mannigfaltige Kanten sowie fehlerhafte Dreiecke. Sie meldet Probleme, repariert sie aber nicht automatisch.\n\n4. OBJEKT AUFNEHMEN\nÖffnen Sie Aufnahmen, wählen Sie Neue Aufnahme und erlauben Sie den Kamerazugriff. Verwenden Sie gleichmäßiges Licht und matte, strukturierte Oberflächen. Glas, Spiegel, glänzendes Metall und einfarbige Flächen sind schwierig zu rekonstruieren. Tippen Sie auf das Objekt, um zu starten. Gehen Sie langsam darum herum und halten Sie es im Bild. Die Fotos müssen sich überlappen. Etwa 40 oder mehr Fotos sind ein guter Ausgangspunkt.\n\n5. SPEICHERN UND MODELL ERSTELLEN\nTippen Sie auf Fertig. Die Aufnahme erscheint unter Meine Aufnahmen. Sie können sie umbenennen oder als ZIP sichern. Öffnen Sie die Aufnahme und wählen Sie 3D-Modell erstellen. Die Berechnung erfolgt auf dem Telefon und kann mehrere Minuten dauern. Sorgen Sie für ausreichend freien Speicher.\n\n6. ERGEBNIS PRÜFEN UND EXPORTIEREN\nÖffnen Sie das fertige Modell und prüfen Sie alle Seiten. Bereiche mit zu wenigen Fotos können Löcher oder Verzerrungen enthalten. GLB kann Geometrie, Farben und Texturen in einer Datei speichern. OBJ wird als ZIP mit Modell, Materialien und Texturen exportiert.\n\n7. FEHLERBEHEBUNG\n• Zu wenige Fotos zugeordnet: mit mehr Überlappung und besserer Oberflächenstruktur erneut aufnehmen.\n• Eine Seite fehlt: zusätzliche Blickwinkel aufnehmen, ohne das Objekt während einer Sitzung zu bewegen.\n• Löcher im Modell: fehlende Bereiche fotografieren und erneut rekonstruieren. Eine garantierte automatische Lochfüllung ist in dieser Version nicht enthalten.\n• Zu wenig Speicher: andere Apps schließen und Gerätespeicher freigeben."
})

translate("app/src/main/res/values/strings_capture.xml", capture_ru)
translate("app/src/main/res/values/strings_recon.xml", recon_ru)

# Rebrand the launcher and remove the upstream donation/support destination from navigation.
translate("app/src/main/res/values/strings.xml", {"app_name": "ReverseScan 3D"})

# Translate the complete viewer/home interface; previously only capture and reconstruction
# resources were localized, leaving the main screen in English.
translate("app/src/main/res/values/strings.xml", {
    "open_file": "Открыть 3D-модель",
    "model_info": "Информация о модели",
    "settings": "Настройки",
    "settings_panel_title": "Параметры",
    "theme_switch_to_dark": "Включить тёмную тему",
    "theme_switch_to_light": "Включить светлую тему",
    "view_rail": "Виды",
    "view_rail_collapse": "Скрыть панель видов",
    "view_rail_expand": "Показать панель видов",
    "view_persp": "Перспектива",
    "view_ortho": "Ортографический вид",
    "view_switch_to_ortho": "Перспектива. Переключить на ортографический вид",
    "view_switch_to_persp": "Ортографический вид. Переключить на перспективу",
    "view_top": "Сверху",
    "view_front": "Спереди",
    "view_side": "Сбоку",
    "view_iso": "Изометрия",
    "view_fit": "По размеру",
    "view_top_desc": "Вид сверху",
    "view_front_desc": "Вид спереди",
    "view_side_desc": "Вид сбоку",
    "view_iso_desc": "Изометрический вид",
    "view_fit_desc": "Вписать модель в экран",
    "snapshot_title": "Снимок экрана",
    "recent_models": "Недавние модели",
    "recent_view_all": "Показать все",
    "recent_files": "Недавние файлы",
    "recent_reopen": "Открыть заново",
    "recent_needs_reopen": "Файл недоступен. Выберите его повторно.",
    "recent_plus_files": "+%1$d",
    "recent_more": "Дополнительные действия: %1$s",
    "recent_remove": "Убрать из списка",
    "recent_clear": "Очистить",
    "recent_clear_title": "Очистить список недавних файлов?",
    "recent_clear_body": "Будет очищен только список. Файлы не удаляются.",
    "recent_empty": "Открытые модели будут отображаться здесь.",
    "recent_limit_note": "Здесь хранятся последние %1$d моделей.",
    "recent_back": "Назад",
    "recent_unavailable": "Файл больше недоступен. Выберите его повторно.",
    "snapshot_preview": "Предпросмотр снимка",
    "snapshot_background": "Фон",
    "snapshot_transparent": "Прозрачный",
    "snapshot_framed": "С рамкой",
    "snapshot_transparent_hint": "Только модель на прозрачном фоне (PNG с альфа-каналом).",
    "snapshot_grid": "Сетка",
    "snapshot_caption": "Подпись с названием и размером",
    "snapshot_size": "Размер",
    "snapshot_size_screen": "Как на экране",
    "snapshot_size_double": "2×",
    "snapshot_size_uhd": "4K",
    "snapshot_size_unsupported": "Недоступные для видеокарты размеры нельзя отобразить. Изображения не уменьшаются.",
    "snapshot_not_ready": "3D-вид ещё загружается.",
    "snapshot_save": "Сохранить",
    "snapshot_share": "Поделиться",
    "snapshot_share_title": "Поделиться снимком",
    "snapshot_saved": "Изображение сохранено",
    "snapshot_failed": "Не удалось создать снимок",
    "snapshot_out_of_memory": "Недостаточно памяти для этого размера. Выберите меньший.",
    "snapshot_no_share_target": "Нет приложения для получения изображений.",
    "show_grid": "Показать сетку",
    "model_color": "Цвет модели",
    "close_model": "Закрыть модель",
    "empty_title": "Модель не загружена",
    "empty_body": "Откройте файл STL, OBJ, PLY, 3MF, glTF или GLB с устройства либо выберите «Открыть с помощью» / «Поделиться» в файловом менеджере.",
    "loading": "Загрузка…",
    "loading_named": "Загрузка %1$s…",
    "mode_solid_desc": "Сплошное отображение",
    "mode_edges_desc": "Модель с рёбрами",
    "mode_wire_desc": "Каркасное отображение",
    "info_triangles": "Треугольники",
    "info_dimensions": "Габариты",
    "info_volume": "Объём",
    "info_area": "Площадь поверхности",
    "info_file_size": "Размер файла",
    "info_load_time": "Время загрузки",
    "info_units_note": "Файлы glTF и 3MF содержат сведения о единицах измерения. Для STL, OBJ и PLY до выбора единиц предполагаются миллиметры. Объём точен только для замкнутых сеток.",
    "info_units": "Единицы измерения",
    "gestures_hint": "Перетаскивание — вращение · два пальца — перемещение · щипок — масштаб · двойное касание — сброс",
    "file_location": "Расположение файла",
    "info_location": "Путь",
    "source_uri": "URI источника",
    "copy_path": "Копировать путь",
    "copy_uri": "Копировать URI",
    "location_copied": "Путь скопирован",
    "download_as_new_file": "Сохранить как новый файл",
    "file_saved": "Сохранено: %1$s",
    "error_saving": "Не удалось сохранить файл: %1$s",
    "measure": "Измерение",
    "measure_instruction_p1": "Коснитесь первой точки",
    "measure_instruction_p2": "Коснитесь второй точки",
    "measure_title": "Измерение",
    "measure_distance": "Расстояние",
    "measure_clear": "Очистить",
    "measure_done": "Готово",
    "diag_title": "Проверка сетки",
    "diag_not_analyzed": "Не проверено",
    "diag_not_analyzed_hint": "Проверяет открытые и неманифолдные рёбра, перевёрнутые и нулевые треугольники, а также внутренние части. Модель не изменяется.",
    "diag_analyze": "Проверить",
    "diag_analyzing": "Проверка…",
    "diag_cancel": "Отмена",
    "diag_no_issues": "Проблем не обнаружено",
    "diag_issues_found": "Обнаружены проблемы",
    "diag_failed": "Не удалось выполнить проверку",
    "diag_retry": "Повторить",
    "diag_out_of_memory": "Недостаточно оперативной памяти для проверки модели",
    "diag_summary": "%1$s · %2$s · проверено за %3$d мс",
    "diag_possible": "возможно",
    "diag_show_in_3d": "Показать проблемы в 3D",
    "diag_truncated": "Проблем очень много: в 3D выделены только первые 250 000 каждого типа.",
    "diag_issues_badge": "Информация о модели: найдены дефекты сетки",
    "diag_legend_desc": "Цвета выделения",
    "diag_open_edges": "Открытые рёбра",
    "diag_non_manifold": "Неманифолдные рёбра",
    "diag_flipped": "Перевёрнутые треугольники",
    "diag_degenerate": "Треугольники нулевой площади",
    "diag_non_orientable": "Неориентируемые части",
    "diag_inverted": "Вывернутые части",
    "diag_cavity": "Внутренние полости",
    "diag_not_highlighted": "Не выделено в 3D (нулевая площадь)",
    "section": "Сечение",
    "section_title": "Сечение",
    "section_axis_desc": "Разрез по оси %1$s",
    "section_flip": "Показать другую сторону",
    "section_close": "Закрыть сечение",
    "section_position_desc": "Положение сечения",
    "section_fill_checking": "Проверка модели для заполнения среза…",
    "section_fill_open": "Не заполнено: модель не замкнута (см. информацию о модели)",
    "section_fill_no_stencil": "Не заполнено: устройство не поддерживает эту функцию",
    "section_fill_failed": "Не заполнено: ошибка проверки сетки",
    "section_fill_unchecked": "Не заполнено: модель ещё не проверена",
    "section_fill_wireframe": "В каркасном режиме срез не заполняется",
    "measure_copied": "Измерение скопировано",
    "measure_copy": "Копировать измерение",
    "measure_snap": "Привязка к поверхности",
    "measure_snap_desc": "Привязывать точки измерения к поверхности модели",
    "measure_units_chip": "Единицы",
    "measure_units_desc": "Единицы измерения модели",
    "unit_source_file": "Из файла",
    "unit_source_user": "Заданы вручную",
    "unit_source_assumed": "Предполагаемые",
    "units_as_in_file": "Как в файле",
    "units_not_specified": "Не указаны",
    "unit_micron": "Микрометры",
    "unit_millimeter": "Миллиметры",
    "unit_centimeter": "Сантиметры",
    "unit_meter": "Метры",
    "unit_inch": "Дюймы",
    "unit_foot": "Футы",
    "measure_units_assumed_note": "Единицы не указаны. Предполагаются миллиметры.",
    "view_photo": "Фото",
    "view_photo_show": "Показать фотографии",
    "view_photo_hide": "Скрыть фотографии"
})

p = ROOT / "app/src/main/java/app/strata3d/ui/InfoPages.kt"
info = p.read_text()
info = info.replace("SUPPORT(R.string.info_support), HELP(R.string.info_help), ABOUT(R.string.info_about),", "HELP(R.string.info_help), ABOUT(R.string.info_about),")
info = info.replace("                        InfoPage.SUPPORT -> Body(stringResource(R.string.support_body))\n", "")
p.write_text(info)
p = ROOT / "app/src/main/java/app/strata3d/ui/ViewerScreen.kt"
viewer = p.read_text()
viewer = viewer.replace("import androidx.compose.material.icons.outlined.VolunteerActivism\\n", "")
viewer = viewer.replace("                        InfoPage.SUPPORT to Icons.Outlined.VolunteerActivism, InfoPage.HELP to Icons.AutoMirrored.Outlined.HelpOutline,", "                        InfoPage.HELP to Icons.AutoMirrored.Outlined.HelpOutline,")
p.write_text(viewer)

# Keep the upstream, unit-tested shutter defaults (9 degrees, 150 ms steady, 400 ms interval).
# Do not rewrite these values: CoverageRingsTest and SmartShutterTest validate them.

# Do not accept a reconstruction whose camera alignment is below the quality target:
# the former 30% emergency threshold allowed sparse/degenerate geometry to continue.
replace_once(
    "app/src/main/java/app/strata3d/capture/recon/ReconRunner.kt",
    "if (placed < ReconPlan.minPlacement(views)) {",
    "if (placed < ReconPlan.minPlacement(views)) {"
)

# Translate the information pages while preserving the original author and AGPL notices.
translate("app/src/main/res/values/strings_info.xml", {
    "info_support": "Поддержка",
    "info_help": "Помощь",
    "info_about": "О приложении",
    "info_credits": "Авторы и компоненты",
    "info_license": "Лицензии",
    "info_close": "Закрыть",
    "support_body": "Раздел поддержки отключён.",
    "about_body": "ReverseScan 3D — приложение для просмотра и создания трёхмерных моделей непосредственно на телефоне. Открывайте STL, OBJ, PLY, 3MF, glTF и GLB. Сканируйте неподвижные предметы камерой и создавайте текстурированные 3D-модели из фотографий без отправки данных в интернет.",
    "about_thanks": "Сведения об авторах и используемых компонентах приведены в разделе «Авторы и компоненты».",
    "license_copyright": "Авторские права на исходный проект Strata:3D принадлежат David Morales. ReverseScan 3D содержит модификации исходного проекта.",
    "license_full": "Полный текст лицензии GNU AGPL v3",
    "about_body": "ReverseScan 3D — приложение для съёмки предметов, построения и просмотра 3D-моделей непосредственно на телефоне. Поддерживается импорт STL, OBJ, PLY, 3MF, glTF и GLB. Можно вращать и измерять модели, просматривать сечения, проверять геометрию, сохранять снимки экрана и экспортировать результат. Для сканирования приложение делает фотографии предмета с разных ракурсов и строит текстурированную модель на устройстве. Результат зависит от освещения, фактуры поверхности, перекрытия ракурсов и возможностей телефона. Приложение не является калиброванным измерительным прибором и не гарантирует полностью замкнутую сетку.",
    "about_thanks": "Раздел «Авторы и компоненты» содержит сведения об исходных проектах и сторонних библиотеках. Разработчик модификаций ReverseScan 3D: Bähr. Copyright © 2026. Контакт: rb-service@live.de.",
    "help_body": "ОТКРЫТИЕ И ИМПОРТ МОДЕЛИ\n1. Нажмите «Открыть 3D-модель» и выберите файл в системном окне Android. Также можно открыть поддерживаемый файл через «Открыть с помощью» или «Поделиться» в файловом менеджере.\n2. Поддерживаются STL, OBJ, PLY, 3MF, glTF и GLB. ZIP можно открыть, если внутри находится поддерживаемая модель.\n3. Недавно открытые модели отображаются на начальном экране и в списке последних файлов.\n\nУПРАВЛЕНИЕ 3D-ВИДОМ\n1. Перетаскивание одним пальцем вращает модель, двумя пальцами — перемещает её; сведением и разведением пальцев меняется масштаб.\n2. Панель видов переключает перспективную и ортографическую проекции, виды сверху, спереди, сбоку и изометрический вид. Кнопка подгонки помещает модель в область просмотра.\n3. Режимы отображения показывают сплошную поверхность, рёбра или каркас. Если у модели есть фотографии, можно включить отображение их цветов.\n\nИЗМЕРЕНИЕ, СЕЧЕНИЕ И ПРОВЕРКА\n1. Выберите «Измерение» и коснитесь двух точек поверхности — приложение покажет расстояние между ними в координатах модели. Это не независимая физическая калибровка.\n2. «Сечение» позволяет перемещать плоскость разреза и осматривать внутреннюю часть модели.\n3. «Проверка сетки» выявляет открытые и неманифолдные рёбра, перевёрнутые и вырожденные треугольники и другие дефекты. Проверка сообщает о проблемах, но не исправляет их.\n4. «Снимок экрана» сохраняет изображение текущего вида. Информация о модели показывает параметры файла и геометрии. Для STL, OBJ и PLY проверьте единицы измерения.\n\nСЪЁМКА ПРЕДМЕТА\n1. Откройте раздел «Съёмки», выберите новую съёмку и разрешите доступ к камере. Предмет должен оставаться неподвижным.\n2. Используйте равномерное яркое освещение. Лучше всего подходят матовые поверхности с заметной фактурой. Стекло, зеркала, блестящий металл и однотонные поверхности трудно реконструировать.\n3. Коснитесь предмета в окне камеры, чтобы начать. В автоматическом режиме снимки делаются при смене ракурса и короткой остановке телефона; в ручном режиме нажимайте кнопку затвора.\n4. Медленно обойдите предмет по кругу, удерживая его в кадре. Сделайте дополнительные снимки сверху и снизу. Соседние фотографии должны перекрываться. Начните примерно с 40 снимков; сложным предметам может потребоваться больше.\n5. Нажмите «Готово», чтобы сохранить съёмку. Её можно переименовать и экспортировать в ZIP. ZIP-архив съёмки можно импортировать на другом телефоне.\n\nПОСТРОЕНИЕ И ЭКСПОРТ\n1. Откройте сохранённую съёмку и нажмите «Построить 3D-модель». Построение выполняется на телефоне и может занять несколько минут. Не закрывайте приложение принудительно и обеспечьте свободное место.\n2. Если доступна проверка рамки, убедитесь, что она охватывает весь предмет.\n3. После завершения откройте модель в просмотрщике и проверьте все стороны: участки без достаточного числа ракурсов могут содержать отверстия или искажения.\n4. GLB может содержать геометрию, цвет и текстуры в одном файле. OBJ экспортируется в ZIP вместе с материалами и изображениями текстур.\n\nЕСЛИ ПОСТРОЕНИЕ НЕ УДАЛОСЬ\n• Недостаточно сопоставленных фотографий: повторите съёмку с большим перекрытием ракурсов и более выраженной фактурой.\n• Отсутствует часть предмета: добавьте фотографии недостающей стороны.\n• Недостаточно памяти или места: закройте другие приложения и освободите хранилище.",
    "plans_title": "Планы будущих версий",
    "plans_body": "Следующие функции рассматриваются и пока не входят в эту версию:\n• Калибровка масштаба и повышение точности измерений.\n• Инструменты редактирования сетки, заполнение отверстий и исправление геометрии.\n• Дополнительные форматы обмена, включая STEP, после разработки полноценного CAD-конвертера.\n• Улучшение реконструкции однотонных и отражающих поверхностей.\n• Дополнительный анализ моделей и подготовка к 3D-печати.\n\nСостав и сроки могут измениться. Упоминание функции в списке не означает, что она уже реализована.",
    "license_body": "Эта программа является свободным программным обеспечением: её можно распространять и/или изменять на условиях GNU Affero General Public License версии 3 либо, по вашему выбору, любой более поздней версии. Программа распространяется в надежде, что будет полезна, но БЕЗ КАКИХ-ЛИБО ГАРАНТИЙ, в том числе без подразумеваемых гарантий ТОВАРНОЙ ПРИГОДНОСТИ или ПРИГОДНОСТИ ДЛЯ КОНКРЕТНОЙ ЦЕЛИ. Подробности приведены в GNU AGPL. Части приложения основаны на других проектах с открытым исходным кодом и собственными лицензиями; см. раздел «Авторы и компоненты» и уведомления о сторонних компонентах. Исходный код и сведения о проекте: https://github.com/rb777pc-dotcom/ReverseScanAndroid",
    "license_full": "Полный текст лицензии (GNU AGPL v3)",
    "license_notices": "Уведомления о сторонних компонентах",
    "info_version": "%1$s (сборка %2$d)",
    "credit_viewer": "исходный 3D-просмотрщик, на основе которого создано приложение",
    "credit_drako": "декодирование glTF-моделей со сжатием Draco",
    "credit_meshopt": "декодирование glTF-моделей со сжатием meshoptimizer",
    "credit_mve": "импорт фотографий, определение положения камер и очистка построенной модели",
    "credit_texturing": "перенос цвета на модель по фотографиям",
    "credit_mapmap": "выбор фотографий, задающих цвет каждой части модели",
    "credit_rayint": "определение видимых на каждой фотографии частей модели",
    "credit_openmvs": "расчёт глубины по фотографиям и построение поверхности модели",
    "credit_opencv": "обработка изображений при построении модели",
    "credit_boost": "универсальные компоненты C++ для построителя моделей",
    "credit_cgal": "геометрические алгоритмы построения поверхности модели",
    "credit_vcg": "очистка и упрощение построенной поверхности",
    "credit_nanoflann": "быстрый поиск ближайших точек при построении модели",
    "credit_eigen": "математические операции с матрицами и векторами",
    "credit_tbb": "выполнение этапа текстурирования на нескольких ядрах процессора",
    "credit_libjpeg": "чтение фотографий",
    "credit_libpng": "чтение и запись изображений при построении модели",
    "credit_llvm_omp": "выполнение построения модели на нескольких ядрах процессора",
    "credit_androidx": "экраны приложения, камера и работа с фотографиями",
    "license_notices": "Уведомления о сторонних компонентах"
})


# Keep the display awake only while the live camera capture screen is active.
replace_once(
    "app/src/main/java/app/strata3d/capture/ui/CaptureActivity.kt",
    "            var shutterSettings by remember { mutableStateOf(false) }",
    """            var shutterSettings by remember { mutableStateOf(false) }

            DisposableEffect(screen) {
                if (screen == Screen.CAPTURE) window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                else window.clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                onDispose { window.clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) }
            }"""
)

# Expose CameraX torch state and control in the live preview. The torch belongs to
# CameraControl, not ImageCapture flash mode, so it remains on continuously between photos.
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "        val smartAvailable: Boolean = true,",
    "        val smartAvailable: Boolean = true,\n        val torchAvailable: Boolean = false,\n        val torchOn: Boolean = false,"
)
# Camera binding is patched together with ImageAnalysis below to avoid duplicate Camera instances.
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "    /** Switches between the smart shutter and the manual button for this capture. */",
    """    /** Toggles the continuous LED torch while the camera preview is active. */
    fun toggleTorch() {
        val cam = camera ?: return
        if (!cam.cameraInfo.hasFlashUnit()) {
            _state.update { it.copy(torchAvailable = false, torchOn = false) }
            return
        }
        val enabled = !_state.value.torchOn
        cam.cameraControl.enableTorch(enabled).addListener({
            _state.update { it.copy(torchOn = enabled) }
        }, ContextCompat.getMainExecutor(context))
    }

    /** Switches between the smart shutter and the manual button for this capture. */"""
)
# ContextCompat is already imported by the upstream camera class in the pinned source.
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "        provider?.unbindAll()\n        provider = null; camera = null; imageCapture = null; previewView = null",
    "        camera?.cameraControl?.enableTorch(false)\n        _state.update { it.copy(torchOn = false) }\n        provider?.unbindAll()\n        provider = null; camera = null; imageCapture = null; previewView = null"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/ui/CaptureScreen.kt",
    "                ModeChip(state.mode, enabled = state.smartAvailable) {",
    """                Text(
                    if (state.torchOn) stringResource(R.string.capture_torch_on) else stringResource(R.string.capture_torch_off),
                    color = if (state.torchOn) Teal else OnScrim,
                    fontSize = 12.sp,
                    modifier = Modifier
                        .background(Scrim, RoundedCornerShape(50))
                        .clickable(enabled = state.torchAvailable) { engine.toggleTorch() }
                        .padding(horizontal = 10.dp, vertical = 7.dp),
                )
                Spacer(Modifier.width(8.dp))
                ModeChip(state.mode, enabled = state.smartAvailable) {"""
)
# Make the capture coverage graphic large enough to inspect instead of leaving it as a tiny icon.
replace_once(
    "app/src/main/java/app/strata3d/capture/ui/CaptureScreen.kt",
    """            Row(Modifier.fillMaxWidth().padding(end = 12.dp)) {
                Spacer(Modifier.weight(1f))
                CoverageDome(listOf(state.lowerRing, state.upperRing), null, Modifier.size(52.dp))
            }""",
    """            Row(
                Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    Text(stringResource(R.string.capture_coverage_title), color = OnScrim, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                    Text(stringResource(R.string.capture_coverage_done), color = Teal, fontSize = 11.sp)
                    Text(stringResource(R.string.capture_coverage_missing), color = OnScrim, fontSize = 11.sp)
                    Text(stringResource(R.string.capture_coverage_bottom), color = OnScrim, fontSize = 10.sp)
                }
                CoverageDome(listOf(state.lowerRing, state.upperRing), null, Modifier.size(104.dp))
            }"""
)

print("Applied Russian capture/reconstruction UI, larger coverage dial, and deterministic SfM first pass.")


# If the exhaustive pair graph is weak, rebuild the feature matches rather than
# repeatedly solving the same cached prebundle. A sequential fallback is useful
# for handheld orbit captures: it links each image to a bounded set of nearby
# frames. Preserve the better camera solution by re-running the exhaustive path
# from freshly computed matches if the sequential fallback places fewer views.
replace_once(
    "app/src/main/java/app/strata3d/capture/recon/ReconPlan.kt",
    '        fun sfm(scene: String, setting: SfmSetting) = listOf("--max-pixels=${setting.maxPixels}", scene)',
    '''        fun sfm(scene: String, setting: SfmSetting) = listOf("--max-pixels=${setting.maxPixels}", scene)
        fun sfmSequential(scene: String, setting: SfmSetting, previousFrames: Int = 8) =
            listOf("--max-pixels=${setting.maxPixels}", "--video-matching=$previousFrames", scene)'''
)
def replace_region(path, start_marker, end_marker, replacement):
    p = ROOT / path
    source = p.read_text()
    start = source.find(start_marker)
    end = source.find(end_marker, start + len(start_marker))
    if start < 0 or end < 0:
        raise SystemExit(f"Expected region not found in {path}; refusing partial patch")
    p.write_text(source[:start] + replacement + source[end:])

replace_region(
    "app/src/main/java/app/strata3d/capture/recon/ReconRunner.kt",
    "        var attempt = 1\n        var singleThreaded = -1",
    "        status = status.copy(photos = views, placed = placed)",
    """        // Rebuild feature matches for a sequential fallback; never reuse stale prebundle.sfm.
        var attempt = 1
        val firstPlaced = placed
        if (placed < ReconPlan.goodPlacement(views)) {
            Log.w(TAG, "SfM placed only $placed of $views photos; rebuilding sequential matches")
            attempt++
            File(scene, "prebundle.sfm").delete()
            File(scene, "synth_0.out").delete()
            val sequentialArgs = ReconPlan.Args.sfmSequential(scene.path, settings.sfm, 8)
            exec("sfmrecon", sequentialArgs, Stage.CAMERAS, threads = 1)
            placed = registeredViews()
            if (placed < ReconPlan.goodPlacement(views)) {
                Log.w(TAG, "SfM remains below the placement target ($placed/$views); testing alternate initial pairs")
            }

            // A weak automatic seed can leave most views unregistered even when the matching graph
            // contains usable pairs. Try deterministic pairs spread around the capture, then restore
            // the best seed so a later, worse attempt cannot replace it.
            val gap = (views / 16).coerceIn(2, 8)
            val stride = (views / 8).coerceAtLeast(1)
            val candidates = (0 until (views - gap) step stride).take(8).map { it to (it + gap) }
            var bestPair: Pair<Int, Int>? = null
            var bestPlaced = placed
            for ((a, b) in candidates) {
                attempt++
                val args = sequentialArgs.dropLast(1) + listOf("--initial-pair=$a,$b", scene.path)
                val succeeded = try {
                    exec("sfmrecon", args, Stage.CAMERAS, threads = 1)
                    true
                } catch (e: Stop) {
                    if (e.error != Error.TOOL_FAILED) throw e
                    Log.w(TAG, "SfM seed $a,$b rejected: ${e.detail}")
                    false
                }
                if (succeeded) {
                    val candidatePlaced = registeredViews()
                    Log.i(TAG, "SfM seed $a,$b placed $candidatePlaced of $views")
                    if (candidatePlaced > bestPlaced) {
                        bestPlaced = candidatePlaced
                        bestPair = a to b
                    }
                    if (bestPlaced >= ReconPlan.goodPlacement(views)) break
                }
            }
            if (bestPlaced < firstPlaced) {
                // Alternate sequential seeds did not beat the original solution. Rebuild exhaustive
                // matches and restore the deterministic original path rather than keeping a worse model.
                File(scene, "prebundle.sfm").delete()
                File(scene, "synth_0.out").delete()
                exec("sfmrecon", ReconPlan.Args.sfm(scene.path, settings.sfm), Stage.CAMERAS, threads = 1)
                placed = registeredViews()
                if (placed < firstPlaced) {
                    throw Stop(Error.TOO_FEW_PHOTOS_PLACED,
                        "best recovery placed $placed photos, below the initial $firstPlaced")
                }
                Log.i(TAG, "SfM restored original exhaustive solution")
            } else {
                val restoreArgs = bestPair?.let { (a, b) ->
                    sequentialArgs.dropLast(1) + listOf("--initial-pair=$a,$b", scene.path)
                } ?: sequentialArgs
                exec("sfmrecon", restoreArgs, Stage.CAMERAS, threads = 1)
                placed = registeredViews()
                Log.i(TAG, "SfM best seed: ${bestPair?.let { "${it.first},${it.second}" } ?: "automatic"}")
            }
        }
        Log.i(TAG, "SfM placed $placed of $views photos after $attempt matching/seed attempt(s) (${settings.reason})")
""",
)

print("Added fresh sequential SfM matching fallback and fresh exhaustive comparison.")


# ReverseScan 3D visual identity: dark graphite field and a neutral 3D wireframe mark.
def write_asset(relative_path, body):
    target = ROOT / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body.strip() + "\n")

write_asset("app/src/main/res/values/colors_brand.xml", """<resources>
    <color name="brand_night">#07111F</color>
    <color name="brand_blue">#176BFF</color>
    <color name="brand_cyan">#35E7FF</color>
</resources>""")

write_asset("app/src/main/res/drawable/ic_brand_mark.xml", """<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#00000000" android:strokeColor="#176BFF"
        android:strokeWidth="5" android:strokeLineCap="round" android:strokeLineJoin="round"
        android:pathData="M54,9 L94,31 L94,77 L54,99 L14,77 L14,31 Z" />
    <path android:fillColor="#00000000" android:strokeColor="#35E7FF"
        android:strokeWidth="4.5" android:strokeLineCap="round" android:strokeLineJoin="round"
        android:pathData="M14,31 L54,53 L94,31 M54,53 L54,99" />
</vector>""")

write_asset("app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml", """<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/brand_night" />
    <foreground android:drawable="@drawable/ic_brand_mark" />
    <monochrome android:drawable="@drawable/ic_brand_mark" />
</adaptive-icon>""")

# Upstream already defines Theme.Strata in values-v31/themes.xml. Replace that
# resource in-place so the branded splash attributes extend the existing style
# rather than creating a duplicate resource with the same name.
write_asset("app/src/main/res/values-v31/themes.xml", """<resources>
    <style name="Theme.Strata" parent="Theme.Strata.Light">
        <item name="android:windowSplashScreenBackground">@color/brand_night</item>
        <item name="android:windowSplashScreenAnimatedIcon">@drawable/ic_brand_mark</item>
        <item name="android:windowSplashScreenIconBackgroundColor">@color/brand_night</item>
    </style>
</resources>""")

manifest = ROOT / "app/src/main/AndroidManifest.xml"
manifest_text = manifest.read_text()
manifest_text = manifest_text.replace(
    'android:icon="@mipmap/ic_launcher"',
    'android:icon="@mipmap/ic_launcher"\n        android:roundIcon="@mipmap/ic_launcher"'
)
manifest.write_text(manifest_text)


# Replace the upstream Strata glyph everywhere in the viewer with the same neutral
# 3D wireframe mark used by ReverseScan. No letter-shaped monogram.
replace_once(
    "app/src/main/java/app/strata3d/ui/ViewerScreen.kt",
    """/** The Strata:3D logo; its dark strokes use the theme's text colour so it reads on light and dark bars. */
@Composable
fun StrataLogo(modifier: Modifier = Modifier) {
    val ink = MaterialTheme.colorScheme.onSurface
    Box(modifier) {
        Image(
            painter = painterResource(R.drawable.logo_layer_ink),
            contentDescription = null,
            colorFilter = ColorFilter.tint(ink),
            modifier = Modifier.matchParentSize(),
        )
        Image(
            painter = painterResource(R.drawable.logo_layer_cyan),
            contentDescription = null,
            colorFilter = ColorFilter.tint(BrandCyan),
            modifier = Modifier.matchParentSize(),
        )
    }
}""",
    """/** ReverseScan 3D wireframe mark; deliberately contains no Strata lettering. */
@Composable
fun StrataLogo(modifier: Modifier = Modifier) {
    Image(
        painter = painterResource(R.drawable.ic_brand_mark),
        contentDescription = stringResource(R.string.app_name),
        modifier = modifier,
    )
}"""
)

# Make model import a permanent, visible top-bar action instead of hiding it in Settings.
replace_once(
    "app/src/main/java/app/strata3d/ui/ViewerScreen.kt",
    """                            ThemeToggleButton(dark = dark, onToggle = onToggleTheme)""",
    """                            TextButton(onClick = launchPicker) {
                                Icon(Icons.Outlined.FolderOpen, contentDescription = null)
                                Spacer(Modifier.width(6.dp))
                                Text(stringResource(R.string.open_file))
                            }
                            ThemeToggleButton(dark = dark, onToggle = onToggleTheme)"""
)

# Live object detection and tracking in the camera preview.
# ML Kit's bundled stream detector supplies a real object bounding box and tracking ID.
# This is deliberately described as object tracking, not pixel-level segmentation.
replace_once(
    "app/build.gradle.kts",
    "    testImplementation(libs.junit)",
    "    implementation(\"com.google.mlkit:object-detection:17.0.2\")\n\n    implementation(libs.junit)"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "import android.annotation.SuppressLint",
    "import android.annotation.SuppressLint\nimport android.graphics.RectF"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "import androidx.camera.core.ImageCaptureException",
    "import androidx.camera.core.ImageCaptureException\nimport androidx.camera.core.ImageAnalysis"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "import androidx.lifecycle.LifecycleOwner",
    """import androidx.lifecycle.LifecycleOwner
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.objects.ObjectDetection
import com.google.mlkit.vision.objects.defaults.ObjectDetectorOptions"""
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "        val smartAvailable: Boolean = true,",
    "        val smartAvailable: Boolean = true,\n        val objectDetected: Boolean? = null,\n        val objectNearEdge: Boolean = false,\n        val objectBox: RectF? = null,\n        val objectTrackingId: Int? = null,"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "    private var previewView: PreviewView? = null",
    """    private var previewView: PreviewView? = null
    private var imageAnalysis: ImageAnalysis? = null
    private val analysisExecutor = Executors.newSingleThreadExecutor { r -> Thread(r, "reversescan-object-analysis") }
    private val objectDetector = ObjectDetection.getClient(
        ObjectDetectorOptions.Builder()
            .setDetectorMode(ObjectDetectorOptions.STREAM_MODE)
            .enableMultipleObjects()
            .build()
    )
    @Volatile private var missedObjectFrames = 0
    @Volatile private var selectedObjectTrackingId: Int? = null"""
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    """        p.unbindAll()
        val cam = p.bindToLifecycle(owner, CameraSelector.DEFAULT_BACK_CAMERA, preview, capture)
        preview.surfaceProvider = view.surfaceProvider
        camera = cam
        imageCapture = capture
        cameraInfo = readCameraInfo(cam, capture)""",
    """        val analysis = ImageAnalysis.Builder()
            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
            .build()
        analysis.setAnalyzer(analysisExecutor) { proxy ->
            val media = proxy.image
            if (media == null) {
                proxy.close()
            } else {
                val rotation = proxy.imageInfo.rotationDegrees
                objectDetector.process(InputImage.fromMediaImage(media, rotation))
                    .addOnSuccessListener { objects ->
                        val selectedTap = synchronized(lock) { manifest?.objectTap }
                        val rotatedWidth = if (rotation % 180 == 0) proxy.width else proxy.height
                        val rotatedHeight = if (rotation % 180 == 0) proxy.height else proxy.width
                        val lockedId = selectedObjectTrackingId
                        val target = when {
                            selectedTap == null -> objects.maxByOrNull { it.boundingBox.width() * it.boundingBox.height() }
                            lockedId != null -> objects.firstOrNull { it.trackingId == lockedId }
                            else -> objects.mapNotNull { obj ->
                                val b = obj.boundingBox
                                val left = b.left.toFloat() / rotatedWidth
                                val top = b.top.toFloat() / rotatedHeight
                                val right = b.right.toFloat() / rotatedWidth
                                val bottom = b.bottom.toFloat() / rotatedHeight
                                val u = selectedTap.u.toFloat()
                                val v = selectedTap.v.toFloat()
                                val dx = maxOf(left - u, 0f, u - right)
                                val dy = maxOf(top - v, 0f, v - bottom)
                                obj to (dx * dx + dy * dy)
                            }.filter { it.second <= 0.16f * 0.16f }
                                .minByOrNull { it.second }?.first
                        }
                        if (target != null) {
                            missedObjectFrames = 0
                            target.trackingId?.let { selectedObjectTrackingId = it }
                            val box = target.boundingBox
                            val left = (box.left.toFloat() / rotatedWidth).coerceIn(0f, 1f)
                            val top = (box.top.toFloat() / rotatedHeight).coerceIn(0f, 1f)
                            val right = (box.right.toFloat() / rotatedWidth).coerceIn(0f, 1f)
                            val bottom = (box.bottom.toFloat() / rotatedHeight).coerceIn(0f, 1f)
                            val nearEdge = left <= 0.03f || top <= 0.03f || right >= 0.97f || bottom >= 0.97f
                            _state.update { it.copy(
                                objectDetected = true,
                                objectNearEdge = nearEdge,
                                objectBox = RectF(left, top, right, bottom),
                                objectTrackingId = target.trackingId,
                                notice = when {
                                    nearEdge -> Notice.TARGET_EDGE
                                    it.notice == Notice.TARGET_EDGE || it.notice == Notice.TARGET_LOST ->
                                        noticeFor(it.mode, armed = it.phase == Phase.CAPTURING)
                                    else -> it.notice
                                },
                            ) }
                        } else {
                            missedObjectFrames++
                            if (missedObjectFrames >= 3) {
                                selectedObjectTrackingId = null
                                _state.update { it.copy(objectDetected = false, objectNearEdge = false, objectBox = null, objectTrackingId = null, notice = Notice.TARGET_LOST) }
                            }
                        }
                    }
                    .addOnFailureListener {
                        missedObjectFrames++
                        if (missedObjectFrames >= 3) {
                            selectedObjectTrackingId = null
                                _state.update { it.copy(objectDetected = false, objectNearEdge = false, objectBox = null, objectTrackingId = null, notice = Notice.TARGET_LOST) }
                        }
                    }
                    .addOnCompleteListener { proxy.close() }
            }
        }
        p.unbindAll()
        val cam = p.bindToLifecycle(owner, CameraSelector.DEFAULT_BACK_CAMERA, preview, capture, analysis)
        preview.surfaceProvider = view.surfaceProvider
        camera = cam
        val hasTorch = cam.cameraInfo.hasFlashUnit()
        _state.update { it.copy(torchAvailable = hasTorch, torchOn = false) }
        imageCapture = capture
        imageAnalysis = analysis
        cameraInfo = readCameraInfo(cam, capture)"""
)

replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "        camera?.cameraControl?.enableTorch(false)\n        _state.update { it.copy(torchOn = false) }\n        provider?.unbindAll()\n        provider = null; camera = null; imageCapture = null; previewView = null",
    """        camera?.cameraControl?.enableTorch(false)
        _state.update { it.copy(torchOn = false) }
        imageAnalysis?.clearAnalyzer()
        imageAnalysis = null
        provider?.unbindAll()
        provider = null; camera = null; imageCapture = null; previewView = null
        objectDetector.close()
        analysisExecutor.shutdown()""")
replace_once(
    "app/src/main/java/app/strata3d/capture/ui/CaptureScreen.kt",
    "        // Taps over the camera mark the object (before the first photo).",
    """        // Live ML Kit object tracking: green = detected, red = lost.
        val detectedBox = state.objectBox
        Canvas(Modifier.fillMaxSize()) {
            val portrait = size.height >= size.width
            val frameAspect = if (portrait) 3f / 4f else 4f / 3f
            val contentWidth = minOf(size.width, size.height * frameAspect)
            val contentHeight = minOf(size.height, size.width / frameAspect)
            val offsetX = (size.width - contentWidth) / 2f
            val offsetY = (size.height - contentHeight) / 2f
            if (state.objectDetected == true && detectedBox != null) {
                val l = offsetX + detectedBox.left * contentWidth
                val t = offsetY + detectedBox.top * contentHeight
                val r = offsetX + detectedBox.right * contentWidth
                val b = offsetY + detectedBox.bottom * contentHeight
                drawRect(if (state.objectNearEdge) Color(0xFFFFC04D) else Color(0xFF36E58A), topLeft = Offset(l, t), size = Size(r - l, b - t), style = Stroke(width = 3.dp.toPx()))
                drawCircle(Color(0xFF36E58A), radius = 5.dp.toPx(), center = Offset((l + r) / 2f, t))
            }
        }
        Box(
            Modifier.fillMaxWidth().padding(top = 54.dp),
            contentAlignment = Alignment.TopCenter,
        ) {
            val trackingLabel = when {
                state.objectNearEdge -> "ОБЪЕКТ У КРАЯ · ВЕРНИТЕ В ЦЕНТР"
                state.objectDetected == true -> "ОБЪЕКТ В КАДРЕ · ОТСЛЕЖИВАЕТСЯ"
                state.objectDetected == false -> "ОБЪЕКТ ПОТЕРЯН · НАВЕДИТЕ КАМЕРУ"
                else -> "НАВЕДИТЕ КАМЕРУ НА ПРЕДМЕТ"
            }
            Text(
                trackingLabel,
                color = if (state.objectNearEdge) Color(0xFFFFC04D) else if (state.objectDetected == true) Color(0xFF36E58A) else Color.White,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.background(
                    if (state.objectNearEdge) Color(0xCC8A5A00) else if (state.objectDetected == false) Color(0xCCB3261E) else Scrim,
                    RoundedCornerShape(50),
                ).padding(horizontal = 12.dp, vertical = 7.dp),
            )
        }
        // Taps over the camera mark the object (before the first photo)."""
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "        val tap = ObjectTap(u, v, SystemClock.elapsedRealtimeNanos(), o?.toSensorOrientation())",
    """        val tap = ObjectTap(u, v, SystemClock.elapsedRealtimeNanos(), o?.toSensorOrientation())
        selectedObjectTrackingId = null
        missedObjectFrames = 0"""
)

print("Added live ML Kit object detection/tracking, bounding-box overlay, and lost-target status.")


# Target selection is already implemented in the ImageAnalysis callback above.
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "    enum class Notice { NONE, TAP_OBJECT, KEEP_MOVING, HOLD_STEADY, SAVING_PHOTO, PAUSED, MANUAL, HOT, LOW_STORAGE, PHOTO_FAILED, NO_SENSORS }",
    "    enum class Notice { NONE, TAP_OBJECT, KEEP_MOVING, HOLD_STEADY, SAVING_PHOTO, PAUSED, MANUAL, HOT, LOW_STORAGE, PHOTO_FAILED, NO_SENSORS, TARGET_LOST, TARGET_EDGE }"
)

replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "    private fun takePhoto(orientation: DeviceOrientation?, manual: Boolean) {\n        val ic = imageCapture ?: run { synchronized(lock) { shutter.onPhotoFinished(false) }; return }",
    """    private fun takePhoto(orientation: DeviceOrientation?, manual: Boolean) {
        val liveTarget = _state.value
        if (liveTarget.objectDetected == false || liveTarget.objectNearEdge) {
            synchronized(lock) { shutter.onPhotoFinished(false) }
            _state.update { it.copy(notice = if (it.objectNearEdge) Notice.TARGET_EDGE else Notice.TARGET_LOST) }
            return
        }
        val ic = imageCapture ?: run { synchronized(lock) { shutter.onPhotoFinished(false) }; return }"""
)
replace_once(
    "app/src/main/java/app/strata3d/capture/ui/CaptureScreen.kt",
    "    Notice.NO_SENSORS -> stringResource(R.string.capture_no_sensors)",
    "    Notice.NO_SENSORS -> stringResource(R.string.capture_no_sensors)\n    Notice.TARGET_LOST -> \"Предмет потерян — фото не сделано. Верните его в кадр.\"\n    Notice.TARGET_EDGE -> \"Предмет у края кадра — верните его ближе к центру.\""
)
print("Added tap-nearest target selection and blocked shutter when the target is explicitly lost.")


# ReverseScan capture archive import + resume interrupted scans.
def add_archive_resume():
    vm_path = "app/src/main/java/app/strata3d/capture/ui/CaptureLibraryViewModel.kt"
    p = ROOT / vm_path
    s = p.read_text()
    s = s.replace("import java.io.File\n", "import java.io.File\nimport java.util.zip.ZipInputStream\n")
    anchor = "    /** Writes the capture as a .zip to [uri] (chosen by the user with the system file picker). */"
    method = r'''
    /** Import a ZIP previously created by CaptureExport. */
    fun importCapture(uri: Uri) {
        if (exportJob?.isActive == true) return
        exportJob = viewModelScope.launch {
            val ok = withContext(Dispatchers.IO) {
                val application = getApplication<Application>()
                val temp = File(application.cacheDir, "capture-import-" + System.currentTimeMillis())
                try {
                    temp.mkdirs()
                    application.contentResolver.openInputStream(uri)?.use { raw ->
                        ZipInputStream(raw).use { zip ->
                            val buffer = ByteArray(131072)
                            while (true) {
                                val entry = zip.nextEntry ?: break
                                val name = entry.name.replace('\\', '/')
                                require(!name.startsWith("/") && name.split('/').none { it == ".." })
                                val target = File(temp, name).canonicalFile
                                require(target.path.startsWith(temp.canonicalPath + File.separator))
                                if (entry.isDirectory) target.mkdirs() else {
                                    target.parentFile?.mkdirs()
                                    target.outputStream().use { out ->
                                        while (true) { val n = zip.read(buffer); if (n < 0) break; out.write(buffer, 0, n) }
                                    }
                                }
                                zip.closeEntry()
                            }
                        }
                    } ?: error("Cannot open archive")
                    val mf = File(temp, CaptureStore.MANIFEST)
                    val ff = File(temp, CaptureStore.FRAMES)
                    require(mf.isFile && ff.isFile) { "Not a capture archive" }
                    val decoded = app.strata3d.capture.format.CaptureJson.decodeManifest(mf.readText(Charsets.UTF_8))
                    val records = ff.readLines(Charsets.UTF_8).filter { it.isNotBlank() }
                        .map { app.strata3d.capture.format.CaptureJson.decodeFrame(it) }
                    require(records.isNotEmpty())
                    records.forEach { frame ->
                        val imagePath = frame.image.replace('\\', '/')
                        require(!imagePath.startsWith("/") && imagePath.split('/').none { it == ".." }) { "Unsafe image path" }
                        val imageFile = File(temp, imagePath).canonicalFile
                        require(imageFile.path.startsWith(temp.canonicalPath + File.separator) && imageFile.isFile) { "Missing or unsafe image" }
                    }
                    val created = store.create(decoded.copy(id = "", frameCount = records.size,
                        state = app.strata3d.capture.format.CaptureState.COMPLETE, updatedAt = System.currentTimeMillis()))
                    try {
                        temp.walkTopDown().filter { it.isFile && it.name != CaptureStore.MANIFEST }.forEach { source ->
                            val dest = File(created.dir, source.relativeTo(temp).path)
                            dest.parentFile?.mkdirs()
                            source.copyTo(dest, overwrite = true)
                        }
                        store.writeManifest(created.dir, created.manifest.copy(frameCount = records.size,
                            state = app.strata3d.capture.format.CaptureState.COMPLETE))
                    } catch (e: Exception) { store.delete(created.dir); throw e }
                    true
                } catch (e: Exception) {
                    android.util.Log.e("CaptureImport", "Import failed", e); false
                } finally { temp.deleteRecursively() }
            }
            _messages.value = if (ok) R.string.capture_imported else R.string.capture_import_failed
            if (ok) refresh()
        }
    }

'''
    if "fun importCapture(uri: Uri)" not in s:
        if anchor not in s: raise SystemExit("import VM anchor missing")
        s = s.replace(anchor, method + anchor, 1)
    p.write_text(s)

    lib_path = "app/src/main/java/app/strata3d/capture/ui/CaptureLibraryScreen.kt"
    p = ROOT / lib_path
    s = p.read_text()
    anchor = "    val exporter = rememberCaptureExporter(viewModel)\n"
    if "val importer = rememberLauncherForActivityResult" not in s:
        if anchor not in s: raise SystemExit("import launcher anchor missing")
        s = s.replace(anchor, anchor + '''    val importer = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let { viewModel.importCapture(it) }
    }
''', 1)
    # Visible toolbar action: import is no longer buried in the overflow menu.
    toolbar_anchor = '''                actions = {
                    IconButton(onClick = { menuOpen = true }) { Icon(Icons.Outlined.MoreVert, contentDescription = stringResource(R.string.capture_more)) }'''
    if 'Icon(Icons.Outlined.Share, contentDescription = stringResource(R.string.capture_import))' not in s:
        if toolbar_anchor not in s: raise SystemExit("import toolbar anchor missing")
        s = s.replace(toolbar_anchor, '''                actions = {
                    TextButton(onClick = { importer.launch(arrayOf("application/zip", "application/octet-stream")) }) {
                        Text(stringResource(R.string.capture_import_short))
                    }
                    IconButton(onClick = { menuOpen = true }) { Icon(Icons.Outlined.MoreVert, contentDescription = stringResource(R.string.capture_more)) }''', 1)
    anchor = '''                        DropdownMenuItem(
                            text = { Text(stringResource(R.string.capture_device_report)) },'''
    if "R.string.capture_import))" not in s:
        if anchor not in s: raise SystemExit("import menu anchor missing")
        s = s.replace(anchor, '''                        DropdownMenuItem(
                            text = { Text(stringResource(R.string.capture_import)) },
                            leadingIcon = { Icon(Icons.Outlined.Share, contentDescription = null) },
                            onClick = { menuOpen = false; importer.launch(arrayOf("application/zip", "application/octet-stream")) },
                        )
''' + anchor, 1)
    p.write_text(s)

    cam_path = "app/src/main/java/app/strata3d/capture/CameraXCapture.kt"
    p = ROOT / cam_path
    s = p.read_text()
    s = s.replace("    private val appVersion: String,\n) {",
                  "    private val appVersion: String,\n    private val resumeCaptureId: String? = null,\n) {", 1)
    s = s.replace("    init {\n        val mode =",
'''    init {
        resumeCaptureId?.let { id ->
            store.list().firstOrNull { it.id == id }?.let { existing ->
                capture = existing
                manifest = existing.manifest
                val frames = store.readFrames(existing.dir)
                photoCount = frames.size
                frames.forEach { f -> f.orientation?.let { rings.add(DeviceOrientation.of(it.x, it.y, it.z, it.w)) } }
                _state.update { it.copy(phase = Phase.AIMING, photoCount = photoCount,
                    lowerRing = rings.cells(CoverageRings.Ring.LOWER),
                    upperRing = rings.cells(CoverageRings.Ring.UPPER), notice = Notice.TAP_OBJECT) }
            }
        }
        val mode =''', 1)
    s = s.replace("if (synchronized(lock) { photoCount > 0 || finishing }) return",
                  "if (synchronized(lock) { (photoCount > 0 && resumeCaptureId == null) || finishing }) return", 1)
    s = s.replace('''            } else {
                manifest = manifest?.copy(objectTap = tap)
                manifest?.let { m -> capture?.let { c -> runIo { writeManifestQuietly(c.dir, m) } } }
            }''',
'''            } else if (resumeCaptureId == null) {
                manifest = manifest?.copy(objectTap = tap)
                manifest?.let { m -> capture?.let { c -> runIo { writeManifestQuietly(c.dir, m) } } }
            }''', 1)
    p.write_text(s)

    screen_path = "app/src/main/java/app/strata3d/capture/ui/CaptureScreen.kt"
    p = ROOT / screen_path
    s = p.read_text()
    s = s.replace("fun CaptureScreen(store: CaptureStore, onFinished: (String?) -> Unit) {",
                  "fun CaptureScreen(store: CaptureStore, onFinished: (String?) -> Unit, resumeCaptureId: String? = null) {", 1)
    s = s.replace("val engine = remember {",
                  "val engine = remember(resumeCaptureId) {", 1)
    s = s.replace('CameraXCapture(context.applicationContext, store, version ?: "")',
                  'CameraXCapture(context.applicationContext, store, version ?: "", resumeCaptureId)', 1)
    s = s.replace("DisposableEffect(Unit) { onDispose { engine.shutdown() } }",
                  "DisposableEffect(engine) { onDispose { engine.shutdown() } }", 1)
    p.write_text(s)

    summary_path = "app/src/main/java/app/strata3d/capture/ui/CaptureSummaryScreen.kt"
    p = ROOT / summary_path
    s = p.read_text()
    s = s.replace(
        "fun CaptureSummaryScreen(viewModel: CaptureLibraryViewModel, captureId: String?, onDone: () -> Unit, onCheckBox: (String) -> Unit) {",
        "fun CaptureSummaryScreen(viewModel: CaptureLibraryViewModel, captureId: String?, onDone: () -> Unit, onCheckBox: (String) -> Unit, onContinueCapture: (String) -> Unit = {}) {", 1)
    anchor = '''            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { renaming = true })'''
    if "R.string.capture_continue" not in s:
        if anchor not in s: raise SystemExit("summary continue anchor missing")
        s = s.replace(anchor, '''            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { onContinueCapture(capture.id) }) { Text(stringResource(R.string.capture_continue)) }
                OutlinedButton(onClick = { renaming = true })''', 1)
    p.write_text(s)

    activity_path = "app/src/main/java/app/strata3d/capture/ui/CaptureActivity.kt"
    p = ROOT / activity_path
    s = p.read_text()
    s = s.replace("            var summaryId by rememberSaveable { mutableStateOf(openCapture) }",
                  "            var summaryId by rememberSaveable { mutableStateOf(openCapture) }\n            var resumeCaptureId by rememberSaveable { mutableStateOf<String?>(null) }", 1)
    # Re-scan the on-device library whenever it is shown. CaptureStore repairs an abruptly
    # terminated RECORDING session to INTERRUPTED and recovers all synced frame records.
    if "LaunchedEffect(screen) { if (screen == Screen.LIBRARY) library.refresh() }" not in s:
        s = s.replace("            var shutterSettings by remember { mutableStateOf(false) }",
                      "            var shutterSettings by remember { mutableStateOf(false) }\n\n            LaunchedEffect(screen) { if (screen == Screen.LIBRARY) library.refresh() }", 1)

    s = s.replace("store = library.store,\n                        onFinished =", "store = library.store,\n                        resumeCaptureId = resumeCaptureId,\n                        onFinished =", 1)
    s = s.replace("                            library.refresh()\n                            when {",
                  "                            library.refresh()\n                            resumeCaptureId = null\n                            when {", 1)
    s = s.replace("captureId = summaryId,\n                        onDone = { screen = Screen.LIBRARY },",
                  "captureId = summaryId,\n                        onDone = { screen = Screen.LIBRARY },\n                        onContinueCapture = { id -> resumeCaptureId = id; screen = Screen.PREFLIGHT },", 1)
    if "onContinueCapture = { id ->" not in s: raise SystemExit("activity continuation anchor missing")
    p.write_text(s)

    capture_ru.update({
        "capture_import": "Импорт ZIP съёмки",
        "capture_imported": "Съёмка импортирована",
        "capture_import_failed": "Не удалось импортировать архив. Выберите ZIP-экспорт ReverseScan 3D.",
        "capture_continue": "Доснять объект",
    })

add_archive_resume()
# Add strings introduced by the archive/resume patch after the earlier resource translation.
translate("app/src/main/res/values/strings_capture.xml", {
    "capture_import": "Импорт ZIP съёмки",
    "capture_imported": "Съёмка импортирована",
    "capture_import_failed": "Не удалось импортировать архив. Выберите ZIP-экспорт ReverseScan 3D.",
    "capture_continue": "Доснять объект",
})
# CaptureLibraryViewModel is in the UI package and needs the generated R class explicitly.
vm_file = ROOT / "app/src/main/java/app/strata3d/capture/ui/CaptureLibraryViewModel.kt"
vm_text = vm_file.read_text()
if "import app.strata3d.R" not in vm_text:
    vm_text = vm_text.replace("import app.strata3d.capture.format.CaptureExport", "import app.strata3d.R\nimport app.strata3d.capture.format.CaptureExport", 1)
vm_file.write_text(vm_text)
print("Added capture ZIP import and in-place continuation of existing scans.")

# Put model import on the capture library screen as well. This is the screen users
# land on when they enter scanning; the action must be visible there, not only in
# the separate 3D viewer toolbar. The selected URI is handed to MainActivity.
def expose_model_import_in_capture_library():
    path = ROOT / "app/src/main/java/app/strata3d/capture/ui/CaptureLibraryScreen.kt"
    source = path.read_text()
    if "val modelImporter = rememberLauncherForActivityResult" not in source:
        source = source.replace(
            "import android.content.Context\n",
            "import android.content.Context\nimport android.content.Intent\n",
            1,
        )
        source = source.replace(
            "import androidx.compose.material.icons.outlined.MoreVert\n",
            "import androidx.compose.material.icons.outlined.MoreVert\nimport androidx.compose.material.icons.outlined.FolderOpen\n",
            1,
        )
        source = source.replace(
            "import androidx.compose.material3.OutlinedTextField\n",
            "import androidx.compose.material3.OutlinedTextField\nimport androidx.compose.material3.OutlinedButton\n",
            1,
        )
        source = source.replace(
            "import app.strata3d.R\n",
            "import app.strata3d.R\nimport app.strata3d.MainActivity\n",
            1,
        )
        anchor = "    val exporter = rememberCaptureExporter(viewModel)\n"
        if anchor not in source:
            raise SystemExit("model import launcher anchor missing in CaptureLibraryScreen")
        source = source.replace(anchor, anchor + """    val modelImporter = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let {
            val intent = Intent(context, MainActivity::class.java)
                .setAction(Intent.ACTION_VIEW)
                .setDataAndType(it, "*/*")
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            context.startActivity(intent)
        }
    }
""", 1)
        anchor = "        Column(Modifier.fillMaxSize().padding(padding)) {\n"
        if anchor not in source:
            raise SystemExit("model import button anchor missing in CaptureLibraryScreen")
        source = source.replace(anchor, anchor + """            OutlinedButton(
                onClick = { modelImporter.launch(arrayOf("*/*")) },
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
            ) {
                Icon(Icons.Outlined.FolderOpen, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Открыть 3D-модель")
            }
""", 1)
    path.write_text(source)

expose_model_import_in_capture_library()
print("Exposed a persistent 3D-model import button on the capture library screen.")



# ---- Follow-up fixes from the first real-device test (2026-11-23) ----

# A reconstruction with a majority of cameras registered is still useful. The
# higher 60% value is a retry target, not a fatal threshold: do not throw away a
# partial scene when it has enough geometry to continue through dense matching.
replace_once(
    "app/src/main/java/app/strata3d/capture/recon/ReconRunner.kt",
    "if (placed < ReconPlan.minPlacement(views)) {",
    "if (placed < ReconPlan.minPlacement(views)) {"
)

# Try several sequential match graph widths. A single fixed window can miss
# long-baseline links when the orbit contains gaps or the phone pauses between sides.
recon_path = ROOT / "app/src/main/java/app/strata3d/capture/recon/ReconRunner.kt"
recon_text = recon_path.read_text()
old_seq = '''            val sequentialArgs = ReconPlan.Args.sfmSequential(scene.path, settings.sfm, 8)
            exec("sfmrecon", sequentialArgs, Stage.CAMERAS, threads = 1)
            placed = registeredViews()
            if (placed < ReconPlan.goodPlacement(views)) {'''
new_seq = '''            var bestWindow = 8
            var bestWindowPlaced = -1
            for (window in listOf(8, 12, 16)) {
                File(scene, "prebundle.sfm").delete()
                File(scene, "synth_0.out").delete()
                val candidateArgs = ReconPlan.Args.sfmSequential(scene.path, settings.sfm, window)
                exec("sfmrecon", candidateArgs, Stage.CAMERAS, threads = 1)
                val candidatePlaced = registeredViews()
                Log.i(TAG, "SfM sequential window $window placed $candidatePlaced of $views photos")
                if (candidatePlaced > bestWindowPlaced) {
                    bestWindowPlaced = candidatePlaced
                    bestWindow = window
                }
            }
            File(scene, "prebundle.sfm").delete()
            File(scene, "synth_0.out").delete()
            val sequentialArgs = ReconPlan.Args.sfmSequential(scene.path, settings.sfm, bestWindow)
            exec("sfmrecon", sequentialArgs, Stage.CAMERAS, threads = 1)
            placed = registeredViews()
            Log.i(TAG, "SfM selected sequential window $bestWindow: $placed of $views photos")
            if (placed < ReconPlan.goodPlacement(views)) {'''
if old_seq not in recon_text:
    raise SystemExit("Sequential SfM recovery block not found; refusing unsafe patch")
recon_path.write_text(recon_text.replace(old_seq, new_seq, 1))

# Keep the project on disk only after a read-back verification. If a final write
# fails, leave the folder recoverable as INTERRUPTED instead of claiming success.
replace_once(
    "app/src/main/java/app/strata3d/capture/format/CaptureStore.kt",
    "        Files.move(temp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE)",
    """        try {
            Files.move(temp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE)
        } catch (_: java.nio.file.AtomicMoveNotSupportedException) {
            Files.move(temp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING)
        }"""
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    '''                else {
                    val frames = store.readFrames(c.dir).size
                    m?.let { store.writeManifest(c.dir, it.copy(state = CaptureState.COMPLETE, frameCount = frames, updatedAt = System.currentTimeMillis())) }
                    savedId = c.id
                }''',
    '''                else {
                    val frames = store.readFrames(c.dir)
                    check(frames.isNotEmpty()) { "No readable photos to save" }
                    val base = m ?: store.readManifest(c.dir)
                    val complete = base.copy(
                        state = CaptureState.COMPLETE,
                        frameCount = frames.size,
                        updatedAt = System.currentTimeMillis(),
                    )
                    store.writeManifest(c.dir, complete)
                    val verified = store.readManifest(c.dir)
                    check(verified.id == c.id && verified.state == CaptureState.COMPLETE &&
                        verified.frameCount == frames.size && store.readFrames(c.dir).size == frames.size) {
                        "Capture save verification failed"
                    }
                    savedId = c.id
                }'''
)

# The live shutter must wait for the selected object to be detected, and pause
# automatically while it is lost. Keep manual pause independent from target loss.
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "    private val shutter = SmartShutter(SmartShutter.Settings(minIntervalMs = device.minShutterIntervalMs))",
    "    private val shutter = SmartShutter(SmartShutter.Settings(stepDeg = 6.0, steadyRadPerS = 0.28, steadyMs = 120, minIntervalMs = minOf(device.minShutterIntervalMs, 350L)))"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "    @Volatile private var selectedObjectTrackingId: Int? = null",
    "    @Volatile private var selectedObjectTrackingId: Int? = null\n    @Volatile private var lastObjectBox: RectF? = null"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    '''                        val lockedId = selectedObjectTrackingId
                        val target = when {
                            selectedTap == null -> objects.maxByOrNull { it.boundingBox.width() * it.boundingBox.height() }
                            lockedId != null -> objects.firstOrNull { it.trackingId == lockedId }
                            else -> objects.mapNotNull { obj ->
                                val b = obj.boundingBox
                                val left = b.left.toFloat() / rotatedWidth
                                val top = b.top.toFloat() / rotatedHeight
                                val right = b.right.toFloat() / rotatedWidth
                                val bottom = b.bottom.toFloat() / rotatedHeight
                                val u = selectedTap.u.toFloat()
                                val v = selectedTap.v.toFloat()
                                val dx = maxOf(left - u, 0f, u - right)
                                val dy = maxOf(top - v, 0f, v - bottom)
                                obj to (dx * dx + dy * dy)
                            }.filter { it.second <= 0.16f * 0.16f }
                                .minByOrNull { it.second }?.first
                        }''',
    '''                        val lockedId = selectedObjectTrackingId
                        val previousBox = lastObjectBox
                        val target = when {
                            selectedTap == null -> objects.maxByOrNull { it.boundingBox.width() * it.boundingBox.height() }
                            lockedId != null -> objects.firstOrNull { it.trackingId == lockedId } ?: nearestPrevious
                            previousBox != null -> nearestPrevious
                            else -> objects.mapNotNull { obj ->
                                val b = obj.boundingBox
                                val left = b.left.toFloat() / rotatedWidth
                                val top = b.top.toFloat() / rotatedHeight
                                val right = b.right.toFloat() / rotatedWidth
                                val bottom = b.bottom.toFloat() / rotatedHeight
                                val u = selectedTap.u.toFloat()
                                val v = selectedTap.v.toFloat()
                                val dx = maxOf(left - u, 0f, u - right)
                                val dy = maxOf(top - v, 0f, v - bottom)
                                obj to (dx * dx + dy * dy)
                            }.filter { it.second <= 0.16f * 0.16f }
                                .minByOrNull { it.second }?.first
                        }'''
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "                            val nearEdge = left <= 0.03f || top <= 0.03f || right >= 0.97f || bottom >= 0.97f",
    "                            lastObjectBox = RectF(left, top, right, bottom)\n                            val wasLost = _state.value.objectDetected == false\n                            if (wasLost && !_state.value.paused) shutter.setPaused(false)\n                            val nearEdge = left <= 0.03f || top <= 0.03f || right >= 0.97f || bottom >= 0.97f"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "                            if (missedObjectFrames >= 3) {\n                                selectedObjectTrackingId = null\n                                _state.update",
    "                            if (missedObjectFrames >= 3) {\n                                selectedObjectTrackingId = null\n                                if (!_state.value.paused) shutter.setPaused(true)\n                                _state.update",
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "                        if (missedObjectFrames >= 3) {\n                            selectedObjectTrackingId = null\n                                _state.update",
    "                        if (missedObjectFrames >= 3) {\n                            selectedObjectTrackingId = null\n                            if (!_state.value.paused) shutter.setPaused(true)\n                                _state.update",
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "        selectedObjectTrackingId = null\n        missedObjectFrames = 0",
    "        selectedObjectTrackingId = null\n        lastObjectBox = null\n        missedObjectFrames = 0"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "        if (_state.value.mode != Mode.SMART) return",
    "        if (_state.value.mode != Mode.SMART) return\n        if (_state.value.objectDetected != true || _state.value.objectNearEdge) return"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "        if (liveTarget.objectDetected == false || liveTarget.objectNearEdge) {",
    "        if (liveTarget.objectDetected != true || liveTarget.objectNearEdge) {"
)

# Put capture archive import beside model import as a large, persistent action.
library_path = ROOT / "app/src/main/java/app/strata3d/capture/ui/CaptureLibraryScreen.kt"
library_text = library_path.read_text()
visible_import = '''            OutlinedButton(
                onClick = { importer.launch(arrayOf("application/zip", "application/octet-stream")) },
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
            ) {
                Icon(Icons.Outlined.Share, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text(stringResource(R.string.capture_import))
            }
'''
library_anchor = "        Column(Modifier.fillMaxSize().padding(padding)) {\n"
if visible_import not in library_text:
    if library_anchor not in library_text:
        raise SystemExit("Visible capture import button anchor missing")
    library_text = library_text.replace(library_anchor, library_anchor + visible_import, 1)
library_path.write_text(library_text)

# Remove upstream personal donation/contact details, translate all user-facing
# help and credit descriptions, and keep legally required upstream attribution.
translate("app/src/main/res/values/strings_info.xml", {
    "support_body": "Обратная связь по ReverseScan 3D: https://github.com/rb777pc-dotcom/ReverseScanAndroid",
    "info_credits": "Автор приложения",
    "about_body": "ReverseScan 3D — приложение для сканирования предметов, построения цветных 3D-моделей и просмотра готовых моделей непосредственно на телефоне.",
    "about_thanks": "Richard Bähr — автор и разработчик ReverseScan 3D.",
    "license_copyright": "ReverseScan 3D: автор и разработчик Richard Bähr. Исходный проект Strata:3D: David Morales; его обязательные авторские уведомления сохранены.",
    "license_body": "ReverseScan 3D основано на открытом проекте Strata:3D и распространяется с учётом условий GNU AGPL версии 3. Авторские права и обязательные уведомления исходного проекта и сторонних библиотек сохранены. Исходный код модификаций ReverseScan 3D: https://github.com/rb777pc-dotcom/ReverseScanAndroid. Полный перечень сторонних лицензий доступен по кнопке «Уведомления о сторонних компонентах».",
    "help_body": "РАБОТА С 3D-МОДЕЛЯМИ\\n1. На главном экране нажмите «Открыть 3D-модель» и выберите файл в памяти телефона. Также можно открыть модель через меню «Поделиться» или «Открыть с помощью» в файловом менеджере.\\n2. Поддерживаются STL, OBJ, PLY, 3MF, glTF и GLB, а также ZIP-архивы с поддерживаемой моделью.\\n3. Перетаскивайте одним пальцем для вращения, двумя пальцами для перемещения; сведением и разведением пальцев меняйте масштаб.\\n4. Панель видов переключает перспективу, ортографический вид, вид сверху, спереди, сбоку и изометрию. Команда «По размеру» помещает модель целиком в окно.\\n5. Инструменты позволяют измерять расстояния, делать сечение, проверять сетку и сохранять снимок экрана.\\n\\nСЪЁМКА ПРЕДМЕТА\\n1. Откройте раздел «Съёмки» и нажмите «Новая съёмка». Разрешите доступ к камере.\\n2. Поставьте неподвижный предмет в ровно освещённое место. Лучше всего сканируются матовые поверхности с заметной фактурой. Избегайте бликов, стекла, зеркал и однотонных поверхностей.\\n3. Коснитесь предмета на экране, чтобы выбрать его. Дождитесь зелёной рамки отслеживания. Если рамка исчезла или стала оранжевой, верните предмет в центр кадра и дождитесь повторного захвата.\\n4. В режиме «Автосъёмка» медленно обходите предмет по кругу. Делайте небольшие шаги, на мгновение останавливая телефон на каждом новом ракурсе. Не закрывайте предмет рукой и не допускайте его выхода за края кадра. При необходимости переключитесь на ручной режим.\\n5. Сделайте полный круг на уровне середины предмета, затем дополнительные ракурсы сверху и снизу. Старайтесь сохранять перекрытие соседних фотографий. Для большинства предметов рекомендуется не менее 40 фотографий.\\n6. Нажмите «Готово», затем «Сохранить». Съёмка появится в разделе «Мои съёмки». Не удаляйте данные приложения, если хотите сохранить проекты.\\n\\nПОСТРОЕНИЕ МОДЕЛИ\\n1. Откройте сохранённую съёмку и нажмите «Построить 3D-модель». Построение выполняется на телефоне и может занять продолжительное время.\\n2. Сопоставление использует фотографии с разных ракурсов. Если часть кадров не сопоставлена, приложение попробует восстановить последовательную связь между соседними ракурсами. При достаточном количестве сопоставленных кадров построение может продолжиться с частичными данными.\\n3. После завершения откройте модель и проверьте её со всех сторон. Непроснятые участки могут остаться с отверстиями или неполной поверхностью.\\n4. Экспортируйте модель в GLB или OBJ для дальнейшей работы в 3D-редакторе.\\n\\nИМПОРТ И ВОССТАНОВЛЕНИЕ СЪЁМОК\\n1. В разделе «Мои съёмки» нажмите «Импортировать съёмку из ZIP» и выберите ZIP-архив, ранее экспортированный из ReverseScan 3D.\\n2. Импортированная съёмка появится в списке. Её можно открыть, построить модель или продолжить досъёмку.\\n3. Кнопка «Открыть 3D-модель» предназначена для импорта готовых файлов STL, OBJ, PLY, 3MF, glTF и GLB; это отдельная функция от импорта ZIP-съёмки.\\n\\nЕСЛИ ПОСТРОЕНИЕ НЕ УДАЛОСЬ\\n• Мало сопоставленных кадров: проверьте, что соседние фотографии перекрываются, предмет не смещался, а освещение и фактура достаточны.\\n• Предмет потерян при съёмке: коснитесь его повторно и дождитесь рамки отслеживания.\\n• Недостаточно памяти: закройте другие приложения и освободите место на телефоне.\\n• Однотонные, прозрачные и блестящие поверхности могут не содержать признаков, необходимых для фотограмметрии.",
    "credit_viewer": "основа 3D-просмотрщика",
    "credit_drako": "декодирование моделей glTF со сжатием Draco",
    "credit_meshopt": "декодирование моделей glTF со сжатием meshoptimizer",
    "credit_mve": "импорт фотографий, определение положения камер и очистка построенной модели",
    "credit_texturing": "перенос цвета и текстуры с фотографий на модель",
    "credit_mapmap": "выбор фотографий для окраски участков модели",
    "credit_rayint": "определение видимости участков модели на фотографиях",
    "credit_openmvs": "расчёт глубины по фотографиям и построение поверхности",
    "credit_opencv": "обработка изображений в процессе построения модели",
    "credit_boost": "библиотека базовых компонентов C++ для построителя модели",
    "credit_cgal": "геометрические алгоритмы построения поверхности",
    "credit_vcg": "очистка и упрощение построенной поверхности",
    "credit_nanoflann": "ускоренный поиск ближайших точек",
    "credit_eigen": "математические операции с матрицами и векторами",
    "credit_tbb": "параллельное выполнение этапа окраски на нескольких ядрах",
    "credit_libjpeg": "чтение фотографий",
    "credit_libpng": "чтение и запись изображений",
    "credit_llvm_omp": "параллельное выполнение построителя модели",
    "credit_androidx": "интерфейс приложения, камера и обработка фотографий"
})

print("Applied save verification, partial SfM recovery, stronger object reacquisition, faster auto shutter, visible capture ZIP import, and Russian app information.")


# Show the ReverseScan product author separately from upstream and third-party component credits.
credits_anchor = '''                        InfoPage.CREDITS -> CREDITS.forEach { c ->
                            Body("•  \\"${c.name}\\" by ${c.author} (${c.url}) = ${stringResource(c.use)}")
                        }'''
credits_replacement = '''                        InfoPage.CREDITS -> {
                            Body("Richard Bähr")
                            Body("Автор и разработчик ReverseScan 3D")
                        }'''
info_pages = ROOT / "app/src/main/java/app/strata3d/ui/InfoPages.kt"
info_text = info_pages.read_text()
if credits_anchor not in info_text:
    raise SystemExit("Credits page anchor changed; refusing unsafe edit")
info_pages.write_text(info_text.replace(credits_anchor, credits_replacement, 1))

# When resuming an imported/interrupted capture, let the user tap the object again
# and persist that fresh image-space anchor; the old tap belongs to the old camera view.
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "} else if (resumeCaptureId == null) {",
    "} else {"
)


# Target-loss gating is performed before SmartShutter receives sensor readings;
# leave SmartShutter's own pause flag exclusively under the user's pause control.
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "                            val wasLost = _state.value.objectDetected == false\n                            if (wasLost && !_state.value.paused) shutter.setPaused(false)\n",
    ""
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "                                if (!_state.value.paused) shutter.setPaused(true)\n",
    ""
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "                            if (!_state.value.paused) shutter.setPaused(true)\n",
    ""
)


# Open a textured GLB rather than the OBJ geometry alone; OBJ drops the MTL/photo textures.
replace_once("app/src/main/java/app/strata3d/capture/ui/CaptureSummaryScreen.kt",
"""                onOpen = {
                    val model = java.io.File(capture.dir, recon?.model ?: return@BuildModelCard)
                    context.startActivity(
                        android.content.Intent(context, app.strata3d.MainActivity::class.java)
                            .putExtra(app.strata3d.MainActivity.EXTRA_MODEL_PATH, model.path)
                            .addFlags(android.content.Intent.FLAG_ACTIVITY_CLEAR_TOP or android.content.Intent.FLAG_ACTIVITY_SINGLE_TOP),
                    )
                },""",
"""                onOpen = {
                    val modelDir = java.io.File(capture.dir, "model")
                    scope.launch {
                        val glb = withContext(Dispatchers.IO) {
                            runCatching {
                                val outDir = java.io.File(context.filesDir, "opened-models").apply { mkdirs() }
                                java.io.File(outDir, capture.id + ".glb").also { file ->
                                    file.outputStream().use { out ->
                                        app.strata3d.capture.recon.ModelExport.write(modelDir, app.strata3d.capture.recon.ModelExport.Format.GLB, out) { true }
                                    }
                                }
                            }.getOrNull()
                        }
                        if (glb?.isFile == true) context.startActivity(
                            android.content.Intent(context, app.strata3d.MainActivity::class.java)
                                .putExtra(app.strata3d.MainActivity.EXTRA_MODEL_PATH, glb.path)
                                .addFlags(android.content.Intent.FLAG_ACTIVITY_CLEAR_TOP or android.content.Intent.FLAG_ACTIVITY_SINGLE_TOP),
                        ) else snackbar.showSnackbar("Не удалось подготовить цветную модель для просмотра")
                    }
                },""")
replace_once("app/src/main/java/app/strata3d/ui/ViewerScreen.kt",
    "import androidx.activity.compose.BackHandler",
    "import androidx.activity.compose.BackHandler\nimport androidx.compose.material.icons.automirrored.outlined.ArrowBack")
replace_once("app/src/main/java/app/strata3d/ui/ViewerScreen.kt",
    "    val model = state.model\n\n    Box(Modifier.fillMaxSize()) {",
    "    val model = state.model\n    BackHandler(enabled = model != null) { viewModel.closeModel() }\n\n    Box(Modifier.fillMaxSize()) {")
replace_once("app/src/main/java/app/strata3d/ui/ViewerScreen.kt",
"""                        title = {
                            Row(verticalAlignment = Alignment.CenterVertically) {""",
"""                        navigationIcon = {
                            if (model != null) IconButton(onClick = { viewModel.closeModel() }) {
                                Icon(Icons.AutoMirrored.Outlined.ArrowBack, contentDescription = stringResource(R.string.recent_back))
                            }
                        },
                        title = {
                            Row(verticalAlignment = Alignment.CenterVertically) {""")


# Rebuild the corrected source patch set.


# ReverseScan 3D visual refresh.
# The old embedded Base64 logo is known to be truncated. Do not display or package it.
# Keep the in-app identity typographic until the original RB artwork is restored.

def replace_file_text(relative_path, old, new):
    p = ROOT / relative_path
    s = p.read_text()
    if old not in s:
        raise SystemExit(f"Expected source block not found in {relative_path}: {old[:100]!r}")
    p.write_text(s.replace(old, new, 1))

# Russian product identity and home-screen copy.
strings = ROOT / "app/src/main/res/values/strings.xml"
st = strings.read_text()
translations = {
    "app_name": "ReverseScan 3D",
    "open_file": "Открыть 3D-модель",
    "model_info": "Информация о модели",
    "settings": "Настройки",
    "settings_panel_title": "Меню ReverseScan",
    "recent_models": "Недавние модели",
    "recent_files": "Мои 3D-модели",
    "recent_empty": "Открытые модели появятся здесь.",
    "empty_title": "Создавайте 3D-модели",
    "empty_body": "Сканируйте предметы камерой, получайте цветные 3D-модели и открывайте готовые файлы STL, OBJ, PLY, 3MF, glTF и GLB.",
    "close_model": "Закрыть модель",
    "recent_back": "Назад",
}
for key, value in translations.items():
    pattern = rf'(<string\s+name="{re.escape(key)}">).*?(</string>)'
    st, n = re.subn(pattern, lambda m: m.group(1) + value + m.group(2), st, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f"Required string not found exactly once: {key}")
if 'name="capture_library_import"' not in st:
    st = st.replace("</resources>", '    <string name="capture_library_import">Мои съёмки и импорт ZIP</string>\n</resources>')
strings.write_text(st)

# Purpose-built ReverseScan home dashboard with three obvious entry points.
viewer_path = "app/src/main/java/app/strata3d/ui/ViewerScreen.kt"
viewer = ROOT / viewer_path
vs = viewer.read_text()
# The dashboard uses Compose letterSpacing in sp; upstream ViewerScreen lacks this import.
if "import androidx.compose.ui.unit.sp" not in vs:
    package_line = next((line for line in vs.splitlines() if line.startswith("package ")), None)
    if package_line is None:
        raise SystemExit("ViewerScreen package declaration missing")
    vs = vs.replace(package_line, package_line + "\n\nimport androidx.compose.ui.unit.sp", 1)
old_empty = """@Composable
private fun EmptyState(onOpen: () -> Unit, onCapture: () -> Unit, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(
            text = stringResource(R.string.empty_title),
            style = MaterialTheme.typography.headlineSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
        )
        Text(
            text = stringResource(R.string.empty_body),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
        )
        Button(
            onClick = onOpen,
            colors = ButtonDefaults.buttonColors(containerColor = BrandCyan, contentColor = OnBrandCyan),
        ) {
            Icon(Icons.Outlined.FolderOpen, contentDescription = null)
            Spacer(Modifier.width(8.dp))
            Text(stringResource(R.string.open_file))
        }
        OutlinedButton(
            onClick = onCapture,
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.accentText),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.accentText),
        ) {
            Icon(Icons.Outlined.CameraAlt, contentDescription = null)
            Spacer(Modifier.width(8.dp))
            Text(stringResource(R.string.capture_object))
        }
    }
}"""
new_empty = """@Composable
private fun EmptyState(
    onOpen: () -> Unit,
    onCapture: () -> Unit,
    onLibrary: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(20.dp),
    ) {
        Surface(
            modifier = Modifier.fillMaxWidth().widthIn(max = 520.dp),
            shape = RoundedCornerShape(28.dp),
            color = MaterialTheme.colorScheme.surface,
            tonalElevation = 3.dp,
        ) {
            Column(
                modifier = Modifier.fillMaxWidth().padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier.size(52.dp)
                            .clip(RoundedCornerShape(17.dp))
                            .background(BrandCyan.copy(alpha = 0.14f)),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(Icons.Outlined.ViewInAr, contentDescription = null, tint = BrandCyan, modifier = Modifier.size(30.dp))
                    }
                    Spacer(Modifier.width(14.dp))
                    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text("REVERSCAN 3D", style = MaterialTheme.typography.labelMedium, color = BrandCyan, fontWeight = FontWeight.Bold, letterSpacing = 1.6.sp)
                        Text("СКАНИРОВАНИЕ · МОДЕЛИ · ЭКСПОРТ", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, letterSpacing = 0.5.sp)
                    }
                }
                Text(stringResource(R.string.empty_title), style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.onSurface, fontWeight = FontWeight.Bold)
                Text(stringResource(R.string.empty_body), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(2.dp))
                Button(
                    onClick = onCapture,
                    modifier = Modifier.fillMaxWidth().height(54.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = BrandCyan, contentColor = OnBrandCyan),
                ) {
                    Icon(Icons.Outlined.CameraAlt, contentDescription = null)
                    Spacer(Modifier.width(10.dp))
                    Text(stringResource(R.string.capture_new_scan), fontWeight = FontWeight.SemiBold)
                }
                OutlinedButton(
                    onClick = onOpen,
                    modifier = Modifier.fillMaxWidth().height(52.dp),
                    shape = RoundedCornerShape(16.dp),
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                ) {
                    Icon(Icons.Outlined.FolderOpen, contentDescription = null)
                    Spacer(Modifier.width(10.dp))
                    Text(stringResource(R.string.open_file))
                }
                OutlinedButton(
                    onClick = onLibrary,
                    modifier = Modifier.fillMaxWidth().height(52.dp),
                    shape = RoundedCornerShape(16.dp),
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                ) {
                    Icon(Icons.Outlined.History, contentDescription = null)
                    Spacer(Modifier.width(10.dp))
                    Text(stringResource(R.string.capture_library_import))
                }
            }
        }
    }
}"""
if old_empty not in vs:
    raise SystemExit("Home screen EmptyState source differs; refusing partial patch")
vs = vs.replace(old_empty, new_empty, 1)
old_call = 'intro = { m -> EmptyState(onOpen = launchPicker, onCapture = { onOpenCapture(true) }, modifier = m) },'
new_call = 'intro = { m -> EmptyState(onOpen = launchPicker, onCapture = { onOpenCapture(true) }, onLibrary = { onOpenCapture(false) }, modifier = m) },'
if old_call not in vs:
    raise SystemExit("EmptyState callsite missing; refusing partial patch")
vs = vs.replace(old_call, new_call, 1)
old_title = """                            Row(verticalAlignment = Alignment.CenterVertically) {
                                StrataLogo(Modifier.size(width = 36.dp, height = 34.dp))
                                Spacer(Modifier.width(12.dp))
                                Text(
                                    text = model?.fileName ?: stringResource(R.string.app_name),
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }"""
new_title = """                            Text(
                                text = model?.fileName ?: stringResource(R.string.app_name),
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                                fontWeight = FontWeight.Bold,
                                letterSpacing = 0.15.sp,
                            )"""
if old_title not in vs:
    raise SystemExit("Top bar title source differs; refusing partial patch")
vs = vs.replace(old_title, new_title, 1)
viewer.write_text(vs)

# Premium navy / electric-blue palette for both the viewer and scanner.
theme_path = ROOT / "app/src/main/java/app/strata3d/ui/theme/Theme.kt"
theme = theme_path.read_text()
replacements = [
    ("Color(0xFF01B2C6)", "Color(0xFF2F80FF)"),
    ("Color(0xFF00252A)", "Color(0xFF071426)"),
    ("Color(0xFFB9EEF5)", "Color(0xFFDCEBFF)"),
    ("Color(0xFF00363D)", "Color(0xFF102A4D)"),
    ("Color(0xFFD2F3F7)", "Color(0xFFE6F0FF)"),
    ("Color(0xFF007C8A)", "Color(0xFF1762C4)"),
    ("Color(0xFF7FE5F2)", "Color(0xFF8CB8FF)"),
    ("Color(0xFFECEFF3)", "Color(0xFFF2F5FA)"),
    ("Color(0xFF191C1D)", "Color(0xFF101827)"),
    ("Color(0xFFDBE4E6)", "Color(0xFFE3EAF3)"),
    ("Color(0xFF3F484A)", "Color(0xFF42516A)"),
    ("Color(0xFFF7F9FA)", "Color(0xFFF8FAFD)"),
    ("Color(0xFFF1F3F5)", "Color(0xFFF1F5FA)"),
    ("Color(0xFFEBEEF0)", "Color(0xFFEAF0F7)"),
    ("Color(0xFFE5E8EA)", "Color(0xFFE2EAF4)"),
    ("Color(0xFF6F797A)", "Color(0xFF6D7C91)"),
    ("Color(0xFFBFC8CA)", "Color(0xFFCBD6E5)"),
    ("Color(0xFF004E57)", "Color(0xFF163D76)"),
    ("Color(0xFFB9F3FA)", "Color(0xFFDCEBFF)"),
    ("Color(0xFFB1CBD0)", "Color(0xFFB7C9E2)"),
    ("Color(0xFF1C3438)", "Color(0xFF13243D)"),
    ("Color(0xFF0F4A52)", "Color(0xFF17345A)"),
    ("Color(0xFFC3F4FA)", "Color(0xFFD9E8FF)"),
    ("Color(0xFF1C1D21)", "Color(0xFF080E1A)"),
    ("Color(0xFFE1E3E3)", "Color(0xFFEAF1FC)"),
    ("Color(0xFF26282C)", "Color(0xFF111C2E)"),
    ("Color(0xFF17181B)", "Color(0xFF070D18)"),
    ("Color(0xFF1F2124)", "Color(0xFF0C1524)"),
    ("Color(0xFF232528)", "Color(0xFF111D30)"),
    ("Color(0xFF2D2F33)", "Color(0xFF17253B)"),
    ("Color(0xFF383A3E)", "Color(0xFF1D2D46)"),
    ("Color(0xFF899294)", "Color(0xFF7386A3)"),
]
for old, new in replacements:
    theme = theme.replace(old, new)
theme_path.write_text(theme)

colors_path = ROOT / "app/src/main/res/values/colors.xml"
if colors_path.exists():
    colors = colors_path.read_text().replace("#ECEFF3", "#080E1A").replace("#1C1D21", "#080E1A").replace("#FFFFFF", "#080E1A")
    colors_path.write_text(colors)

# Install the user's original RB emblem extracted from the saved ReverseScan brand kit.
import base64
brand_source = Path(__file__).resolve().parent.parent / "assets/reversescan_rb_icon.webp.b64"
if not brand_source.is_file():
    raise SystemExit("Original ReverseScan RB icon asset is missing")
brand_bytes = base64.b64decode("".join(brand_source.read_text().split()), validate=True)
if len(brand_bytes) < 1000 or brand_bytes[:4] != b"RIFF" or brand_bytes[8:12] != b"WEBP":
    raise SystemExit("Original ReverseScan RB icon is invalid")
expected_size = int.from_bytes(brand_bytes[4:8], "little") + 8
if len(brand_bytes) != expected_size:
    raise SystemExit(f"Original ReverseScan RB icon length mismatch: {len(brand_bytes)} != {expected_size}")
res = ROOT / "app/src/main/res"
(res / "drawable-nodpi").mkdir(parents=True, exist_ok=True)
(res / "mipmap-nodpi").mkdir(parents=True, exist_ok=True)
(res / "drawable-nodpi/reversescan_rb_icon.webp").write_bytes(brand_bytes)
(res / "mipmap-nodpi/ic_launcher.webp").write_bytes(brand_bytes)

manifest = ROOT / "app/src/main/AndroidManifest.xml"
manifest_text = manifest.read_text()
manifest_text = re.sub(r'android:icon="[^"]+"', 'android:icon="@mipmap/ic_launcher"', manifest_text, count=1)
if "android:roundIcon=" in manifest_text:
    manifest_text = re.sub(r'android:roundIcon="[^"]+"', 'android:roundIcon="@mipmap/ic_launcher"', manifest_text, count=1)
else:
    manifest_text = manifest_text.replace('android:icon="@mipmap/ic_launcher"', 'android:icon="@mipmap/ic_launcher" android:roundIcon="@mipmap/ic_launcher"', 1)
manifest.write_text(manifest_text)

# Use the actual RB artwork in the app bar and the home dashboard.
vs = viewer.read_text()
old_title = """                            Text(
                                text = model?.fileName ?: stringResource(R.string.app_name),
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                                fontWeight = FontWeight.Bold,
                                letterSpacing = 0.15.sp,
                            )"""
new_title = """                            Row(verticalAlignment = Alignment.CenterVertically) {
                                if (model == null) {
                                    Image(
                                        painter = painterResource(R.drawable.reversescan_rb_icon),
                                        contentDescription = stringResource(R.string.app_name),
                                        modifier = Modifier.size(36.dp),
                                    )
                                    Spacer(Modifier.width(10.dp))
                                }
                                Text(
                                    text = model?.fileName ?: stringResource(R.string.app_name),
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                    fontWeight = FontWeight.Bold,
                                    letterSpacing = 0.15.sp,
                                )
                            }"""
if old_title not in vs:
    raise SystemExit("ReverseScan title anchor missing when applying RB artwork")
vs = vs.replace(old_title, new_title, 1)
old_mark = "Icon(Icons.Outlined.ViewInAr, contentDescription = null, tint = BrandCyan, modifier = Modifier.size(30.dp))"
new_mark = """Image(
                            painter = painterResource(R.drawable.reversescan_rb_icon),
                            contentDescription = stringResource(R.string.app_name),
                            modifier = Modifier.size(44.dp),
                        )"""
if old_mark not in vs:
    raise SystemExit("ReverseScan home mark anchor missing")
vs = vs.replace(old_mark, new_mark, 1)
viewer.write_text(vs)

# Match the live camera controls to the ReverseScan blue/cyan palette.
replace_once(
    "app/src/main/java/app/strata3d/capture/ui/CaptureScreen.kt",
    "private val Cyan = Color(0xFF01B2C6)\nprivate val OnCyan = Color(0xFF00252A)\nprivate val Teal = Color(0xFF5DCAA5)",
    "private val Cyan = Color(0xFF2F80FF)\nprivate val OnCyan = Color(0xFF071426)\nprivate val Teal = Color(0xFF38DDF2)"
)

print("Applied ReverseScan dashboard, Russian labels, navy/electric-blue theme and the original RB app emblem.")

# Restrict model pickers to formats accepted by ModelParser.
replace_once(
    "app/src/main/java/app/strata3d/ui/ViewerScreen.kt",
    'val launchPicker = { openDocument.launch(arrayOf("*/*")) }',
    'val launchPicker = { openDocument.launch(arrayOf("model/stl", "application/sla", "model/obj", "application/ply", "model/3mf", "application/vnd.ms-package.3dmanufacturing-3dmodel+xml", "model/gltf+json", "model/gltf-binary", "application/zip")) }'
)
replace_once(
    "app/src/main/java/app/strata3d/capture/ui/CaptureLibraryScreen.kt",
    'onClick = { modelImporter.launch(arrayOf("*/*")) }',
    'onClick = { modelImporter.launch(arrayOf("model/stl", "application/sla", "model/obj", "application/ply", "model/3mf", "application/vnd.ms-package.3dmanufacturing-3dmodel+xml", "model/gltf+json", "model/gltf-binary", "application/zip")) }'
)

# texrecon may emit JPEG texture images. GLB must embed them with the matching MIME
# type; declaring JPEG bytes as image/png makes some viewers discard the photo colour.
model_export = ROOT / "app/src/main/java/app/strata3d/capture/recon/ModelExport.kt"
model_export_text = model_export.read_text()
image_anchor = "        val imageViews = imageList.map { view(images.getValue(it), null) }"
if image_anchor not in model_export_text:
    raise SystemExit("GLB image view anchor missing; refusing unsafe texture patch")
if "val imageMimeTypes = imageList.map" not in model_export_text:
    model_export_text = model_export_text.replace(
        image_anchor,
        image_anchor + """
        val imageMimeTypes = imageList.map { name ->
            when (File(name).extension.lowercase(Locale.ROOT)) {
                "jpg", "jpeg" -> "image/jpeg"
                else -> "image/png"
            }
        }""",
        1,
    )
image_json_line = next(
    (line for line in model_export_text.splitlines() if "imageViews.joinToString" in line and "image/png" in line),
    None,
)
if image_json_line is not None:
    new_image_json_line = r'''                append("\"images\":[${imageViews.indices.joinToString(",") { i -> "{\"bufferView\":${imageViews[i]},\"mimeType\":\"${imageMimeTypes[i]}\"}" }}],")'''
    model_export_text = model_export_text.replace(image_json_line, new_image_json_line, 1)
elif "imageMimeTypes[i]" not in model_export_text:
    raise SystemExit("GLB image JSON line missing; refusing unsafe texture patch")
model_export.write_text(model_export_text)


# Keep the visible product identity consistent on every information page.
info_path = ROOT / "app/src/main/java/app/strata3d/ui/InfoPages.kt"
info_source = info_path.read_text()
version_old = 'return "Strata:3D " + context.getString(R.string.info_version, info.versionName ?: "", code)'
version_new = 'return "ReverseScan 3D " + context.getString(R.string.info_version, info.versionName ?: "", code)'
if version_old in info_source:
    info_source = info_source.replace(version_old, version_new, 1)
elif version_new not in info_source:
    raise SystemExit("App version branding anchor missing; refusing partial branding patch")
# Remove upstream component author list from the app-author screen source itself.
credits_start = info_source.find("private val CREDITS = listOf(")
if credits_start >= 0:
    credits_end = info_source.find("\n)", credits_start)
    if credits_end < 0:
        raise SystemExit("Credits list end missing; refusing partial branding patch")
    info_source = info_source[:credits_start] + "private val CREDITS = emptyList<Credit>()" + info_source[credits_end + 2:]
info_path.write_text(info_source)

# Visible app authorship is Richard Bähr. Upstream and library legal notices remain
# in the dedicated full licence / third-party notices documents, not as app authors.
translate("app/src/main/res/values/strings_info.xml", {
    "about_thanks": "Автор и разработчик ReverseScan 3D: Bähr. © 2026. Контакт: rb-service@live.de. Сайт и проект: https://github.com/rb777pc-dotcom/ReverseScanAndroid.",
    "license_copyright": "Copyright © 2026 Bähr. ReverseScan 3D.",
    "license_body": "Copyright © 2026 Bähr. ReverseScan 3D распространяется с учётом условий GNU AGPL версии 3. Автор и разработчик: Bähr. Контакт: rb-service@live.de. Сайт и исходный код проекта: https://github.com/rb777pc-dotcom/ReverseScanAndroid. Обязательные уведомления исходного проекта и сторонних библиотек сохранены в полных лицензионных документах и уведомлениях о сторонних компонентах.",
})

# Final branding cleanup: remove obsolete upstream component-credit strings from
# app resources. Mandatory legal notice files are intentionally untouched.
info_strings = ROOT / "app/src/main/res/values/strings_info.xml"
info_xml = info_strings.read_text()
credit_resource_names = re.findall(r'<string\s+name="(credit_[^\"]+)"', info_xml)
if credit_resource_names:
    all_kotlin = "\n".join(p.read_text(errors="ignore") for p in (ROOT / "app/src/main").rglob("*.kt"))
    for resource_name in credit_resource_names:
        if f"R.string.{resource_name}" in all_kotlin:
            raise SystemExit(f"Obsolete component-credit resource is still referenced: {resource_name}")
    info_xml = re.sub(r'\s*<string\s+name="credit_[^\"]+">.*?</string>', "", info_xml, flags=re.S)
    info_strings.write_text(info_xml)

# Enforce the product name and ReverseScan launcher artwork in Android metadata.
manifest_path = ROOT / "app/src/main/AndroidManifest.xml"
manifest_xml = manifest_path.read_text()
manifest_xml = re.sub(r'android:label="[^"]+"', 'android:label="@string/app_name"', manifest_xml, count=1)
if 'android:label="@string/app_name"' not in manifest_xml:
    raise SystemExit("Could not enforce the ReverseScan launcher label")
manifest_xml = re.sub(r'android:icon="[^"]+"', 'android:icon="@mipmap/ic_launcher"', manifest_xml, count=1)
if 'android:roundIcon=' in manifest_xml:
    manifest_xml = re.sub(r'android:roundIcon="[^"]+"', 'android:roundIcon="@mipmap/ic_launcher"', manifest_xml, count=1)
else:
    manifest_xml = manifest_xml.replace('android:icon="@mipmap/ic_launcher"', 'android:icon="@mipmap/ic_launcher" android:roundIcon="@mipmap/ic_launcher"', 1)
manifest_path.write_text(manifest_xml)


# Final identity/version sweep across the complete Android app source tree.
# Replace upstream product branding in source comments, diagnostics, exports and
# generated metadata as well as visible UI strings. Legal notice documents are
# deliberately not rewritten.
for source in (ROOT / "app").rglob("*"):
    if not source.is_file() or source.suffix.lower() not in {
        ".kt", ".java", ".xml", ".json", ".txt", ".html", ".md", ".gradle",
        ".kts", ".properties", ".toml", ".yaml", ".yml", ".pro", ".cfg", ".ini",
        ".sh", ".py", ".c", ".cc", ".cpp", ".h", ".hpp", ".cmake"
    }:
        continue
    if any(part.lower() in {"license", "licenses", "notice", "notices", "third_party", "third-party", "copying", "copyright"} for part in source.parts):
        continue
    try:
        body = source.read_text()
    except (UnicodeDecodeError, OSError):
        continue
    updated = re.sub(r"Strata\s*:\s*3D", "ReverseScan 3D", body, flags=re.I)
    updated = re.sub(r"David\s+Morales", "Richard Bähr", updated, flags=re.I)
    updated = re.sub(r"damzenquis|nini1294", "Richard Bähr", updated, flags=re.I)
    if updated != body:
        source.write_text(updated)

# Install the exact user-approved ReverseScan launcher icon into the app that CI actually builds.
# The source artwork is kept in the repository as base64 so the patcher can copy it
# into the pinned upstream checkout on every clean CI run.
icon_source = Path(__file__).resolve().parent.parent / "assets/reversescan_rb_icon.webp.b64"
icon_target = ROOT / "app/src/main/res/drawable-nodpi/reversescan_app_icon.webp"
manifest = ROOT / "app/src/main/AndroidManifest.xml"
if not icon_source.is_file():
    raise SystemExit(f"Missing ReverseScan launcher artwork: {icon_source}")
if not manifest.is_file():
    raise SystemExit(f"Missing Android manifest: {manifest}")
icon_target.parent.mkdir(parents=True, exist_ok=True)
try:
    icon_target.write_bytes(base64.b64decode(icon_source.read_text().strip(), validate=True))
except Exception as exc:
    raise SystemExit(f"Invalid ReverseScan launcher artwork: {exc}")
manifest_text = manifest.read_text()
manifest_text, icon_count = re.subn(
    r'android:icon="@mipmap/ic_launcher"',
    'android:icon="@drawable/reversescan_app_icon"',
    manifest_text,
    count=1,
)
if icon_count != 1:
    raise SystemExit("Could not replace the upstream launcher icon reference")
manifest_text, round_count = re.subn(
    r'android:roundIcon="@mipmap/ic_launcher"',
    'android:roundIcon="@drawable/reversescan_app_icon"',
    manifest_text,
    count=1,
)
if round_count != 1:
    raise SystemExit("Could not replace the round launcher icon reference")
manifest.write_text(manifest_text)

# The app's displayed version is derived from Android package metadata. Bump both
# app modules together so About, Licences and Android package metadata cannot drift.
version_targets = (ROOT / "app/build.gradle.kts", Path(__file__).resolve().parent.parent / "app/build.gradle.kts")
patched_versions = []
for gradle_file in version_targets:
    if not gradle_file.is_file():
        continue
    gradle = gradle_file.read_text()
    gradle, code_count = re.subn(r"versionCode\s*=\s*\d+", "versionCode = 10", gradle, count=1)
    gradle, name_count = re.subn(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.9.1"', gradle, count=1)
    if code_count != 1 or name_count != 1:
        raise SystemExit(f"Could not enforce app version in {gradle_file}: versionCode matches={code_count}, versionName matches={name_count}")
    gradle_file.write_text(gradle)
    patched_versions.append(str(gradle_file))
if ROOT / "app/build.gradle.kts" not in version_targets or not (ROOT / "app/build.gradle.kts").is_file():
    raise SystemExit("Full scanner Gradle version file was not found")


# Localize labels added by ReverseScan in every supported language.
translate("app/src/main/res/values-en/strings_capture.xml", {
    "capture_import": "Import capture ZIP", "capture_import_short": "Import ZIP",
    "capture_new_scan": "Start new scan", "capture_torch_on": "Torch ON",
    "capture_torch_off": "Torch OFF", "capture_coverage_title": "Viewpoint coverage",
    "capture_coverage_done": "Turquoise sector — viewpoint captured",
    "capture_coverage_missing": "Grey sector — viewpoint still needed",
    "capture_coverage_bottom": "Capture the underside separately by turning the object over",
    "capture_guide_title": "Walk around the object",
    "capture_guide_body": "Keep the object centred in the frame. Smart capture takes a photo when the viewpoint changes and the phone becomes steady. Tilt the camera slightly down for higher viewpoints. The indicator shows viewpoint coverage based on phone tilt; it does not measure which surface areas were photographed.",
    "capture_guide_done": "Turquoise — captured",
    "capture_guide_missing": "Grey — not captured yet"
})
translate("app/src/main/res/values-de/strings_capture.xml", {
    "capture_import": "Aufnahme-ZIP importieren", "capture_import_short": "ZIP importieren",
    "capture_new_scan": "Neue Aufnahme starten", "capture_torch_on": "Taschenlampe EIN",
    "capture_torch_off": "Taschenlampe AUS", "capture_coverage_title": "Blickwinkel-Abdeckung",
    "capture_coverage_done": "Türkis — Blickwinkel aufgenommen",
    "capture_coverage_missing": "Grau — Blickwinkel fehlt noch",
    "capture_coverage_bottom": "Die Unterseite separat aufnehmen, indem Sie das Objekt umdrehen",
    "capture_guide_title": "Gehen Sie um das Objekt herum",
    "capture_guide_body": "Halten Sie das Objekt in der Mitte des Bildes. Die automatische Aufnahme erstellt ein Foto, wenn sich der Blickwinkel ändert und das Telefon kurz ruhig gehalten wird. Für höhere Blickwinkel die Kamera leicht nach unten neigen. Die Anzeige zeigt die Blickwinkel-Abdeckung anhand der Neigung des Telefons; sie misst nicht die tatsächlich fotografierten Oberflächenbereiche.",
    "capture_guide_done": "Türkis — aufgenommen",
    "capture_guide_missing": "Grau — noch nicht aufgenommen"
})
# Persistent in-app language selection. The locale wrapper is applied to both
# activities so the viewer, camera, reconstruction and all dialogs use one language.
locale_source = ROOT / "app/src/main/java/app/strata3d/LocalePreferences.kt"
locale_source.parent.mkdir(parents=True, exist_ok=True)
locale_source.write_text("""package app.strata3d

import android.content.Context
import android.content.res.Configuration
import java.util.Locale

object LocalePreferences {
    private const val PREFS = "reversescan_preferences"
    private const val KEY_LANGUAGE = "language"
    private val SUPPORTED_LANGUAGES = setOf("ru", "en", "de")

    // A saved user choice always wins. On first launch, follow the device language
    // when supported; otherwise use English. No preference is written for this
    // automatic choice, so an explicit selection remains distinguishable and durable.
    fun selected(context: Context): String {
        val preferences = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val saved = preferences.getString(KEY_LANGUAGE, null)
        if (saved != null && saved in SUPPORTED_LANGUAGES) return saved

        val deviceLanguage = context.resources.configuration.locales
            .get(0)?.language?.lowercase(Locale.ROOT)
        return if (deviceLanguage != null && deviceLanguage in SUPPORTED_LANGUAGES) deviceLanguage else "en"
    }

    fun save(context: Context, language: String) {
        require(language in setOf("ru", "en", "de"))
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY_LANGUAGE, language).apply()
    }

    fun wrap(context: Context): Context {
        val locale = Locale.forLanguageTag(selected(context))
        Locale.setDefault(locale)
        val configuration = Configuration(context.resources.configuration)
        configuration.setLocale(locale)
        configuration.setLayoutDirection(locale)
        return context.createConfigurationContext(configuration)
    }
}
""")

main_activity = ROOT / "app/src/main/java/app/strata3d/MainActivity.kt"
main_source = main_activity.read_text()
if "override fun attachBaseContext" not in main_source:
    main_source = main_source.replace(
        "class MainActivity : ComponentActivity() {",
        "class MainActivity : ComponentActivity() {\n\n    override fun attachBaseContext(newBase: android.content.Context) {\n        super.attachBaseContext(LocalePreferences.wrap(newBase))\n    }",
        1,
    )
if "onChangeLanguage =" not in main_source:
    main_source = main_source.replace(
        "                    onToggleTheme = {",
        "                    onChangeLanguage = { language ->\n                        LocalePreferences.save(this@MainActivity, language)\n                        recreate()\n                    },\n                    onToggleTheme = {",
        1,
    )
if "onChangeLanguage =" not in main_source:
    raise SystemExit("Could not add language callback to MainActivity")
main_activity.write_text(main_source)

capture_activity = ROOT / "app/src/main/java/app/strata3d/capture/ui/CaptureActivity.kt"
capture_source = capture_activity.read_text()
if "override fun attachBaseContext" not in capture_source:
    capture_source = capture_source.replace(
        "class CaptureActivity : ComponentActivity() {",
        "class CaptureActivity : ComponentActivity() {\n\n    override fun attachBaseContext(newBase: android.content.Context) {\n        super.attachBaseContext(app.strata3d.LocalePreferences.wrap(newBase))\n    }",
        1,
    )
capture_activity.write_text(capture_source)

# Reconstruction runs in a separate process; wrap its service context too so progress
# notifications follow the language selected in the app.
service_path = ROOT / "app/src/main/java/app/strata3d/capture/recon/ReconService.kt"
service_source = service_path.read_text()
if "override fun attachBaseContext" not in service_source:
    service_source = service_source.replace(
        "class ReconService : Service() {",
        "class ReconService : Service() {\n\n    override fun attachBaseContext(newBase: android.content.Context) {\n        super.attachBaseContext(app.strata3d.LocalePreferences.wrap(newBase))\n    }",
        1,
    )
service_path.write_text(service_source)

viewer_path = ROOT / "app/src/main/java/app/strata3d/ui/ViewerScreen.kt"
viewer_source = viewer_path.read_text()
if "onChangeLanguage: (String) -> Unit" not in viewer_source:
    viewer_source = viewer_source.replace(
        "    onToggleTheme: () -> Unit,",
        "    onToggleTheme: () -> Unit,\n    onChangeLanguage: (String) -> Unit = {},",
        1,
    )
    viewer_source = viewer_source.replace(
        "            onOpenCapture = { onOpenCapture(false) },",
        "            onOpenCapture = { onOpenCapture(false) },\n            onChangeLanguage = onChangeLanguage,",
        1,
    )
    viewer_source = viewer_source.replace(
        "    onOpenCapture: () -> Unit,\n) {",
        "    onOpenCapture: () -> Unit,\n    onChangeLanguage: (String) -> Unit,\n) {",
        1,
    )
if "var showLanguagePicker" not in viewer_source:
    viewer_source = viewer_source.replace(
        "    var infoPage by remember { mutableStateOf<InfoPage?>(null) }",
        "    var infoPage by remember { mutableStateOf<InfoPage?>(null) }\n    var showLanguagePicker by remember { mutableStateOf(false) }",
        1,
    )
    viewer_source = viewer_source.replace(
        "                    HorizontalDivider(Modifier.padding(vertical = 8.dp, horizontal = 16.dp))\n                    listOf(\n                        InfoPage.HELP",
        """                    HorizontalDivider(Modifier.padding(vertical = 8.dp, horizontal = 16.dp))
                    PanelItem(
                        icon = Icons.Outlined.Language,
                        label = stringResource(R.string.language_title),
                        onClick = { showLanguagePicker = true },
                    )
                    listOf(
                        InfoPage.HELP""",
        1,
    )
    # Insert the dialog immediately before SettingsPanel's closing brace.
    dialog = """    if (showLanguagePicker) {
        val context = LocalContext.current
        val selectedLanguage = app.strata3d.LocalePreferences.selected(context)
        AlertDialog(
            onDismissRequest = { showLanguagePicker = false },
            title = { Text(stringResource(R.string.language_title)) },
            text = {
                Column {
                    listOf(
                        "ru" to stringResource(R.string.language_russian),
                        "en" to stringResource(R.string.language_english),
                        "de" to stringResource(R.string.language_german),
                    ).forEach { (tag, label) ->
                        Row(
                            Modifier.fillMaxWidth().clickable {
                                showLanguagePicker = false
                                if (tag != selectedLanguage) onChangeLanguage(tag)
                            }.padding(vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            RadioButton(selected = selectedLanguage == tag, onClick = {
                                showLanguagePicker = false
                                if (tag != selectedLanguage) onChangeLanguage(tag)
                            })
                            Text(label, modifier = Modifier.padding(start = 8.dp))
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showLanguagePicker = false }) {
                    Text(stringResource(R.string.close))
                }
            },
        )
    }
"""
    end_marker = "\n}\n\n/**\n * Collapsible right-edge rail"
    end_pos = viewer_source.find(end_marker)
    if end_pos < 0:
        raise SystemExit("SettingsPanel closing anchor missing")
    viewer_source = viewer_source[:end_pos] + "\n" + dialog + viewer_source[end_pos:]
    # Ensure required Compose imports exist.
    imports = [
        "import androidx.compose.material3.AlertDialog",
        "import androidx.compose.material3.RadioButton",
        "import androidx.compose.material3.TextButton",
    ]
    for imp in imports:
        if imp not in viewer_source:
            viewer_source = viewer_source.replace("import androidx.compose.material3.", imp + "\nimport androidx.compose.material3.", 1)
    if "import androidx.compose.material.icons.outlined.Language" not in viewer_source:
        viewer_source = viewer_source.replace("import androidx.compose.material.icons.outlined.", "import androidx.compose.material.icons.outlined.Language\nimport androidx.compose.material.icons.outlined.", 1)
if "label = stringResource(R.string.language_title)" not in viewer_source:
        raise SystemExit("Could not add language selector to SettingsPanel")
viewer_path.write_text(viewer_source)

# Language selector labels exist in every locale. Russian is the current default UI;
# English strings are supplied by the upstream base pack, and German receives its
# own translated resource files below.
translate("app/src/main/res/values/strings.xml", {
    "language_title": "Язык приложения",
    "language_russian": "Русский",
    "language_english": "English",
    "language_german": "Deutsch",
})

# Final Russian product description and app-specific help. Keep the roadmap explicitly
# separate from features available in this build; do not advertise planned work as shipped.
translate("app/src/main/res/values/strings_info.xml", {
    "support_body": "Связь с разработчиком ReverseScan 3D: rb-service@live.de\nИсходный код и сообщения об ошибках: https://github.com/rb777pc-dotcom/ReverseScanAndroid",
    "about_body": "ReverseScan 3D — приложение для создания и просмотра трёхмерных моделей на Android.\n\nСКАНИРОВАНИЕ И ПОСТРОЕНИЕ\n• Съёмка неподвижного предмета камерой с автоматическим или ручным затвором.\n• Подсказки по выбору предмета, удержанию его в кадре и набору ракурсов.\n• Сохранение съёмок и фотографий на устройстве; экспорт и импорт архива съёмки ZIP.\n• Построение 3D-модели по серии фотографий непосредственно на телефоне.\n• Перенос цвета и текстуры с фотографий на полученную модель.\n\nПРОСМОТР И РАБОТА С МОДЕЛЬЮ\n• Импорт STL, OBJ, PLY, 3MF, glTF и GLB.\n• Вращение, перемещение и масштабирование модели; перспективный и ортографический режимы, виды сверху, спереди, сбоку и изометрия.\n• Измерение расстояния между двумя выбранными точками и просмотр сечения модели.\n• Просмотр сведений о модели и диагностика геометрии: открытые и неманифолдные рёбра, перевёрнутые и вырожденные треугольники и другие дефекты.\n• Сохранение снимка экрана; экспорт результата в GLB или OBJ.\n\nОбработка съёмок и построение выполняются на устройстве. Качество результата зависит от освещения, фактуры и отражающих свойств предмета, количества и перекрытия ракурсов, а также возможностей телефона. Приложение не является измерительным прибором и не гарантирует замкнутую или пригодную для печати сетку.",
    "about_thanks": "Автор и разработчик ReverseScan 3D: Bähr. © 2026. Контакт: rb-service@live.de. Сайт и исходный код: https://github.com/rb777pc-dotcom/ReverseScanAndroid.",
    "plans_title": "В планах развития",
    "plans_body": "Следующие направления рассматриваются для будущих версий и пока не являются функциями текущей сборки:\n• Калибровка масштаба по контрольному размеру и повышение точности измерений.\n• Инструменты редактирования сетки: заполнение отверстий, исправление дефектов и упрощение геометрии.\n• Дополнительные форматы обмена, включая STEP, после реализации полноценного CAD-конвертера.\n• Более точное управление областью сканирования и улучшение восстановления сложных, однотонных и блестящих поверхностей.\n• Дополнительные инструменты анализа и подготовки модели к 3D-печати.\n\nСроки и состав будущих выпусков могут меняться. Наличие пункта в этом списке не означает, что функция уже реализована.",
    "help_body": "1. ГЛАВНЫЙ ЭКРАН И ИМПОРТ МОДЕЛИ\nНажмите «Открыть 3D-модель» и выберите файл в системном окне Android. Также можно открыть поддерживаемый файл из файлового менеджера командой «Открыть с помощью» или передать его через «Поделиться». Поддерживаются STL, OBJ, PLY, 3MF, glTF и GLB. ZIP с моделью можно открыть, если внутри находится поддерживаемый файл. Список недавних моделей — это история открытий; если исходный файл перемещён или удалён, выберите его заново.\n\n2. УПРАВЛЕНИЕ 3D-ПРОСМОТРОМ\n• Один палец — вращение модели; два пальца — перемещение; сведение и разведение пальцев — масштаб.\n• Панель видов переключает перспективу и ортографическую проекцию, показывает модель сверху, спереди, сбоку или в изометрии.\n• «По размеру» вписывает модель в область просмотра. Режимы отображения позволяют смотреть сплошную поверхность, рёбра или каркас; доступность цвета зависит от данных исходной модели.\n• «Информация о модели» показывает характеристики файла и геометрии. Единицы STL, OBJ и PLY могут быть неизвестны: проверьте их перед использованием размеров и объёма.\n\n3. ИЗМЕРЕНИЕ, СЕЧЕНИЕ И ПРОВЕРКА\n• Откройте «Измерение» и последовательно коснитесь двух точек на поверхности. Приложение покажет расстояние между выбранными точками. Это измерение по геометрии модели, а не независимая физическая калибровка.\n• «Сечение» позволяет перемещать плоскость разреза и осматривать внутреннюю часть модели.\n• В «Проверке сетки» запустите анализ. Он может обнаружить открытые и неманифолдные рёбра, перевёрнутые или вырожденные треугольники и другие проблемы. Проверка сообщает о дефектах, но сама по себе их не исправляет.\n• «Снимок экрана» сохраняет изображение текущего вида; доступны настройки фона, сетки, подписи и разрешения.\n\n4. СЪЁМКА НОВОГО ПРЕДМЕТА\nОткройте «Съёмки» → «Новая съёмка» и разрешите доступ к камере. Поставьте неподвижный предмет в хорошо освещённое место. Лучше подходят матовые поверхности с заметной фактурой. Стекло, зеркала, блестящий металл, прозрачные и однотонные поверхности часто сканируются плохо.\nКоснитесь предмета в кадре, чтобы начать. В режиме «Автосъёмка» приложение делает снимок после смены ракурса и короткой остановки телефона. В ручном режиме каждый кадр снимается кнопкой. Фонарик доступен только если камера телефона поддерживает вспышку. Медленно обойдите предмет по кругу, удерживая его в кадре; затем снимите дополнительные ракурсы сверху и снизу. Соседние фотографии должны перекрывать друг друга. Для большинства объектов ориентир — от 40 фотографий, но количество зависит от формы и фактуры.\nИндикатор ракурсов оценивает направления наклона телефона и служит подсказкой оператору; он не измеряет фактическую полноту покрытия поверхности предмета.\n\n5. СОХРАНЕНИЕ И ПОСТРОЕНИЕ\nЗавершите съёмку кнопкой «Готово» и сохраните её. Она появится в «Моих съёмках». При необходимости переименуйте её или экспортируйте ZIP-архив для резервной копии. Чтобы перенести съёмку на этот телефон, используйте «Импортировать съёмку из ZIP» в библиотеке съёмок.\nОткройте сохранённую съёмку и выберите «Построить 3D-модель». Расчёт выполняется на телефоне и может занять значительное время; длительность зависит от числа фотографий, сложности сцены и производительности устройства. Не закрывайте приложение принудительно и обеспечьте достаточно свободной памяти. Если доступна проверка рамки предмета, убедитесь, что она охватывает весь объект, и продолжите построение.\n\n6. ПРОВЕРКА И ЭКСПОРТ РЕЗУЛЬТАТА\nПосле построения откройте модель в просмотрщике и осмотрите её со всех сторон. Участки без достаточного числа ракурсов могут иметь пропуски, отверстия или искажения. Экспорт GLB предназначен для передачи модели вместе с цветом и текстурами в одном файле. OBJ экспортируется комплектом с материалами и текстурами в ZIP. После экспорта выберите папку или приложение в системном окне Android.\n\n7. ЕСЛИ РЕЗУЛЬТАТ НЕУДОВЛЕТВОРИТЕЛЬНЫЙ\n• Мало сопоставленных фотографий — повторите съёмку с большим перекрытием кадров и более выраженной фактурой.\n• Пропущена сторона — доснимите её отдельными ракурсами; не перемещайте сам предмет во время одного прохода.\n• Поверхность с отверстиями — добавьте фотографии недостающих областей и повторите построение. Автоматическое гарантированное заполнение отверстий в текущей версии не предусмотрено.\n• Ошибка нехватки памяти или места — освободите память устройства и закройте другие приложения.\n• Модель не имеет верного физического масштаба — используйте известный контрольный размер, если соответствующее поле доступно, и перепроверьте результат отдельным измерительным инструментом."
})

# Add the roadmap as a distinct subsection on the About page, not as a fake working feature.
info_path = ROOT / "app/src/main/java/app/strata3d/ui/InfoPages.kt"
info_source = info_path.read_text()
old_about = '                            Body(stringResource(R.string.about_thanks))'
new_about = '''                            Body(stringResource(R.string.about_thanks))
                            Text(stringResource(R.string.plans_title), style = MaterialTheme.typography.titleMedium)
                            Body(stringResource(R.string.plans_body))'''
if old_about in info_source:
    info_source = info_source.replace(old_about, new_about, 1)
elif "R.string.plans_body" not in info_source:
    raise SystemExit("About page roadmap insertion anchor missing")
info_path.write_text(info_source)

print("Enforced full scanner version 0.9.1 (versionCode 10) in: " + ", ".join(patched_versions))


# Improve object picking and identity continuity. A tap must hit a detected object;
# never silently fall back to the largest object or a nearby unrelated detection.
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    '''                        val target = when {
                            selectedTap == null -> objects.maxByOrNull { it.boundingBox.width() * it.boundingBox.height() }
                            lockedId != null -> objects.firstOrNull { it.trackingId == lockedId } ?: nearestPrevious
                            previousBox != null -> nearestPrevious
                            else -> objects.mapNotNull { obj ->
                                val b = obj.boundingBox
                                val left = b.left.toFloat() / rotatedWidth
                                val top = b.top.toFloat() / rotatedHeight
                                val right = b.right.toFloat() / rotatedWidth
                                val bottom = b.bottom.toFloat() / rotatedHeight
                                val u = selectedTap.u.toFloat()
                                val v = selectedTap.v.toFloat()
                                val dx = maxOf(left - u, 0f, u - right)
                                val dy = maxOf(top - v, 0f, v - bottom)
                                obj to (dx * dx + dy * dy)
                            }.filter { it.second <= 0.16f * 0.16f }
                                .minByOrNull { it.second }?.first
                        }''',
    '''                        val target = when {
                            // No tap means no selected target. Never guess by choosing the largest detection.
                            selectedTap == null -> null
                            lockedId != null && objects.any { it.trackingId == lockedId } ->
                                objects.first { it.trackingId == lockedId }
                            else -> {
                                val tapU = selectedTap.u.toFloat()
                                val tapV = selectedTap.v.toFloat()
                                val candidates = objects.mapNotNull { obj ->
                                    val b = obj.boundingBox
                                    val left = (b.left.toFloat() / rotatedWidth).coerceIn(0f, 1f)
                                    val top = (b.top.toFloat() / rotatedHeight).coerceIn(0f, 1f)
                                    val right = (b.right.toFloat() / rotatedWidth).coerceIn(0f, 1f)
                                    val bottom = (b.bottom.toFloat() / rotatedHeight).coerceIn(0f, 1f)
                                    val area = ((right - left) * (bottom - top)).coerceAtLeast(0.0001f)
                                    if (previousBox == null) {
                                        // Initial selection: the selected tap must land inside the detected object,
                                        // allowing only a very small tolerance for detector-box rounding.
                                        val margin = 0.015f
                                        if (tapU >= left - margin && tapU <= right + margin &&
                                            tapV >= top - margin && tapV <= bottom + margin) {
                                            obj to area // Prefer the smallest box when detections overlap.
                                        } else null
                                    } else {
                                        // Re-identification after an occlusion: require strong spatial continuity.
                                        // A neighbouring object outside this gate is never adopted as the target.
                                        val old = previousBox
                                        val oldArea = (old.width() * old.height()).coerceAtLeast(0.0001f)
                                        val ratio = area / oldArea
                                        val ix = (minOf(right, old.right) - maxOf(left, old.left)).coerceAtLeast(0f)
                                        val iy = (minOf(bottom, old.bottom) - maxOf(top, old.top)).coerceAtLeast(0f)
                                        val intersection = ix * iy
                                        val union = area + oldArea - intersection
                                        val iou = if (union > 0f) intersection / union else 0f
                                        val dx = (left + right) * 0.5f - old.centerX()
                                        val dy = (top + bottom) * 0.5f - old.centerY()
                                        val distance2 = dx * dx + dy * dy
                                        val sameTarget = ratio in 0.35f..2.8f &&
                                            (iou >= 0.08f || (distance2 <= 0.055f * 0.055f && iou >= 0.02f))
                                        if (sameTarget) obj to (distance2 - iou * 0.04f) else null
                                    }
                                }
                                candidates.minByOrNull { it.second }?.first
                            }
                        }'''
)
# Localize the live target status and target-loss notices in all three app languages.
replace_once(
    "app/src/main/java/app/strata3d/capture/ui/CaptureScreen.kt",
    'Notice.TARGET_LOST -> "Предмет потерян — фото не сделано. Верните его в кадр."',
    "Notice.TARGET_LOST -> stringResource(R.string.capture_target_lost)"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/ui/CaptureScreen.kt",
    'Notice.TARGET_EDGE -> "Предмет у края кадра — верните его ближе к центру."',
    "Notice.TARGET_EDGE -> stringResource(R.string.capture_target_edge)"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/ui/CaptureScreen.kt",
    'state.objectNearEdge -> "ОБЪЕКТ У КРАЯ · ВЕРНИТЕ В ЦЕНТР"',
    "state.objectNearEdge -> stringResource(R.string.capture_target_edge_label)"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/ui/CaptureScreen.kt",
    'state.objectDetected == true -> "ОБЪЕКТ В КАДРЕ · ОТСЛЕЖИВАЕТСЯ"',
    "state.objectDetected == true -> stringResource(R.string.capture_target_detected_label)"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/ui/CaptureScreen.kt",
    'state.objectDetected == false -> "ОБЪЕКТ ПОТЕРЯН · НАВЕДИТЕ КАМЕРУ"',
    "state.objectDetected == false -> stringResource(R.string.capture_target_lost_label)"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/ui/CaptureScreen.kt",
    'else -> "НАВЕДИТЕ КАМЕРУ НА ПРЕДМЕТ"',
    "else -> stringResource(R.string.capture_target_wait_label)"
)

translate("app/src/main/res/values/strings_capture.xml", {
    "capture_target_lost": "Предмет потерян — фото не сделано. Верните его в кадр.",
    "capture_target_edge": "Предмет у края кадра — переместите его ближе к центру.",
    "capture_target_edge_label": "ПРЕДМЕТ У КРАЯ — ВЕРНИТЕ В ЦЕНТР",
    "capture_target_detected_label": "ПРЕДМЕТ В КАДРЕ — ОТСЛЕЖИВАЕТСЯ",
    "capture_target_lost_label": "ПРЕДМЕТ ПОТЕРЯН — НАВЕДИТЕ КАМЕРУ",
    "capture_target_wait_label": "НАЖМИТЕ НА ПРЕДМЕТ В КАДРЕ"
})
translate("app/src/main/res/values-en/strings_capture.xml", {
    "capture_target_lost": "Target lost — no photo taken. Bring the object back into view.",
    "capture_target_edge": "The object is at the edge of the frame. Move it closer to the centre.",
    "capture_target_edge_label": "OBJECT AT EDGE — MOVE IT TO THE CENTRE",
    "capture_target_detected_label": "OBJECT IN VIEW — TRACKING",
    "capture_target_lost_label": "OBJECT LOST — POINT THE CAMERA AT IT",
    "capture_target_wait_label": "TAP THE OBJECT IN THE FRAME"
})
translate("app/src/main/res/values-de/strings_capture.xml", {
    "capture_target_lost": "Objekt verloren — kein Foto aufgenommen. Bringen Sie es wieder ins Bild.",
    "capture_target_edge": "Das Objekt befindet sich am Bildrand. Bewegen Sie es näher zur Mitte.",
    "capture_target_edge_label": "OBJEKT AM RAND — ZUR MITTE BEWEGEN",
    "capture_target_detected_label": "OBJEKT IM BILD — WIRD VERFOLGT",
    "capture_target_lost_label": "OBJEKT VERLOREN — KAMERA DARAUF RICHTEN",
    "capture_target_wait_label": "TIPPE AUF DAS OBJEKT IM BILD"
})

# Complete the remaining German viewer, capture, information and reconstruction strings.
translate("app/src/main/res/values-de/strings.xml", {
    "view_switch_to_ortho": "Perspektivische Ansicht. Zur orthografischen Ansicht wechseln",
    "view_switch_to_persp": "Orthografische Ansicht. Zur perspektivischen Ansicht wechseln",
    "view_top_desc": "Ansicht von oben", "view_front_desc": "Vorderansicht",
    "view_side_desc": "Seitenansicht", "view_iso_desc": "Isometrische Ansicht",
    "view_fit_desc": "Modell an den Bildschirm anpassen",
    "recent_needs_reopen": "Nicht verfügbar. Öffnen Sie die Datei erneut und wählen Sie sie aus.",
    "recent_plus_files": "+%1$d", "recent_more": "Weitere Optionen für %1$s",
    "recent_clear_title": "Liste der zuletzt geöffneten Dateien leeren?",
    "recent_clear_body": "Nur die Liste wird geleert. Ihre Dateien werden nicht gelöscht.",
    "recent_limit_note": "Ihre letzten %1$d Modelle werden hier gespeichert.",
    "recent_unavailable": "Diese Datei ist nicht mehr verfügbar. Wählen Sie sie über „Erneut öffnen“ noch einmal aus.",
    "snapshot_transparent_hint": "Nur das Modell auf transparentem Hintergrund (PNG mit Alphakanal).",
    "snapshot_caption": "Beschriftung mit Name und Größe",
    "snapshot_size": "Auflösung", "snapshot_size_screen": "Bildschirm",
    "snapshot_size_double": "2×", "snapshot_size_uhd": "4K",
    "snapshot_size_unsupported": "Auflösungen, die die GPU dieses Geräts nicht darstellen kann, sind nicht verfügbar. Bilder werden niemals verkleinert.",
    "snapshot_not_ready": "Die 3D-Ansicht wird noch gestartet.",
    "snapshot_share_title": "Aufnahme teilen", "snapshot_failed": "Die Aufnahme konnte nicht erstellt werden.",
    "snapshot_out_of_memory": "Nicht genügend Speicher für diese Auflösung. Versuchen Sie eine kleinere.",
    "snapshot_no_share_target": "Keine App kann Bilder empfangen.",
    "loading_named": "%1$s wird geladen …",
    "mode_solid_desc": "Gefüllte Ansicht", "mode_edges_desc": "Gefüllte Ansicht mit Kanten",
    "mode_wire_desc": "Drahtgitteransicht",
    "info_triangles": "Dreiecke", "info_dimensions": "Abmessungen",
    "info_volume": "Volumen", "info_area": "Oberfläche", "info_file_size": "Dateigröße",
    "info_load_time": "Ladezeit",
    "info_units_note": "glTF- und 3MF-Dateien enthalten Einheitenangaben. STL-, OBJ- und PLY-Dateien nicht; bis Sie im Messwerkzeug eine Einheit wählen, werden Millimeter angenommen. Das Volumen ist nur bei geschlossenen Netzen genau.",
    "info_units": "Einheiten",
    "gestures_hint": "Ziehen zum Drehen · zwei Finger zum Verschieben · zusammenziehen zum Zoomen · doppeltippen zum Zurücksetzen",
    "info_location": "Speicherort", "source_uri": "Quell-URI",
    "location_copied": "Speicherort in die Zwischenablage kopiert",
    "diag_not_analyzed": "Nicht analysiert",
    "diag_not_analyzed_hint": "Prüft offene und nicht-mannigfaltige Kanten, umgedrehte oder flächenlose Dreiecke sowie nach innen gekehrte Bereiche. Das Modell wird nicht verändert.",
    "diag_out_of_memory": "Nicht genügend Speicher, um dieses Modell auf diesem Gerät zu analysieren.",
    "diag_summary": "%1$s · %2$s · geprüft in %3$d ms",
    "diag_possible": "möglich", "diag_show_in_3d": "Probleme in 3D anzeigen",
    "diag_truncated": "Sehr viele Probleme: Es werden nur die ersten 250.000 Einträge jeder Art hervorgehoben.",
    "diag_issues_badge": "Modellinformationen: Netzfehler gefunden",
    "diag_legend_desc": "Farben der Hervorhebungen",
    "diag_open_edges": "Offene Kanten", "diag_non_manifold": "Nicht-mannigfaltige Kanten",
    "diag_flipped": "Umgedrehte Dreiecke", "diag_degenerate": "Dreiecke ohne Fläche",
    "diag_non_orientable": "Nicht orientierbare Bereiche", "diag_inverted": "Nach innen gekehrte Bereiche",
    "diag_cavity": "Innere Hohlräume", "diag_not_highlighted": "In 3D nicht hervorgehoben (Fläche null)",
    "section_axis_desc": "Schnitt entlang der %1$s-Achse",
    "section_position_desc": "Position des Schnitts",
    "section_fill_checking": "Modell wird geprüft, damit der Schnitt gefüllt werden kann …",
    "section_fill_open": "Nicht gefüllt: Das Modell ist nicht geschlossen (siehe Modellinformationen).",
    "section_fill_no_stencil": "Nicht gefüllt: Dieses Gerät unterstützt diese Funktion nicht.",
    "section_fill_failed": "Nicht gefüllt: Die Netzprüfung ist fehlgeschlagen.",
    "section_fill_unchecked": "Nicht gefüllt: Das Modell wurde noch nicht geprüft.",
    "section_fill_wireframe": "In der Drahtgitteransicht wird der Schnitt nicht gefüllt.",
    "measure_copied": "Messwert in die Zwischenablage kopiert",
    "measure_copy": "Messwert kopieren", "measure_snap": "Einrasten",
    "measure_snap_desc": "An sichtbaren Eckpunkten einrasten",
    "measure_units_chip": "Einheiten: %1$s",
    "measure_units_desc": "Einheiten der Modellkoordinaten: %1$s, %2$s",
    "unit_source_file": "aus Datei", "unit_source_user": "von Ihnen festgelegt",
    "unit_source_assumed": "angenommen", "units_as_in_file": "Wie in der Datei (%1$s)",
    "units_not_specified": "Nicht angegeben (mm annehmen)",
    "unit_micron": "Mikrometer (µm)", "unit_millimeter": "Millimeter (mm)",
    "unit_centimeter": "Zentimeter (cm)", "unit_meter": "Meter (m)",
    "unit_inch": "Zoll (in)", "unit_foot": "Fuß (ft)",
    "measure_units_assumed_note": "Einheiten angenommen (mm)"
})
translate("app/src/main/res/values-de/strings_capture.xml", {
    "captures_empty_body": "Gehen Sie mit dem Telefon um einen Gegenstand herum. ReverseScan 3D nimmt scharfe Fotos von allen Seiten für die 3D-Rekonstruktion auf.",
    "capture_stats": "%1$d Fotos · %2$d%% abgedeckt · %3$s",
    "capture_interrupted": "Unterbrochen · %1$d Fotos behalten",
    "capture_delete_body": "Die %1$d Fotos werden von diesem Telefon gelöscht. Dieser Vorgang kann nicht rückgängig gemacht werden.",
    "capture_rename_title": "Aufnahme umbenennen",
    "capture_export_failed": "Export fehlgeschlagen. Prüfen Sie den freien Speicher am Speicherort.",
    "capture_more": "Weitere Optionen", "capture_device_report": "Gerätebericht",
    "capture_close": "Aufnahme schließen",
    "capture_coverage_desc": "%1$d%% des Objekts abgedeckt",
    "capture_leave_body": "%1$d Fotos wurden bisher aufgenommen.",
    "capture_error_title": "Aufnahme angehalten",
    "guide_hot": "Das Telefon ist heiß. Aufnahme pausiert, bis es abgekühlt ist.",
    "guide_low_storage": "Speicher fast voll. Aufnahme pausiert.",
    "guide_paused": "Pausiert",
    "capture_summary_missing_low": "Fehlen: einige Blickwinkel von unten.",
    "capture_summary_missing_mid": "Fehlen: einige Blickwinkel von oben.",
    "capture_summary_complete": "Alle Seiten wurden erfasst.",
    "capture_summary_next": "Sie können jetzt mit der 3D-Modellerstellung beginnen.",
    "capture_photo_failed": "Das letzte Foto konnte nicht gespeichert werden. Die automatische Aufnahme wurde pausiert.",
    "capture_no_sensors": "Dieses Telefon hat keine Bewegungssensoren für die automatische Aufnahme. Verwenden Sie den manuellen Auslöser.",
    "capture_count": "%1$d Fotos · empfohlen: mindestens 40",
    "capture_shutter_locked": "Auslöser gesperrt, bis das Objekt markiert ist",
    "capture_shutter_smart_desc": "Nimmt ein Foto auf, wenn Sie den Blickwinkel ausreichend geändert haben und das Telefon ruhig halten.",
    "capture_shutter_manual_desc": "Sie lösen jedes Foto manuell aus."
})
translate("app/src/main/res/values-de/strings_info.xml", {
    "license_full": "Vollständiger Lizenztext (GNU AGPL v3)",
    "license_notices": "Hinweise zu Drittanbieter-Komponenten",
    "credit_viewer": "der ursprüngliche 3D-Viewer, aus dem diese App hervorgegangen ist",
    "credit_drako": "Dekodierung von Draco-komprimierten glTF-Modellen",
    "credit_meshopt": "Dekodierung von meshoptimizer-komprimierten glTF-Modellen",
    "credit_mve": "Import von Fotos, Bestimmung der Kamerapositionen und Bereinigung des erstellten Modells",
    "credit_texturing": "Einfärben des erstellten Modells anhand der Fotos",
    "credit_mapmap": "Auswahl des Fotos, dessen Farben auf den jeweiligen Modellbereich übertragen werden",
    "credit_rayint": "Prüfung, welche Modellbereiche auf den einzelnen Fotos sichtbar sind",
    "credit_openmvs": "Berechnung der Tiefe aus Fotos und Aufbau der Modelloberfläche",
    "credit_opencv": "Bildverarbeitung innerhalb der Modellrekonstruktion",
    "credit_boost": "Allgemeine C++-Bausteine für die Modellrekonstruktion",
    "credit_cgal": "Geometrieverarbeitung zum Aufbau der Modelloberfläche",
    "credit_vcg": "Bereinigung und Vereinfachung der erstellten Oberfläche",
    "credit_nanoflann": "Schnelle Suche nach nächstgelegenen Punkten während des Aufbaus",
    "credit_eigen": "Mathematik (Matrizen und Vektoren) in der Modellrekonstruktion",
    "credit_tbb": "Ausführung des Texturschritts auf mehreren Prozessorkernen",
    "credit_libjpeg": "Einlesen der Fotos",
    "credit_libpng": "Einlesen und Schreiben von Bildern innerhalb der Modellrekonstruktion",
    "credit_llvm_omp": "Ausführung der Modellrekonstruktion auf mehreren Prozessorkernen",
    "credit_androidx": "App-Bildschirme, Kamera und Fotoverwaltung"
})
translate("app/src/main/res/values-de/strings_recon.xml", {
    "recon_channel": "Modellrekonstruktion", "recon_notification_title": "3D-Modell wird erstellt",
    "recon_notification_starting": "Wird gestartet …",
    "recon_stage_import": "Fotos werden vorbereitet",
    "recon_stage_cameras": "Fotos werden zugeordnet",
    "recon_stage_box": "Objekt wird erkannt",
    "recon_stage_depth": "Tiefe wird berechnet",
    "recon_stage_points": "Punktwolke wird erstellt",
    "recon_stage_surface": "Oberfläche wird erstellt",
    "recon_stage_ground": "Unterlage unter dem Objekt wird entfernt",
    "recon_stage_clean": "Modell wird bereinigt",
    "recon_stage_texture": "Farben und Textur werden übertragen",
    "recon_stage_steps": "%1$s (%2$d von %3$d)",
    "recon_build_title": "3D-Modell erstellen",
    "recon_build_body": "Die Berechnung läuft auf diesem Telefon und dauert etwa 5–25 Minuten. Sie können die App verlassen; der Vorgang läuft weiter.",
    "recon_build": "Modell erstellen", "recon_building": "3D-Modell wird erstellt",
    "recon_placed_detail": "%1$s · %2$d von %3$d Fotos verwendet",
    "recon_ready_stats": "Dauer: %1$s · verwendete Fotos: %2$d von %3$d · Punkte: %4$s",
    "recon_ready_gaps": "%1$d Fotos konnten nicht zugeordnet werden (möglicherweise wegen glatter oder glänzender Flächen). Dort kann das Modell Lücken aufweisen.",
    "recon_minutes_seconds": "%1$d Min. %2$d Sek.", "recon_seconds": "%1$d Sek.",
    "recon_err_unsupported": "Der Prozessor dieses Telefons wird für die Modellrekonstruktion nicht unterstützt.",
    "recon_err_tap": "Das angetippte Objekt stimmt nicht mit dem Objekt überein, das auf den Fotos im Mittelpunkt steht. Starten Sie eine neue Aufnahme und tippen Sie auf das Objekt, das Sie umrunden.",
    "recon_err_interrupted": "Die Modellrekonstruktion wurde unerwartet beendet. Versuchen Sie es erneut.",
    "recon_review_switch": "Begrenzungsrahmen vor dem Erstellen prüfen",
    "recon_review_switch_body": "Aus: Die App bestimmt den Rahmen automatisch und erstellt das Modell ohne Unterbrechung. Ein: Nach dem Zuordnen der Fotos wird angehalten, damit Sie den Rahmen prüfen können.",
    "recon_review_notification": "Fotos zugeordnet. Tippen Sie hier, um den Rahmen zu prüfen und fortzufahren.",
    "recon_review_photo": "Foto %1$d von %2$d",
    "recon_review_unavailable": "Der Begrenzungsrahmen kann auf diesen Fotos nicht angezeigt werden.",
    "size_row_height": "Höhe %1$s", "size_row_width": "Breite %1$s",
    "size_body_height": "Von der Standfläche bis zum höchsten Punkt des Objekts. Ein ungefährer Wert genügt.",
    "size_body_width": "An der breitesten Stelle des Objekts, von oben gesehen. Ein ungefährer Wert genügt.",
    "size_axis_height": "Höhe", "size_axis_width": "Breite",
    "size_follow_height": "Breite und Tiefe werden anhand der Fotos berechnet.",
    "size_follow_width": "Höhe und Tiefe werden anhand der Fotos berechnet.",
    "size_value_label": "Größe", "size_error_range": "Geben Sie eine Größe zwischen %1$s und %2$s ein.",
    "size_failed": "Die Größe konnte nicht übernommen werden. Versuchen Sie es erneut.",
    "recon_preview_description": "Vorschau des erstellten Modells",
    "export_glb": "GLB", "export_obj": "OBJ (.zip)",
    "export_about_size": "ca. %1$s",
    "export_sized": "In realer Größe gespeichert.",
    "export_unsized": "Für dieses Modell ist noch keine reale Größe festgelegt. Fügen Sie eine Größe hinzu, um im realen Maßstab zu exportieren.",
    "export_no_app": "Auf diesem Telefon ist keine App zum Öffnen dieses Dateityps installiert."
})


# Make preview selection resilient to camera startup and permit deliberate re-selection.
# A tap is valid as soon as the PreviewView has dimensions; ImageCapture resolution is
# used when ready, otherwise the camera's documented portrait 4:3 fallback is used.
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "        val ic = imageCapture ?: return",
    "        val ic = imageCapture"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "        if (synchronized(lock) { (photoCount > 0 && resumeCaptureId == null) || finishing }) return",
    "        if (synchronized(lock) { finishing }) return"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/CameraXCapture.kt",
    "        val info = ic.resolutionInfo",
    "        val info = ic?.resolutionInfo"
)
