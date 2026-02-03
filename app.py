# pylint: disable=E0611
import os
import glob
import logging
import sys


from PIL import Image as PILImage
import arabic_reshaper
from bidi.algorithm import get_display

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.utils import platform
from kivy.metrics import dp
from kivy.properties import BooleanProperty, StringProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView

import threading
import requests

# ---------------- Logging ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("PalmKivy")

# ---------------- Translations ----------------
TRANSLATIONS = {
    "EN": {
        "title": "Palm Tree Classifier",
        "beta": "BETA VERSION",
        "desc": (
            "Welcome to the Smart Palm Classifier!\n"
            "This AI tool identifies palm types (Khalas, Razeez, Shishi).\n\n"
            "How to use:\n"
            "1) Take Photo or Upload File\n"
            "2) Provide an image\n"
            "3) Get instant results!"
        ),
        "abs_title": "About the Project",
        "abs_text": (
            "Ensemble of ConvNeXt Small models (TFLite). Uses Test Time Augmentation (flip) "
            "to classify palm types with robustness."
        ),
        "cam": "Take Photo",
        "up": "Upload File",
        "res": "Result",
        "conf": "Confidence",
        "unk": "Unknown / Other",
        "labels": ["Khalas", "Razeez", "Shishi"],
        "act_cam": "Activate Camera",
        "close_cam": "Close Camera",
        "reset": "Reset / New Prediction",
        "analyzing": "Analyzing...",
        "no_models": "No TFLite models found (*.tflite).",
        "pick_image": "Pick an image (jpg/png)",
        "about": "About",
    },
    "AR": {
        "title": "مُصنف النخيل",
        "beta": "نسخة تجريبية",
        "desc": (
            "مرحبًا بكم في المصنف الذكي للنخيل!\n"
            "تقوم هذه الأداة بتصنيف أنواع النخيل (خلاص، رزيز، شيشي).\n\n"
            "طريقة الاستخدام:\n"
            "1) التقط صورة أو ارفع صورة\n"
            "2) اختر صورة للنخلة\n"
            "3) ستحصل على النتيجة فوراً!"
        ),
        "abs_title": "عن المشروع",
        "abs_text": (
            "مجموعة نماذج ConvNeXt Small (TFLite). يستخدم TTA (قلب الصورة) "
            "لزيادة ثبات ودقة التصنيف."
        ),
        "cam": "التقط صورة",
        "up": "ارفع صورة",
        "res": "النتيجة",
        "conf": "الدقة",
        "unk": "غير معروف / نوع آخر",
        "labels": ["خلاص", "رزيز", "شيشي"],
        "act_cam": "تشغيل الكاميرا",
        "close_cam": "إغلاق الكاميرا",
        "reset": "إعادة تعيين / فحص جديد",
        "analyzing": "جاري التحليل...",
        "no_models": "لم يتم العثور على نماذج TFLite (*.tflite).",
        "pick_image": "اختر صورة (jpg/png)",
        "about": "عن المشروع",
    },
}

# ---------------- Font ----------------
ARABIC_FONT_PATH = "C:\\Windows\\Fonts\\arial.ttf"
if not os.path.exists(ARABIC_FONT_PATH):
    ARABIC_FONT_PATH = "C:\\Windows\\Fonts\\segoeui.ttf"

