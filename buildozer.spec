[app]

title = Bestemmia Counter
package.name = bestemmiacounter
package.domain = org.example

source.dir = .
source.include_exts = py,txt,png,jpg,kv,atlas

version = 1.0

requirements = python3,kivy,pyjnius

orientation = portrait

fullscreen = 0

android.permissions = RECORD_AUDIO

android.api = 35
android.minapi = 24

android.archs = arm64-v8a, armeabi-v7a

[buildozer]

log_level = 2
warn_on_root = 1