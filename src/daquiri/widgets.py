import os
from functools import partial
from loguru import logger

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTextEdit,
    QWidget,
)
from rx.subject import BehaviorSubject, Subject

from PyQt5 import QtCore, QtGui

__all__ = (
    "PushButton",
    "CheckBox",
    "ComboBox",
    "FileDialog",
    "LineEdit",
    "NumericEdit",
    "RadioButton",
    "Slider",
    "SpinBox",
    "DoubleSpinBox",
    "TextEdit",
)


class Subjective:
    subject: BehaviorSubject = None

    def subscribe(self, *args, **kwargs):
        self.subject.subscribe(*args, **kwargs)

    def on_next(self, *args, **kwargs):
        self.subject.on_next(*args, **kwargs)


class ComboBox(QComboBox, Subjective):
    def __init__(self, *args, subject=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.subject = subject
        if self.subject is None:
            self.subject = BehaviorSubject(self.currentData())

        self.currentIndexChanged.connect(
            lambda: self.subject.on_next(self.currentText())
        )
        self.subject.subscribe(self.update_ui)

    def update_ui(self, value):
        if self.currentText() != value:
            self.setCurrentText(value)


class SpinBox(QSpinBox, Subjective):
    def __init__(self, *args, subject=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.subject = subject
        if self.subject is None:
            self.subject = BehaviorSubject(self.value())

        self.valueChanged.connect(self.subject.on_next)
        self.subject.subscribe(self.update_ui)

    def update_ui(self, value):
        self.setValue(value)


class TextEdit(QTextEdit, Subjective):
    def __init__(self, *args, subject=None):
        super().__init__(*args)

        self.subject = subject
        if self.subject is None:
            self.subject = BehaviorSubject(self.toPlainText())

        self.textChanged.connect(lambda: self.subject.on_next(self.toPlainText()))
        self.subject.subscribe(self.update_ui)

    def update_ui(self, value):
        if self.toPlainText() != value:
            self.setPlainText(value)


class Slider(QSlider, Subjective):
    def __init__(self, *args, subject=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.subject = subject
        if self.subject is None:
            self.subject = BehaviorSubject(self.value())

        self.valueChanged.connect(self.subject.on_next)
        self.subject.subscribe(self.update_ui)

    def update_ui(self, value):
        self.setValue(value)


class LineEdit(QLineEdit, Subjective):
    def __init__(self, *args, subject=None, process_on_next=None):
        super().__init__(*args)

        self.subject = subject
        self.process_on_next = process_on_next
        if self.subject is None:
            self.subject = BehaviorSubject(self.text())

        self.textChanged[str].connect(self.subject.on_next)
        self.subject.subscribe(self.update_ui)

    def update_ui(self, value):
        if self.process_on_next:
            value = self.process_on_next(value)

        if value != self.text():
            self.setText(value)


class NumericEdit(QLineEdit, Subjective):
    _validator: QtGui.QIntValidator | QtGui.QDoubleValidator
    validatedTextChanged = QtCore.pyqtSignal(str)

    def __init__(
        self,
        *args,
        subject=None,
        process_on_next=None,
        validator: QtGui.QDoubleValidator = None,
        increment: float = 1.0,
        multiplier: float = 5.0,
    ):
        super().__init__(*args)

        self.increment = increment
        self.multiplier = multiplier

        self.subject = subject if subject is not None else BehaviorSubject(self.text())
        self.process_on_next = process_on_next

        self._validator = (
            QtGui.QDoubleValidator({"bottom": -1e6, "top": 1e6, "decimals": 3})
            if validator is None
            else validator
        )
        self.setValidator(self._validator)

        self.n_decimals = self._validator.decimals()

        self.fallback_value = self.text()
        self.validatedTextChanged.connect(partial(setattr, self, "fallback_value"))

        self.validatedTextChanged.connect(self.subject.on_next)

    def setText(self, a0: str, emit_signal: bool = True) -> None:
        if self._validator.validate(a0, 0)[0] != QtGui.QValidator.State.Acceptable:
            self.setStyleSheet(
                """
                    QLineEdit:focus {
                        border-color: red;
                        border-width: 4px;
                    }
                """
            )
            a0 = self.fixup(a0)
        else:
            # TODO get from default
            self.setStyleSheet(
                """
                    QLineEdit:focus {
                        border-color: #2995cb;
                        border-width: 4px;
                    }
                """
            )
        if emit_signal:
            self.validatedTextChanged.emit(a0)
        return super().setText(a0)

    def increment_value(self, amount: float) -> None:
        try:
            value = float(self.text())
        except ValueError:
            return
        value += amount
        value = round(value, self.n_decimals)
        self.setText(str(value))

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        def get_increment() -> float:
            if a0.modifiers() & QtCore.Qt.Modifier.SHIFT:
                return self.increment * self.multiplier
            elif a0.modifiers() & QtCore.Qt.Modifier.CTRL:
                return self.increment / self.multiplier
            return self.increment

        if a0.key() == QtCore.Qt.Key.Key_Up:
            self.increment_value(get_increment())
        elif a0.key() == QtCore.Qt.Key.Key_Down:
            self.increment_value(-get_increment())
        return super().keyPressEvent(a0)

    def keyReleaseEvent(self, a0: QtGui.QKeyEvent) -> None:
        """
        TODO: might want to handle any case where the text is changed (e.g. backspace)
        I think I prefer it this way where you have to enter a valid value
        so deleting characters doesn't result in value changes.
        """
        if a0.text().isdigit():
            input = self.text()
            if not self.hasAcceptableInput():
                input = self.fixup(input)
            self.validatedTextChanged.emit(input)
        return super().keyReleaseEvent(a0)

    def fixup(self, value: str) -> str:
        # builtin validator.fixup doesn't seem to work
        try:
            value = float(value)
        except ValueError:
            return self.fallback_value

        if value < self._validator.bottom():
            return str(self._validator.bottom())
        elif value > self._validator.top():
            return str(self._validator.top())
        else:
            return str(round(value, self.n_decimals))


class RadioButton(QRadioButton, Subjective):
    def __init__(self, *args, subject=None):
        super().__init__(*args)

        self.subject = subject
        if self.subject is None:
            self.subject = BehaviorSubject(self.isChecked())

        self.toggled.connect(lambda: self.subject.on_next(self.isChecked()))
        self.subject.subscribe(self.update_ui)

    def update_ui(self, value):
        self.setChecked(value)


class FileDialog(QWidget, Subjective):
    def __init__(self, *args, subject=None, single=True, dialog_root=None):
        if dialog_root is None:
            dialog_root = os.getcwd()

        super().__init__(*args)

        self.dialog_root = dialog_root

        self.subject = subject
        if self.subject is None:
            self.subject = BehaviorSubject(None)

        layout = QHBoxLayout()
        self.btn = PushButton("Open")
        if single:
            self.btn.subject.subscribe(on_next=lambda _: self.get_file())
        else:
            self.btn.subject.subscribe(on_next=lambda _: self.get_files())

        layout.addWidget(self.btn)
        self.setLayout(layout)

    def get_file(self):
        filename = QFileDialog.getOpenFileName(self, "Open File", self.dialog_root)

        self.subject.on_next(filename[0])

    def get_files(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.AnyFile)

        if dialog.exec_():
            filenames = dialog.selectedFiles()
            self.subject.on_next(filenames)


class PushButton(QPushButton, Subjective):
    def __init__(self, *args, subject=None, **kwargs):
        super().__init__(*args)

        self.subject = subject
        if self.subject is None:
            self.subject = Subject()
        self.clicked.connect(lambda: self.subject.on_next(True))


class CheckBox(QCheckBox, Subjective):
    def __init__(self, *args, default=False, subject=None, **kwargs):
        super().__init__(*args)

        self.setChecked(default)

        self.subject = subject
        if self.subject is None:
            self.subject = BehaviorSubject(self.checkState())

        self.stateChanged.connect(self.subject.on_next)
        self.subject.subscribe(self.update_ui)

    def update_ui(self, value):
        self.setCheckState(value)


class SpinBox(QSpinBox, Subjective):
    def __init__(self, *args, subject=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.subject = subject
        if self.subject is None:
            self.subject = BehaviorSubject(self.value())

        self.valueChanged.connect(self.subject.on_next)
        self.subject.subscribe(self.update_ui)

    def update_ui(self, value):
        self.setValue(int(value))


class DoubleSpinBox(QDoubleSpinBox, Subjective):
    def __init__(self, *args, subject=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.subject = subject
        if self.subject is None:
            self.subject = BehaviorSubject(self.value())

        self.valueChanged.connect(self.subject.on_next)
        self.subject.subscribe(self.update_ui)

    def update_ui(self, value):
        self.setValue(float(value))
