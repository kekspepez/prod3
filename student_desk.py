import os
import sys
import shutil
import sqlite3
import subprocess
from pathlib import Path
from datetime import date, datetime

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QIcon, QPixmap, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox, QCheckBox, QDateEdit,
    QDialog, QDialogButtonBox, QMessageBox, QListWidget, QListWidgetItem,
    QStackedWidget, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QAbstractItemView, QSplitter, QProgressBar, QMenu, QInputDialog
)

APP_NAME = "Student Desk"

def resource_dir():
    # В собранном PyInstaller-приложении ресурсы лежат в sys._MEIPASS
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent

ROOT = resource_dir()
DATA_DIR = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "StudentDesk"
DB_PATH = DATA_DIR / "student_desk.db"
ATTACH_DIR = DATA_DIR / "attachments"
LOGO_PATH = ROOT / "assets" / "student_desk_logo.png"

DARK_STYLE = """
QWidget { background:#111827; color:#E5E7EB; font-family:'Segoe UI'; font-size:10pt; }
QMainWindow { background:#0B1120; }
QFrame#Sidebar { background:#0F172A; border-right:1px solid #263247; }
QLabel#Brand { color:#FFFFFF; font-size:18pt; font-weight:700; }
QLabel#Subtle { color:#94A3B8; }
QLabel#PageTitle { color:#F8FAFC; font-size:21pt; font-weight:700; }
QLabel#Metric { color:#FFFFFF; font-size:23pt; font-weight:700; }
QFrame#Panel, QFrame#MetricCard { background:#172235; border:1px solid #29384F; border-radius:12px; }
QPushButton { background:#26364F; color:#F8FAFC; border:1px solid #354761; border-radius:8px; padding:8px 13px; }
QPushButton:hover { background:#344966; }
QPushButton#Primary { background:#3047E8; border:1px solid #4359F0; font-weight:600; }
QPushButton#Primary:hover { background:#4058F5; }
QPushButton#Nav { text-align:left; padding:11px 13px; background:transparent; border:0; color:#CBD5E1; }
QPushButton#Nav:checked { background:#25345A; color:#FFFFFF; border-left:3px solid #FFD166; }
QLineEdit, QTextEdit, QComboBox, QDateEdit, QListWidget, QTableWidget {
 background:#0F1A2B; border:1px solid #334155; border-radius:7px; padding:7px; selection-background-color:#3047E8;
}
QComboBox QAbstractItemView { background:#172235; selection-background-color:#3047E8; }
QHeaderView::section { background:#223149; color:#CBD5E1; border:0; padding:8px; }
QTableWidget { gridline-color:#29384F; }
QProgressBar { border:0; border-radius:4px; background:#29384F; text-align:center; height:9px; }
QProgressBar::chunk { background:#2DD4BF; border-radius:4px; }
QCheckBox { spacing:7px; }
QCheckBox::indicator { width:16px; height:16px; }
QScrollBar:vertical { background:#111827; width:10px; }
QScrollBar::handle:vertical { background:#34445C; border-radius:5px; min-height:25px; }
"""

