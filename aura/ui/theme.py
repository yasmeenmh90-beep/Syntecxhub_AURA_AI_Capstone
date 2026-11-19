"""AURA design tokens and Qt stylesheet (dark, glass-card aesthetic)."""

BG = "#090C17"
SIDEBAR = "#0C1021"
SURFACE = "#11162A"
SURFACE_2 = "#171D36"
SURFACE_3 = "#1D2443"
BORDER = "#232A47"
BORDER_HI = "#38406A"
TEXT = "#E8EBF5"
MUTED = "#8A93AF"
FAINT = "#5B6383"
VIOLET = "#8B5CF6"
CYAN = "#22D3EE"
OK = "#34D399"
WARN = "#FBBF24"
ERR = "#F87171"

STATUS_COLOURS = {
    "success": OK, "locked": VIOLET, "exit": VIOLET, "error": ERR,
    "rejected": WARN, "confirmation_required": WARN, "cancelled": MUTED,
}

GRADIENT = f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {VIOLET}, stop:1 {CYAN})"

STYLESHEET = f"""
* {{ outline: none; }}
QWidget {{ color: {TEXT}; font-size: 13px; }}
QMainWindow, #Root {{ background: {BG}; }}
QToolTip {{ background: {SURFACE_3}; color: {TEXT}; border: 1px solid {BORDER_HI}; padding: 6px 8px; border-radius: 8px; }}

#Sidebar {{ background: {SIDEBAR}; border-right: 1px solid {BORDER}; }}
#Card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 20px; }}
#Inset {{ background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 14px; }}

QLabel {{ background: transparent; }}
QLabel#Display {{ font-size: 44px; font-weight: 800; letter-spacing: 6px; }}
QLabel#H1 {{ font-size: 24px; font-weight: 700; }}
QLabel#H2 {{ font-size: 16px; font-weight: 650; }}
QLabel#Eyebrow {{ color: {CYAN}; font-size: 11px; font-weight: 700; letter-spacing: 2px; }}
QLabel#Muted {{ color: {MUTED}; }}
QLabel#Faint {{ color: {FAINT}; font-size: 12px; }}
QLabel#Error {{ color: {ERR}; }}
QLabel#Pill {{ background: rgba(251,191,36,0.12); color: {WARN}; border: 1px solid rgba(251,191,36,0.35);
               border-radius: 11px; padding: 3px 10px; font-size: 12px; font-weight: 600; }}
QLabel#PillOk {{ background: rgba(52,211,153,0.12); color: {OK}; border: 1px solid rgba(52,211,153,0.35);
                 border-radius: 11px; padding: 3px 10px; font-size: 12px; font-weight: 600; }}

QPushButton {{ background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 12px;
               padding: 10px 16px; font-weight: 600; }}
QPushButton:hover {{ background: {SURFACE_3}; border-color: {BORDER_HI}; }}
QPushButton:pressed {{ background: {SURFACE}; }}
QPushButton:disabled {{ color: {FAINT}; background: {SURFACE}; border-color: {BORDER}; }}
QPushButton#Primary {{ background: {GRADIENT}; border: none; color: white; padding: 12px 18px; font-size: 14px; }}
QPushButton#Primary:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #9D74FF, stop:1 #4FE0F5); }}
QPushButton#Primary:disabled {{ background: {SURFACE_2}; color: {FAINT}; }}
QPushButton#Danger {{ color: {ERR}; }}
QPushButton#Danger:hover {{ border-color: rgba(248,113,113,0.5); background: rgba(248,113,113,0.08); }}
QPushButton#Nav {{ background: transparent; border: 1px solid transparent; color: {MUTED}; text-align: left;
                   padding: 11px 14px; font-size: 13px; }}
QPushButton#Nav:hover {{ color: {TEXT}; background: {SURFACE}; }}
QPushButton#Nav:checked {{ color: {TEXT}; background: {SURFACE_2}; border: 1px solid {BORDER}; }}
QPushButton#Chip {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 13px; padding: 6px 13px;
                    color: {MUTED}; font-weight: 500; font-size: 12px; }}
QPushButton#Chip:hover {{ color: {TEXT}; border-color: {VIOLET}; }}
QPushButton#Round {{ border-radius: 23px; padding: 0; min-width: 46px; max-width: 46px; min-height: 46px;
                     max-height: 46px; font-size: 17px; }}
QPushButton#Round[active="true"] {{ background: {GRADIENT}; border: none; color: white; }}
QPushButton#Send {{ border-radius: 23px; padding: 0; min-width: 46px; max-width: 46px; min-height: 46px;
                    max-height: 46px; font-size: 17px; background: {GRADIENT}; border: none; color: white; }}

QLineEdit {{ background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 14px; padding: 12px 16px;
             selection-background-color: {VIOLET}; font-size: 14px; }}
QLineEdit:focus {{ border-color: {VIOLET}; }}
QLineEdit#Composer {{ border-radius: 23px; padding: 12px 20px; min-height: 22px; }}

QCheckBox {{ color: {MUTED}; spacing: 8px; }}
QCheckBox::indicator {{ width: 34px; height: 18px; border-radius: 9px; background: {SURFACE_3}; border: 1px solid {BORDER_HI}; }}
QCheckBox::indicator:checked {{ background: {VIOLET}; border-color: {VIOLET}; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ width: 8px; background: transparent; margin: 4px 0; }}
QScrollBar::handle:vertical {{ background: {SURFACE_3}; border-radius: 4px; min-height: 36px; }}
QScrollBar::handle:vertical:hover {{ background: {BORDER_HI}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; background: none; }}

QTableWidget {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 16px; gridline-color: transparent;
                alternate-background-color: #131830; selection-background-color: {SURFACE_3}; padding: 6px; }}
QTableWidget::item {{ padding: 8px 10px; border: none; }}
QHeaderView {{ background: transparent; border: none; }}
QHeaderView::section {{ background: transparent; color: {MUTED}; border: none; border-bottom: 1px solid {BORDER};
                        padding: 10px; font-weight: 700; font-size: 11px; text-transform: uppercase; }}
QTableCornerButton::section {{ background: transparent; border: none; }}
QMessageBox {{ background: {SURFACE}; }}
"""
