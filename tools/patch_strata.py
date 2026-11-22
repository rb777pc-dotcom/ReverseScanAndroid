#!/usr/bin/env python3
"""Apply the ReverseScan usability and reconstruction fixes to the pinned Strata checkout."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent / "strata"

def replace_once(path, old, new):
    p = ROOT / path
    s = p.read_text()
    if old not in s:
        raise SystemExit(f"Expected source block not found in {path}; refusing partial patch")
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

# Make the two-ring coverage indicator readable and explain what the app is doing.
replace_once(
    "app/src/main/java/app/strata3d/capture/ui/CaptureScreen.kt",
    """            Row(Modifier.fillMaxWidth().padding(end = 12.dp)) {
                Spacer(Modifier.weight(1f))
                CoverageDome(listOf(state.lowerRing, state.upperRing), null, Modifier.size(52.dp))
            }""",
    """            Row(
                Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(stringResource(R.string.capture_guide_title), color = OnScrim, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                    Text(stringResource(R.string.capture_guide_body), color = OnScrim, fontSize = 12.sp)
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text(stringResource(R.string.capture_guide_done), color = Teal, fontSize = 11.sp)
                        Text(stringResource(R.string.capture_guide_missing), color = Color(0xFFB0B4BA), fontSize = 11.sp)
                    }
                }
                CoverageDome(listOf(state.lowerRing, state.upperRing), null, Modifier.size(116.dp))
            }"""
)

# Russian capture/library strings. Keep Android format arguments unchanged.
capture_ru = {
"capture_entry":"Съёмки", "capture_object":"Отсканировать предмет",
"captures_title":"Мои съёмки", "capture_new":"Новая съёмка",
"captures_empty_title":"Сделайте первую съёмку",
"captures_empty_body":"Медленно обойдите неподвижный предмет с телефоном. Приложение автоматически делает резкие фотографии со всех сторон для построения 3D-модели.",
"capture_untitled":"Съёмка %1$s", "capture_stats":"%1$d фото · покрытие %2$d%% · %3$s",
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
"capture_coverage_desc":"Покрытие объекта: %1$d%%",
"capture_leave_title":"Сохранить эту съёмку?", "capture_leave_body":"Сделано фотографий: %1$d.",
"capture_keep":"Сохранить", "capture_discard":"Удалить",
"capture_error_title":"Съёмка остановлена",
"guide_hot":"Телефон перегрелся. Съёмка приостановлена до охлаждения.",
"guide_low_storage":"Почти закончилось место. Съёмка приостановлена.",
"guide_paused":"Съёмка на паузе",
"capture_saved":"Съёмка сохранена", "capture_summary_photos":"Фотографии",
"capture_summary_covered":"Покрытие", "capture_summary_size":"Размер",
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
"capture_guide_body":"Держите предмет в центре кадра. Автосъёмка делает фото сама, когда ракурс изменился и телефон неподвижен. Для верхних ракурсов слегка наклоните камеру вниз.",
"capture_guide_done":"Бирюзовый — снято",
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

translate("app/src/main/res/values/strings_capture.xml", capture_ru)
translate("app/src/main/res/values/strings_recon.xml", recon_ru)

# Rebrand the launcher and remove the upstream donation/support destination from navigation.
translate("app/src/main/res/values/strings.xml", {"app_name": "ReverseScan 3D"})
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

# A 6-degree step gives smoother coverage progression; a slightly longer inter-shot
# interval prevents the automatic shutter from firing in bursts while the phone is moving.
replace_once(
    "app/src/main/java/app/strata3d/capture/shutter/SmartShutter.kt",
    "val stepDeg: Double = 6.0,",
    "val stepDeg: Double = 9.0,"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/shutter/SmartShutter.kt",
    "val steadyMs: Long = 120,",
    "val steadyMs: Long = 150,"
)
replace_once(
    "app/src/main/java/app/strata3d/capture/shutter/SmartShutter.kt",
    "val minIntervalMs: Long = 550,",
    "val minIntervalMs: Long = 400,"
)

# Do not accept a reconstruction whose camera alignment is below the quality target:
# the former 30% emergency threshold allowed sparse/degenerate geometry to continue.
replace_once(
    "app/src/main/java/app/strata3d/capture/recon/ReconRunner.kt",
    "if (placed < ReconPlan.minPlacement(views)) {",
    "if (placed < ReconPlan.goodPlacement(views)) {"
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
    "license_notices": "Уведомления о сторонних компонентах"
})

print("Applied Russian capture/reconstruction UI, larger coverage dial, and deterministic SfM first pass.")