def db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ATTACH_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS subjects(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            assessment TEXT NOT NULL DEFAULT 'Зачёт',
            teacher TEXT DEFAULT '',
            archived INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS works(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            work_type TEXT NOT NULL DEFAULT 'Другое',
            completed INTEGER NOT NULL DEFAULT 0,
            submitted INTEGER NOT NULL DEFAULT 0,
            notes TEXT DEFAULT '',
            deadline TEXT DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'Обычный',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS attachments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
            original_name TEXT NOT NULL,
            stored_path TEXT NOT NULL
        );
        """)

def stamp():
    return datetime.now().isoformat(timespec="seconds")

def panel():
    f = QFrame()
    f.setObjectName("Panel")
    return f

class SubjectDialog(QDialog):
    def __init__(self, parent=None, subject=None):
        super().__init__(parent)
        self.setWindowTitle("Предмет")
        self.setMinimumWidth(390)
        lay = QVBoxLayout(self)
        self.name = QLineEdit(subject["name"] if subject else "")
        self.teacher = QLineEdit(subject["teacher"] if subject else "")
        self.assessment = QComboBox()
        self.assessment.addItems(["Зачёт", "Экзамен"])
        if subject:
            self.assessment.setCurrentText(subject["assessment"])
        lay.addWidget(QLabel("Название предмета"))
        lay.addWidget(self.name)
        lay.addWidget(QLabel("Преподаватель (необязательно)"))
        lay.addWidget(self.teacher)
        lay.addWidget(QLabel("Форма аттестации"))
        lay.addWidget(self.assessment)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def values(self):
        return self.name.text().strip(), self.assessment.currentText(), self.teacher.text().strip()

class WorkDialog(QDialog):
    def __init__(self, parent=None, work=None):
        super().__init__(parent)
        self.setWindowTitle("Работа")
        self.setMinimumWidth(480)
        lay = QVBoxLayout(self)
        self.title = QLineEdit(work["title"] if work else "")
        self.kind = QComboBox()
        self.kind.addItems(["Лабораторная", "Коллоквиум", "Практическая", "Курсовая", "Домашнее задание", "Проект", "Другое"])
        if work:
            self.kind.setCurrentText(work["work_type"])
        self.deadline = QDateEdit()
        self.deadline.setCalendarPopup(True)
        self.deadline.setDisplayFormat("dd.MM.yyyy")
        self.deadline.setSpecialValueText("Без срока")
        self.deadline.setMinimumDate(QDate(2000,1,1))
        self.deadline.setDate(QDate.currentDate())
        self.no_deadline = QCheckBox("Без дедлайна")
        self.no_deadline.setChecked(not bool(work and work["deadline"]))
        if work and work["deadline"]:
            d = QDate.fromString(work["deadline"], "yyyy-MM-dd")
            if d.isValid(): self.deadline.setDate(d)
        self.no_deadline.toggled.connect(lambda v: self.deadline.setEnabled(not v))
        self.deadline.setEnabled(not self.no_deadline.isChecked())
        self.priority = QComboBox()
        self.priority.addItems(["Низкий", "Обычный", "Высокий"])
        if work: self.priority.setCurrentText(work["priority"])
        self.completed = QCheckBox("Выполнено")
        self.submitted = QCheckBox("Сдано")
        if work:
            self.completed.setChecked(bool(work["completed"]))
            self.submitted.setChecked(bool(work["submitted"]))
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Требования, замечания преподавателя, что исправить и т. д.")
        self.notes.setPlainText(work["notes"] if work else "")
        for label, widget in [("Название работы", self.title), ("Тип работы", self.kind),
                              ("Дедлайн", self.deadline), ("", self.no_deadline),
                              ("Приоритет", self.priority)]:
            if label: lay.addWidget(QLabel(label))
            lay.addWidget(widget)
        status = QHBoxLayout()
        status.addWidget(self.completed); status.addWidget(self.submitted); status.addStretch()
        lay.addLayout(status)
        lay.addWidget(QLabel("Заметки к работе"))
        lay.addWidget(self.notes)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def values(self):
        due = "" if self.no_deadline.isChecked() else self.deadline.date().toString("yyyy-MM-dd")
        return (self.title.text().strip(), self.kind.currentText(), self.completed.isChecked(),
                self.submitted.isChecked(), self.notes.toPlainText(), due, self.priority.currentText())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1220, 780)
        if LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))
        self.current_subject = None
        self.current_work = None
        self.show_archived = False
        root = QWidget(); self.setCentralWidget(root)
        outer = QHBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)

        side = QFrame(); side.setObjectName("Sidebar"); side.setFixedWidth(235)
        sl = QVBoxLayout(side); sl.setContentsMargins(16,22,16,18)
        logo = QLabel()
        if LOGO_PATH.exists():
            pm = QPixmap(str(LOGO_PATH))
            logo.setPixmap(pm.scaled(190,90,Qt.KeepAspectRatio,Qt.SmoothTransformation))
            logo.setAlignment(Qt.AlignCenter)
        else:
            logo.setText("Student Desk")
        sl.addWidget(logo)
        brand = QLabel("STUDENT DESK"); brand.setObjectName("Brand"); brand.setAlignment(Qt.AlignCenter); sl.addWidget(brand)
        sub = QLabel("Твой учебный органайзер"); sub.setObjectName("Subtle"); sub.setAlignment(Qt.AlignCenter); sl.addWidget(sub)
        sl.addSpacing(28)
        self.nav_home = QPushButton("  Обзор"); self.nav_subjects = QPushButton("  Предметы")
        self.nav_archive = QPushButton("  Архив семестров")
        self.nav_home.setObjectName("Nav"); self.nav_subjects.setObjectName("Nav"); self.nav_archive.setObjectName("Nav")
        for b in (self.nav_home,self.nav_subjects,self.nav_archive):
            b.setCheckable(True); sl.addWidget(b)
        self.nav_home.clicked.connect(lambda: self.switch_page(0))
        self.nav_subjects.clicked.connect(lambda: self.switch_page(1))
        self.nav_archive.clicked.connect(lambda: self.switch_page(2))
        sl.addStretch()
        version = QLabel("Локальное хранение · SQLite"); version.setObjectName("Subtle"); version.setWordWrap(True); sl.addWidget(version)
        outer.addWidget(side)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack,1)
        self.home_page = self.make_home()
        self.subject_page = self.make_subjects()
        self.archive_page = self.make_archive()
        self.stack.addWidget(self.home_page); self.stack.addWidget(self.subject_page); self.stack.addWidget(self.archive_page)
        self.switch_page(0)
        self.refresh_all()

    def switch_page(self, idx):
        self.stack.setCurrentIndex(idx)
        for i,b in enumerate((self.nav_home,self.nav_subjects,self.nav_archive)): b.setChecked(i==idx)
        self.refresh_all()

    def heading(self, title, subtitle=""):
        box = QVBoxLayout()
        t = QLabel(title); t.setObjectName("PageTitle"); box.addWidget(t)
        if subtitle:
            s = QLabel(subtitle); s.setObjectName("Subtle"); box.addWidget(s)
        return box

    def make_home(self):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(28,24,28,24); l.setSpacing(18)
        l.addLayout(self.heading("Обзор", "Краткая сводка по текущему семестру"))
        cards=QGridLayout(); self.metrics=[]
        for i,(name,color) in enumerate([("Предметы","#3047E8"),("Всего работ","#3047E8"),("Выполнено","#2DD4BF"),("Сдано","#FFD166")]):
            f=QFrame(); f.setObjectName("MetricCard"); fl=QVBoxLayout(f)
            lab=QLabel(name); lab.setObjectName("Subtle"); val=QLabel("0"); val.setObjectName("Metric")
            fl.addWidget(lab); fl.addWidget(val); cards.addWidget(f,0,i); self.metrics.append(val)
        l.addLayout(cards)
        row=QHBoxLayout()
        self.home_search=QLineEdit(); self.home_search.setPlaceholderText("Поиск по предметам и работам…")
        self.home_search.textChanged.connect(self.refresh_home)
        row.addWidget(self.home_search,1)
        add=QPushButton("+ Добавить предмет"); add.setObjectName("Primary"); add.clicked.connect(self.add_subject); row.addWidget(add)
        l.addLayout(row)
        self.home_list=QListWidget(); self.home_list.itemDoubleClicked.connect(self.open_subject_from_item); l.addWidget(self.home_list,1)
        return w

    def make_subjects(self):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(28,24,28,24); l.setSpacing(14)
        top=QHBoxLayout(); top.addLayout(self.heading("Предметы", "Предметы и работы текущего семестра"),1)
        add=QPushButton("+ Добавить предмет"); add.setObjectName("Primary"); add.clicked.connect(self.add_subject); top.addWidget(add)
        l.addLayout(top)
        split=QSplitter()
        left=QWidget(); ll=QVBoxLayout(left); ll.setContentsMargins(0,0,8,0)
        self.subject_search=QLineEdit(); self.subject_search.setPlaceholderText("Найти предмет…"); self.subject_search.textChanged.connect(self.refresh_subject_list)
        ll.addWidget(self.subject_search)
        self.subject_list=QListWidget(); self.subject_list.currentItemChanged.connect(self.select_subject); ll.addWidget(self.subject_list,1)
        left.setMinimumWidth(230); split.addWidget(left)
        right=QWidget(); rl=QVBoxLayout(right); rl.setContentsMargins(8,0,0,0)
        self.subject_title=QLabel("Выбери предмет"); self.subject_title.setObjectName("PageTitle"); rl.addWidget(self.subject_title)
        self.subject_meta=QLabel(""); self.subject_meta.setObjectName("Subtle"); rl.addWidget(self.subject_meta)
        actions=QHBoxLayout()
        self.add_work_btn=QPushButton("+ Добавить работу"); self.add_work_btn.setObjectName("Primary"); self.add_work_btn.clicked.connect(self.add_work); actions.addWidget(self.add_work_btn)
        self.edit_subject_btn=QPushButton("Изменить предмет"); self.edit_subject_btn.clicked.connect(self.edit_subject); actions.addWidget(self.edit_subject_btn)
        self.archive_subject_btn=QPushButton("В архив"); self.archive_subject_btn.clicked.connect(self.archive_subject); actions.addWidget(self.archive_subject_btn)
        actions.addStretch(); rl.addLayout(actions)
        filters=QHBoxLayout()
        self.work_search=QLineEdit(); self.work_search.setPlaceholderText("Поиск по работам…"); self.work_search.textChanged.connect(self.refresh_works); filters.addWidget(self.work_search,1)
        self.work_filter=QComboBox(); self.work_filter.addItems(["Все работы","Не выполнено","Не сдано","Выполнено","Сдано","Просрочено"]); self.work_filter.currentTextChanged.connect(self.refresh_works); filters.addWidget(self.work_filter)
        rl.addLayout(filters)
        self.work_table=QTableWidget(0,6); self.work_table.setHorizontalHeaderLabels(["Работа","Выполнено","Сдано","Дедлайн","Приоритет","Вложения"])
        self.work_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        for c in range(1,6): self.work_table.horizontalHeader().setSectionResizeMode(c,QHeaderView.ResizeToContents)
        self.work_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.work_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.work_table.itemDoubleClicked.connect(self.edit_selected_work)
        self.work_table.setContextMenuPolicy(Qt.CustomContextMenu); self.work_table.customContextMenuRequested.connect(self.work_context_menu)
        rl.addWidget(self.work_table,1)
        bottom=QHBoxLayout()
        self.edit_work_btn=QPushButton("Открыть / изменить"); self.edit_work_btn.clicked.connect(self.edit_selected_work); bottom.addWidget(self.edit_work_btn)
        self.attach_btn=QPushButton("Прикрепить файл"); self.attach_btn.clicked.connect(self.attach_file); bottom.addWidget(self.attach_btn)
        self.open_attach_btn=QPushButton("Открыть вложение"); self.open_attach_btn.clicked.connect(self.open_attachment); bottom.addWidget(self.open_attach_btn)
        self.delete_work_btn=QPushButton("Удалить работу"); self.delete_work_btn.clicked.connect(self.delete_work); bottom.addWidget(self.delete_work_btn)
        bottom.addStretch(); rl.addLayout(bottom)
        split.addWidget(right); split.setStretchFactor(1,1); l.addWidget(split,1)
        return w

    def make_archive(self):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(28,24,28,24)
        l.addLayout(self.heading("Архив семестров", "Предметы можно убрать из текущего списка и вернуть позже"))
        row=QHBoxLayout()
        self.archive_list=QListWidget(); row.addWidget(self.archive_list,1)
        col=QVBoxLayout()
        restore=QPushButton("Вернуть в текущий семестр"); restore.clicked.connect(self.restore_subject); col.addWidget(restore)
        delete=QPushButton("Удалить навсегда"); delete.clicked.connect(self.delete_archived_subject); col.addWidget(delete)
        col.addStretch(); row.addLayout(col); l.addLayout(row,1)
        return w

    def refresh_all(self):
        self.refresh_home(); self.refresh_subject_list(); self.refresh_archive()
        if self.current_subject:
            self.load_subject(self.current_subject)

    def refresh_home(self):
        with db() as c:
            subjects=c.execute("SELECT COUNT(*) n FROM subjects WHERE archived=0").fetchone()["n"]
            works=c.execute("SELECT COUNT(*) n FROM works w JOIN subjects s ON s.id=w.subject_id WHERE s.archived=0").fetchone()["n"]
            done=c.execute("SELECT COUNT(*) n FROM works w JOIN subjects s ON s.id=w.subject_id WHERE s.archived=0 AND w.completed=1").fetchone()["n"]
            sent=c.execute("SELECT COUNT(*) n FROM works w JOIN subjects s ON s.id=w.subject_id WHERE s.archived=0 AND w.submitted=1").fetchone()["n"]
            rows=c.execute("""SELECT s.*, COUNT(w.id) work_count,
                SUM(CASE WHEN w.completed=1 THEN 1 ELSE 0 END) done_count,
                SUM(CASE WHEN w.submitted=1 THEN 1 ELSE 0 END) sent_count
                FROM subjects s LEFT JOIN works w ON w.subject_id=s.id
                WHERE s.archived=0 GROUP BY s.id ORDER BY s.name""").fetchall()
        for lab,val in zip(self.metrics,[subjects,works,done,sent]): lab.setText(str(val))
        self.home_list.clear()
        term=self.home_search.text().strip().lower()
        for r in rows:
            if term and term not in r["name"].lower(): continue
            item=QListWidgetItem(f'{r["name"]}  ·  {r["assessment"]}\n{r["done_count"] or 0}/{r["work_count"]} выполнено   ·   {r["sent_count"] or 0} сдано')
            item.setData(Qt.UserRole,r["id"]); self.home_list.addItem(item)

    def open_subject_from_item(self,item):
        self.switch_page(1)
        sid=item.data(Qt.UserRole)
        for i in range(self.subject_list.count()):
            if self.subject_list.item(i).data(Qt.UserRole)==sid:
                self.subject_list.setCurrentRow(i); break

    def refresh_subject_list(self):
        if not hasattr(self,"subject_list"): return
        with db() as c: rows=c.execute("SELECT * FROM subjects WHERE archived=0 ORDER BY name").fetchall()
        term=self.subject_search.text().lower()
        selected=self.current_subject
        self.subject_list.blockSignals(True); self.subject_list.clear()
        for r in rows:
            if term and term not in r["name"].lower(): continue
            it=QListWidgetItem(r["name"]); it.setData(Qt.UserRole,r["id"]); self.subject_list.addItem(it)
            if selected==r["id"]: self.subject_list.setCurrentItem(it)
        self.subject_list.blockSignals(False)
        if self.subject_list.currentItem(): self.select_subject(self.subject_list.currentItem(),None)
        elif not rows: self.current_subject=None; self.subject_title.setText("Пока нет предметов"); self.subject_meta.setText(""); self.work_table.setRowCount(0)

    def select_subject(self,current,previous):
        if not current: return
        self.current_subject=current.data(Qt.UserRole); self.load_subject(self.current_subject)

    def load_subject(self,sid):
        with db() as c: s=c.execute("SELECT * FROM subjects WHERE id=?",(sid,)).fetchone()
        if not s: return
        self.subject_title.setText(s["name"])
        self.subject_meta.setText(f'{s["assessment"]}  ·  {s["teacher"] or "Преподаватель не указан"}')
        self.refresh_works()

    def refresh_works(self):
        if not hasattr(self,"work_table") or not self.current_subject: return
        with db() as c:
            rows=c.execute("""SELECT w.*, (SELECT COUNT(*) FROM attachments a WHERE a.work_id=w.id) files
                FROM works w WHERE w.subject_id=? ORDER BY
                CASE WHEN w.deadline='' THEN 1 ELSE 0 END, w.deadline, w.id DESC""",(self.current_subject,)).fetchall()
        term=self.work_search.text().lower(); filt=self.work_filter.currentText()
        filtered=[]
        today=date.today().isoformat()
        for r in rows:
            if term and term not in (r["title"]+" "+r["work_type"]+" "+r["notes"]).lower(): continue
            if filt=="Не выполнено" and r["completed"]: continue
            if filt=="Не сдано" and r["submitted"]: continue
            if filt=="Выполнено" and not r["completed"]: continue
            if filt=="Сдано" and not r["submitted"]: continue
            if filt=="Просрочено" and (not r["deadline"] or r["deadline"]>=today or r["submitted"]): continue
            filtered.append(r)
        self.work_table.setRowCount(len(filtered))
        for i,r in enumerate(filtered):
            vals=[r["title"]+"  ·  "+r["work_type"],"Да" if r["completed"] else "Нет","Да" if r["submitted"] else "Нет",
                  QDate.fromString(r["deadline"],"yyyy-MM-dd").toString("dd.MM.yyyy") if r["deadline"] else "—",r["priority"],str(r["files"])]
            for j,v in enumerate(vals):
                it=QTableWidgetItem(v); it.setData(Qt.UserRole,r["id"])
                if j in (1,2): it.setTextAlignment(Qt.AlignCenter)
                if j==4 and r["priority"]=="Высокий": it.setForeground(Qt.yellow)
                if j==3 and r["deadline"] and r["deadline"]<today and not r["submitted"]: it.setForeground(Qt.red)
                self.work_table.setItem(i,j,it)

    def selected_work_id(self):
        row=self.work_table.currentRow()
        if row<0: return None
        it=self.work_table.item(row,0)
        return it.data(Qt.UserRole) if it else None

    def add_subject(self):
        d=SubjectDialog(self)
        if d.exec()!=QDialog.Accepted: return
        name,assess,teacher=d.values()
        if not name: QMessageBox.warning(self,"Student Desk","Введи название предмета."); return
        with db() as c: c.execute("INSERT INTO subjects(name,assessment,teacher,created_at) VALUES(?,?,?,?)",(name,assess,teacher,stamp()))
        self.refresh_all()

    def edit_subject(self):
        if not self.current_subject: return
        with db() as c: s=c.execute("SELECT * FROM subjects WHERE id=?",(self.current_subject,)).fetchone()
        d=SubjectDialog(self,s)
        if d.exec()!=QDialog.Accepted: return
        name,assess,teacher=d.values()
        if not name: return
        with db() as c: c.execute("UPDATE subjects SET name=?,assessment=?,teacher=? WHERE id=?",(name,assess,teacher,self.current_subject))
        self.refresh_all()

    def archive_subject(self):
        if not self.current_subject: return
        with db() as c: c.execute("UPDATE subjects SET archived=1 WHERE id=?",(self.current_subject,))
        self.current_subject=None; self.refresh_all()

    def add_work(self):
        if not self.current_subject:
            QMessageBox.information(self,"Student Desk","Сначала выбери предмет."); return
        d=WorkDialog(self)
        if d.exec()!=QDialog.Accepted: return
        vals=d.values()
        if not vals[0]: QMessageBox.warning(self,"Student Desk","Введи название работы."); return
        with db() as c:
            c.execute("""INSERT INTO works(subject_id,title,work_type,completed,submitted,notes,deadline,priority,created_at)
                VALUES(?,?,?,?,?,?,?,?,?)""",(self.current_subject,*vals,stamp()))
        self.refresh_works(); self.refresh_home()

    def edit_selected_work(self,*args):
        wid=self.selected_work_id()
        if not wid: return
        with db() as c: w=c.execute("SELECT * FROM works WHERE id=?",(wid,)).fetchone()
        d=WorkDialog(self,w)
        if d.exec()!=QDialog.Accepted: return
        vals=d.values()
        if not vals[0]: return
        with db() as c:
            c.execute("""UPDATE works SET title=?,work_type=?,completed=?,submitted=?,notes=?,deadline=?,priority=? WHERE id=?""",(*vals,wid))
        self.refresh_works(); self.refresh_home()

    def delete_work(self):
        wid=self.selected_work_id()
        if not wid: return
        if QMessageBox.question(self,"Удалить работу","Удалить выбранную работу и её вложения?")!=QMessageBox.Yes: return
        with db() as c:
            files=c.execute("SELECT stored_path FROM attachments WHERE work_id=?",(wid,)).fetchall()
            c.execute("DELETE FROM works WHERE id=?",(wid,))
        for f in files:
            try: Path(f["stored_path"]).unlink(missing_ok=True)
            except Exception: pass
        self.refresh_works(); self.refresh_home()

    def attach_file(self):
        wid=self.selected_work_id()
        if not wid: QMessageBox.information(self,"Вложения","Сначала выбери работу."); return
        paths,_=QFileDialog.getOpenFileNames(self,"Выбрать файлы")
        if not paths: return
        with db() as c:
            for src in paths:
                p=Path(src); dest=ATTACH_DIR/(f"{wid}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{p.name}")
                shutil.copy2(p,dest)
                c.execute("INSERT INTO attachments(work_id,original_name,stored_path) VALUES(?,?,?)",(wid,p.name,str(dest)))
        self.refresh_works()
        QMessageBox.information(self,"Вложения","Файлы скопированы в локальное хранилище Student Desk.")

    def open_attachment(self):
        wid=self.selected_work_id()
        if not wid: return
        with db() as c: files=c.execute("SELECT * FROM attachments WHERE work_id=? ORDER BY id",(wid,)).fetchall()
        if not files: QMessageBox.information(self,"Вложения","У этой работы пока нет файлов."); return
        names=[f["original_name"] for f in files]
        chosen,ok=QInputDialog.getItem(self,"Открыть вложение","Выбери файл:",names,0,False)
        if not ok: return
        f=files[names.index(chosen)]
        path=Path(f["stored_path"])
        if path.exists(): os.startfile(str(path)) if os.name=="nt" else subprocess.Popen(["xdg-open",str(path)])
        else: QMessageBox.warning(self,"Вложения","Файл не найден.")

    def work_context_menu(self,pos):
        menu=QMenu(self)
        edit=menu.addAction("Открыть / изменить")
        attach=menu.addAction("Прикрепить файл")
        openf=menu.addAction("Открыть вложение")
        delete=menu.addAction("Удалить")
        action=menu.exec(self.work_table.viewport().mapToGlobal(pos))
        if action==edit: self.edit_selected_work()
        elif action==attach: self.attach_file()
        elif action==openf: self.open_attachment()
        elif action==delete: self.delete_work()

    def refresh_archive(self):
        if not hasattr(self,"archive_list"): return
        with db() as c: rows=c.execute("SELECT * FROM subjects WHERE archived=1 ORDER BY name").fetchall()
        self.archive_list.clear()
        for r in rows:
            it=QListWidgetItem(f'{r["name"]}  ·  {r["assessment"]}'); it.setData(Qt.UserRole,r["id"]); self.archive_list.addItem(it)

    def restore_subject(self):
        it=self.archive_list.currentItem()
        if not it: return
        with db() as c: c.execute("UPDATE subjects SET archived=0 WHERE id=?",(it.data(Qt.UserRole),))
        self.refresh_all()

    def delete_archived_subject(self):
        it=self.archive_list.currentItem()
        if not it: return
        if QMessageBox.question(self,"Удалить навсегда","Предмет, работы и вложения будут удалены. Продолжить?")!=QMessageBox.Yes: return
        sid=it.data(Qt.UserRole)
        with db() as c:
            paths=c.execute("SELECT a.stored_path FROM attachments a JOIN works w ON w.id=a.work_id WHERE w.subject_id=?",(sid,)).fetchall()
            c.execute("DELETE FROM subjects WHERE id=?",(sid,))
        for p in paths:
            try: Path(p["stored_path"]).unlink(missing_ok=True)
            except Exception: pass
        self.refresh_all()

def install_crash_handler():
    import traceback

    def hook(exc_type, exc, tb):
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            (DATA_DIR / "error.log").write_text(text, encoding="utf-8")
        except Exception:
            pass
        try:
            QMessageBox.critical(None, APP_NAME, "Произошла ошибка:\n\n" + text[-1500:] +
                                 "\n\nПодробности сохранены в:\n" + str(DATA_DIR / "error.log"))
        except Exception:
            pass

    sys.excepthook = hook

def main():
    app=QApplication(sys.argv)
    install_crash_handler()
    init_db()
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)
    win=MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__=="__main__":
    main()
