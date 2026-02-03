[app]
title = Palm Tree Classifier
package.name = plam_app
package.domain = org.ibrahimfahad
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf
source.exclude_dirs = venv,myvenv,__pycache__,.git,.idea,.vscode,tflite_models

version = 1.0

requirements = python3,kivy,pillow,arabic-reshaper,python-bidi,pyjnius,kivy_garden.xcamera,requests

orientation = portrait
fullscreen = 0

icon.filename = assets/PalmTreeClassifier_logo.png
presplash.filename = assets/PalmTreeClassifier_logo.png

# Android permissions
android.permissions = CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,INTERNET

# Keep logs easy
android.logcat_filters = *:S python:D kivy:D

# TFLite Java dependency (No longer needed for server-based app)
# android.gradle_dependencies = org.tensorflow:tensorflow-lite:2.14.0

# If you need select ops (usually NOT needed for convnext):
# android.gradle_dependencies = org.tensorflow:tensorflow-lite:2.14.0,org.tensorflow:tensorflow-lite-select-tf-ops:2.14.0

# API / NDK
android.api = 34
android.minapi = 21
android.ndk = 25b

# Architectures (use arm64 only if you want smaller build)
android.archs = arm64-v8a,armeabi-v7a

# Fix AndroidX
android.enable_androidx = True

# Extra packaging settings (helps with large assets sometimes)
android.add_src = .

[buildozer]
log_level = 2
warn_on_root = 1


