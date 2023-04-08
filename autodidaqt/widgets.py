import os

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
    QApplication
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
    subject = None

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

        self.currentIndexChanged.connect(lambda: self.subject.on_next(self.currentText()))
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
    validatedTextChanged = QtCore.pyqtSignal(str)

    def __init__(self, *args, subject=None, process_on_next=None, validator:QtGui.QValidator=None, fallback_value=None, **kwargs):
        super().__init__(*args)

        self.increment = kwargs.get("increment", 1.0)
        self.multiplier = kwargs.get("multiplier", 5.0)

        self.subject = subject if subject is not None else BehaviorSubject(self.text())
        self.process_on_next = process_on_next

        if validator is None:
            self.setValidator(QtGui.QDoubleValidator({"bottom": -1e6, "top": 1e6, "decimals": 3}))
        else:
            self.setValidator(validator)

        if fallback_value is not None:
            self.fallback_value = fallback_value
        elif validator is not None:
            self.fallback_value = validator.bottom()
        else:
            self.fallback_value = 1

        self.validatedTextChanged.connect(self.subject.on_next)
        self.subject.subscribe(self.update_ui)

    def setText(self, a0: str) -> None:
        # Need to override this for validation
        if self.validator() is not None and self.validator().validate(a0, 0)[0] != QtGui.QValidator.State.Acceptable:
            return
        # TODO: prevent execution for violation of input mask
        self.validatedTextChanged.emit(a0)
        return super().setText(a0)

    def update_ui(self, value):
        if self.process_on_next:
            value = self.process_on_next(value)

        if value != self.text():
            self.setText(value)

    def increment_value(self, amount:float):
        if self.hasAcceptableInput():
            value = float(self.text())
            value += amount
            self.setText(str(value))

    def decrement_value(self, amount:float):
        if self.hasAcceptableInput():
            value = float(self.text())
            value -= amount
            self.setText(str(value))

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        shift_pressed = a0.modifiers() & QtCore.Qt.ShiftModifier
        if a0.key() == QtCore.Qt.Key_Up:
            self.increment_value(self.increment * self.multiplier if shift_pressed else self.increment)
        elif a0.key() == QtCore.Qt.Key_Down:
            self.decrement_value(self.increment * self.multiplier if shift_pressed else self.increment)
        return super().keyPressEvent(a0)

    def keyReleaseEvent(self, a0: QtGui.QKeyEvent) -> None:
        if self.hasAcceptableInput():
            self.validatedTextChanged.emit(self.text())
        elif a0.key() == QtCore.Qt.Key_Return:
            if self.validator is not None:
                self.validatedTextChanged.emit(self.fixup(self.text()))
            # TODO: handle input masks
        return super().keyReleaseEvent(a0)
    
    def focusOutEvent(self, a0: QtGui.QFocusEvent) -> None:
        if not self.hasAcceptableInput():
            if self.validator is not None:
                self.validatedTextChanged.emit(self.fixup(self.text()))
            # TODO: handle input masks
        return super().focusOutEvent(a0)

    def fixup(self, value:str) -> str:
        if self.validator is None:
            raise AttributeError("No validator set")
        try:
            value = float(value)
        except ValueError:
            return str(self.fallback_value)
        
        if value < self.validator().bottom():
            return str(self.validator().bottom())
        elif value > self.validator().top():
            return str(self.validator().top())
        return str(value) # should never happen


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
