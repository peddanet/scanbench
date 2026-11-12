"""Modal questions of the tabs, replaceable in tests."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog, QInputDialog, QWidget

from scanbench.domain.print_job import PrintJob
from scanbench.infrastructure.cups_client import CupsClient
from scanbench.ui.print_dialog import PrintDialog

SaveAs = Callable[[QWidget, Path], Path | None]
"""Asks for a file name, proposing the given path."""

ChooseFolder = Callable[[QWidget, Path], Path | None]
"""Asks for a folder, starting at the given path."""

AskName = Callable[[QWidget, str], str | None]
"""Asks for a name: (parent, question) -> name or None."""

AskPrint = Callable[[QWidget, str, bool], PrintJob | None]
"""Asks for printer and options: (parent, title, photos) -> job or None."""


def save_pdf_as(parent: QWidget, proposal: Path) -> Path | None:
    """Ask for the PDF file name.

    Args:
        parent: Parent widget.
        proposal: Proposed file.

    Returns:
        The chosen file with ``.pdf`` suffix, or None if cancelled.
    """
    name, _ = QFileDialog.getSaveFileName(parent, "Save PDF", str(proposal), "PDF (*.pdf)")
    return Path(name).with_suffix(".pdf") if name else None


def choose_folder(parent: QWidget, start: Path) -> Path | None:
    """Ask for a folder.

    Args:
        parent: Parent widget.
        start: Folder shown first.

    Returns:
        The chosen folder, or None if cancelled.
    """
    name = QFileDialog.getExistingDirectory(parent, "Album folder", str(start))
    return Path(name) if name else None


def ask_name(parent: QWidget, question: str) -> str | None:
    """Ask for a name, e.g. of a preset.

    Args:
        parent: Parent widget.
        question: Label of the input field.

    Returns:
        The name, or None if cancelled or empty.
    """
    text, accepted = QInputDialog.getText(parent, "scanbench", question)
    return (text.strip() or None) if accepted else None


def print_asker(cups: CupsClient) -> AskPrint:
    """Return a function that shows the CUPS print dialog.

    Args:
        cups: CUPS adapter.

    Returns:
        The question function.
    """
    def ask(parent: QWidget, title: str, photos: bool) -> PrintJob | None:
        """Show the dialog.

        Args:
            parent: Parent widget.
            title: Dialog title.
            photos: Preselect "fit to page".

        Returns:
            The job, or None if cancelled.
        """
        dialog = PrintDialog(cups, title, parent, photos)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        return dialog.job() if accepted else None
    return ask


@dataclass(frozen=True)
class Dialogs:
    """The modal questions of the tabs, replaceable as a whole in tests.

    Attributes:
        ask_print: Printer and options question.
        save_as: PDF file name question.
        choose_folder: Album folder question.
        ask_name: Name question (presets).
    """

    ask_print: AskPrint
    save_as: SaveAs = save_pdf_as
    choose_folder: ChooseFolder = choose_folder
    ask_name: AskName = ask_name
