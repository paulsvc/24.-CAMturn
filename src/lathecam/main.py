from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from lathecam.ui.main_window import LatheCAMMainWindow
from lathecam.ui.theme import apply_dark_cad_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LatheCAM")
    app.setOrganizationName("LatheCAM")
    apply_dark_cad_theme(app)

    window = LatheCAMMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
