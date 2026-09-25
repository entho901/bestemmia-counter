import re
import unicodedata
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.utils import platform


PAROLE_FILE = "parole.txt"


def normalizza(testo):
    testo = testo.lower()

    testo = unicodedata.normalize("NFD", testo)
    testo = "".join(
        c for c in testo
        if unicodedata.category(c) != "Mn"
    )

    testo = re.sub(r"[^a-z0-9\s]", " ", testo)
    testo = re.sub(r"\s+", " ", testo)

    return testo.strip()


def carica_parole():
    parole = []

    try:
        with open(PAROLE_FILE, "r", encoding="utf-8") as file:

            for riga in file:

                parola = normalizza(riga.strip())

                if parola and parola not in parole:
                    parole.append(parola)

    except FileNotFoundError:

        print("ERRORE: parole.txt non trovato.")

    return parole


class ContatoreApp(App):

    def build(self):

        self.title = "Bestemmia Counter"

        self.running = False

        self.parole = carica_parole()

        self.contatori = {
            parola: 0
            for parola in self.parole
        }

        self.pc_listener = None
        self.pc_thread = None

        self.speech_recognizer = None
        self.recognition_listener = None

        root = BoxLayout(
            orientation="vertical",
            padding=15,
            spacing=10
        )

        root.add_widget(
            Label(
                text="BESTEMMIA COUNTER",
                font_size="25sp",
                size_hint_y=None,
                height=55
            )
        )

        self.status_label = Label(
            text="Microfono fermo",
            font_size="18sp",
            size_hint_y=None,
            height=45
        )

        root.add_widget(self.status_label)

        self.total_label = Label(
            text="Totale: 0",
            font_size="20sp",
            size_hint_y=None,
            height=45
        )

        root.add_widget(self.total_label)

        scroll = ScrollView()

        self.counter_grid = GridLayout(
            cols=2,
            spacing=5,
            size_hint_y=None
        )

        self.counter_grid.bind(
            minimum_height=self.counter_grid.setter("height")
        )

        scroll.add_widget(self.counter_grid)

        root.add_widget(scroll)

        buttons = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=70,
            spacing=10
        )

        self.start_button = Button(
            text="START",
            font_size="20sp"
        )

        self.end_button = Button(
            text="END",
            font_size="20sp",
            disabled=True
        )

        self.start_button.bind(
            on_press=self.start
        )

        self.end_button.bind(
            on_press=self.end
        )

        buttons.add_widget(self.start_button)
        buttons.add_widget(self.end_button)

        root.add_widget(buttons)

        self.aggiorna_gui()

        if platform == "android":
            self.richiedi_permesso()

        return root

    # ==================================================
    # PERMESSO ANDROID
    # ==================================================

    def richiedi_permesso(self):

        try:

            from android.permissions import (
                request_permissions,
                Permission
            )

            request_permissions([
                Permission.RECORD_AUDIO
            ])

        except Exception as e:

            print(
                "Errore permesso:",
                e
            )

    # ==================================================
    # START
    # ==================================================

    def start(self, *args):

        if self.running:
            return

        self.running = True

        self.start_button.disabled = True
        self.end_button.disabled = False

        self.status_label.text = "MICROFONO ATTIVO"

        if platform == "android":

            self.avvia_riconoscimento_android()

        else:

            self.avvia_microfono_pc()

    # ==================================================
    # END
    # ==================================================

    def end(self, *args):

        if not self.running:
            return

        self.running = False

        self.start_button.disabled = False
        self.end_button.disabled = True

        self.status_label.text = "Microfono fermo"

        if platform == "android":

            self.stop_riconoscimento_android()

        else:

            self.ferma_microfono_pc()

    # ==================================================
    # MICROFONO PC
    # ==================================================

    def avvia_microfono_pc(self):

        try:

            import speech_recognition as sr

        except ImportError:

            self.status_label.text = (
                "Manca SpeechRecognition"
            )

            print(
                "Installa SpeechRecognition e PyAudio"
            )

            return

        self.status_label.text = (
            "MICROFONO PC ATTIVO"
        )

        self.pc_thread = threading.Thread(
            target=self.ascolta_pc,
            daemon=True
        )

        self.pc_thread.start()

    def ascolta_pc(self):

        import speech_recognition as sr

        recognizer = sr.Recognizer()

        try:

            self.pc_listener = sr.Microphone()

        except Exception as e:

            print(
                "Errore microfono:",
                e
            )

            Clock.schedule_once(
                lambda dt:
                self.imposta_errore_microfono()
            )

            return

        with self.pc_listener as source:

            try:

                recognizer.adjust_for_ambient_noise(
                    source,
                    duration=1
                )

            except Exception as e:

                print(
                    "Errore calibrazione:",
                    e
                )

        while self.running:

            try:

                with self.pc_listener as source:

                    audio = recognizer.listen(
                        source,
                        timeout=None,
                        phrase_time_limit=5
                    )

                testo = recognizer.recognize_google(
                    audio,
                    language="it-IT"
                )

                print(
                    "RICONOSCIUTO PC:",
                    testo
                )

                Clock.schedule_once(
                    lambda dt,
                    testo=testo:
                    self.elabora_testo(testo)
                )

            except sr.UnknownValueError:

                print(
                    "Voce non riconosciuta"
                )

            except sr.RequestError as e:

                print(
                    "Errore servizio Google:",
                    e
                )

                Clock.schedule_once(
                    lambda dt:
                    self.imposta_errore_riconoscimento()
                )

                break

            except Exception as e:

                print(
                    "Errore microfono PC:",
                    e
                )

                break

    def ferma_microfono_pc(self):

        self.pc_listener = None

    def imposta_errore_microfono(self):

        self.status_label.text = (
            "Microfono PC non disponibile"
        )

        self.running = False

        self.start_button.disabled = False
        self.end_button.disabled = True

    def imposta_errore_riconoscimento(self):

        self.status_label.text = (
            "Errore riconoscimento vocale"
        )

    # ==================================================
    # SPEECH RECOGNIZER ANDROID
    # ==================================================

    def avvia_riconoscimento_android(self):

        if not self.running:
            return

        try:

            from jnius import (
                autoclass,
                PythonJavaClass,
                java_method
            )

            SpeechRecognizer = autoclass(
                "android.speech.SpeechRecognizer"
            )

            Intent = autoclass(
                "android.content.Intent"
            )

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )

            activity = PythonActivity.mActivity

            if not SpeechRecognizer.isRecognitionAvailable(
                activity
            ):

                self.status_label.text = (
                    "Riconoscimento non disponibile"
                )

                self.running = False

                return

            app = self

            class Listener(PythonJavaClass):

                __javainterfaces__ = [
                    "android/speech/RecognitionListener"
                ]

                __javacontext__ = "app"

                @java_method(
                    "(Landroid/os/Bundle;)V"
                )
                def onReadyForSpeech(
                    self,
                    params
                ):
                    pass

                @java_method("()V")
                def onBeginningOfSpeech(
                    self
                ):
                    pass

                @java_method("(F)V")
                def onRmsChanged(
                    self,
                    rms
                ):
                    pass

                @java_method("([B)V")
                def onBufferReceived(
                    self,
                    buffer
                ):
                    pass

                @java_method("()V")
                def onEndOfSpeech(
                    self
                ):
                    pass

                @java_method("(I)V")
                def onError(
                    self,
                    error
                ):

                    if app.running:

                        Clock.schedule_once(
                            lambda dt:
                            app.avvia_riconoscimento_android(),
                            0.5
                        )

                @java_method(
                    "(Landroid/os/Bundle;)V"
                )
                def onResults(
                    self,
                    results
                ):

                    if not app.running:
                        return

                    try:

                        matches = (
                            results.getStringArrayList(
                                "results_recognition"
                            )
                        )

                        if matches is not None:

                            if matches.size() > 0:

                                testo = str(
                                    matches.get(0)
                                )

                                app.elabora_testo(
                                    testo
                                )

                    except Exception as e:

                        print(
                            "Errore risultati:",
                            e
                        )

                    if app.running:

                        Clock.schedule_once(
                            lambda dt:
                            app.avvia_riconoscimento_android(),
                            0.2
                        )

                @java_method(
                    "(Landroid/os/Bundle;)V"
                )
                def onPartialResults(
                    self,
                    partial_results
                ):
                    pass

                @java_method(
                    "(ILandroid/os/Bundle;)V"
                )
                def onEvent(
                    self,
                    event_type,
                    params
                ):
                    pass

            self.recognition_listener = Listener()

            self.speech_recognizer = (
                SpeechRecognizer.createSpeechRecognizer(
                    activity
                )
            )

            self.speech_recognizer.setRecognitionListener(
                self.recognition_listener
            )

            intent = Intent(
                "android.speech.action.RECOGNIZE_SPEECH"
            )

            intent.putExtra(
                "android.speech.extra.LANGUAGE_MODEL",
                "free_form"
            )

            intent.putExtra(
                "android.speech.extra.LANGUAGE",
                "it-IT"
            )

            intent.putExtra(
                "android.speech.extra.PARTIAL_RESULTS",
                True
            )

            intent.putExtra(
                "android.speech.extra.MAX_RESULTS",
                1
            )

            self.speech_recognizer.startListening(
                intent
            )

        except Exception as e:

            print(
                "Errore SpeechRecognizer:",
                e
            )

            self.status_label.text = (
                "Errore riconoscimento Android"
            )

    def stop_riconoscimento_android(self):

        try:

            if self.speech_recognizer is not None:

                self.speech_recognizer.stopListening()

                self.speech_recognizer.cancel()

                self.speech_recognizer.destroy()

                self.speech_recognizer = None

        except Exception as e:

            print(
                "Errore arresto:",
                e
            )

    # ==================================================
    # ELABORAZIONE TESTO
    # ==================================================

    def elabora_testo(self, testo):

        if not self.running:
            return

        testo = normalizza(testo)

        if not testo:
            return

        print(
            "TESTO:",
            testo
        )

        parole_testo = testo.split()

        for parola in self.parole:

            if " " in parola:

                if parola in testo:

                    self.contatori[parola] += 1

            else:

                if parola in parole_testo:

                    self.contatori[parola] += 1

        Clock.schedule_once(
            lambda dt:
            self.aggiorna_gui()
        )

    # ==================================================
    # AGGIORNA GUI
    # ==================================================

    def aggiorna_gui(self):

        self.counter_grid.clear_widgets()

        totale = 0

        for parola in self.parole:

            numero = self.contatori[parola]

            totale += numero

            self.counter_grid.add_widget(
                Label(
                    text=parola,
                    font_size="17sp",
                    size_hint_y=None,
                    height=40
                )
            )

            self.counter_grid.add_widget(
                Label(
                    text=str(numero),
                    font_size="17sp",
                    size_hint_y=None,
                    height=40
                )
            )

        self.total_label.text = (
            f"Totale: {totale}"
        )

    # ==================================================
    # CHIUSURA
    # ==================================================

    def on_stop(self):

        self.running = False

        if platform == "android":

            self.stop_riconoscimento_android()

        else:

            self.ferma_microfono_pc()


if __name__ == "__main__":
    ContatoreApp().run()