# ---------------- API Logic ----------------
def predict_via_api(image_path: str, server_url: str):
    """
    Sends the image to the server and returns (class_idx, confidence, label).
    """
    url = f"{server_url}/predict"
    try:
        with open(image_path, "rb") as f:
            files = {"file": f}
            # Timeout set to 15s to avoid hanging forever
            resp = requests.post(url, files=files, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            # data: {"prediction": "Khalas", "confidence": 0.98, "class_id": 0, ...}
            return data.get("class_id"), data.get("confidence"), data.get("prediction")
        else:
            logger.error(f"Server Error: {resp.status_code} - {resp.text}")
            return None, 0.0, f"Error: {resp.status_code}"
    except Exception as e:
        logger.error(f"Connection Error: {e}")
        return None, 0.0, f"Conn Error: {str(e)}"

# ---------------- Kivy UI ----------------
class Root(BoxLayout):
    dark_mode = BooleanProperty(False)
    arabic_mode = BooleanProperty(True)
    
    # Cloud server URL (Render deployment)
    server_url = StringProperty("https://palm-tree-classifier-server.onrender.com")

    result_text = StringProperty("")
    confidence = NumericProperty(0.0)

    image_path = StringProperty("")
    status_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(10), padding=dp(12), **kwargs)


        # self.models_list = []  <-- No longer needed
        self.themed_labels = []

        self._apply_theme()
        Window.bind(on_resize=lambda *args: self._apply_theme())

        # Top bar
        top = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))

        self.btn_theme = Button(text="🌙", size_hint_x=None, width=dp(70), font_name=ARABIC_FONT_PATH)
        self.btn_theme.bind(on_release=self.toggle_theme)

        self.btn_lang = Button(text="EN", size_hint_x=None, width=dp(70), font_name=ARABIC_FONT_PATH)
        self.btn_lang.bind(on_release=self.toggle_language)

        title_wrap = BoxLayout(orientation="vertical")
        self.lbl_title = Label(text="", halign="center", valign="middle", font_size="20sp", font_name=ARABIC_FONT_PATH)
        self.lbl_beta = Label(text="", halign="center", valign="middle", font_size="12sp", font_name=ARABIC_FONT_PATH)
        self.lbl_title.bind(size=self._update_label_text_size)
        self.lbl_beta.bind(size=self._update_label_text_size)
        title_wrap.add_widget(self.lbl_title)
        title_wrap.add_widget(self.lbl_beta)

        self.themed_labels.extend([self.lbl_title, self.lbl_beta])

        top.add_widget(self.btn_theme)
        top.add_widget(title_wrap)
        top.add_widget(self.btn_lang)
        self.add_widget(top)

        # Description + About
        desc_box = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        self.lbl_desc = Label(text="", halign="left", valign="top", font_name=ARABIC_FONT_PATH)
        self.lbl_desc.bind(size=self._update_label_text_size)
        self.themed_labels.append(self.lbl_desc)

        self.btn_about = Button(text="", size_hint_y=None, height=dp(42), font_name=ARABIC_FONT_PATH)
        self.btn_about.bind(on_release=self.show_about)
        desc_box.add_widget(self.lbl_desc)
        desc_box.add_widget(self.btn_about)
        desc_box.height = dp(180)

        scroll = ScrollView(size_hint=(1, None), height=dp(200))
        scroll.add_widget(desc_box)
        self.add_widget(scroll)

        # Actions
        actions = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        self.btn_camera = Button(text="", font_name=ARABIC_FONT_PATH)
        self.btn_upload = Button(text="", font_name=ARABIC_FONT_PATH)
        self.btn_camera.bind(on_release=self.open_camera)
        self.btn_upload.bind(on_release=self.open_file_picker)
        actions.add_widget(self.btn_camera)
        actions.add_widget(self.btn_upload)
        self.add_widget(actions)

        # Image preview
        self.img_preview = Image(size_hint=(1, None), height=dp(260), allow_stretch=True, keep_ratio=True)
        self.add_widget(self.img_preview)

        # Result
        self.result_card = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        self.lbl_result_title = Label(text="", font_size="16sp", font_name=ARABIC_FONT_PATH)
        self.lbl_result_value = Label(text="", font_size="28sp", bold=True, font_name=ARABIC_FONT_PATH)
        self.pb = ProgressBar(max=100, value=0)
        self.lbl_conf = Label(text="", font_size="14sp", font_name=ARABIC_FONT_PATH)
        self.result_card.add_widget(self.lbl_result_title)
        self.result_card.add_widget(self.lbl_result_value)
        self.result_card.add_widget(self.pb)
        self.result_card.add_widget(self.lbl_conf)
        self.add_widget(self.result_card)

        self.themed_labels.extend([self.lbl_result_title, self.lbl_result_value, self.lbl_conf])

        # Bottom
        bottom = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        self.lbl_status = Label(text="", halign="left", valign="middle", font_name=ARABIC_FONT_PATH)
        self.lbl_status.bind(size=self._update_label_text_size)
        self.themed_labels.append(self.lbl_status)

        self.btn_reset = Button(text="", size_hint_x=None, width=dp(220), font_name=ARABIC_FONT_PATH)
        self.btn_reset.bind(on_release=self.reset_all)
        bottom.add_widget(self.lbl_status)
        bottom.add_widget(self.btn_reset)
        self.add_widget(bottom)

        self._set_texts()
        self._set_texts()
        # Clock.schedule_once(self._load_models_async, 0)

    def _update_label_text_size(self, lbl, *_):
        lbl.text_size = (lbl.width, None)

    def _t(self):
        return TRANSLATIONS["AR" if self.arabic_mode else "EN"]

    def _reshape(self, text):
        if self.arabic_mode:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        return text

    def _set_texts(self):
        t = self._t()
        self.lbl_title.text = self._reshape(t["title"])
        self.lbl_beta.text = f"[b]{self._reshape(t['beta'])}[/b]"
        self.lbl_beta.markup = True

        self.lbl_desc.text = self._reshape(t["desc"])
        self.btn_about.text = f"{self._reshape(t['about'])}"

        self.btn_camera.text = self._reshape(t["cam"])
        self.btn_upload.text = self._reshape(t["up"])
        self.lbl_result_title.text = self._reshape(t["res"])
        self.btn_reset.text = self._reshape(t["reset"])

        self.btn_theme.text = "Light" if self.dark_mode else "Dark"
        self.btn_lang.text = "EN" if self.arabic_mode else "ع"

        if self.arabic_mode:
            self.lbl_desc.halign = "right"
            self.lbl_status.halign = "right"
        else:
            self.lbl_desc.halign = "left"
            self.lbl_status.halign = "left"

        self._render_result()

    def _apply_theme(self):
        if self.dark_mode:
            bg = (0.12, 0.12, 0.12, 1)
            txt_col = (1, 1, 1, 1)
        else:
            bg = (0.98, 0.97, 0.96, 1)
            txt_col = (0, 0, 0, 1)

        for lbl in self.themed_labels:
            lbl.color = txt_col

        self.canvas.before.clear()
        with self.canvas.before:
            Color(*bg)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)

        Window.clearcolor = bg
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *_):
        if hasattr(self, "_bg_rect"):
            self._bg_rect.pos = self.pos
            self._bg_rect.size = self.size

    # ---------- Load TFLite models ----------
    def _load_models_async(self, *_):
        # We don't load models locally anymore.
        pass

    # ---------- Actions ----------
    def toggle_theme(self, *_):
        self.dark_mode = not self.dark_mode
        self._apply_theme()
        self._set_texts()

    def toggle_language(self, *_):
        self.arabic_mode = not self.arabic_mode
        self._set_texts()

    def show_about(self, *_):
        t = self._t()
        content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        lbl = Label(
            text=self._reshape(t["abs_text"] + f"\n\nServer: {self.server_url}"),
            halign="right" if self.arabic_mode else "left",
            valign="top",
            font_name=ARABIC_FONT_PATH,
        )
        lbl.bind(size=self._update_label_text_size)
        btn = Button(text="OK", size_hint_y=None, height=dp(44), font_name=ARABIC_FONT_PATH)
        content.add_widget(lbl)
        content.add_widget(btn)
        pop = Popup(title=self._reshape(t["abs_title"]), content=content, size_hint=(0.9, 0.6), title_font=ARABIC_FONT_PATH)
        btn.bind(on_release=pop.dismiss)
        pop.open()

    def open_file_picker(self, *_):
        t = self._t()
        chooser = FileChooserIconView(filters=["*.jpg", "*.jpeg", "*.png"], path=os.getcwd())
        chooser.size_hint = (1, 1)

        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        box.add_widget(chooser)

        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        btn_ok = Button(text="OK", font_name=ARABIC_FONT_PATH)
        btn_cancel = Button(text="Cancel", font_name=ARABIC_FONT_PATH)
        row.add_widget(btn_ok)
        row.add_widget(btn_cancel)
        box.add_widget(row)

        pop = Popup(title=self._reshape(t["pick_image"]), content=box, size_hint=(0.95, 0.85), title_font=ARABIC_FONT_PATH)

        def do_ok(*_):
            if chooser.selection:
                self.set_image_and_predict(chooser.selection[0])
            pop.dismiss()

        btn_ok.bind(on_release=do_ok)
        btn_cancel.bind(on_release=pop.dismiss)
        pop.open()

    def open_camera(self, *_):
        t = self._t()
        if platform != "android":
            self._show_error(
                "Desktop camera is not stable with Kivy Camera.\n"
                "Use Upload File on Windows.\n"
                "On Android APK, use XCamera."
            )
            return

        from android.permissions import request_permissions, Permission
        request_permissions([Permission.CAMERA, Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])

        try:
            from kivy_garden.xcamera import XCamera
        except ImportError:
            self._show_error("XCamera not found. Add 'kivy-garden.xcamera' to buildozer requirements.")
            return

        cam = XCamera(play=True)

        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        box.add_widget(cam)

        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        btn_take = Button(text=self._reshape(t["cam"]), font_name=ARABIC_FONT_PATH)
        btn_close = Button(text=self._reshape(t["close_cam"]), font_name=ARABIC_FONT_PATH)
        row.add_widget(btn_take)
        row.add_widget(btn_close)
        box.add_widget(row)

        view = ModalView(size_hint=(0.95, 0.9))
        view.add_widget(box)

        def take_photo(*_):
            out_path = os.path.join(os.getcwd(), "captured_palm.png")
            try:
                cam.export_to_png(out_path)
                Clock.schedule_once(lambda dt: self.set_image_and_predict(out_path), 0.2)
            except Exception as e:
                self._show_error(f"Failed to capture: {e}")
            view.dismiss()

        btn_take.bind(on_release=take_photo)
        btn_close.bind(on_release=view.dismiss)
        view.open()

    def set_image_and_predict(self, path: str):
        if not os.path.exists(path):
            self._show_error(f"File not found: {path}")
            return

        self.image_path = path
        self.img_preview.source = path
        self.img_preview.reload()

        self.lbl_status.text = self._reshape(self._t()["analyzing"])
        Clock.schedule_once(lambda *_: self._run_prediction(path), 0.05)

    def _run_prediction(self, path: str):
        # Run in a thread so UI doesn't freeze
        t = threading.Thread(target=self._run_prediction_thread, args=(path,))
        t.start()

    def _run_prediction_thread(self, path: str):
        idx, conf, label_or_error = predict_via_api(path, self.server_url)
        
        # Update UI on main thread
        Clock.schedule_once(lambda dt: self._update_result_ui(idx, conf, label_or_error))

    def _update_result_ui(self, idx, conf, label_or_error):
        self.confidence = float(conf)
        
        # If idx is None, then label_or_error is an error message
        if idx is None:
            self.result_text = "Error"
            self.lbl_status.text = self._reshape(f"Error: {label_or_error}")
            self._render_result()
            return
            
        t = self._t()
        # label_or_error contains the class name from server, but we can also look it up or translate it
        # The server returns English labels: "Khalas", "Razeez", "Shishi"
        # We need to map them to the current language
        
        # Map server label to index if possible, or use the index returned
        # Server sends 0, 1, 2 which maps to t["labels"][idx]
        if 0 <= idx < len(t["labels"]):
            self.result_text = t["labels"][idx]
        else:
             self.result_text = label_or_error

        self.lbl_status.text = ""
        self._render_result()

    def _render_result(self):
        t = self._t()
        if not self.result_text:
            self.lbl_result_value.text = "-"
            self.pb.value = 0
            self.lbl_conf.text = ""
            return

        conf_percent = self.confidence * 100.0
        self.lbl_result_value.text = self._reshape(self.result_text)
        self.pb.value = max(0, min(100, conf_percent))
        self.lbl_conf.text = self._reshape(f"{t['conf']}: {conf_percent:.1f}%")

    def reset_all(self, *_):
        self.image_path = ""
        self.img_preview.source = ""
        self.result_text = ""
        self.confidence = 0.0
        self.lbl_status.text = ""
        self._render_result()

    def _show_error(self, msg: str):
        box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
        lbl = Label(
            text=self._reshape(msg),
            halign="right" if self.arabic_mode else "left",
            valign="top",
            font_name=ARABIC_FONT_PATH,
        )
        lbl.bind(size=self._update_label_text_size)
        btn = Button(text="OK", size_hint_y=None, height=dp(44), font_name=ARABIC_FONT_PATH)
        box.add_widget(lbl)
        box.add_widget(btn)
        pop = Popup(title="Error", content=box, size_hint=(0.9, 0.6), title_font=ARABIC_FONT_PATH)
        btn.bind(on_release=pop.dismiss)
        pop.open()


class PalmClassifierApp(App):
    def build(self):
        self.title = "Palm Tree Classifier"
        self.icon = "PalmTreeClassifier_logo.png"
        return Root()


if __name__ == "__main__":
    PalmClassifierApp().run()
