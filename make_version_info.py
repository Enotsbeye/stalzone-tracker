"""Сведения о программе для .exe (Свойства → Подробно, Диспетчер задач): название, версия.
Пишет version_info.txt для PyInstaller (--version-file). Запуск: python make_version_info.py"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "stalzone_app.py"), encoding="utf-8") as f:
    version = re.search(r'^APP_VERSION = "([^"]+)"', f.read(), re.M).group(1)
nums = [int(n) for n in re.findall(r"\d+", version)][:4]
nums += [0] * (4 - len(nums))
ver = tuple(nums)
strings = {
    "CompanyName": "STALZONE Tracker",
    "FileDescription": "STALZONE Трекер",
    "FileVersion": version,
    "InternalName": "STALZONE-Tracker",
    "LegalCopyright": "STALZONE Tracker",
    "OriginalFilename": "STALZONE-Tracker.exe",
    "ProductName": "STALZONE Трекер",
    "ProductVersion": version,
}
table = ",\n          ".join(f"StringStruct({k!r}, {v!r})" for k, v in strings.items())
text = f"""# Создано make_version_info.py — не править руками
VSVersionInfo(
  ffi=FixedFileInfo(filevers={ver}, prodvers={ver}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([
      StringTable('041904B0', [
          {table}])]),
    VarFileInfo([VarStruct('Translation', [1049, 1200])])
  ]
)
"""
with open(os.path.join(HERE, "version_info.txt"), "w", encoding="utf-8") as f:
    f.write(text)
print("version_info.txt:", version)
