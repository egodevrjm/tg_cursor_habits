import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QListWidget, QLineEdit, QProgressBar, 
                             QListWidgetItem, QComboBox, QScrollArea, QGridLayout, QDialog,
                             QCalendarWidget, QTabWidget, QTextEdit, QMessageBox, QSplitter, QTextBrowser,
                             QTabWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QSpinBox, QListWidget, QListWidgetItem, QDialog, 
                             QDialogButtonBox, QFormLayout, QMessageBox)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QDate, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QColor
import json
from datetime import datetime, timedelta
import random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import os

class Habit:
    def __init__(self, name, category="General", streak=0, total_completions=0, last_completed=None):
        self.name = name
        self.category = category
        self.streak = streak
        self.total_completions = total_completions
        self.last_completed = datetime.fromisoformat(last_completed) if last_completed else None

class AddRewardDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Reward")
        self.layout = QFormLayout(self)

        self.name_input = QLineEdit(self)
        self.cost_input = QSpinBox(self)
        self.cost_input.setRange(1, 1000000)
        self.cost_input.setSuffix(" points")

        self.layout.addRow("Reward Name:", self.name_input)
        self.layout.addRow("Cost:", self.cost_input)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addRow(self.buttons)

class RewardItem(QListWidgetItem):
    def __init__(self, reward):
        super().__init__(f"{reward['name']} ({reward['cost']} points)")
        self.reward = reward

class HabitTracker(QMainWindow):
    reward_claimed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Habit Hero")
        self.setGeometry(100, 100, 1000, 600)
        self.setStyleSheet("""
            QMainWindow, QDialog {
                background-color: #f0f0f0;
            }
            QLabel {
                font-size: 14px;
            }
            QPushButton {
                font-size: 14px;
                padding: 8px;
                border-radius: 5px;
            }
            QLineEdit, QComboBox {
                font-size: 14px;
                padding: 8px;
                border-radius: 5px;
            }
        """)

        self.habits = self.load_habits()
        self.points = self.load_points()
        self.rewards = self.load_rewards()
        self.last_update = self.load_last_update()

        self.init_ui()
        self.check_daily_reset()

    def init_ui(self):
        central_widget = QTabWidget()
        self.setCentralWidget(central_widget)

        # Main tab
        main_tab = QWidget()
        main_layout = QHBoxLayout()
        main_tab.setLayout(main_layout)

        # Left panel
        left_panel = QScrollArea()
        left_widget = QWidget()
        left_layout = QVBoxLayout()

        self.habit_list = QListWidget()
        self.habit_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        self.update_habit_list()

        new_habit_input = QLineEdit()
        new_habit_input.setPlaceholderText("Enter new habit")

        category_combo = QComboBox()
        category_combo.addItems(["General", "Health", "Productivity", "Learning"])

        add_habit_btn = QPushButton("Add Habit")
        add_habit_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        add_habit_btn.clicked.connect(lambda: self.add_habit(new_habit_input.text(), category_combo.currentText()))

        left_layout.addWidget(QLabel("Your Habits"))
        left_layout.addWidget(self.habit_list)
        left_layout.addWidget(new_habit_input)
        left_layout.addWidget(category_combo)
        left_layout.addWidget(add_habit_btn)
        left_widget.setLayout(left_layout)
        left_panel.setWidget(left_widget)
        left_panel.setWidgetResizable(True)

        # Right panel
        right_panel = QScrollArea()
        right_widget = QWidget()
        right_layout = QVBoxLayout()

        self.points_label = QLabel(f"Points: {self.points}")
        self.points_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.points_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.level_progress = QProgressBar()
        self.level_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 10px;
                margin: 1px;
            }
        """)
        self.update_level_progress()

        complete_habit_btn = QPushButton("Complete Habit")
        complete_habit_btn.setStyleSheet("background-color: #008CBA; color: white;")
        complete_habit_btn.clicked.connect(self.complete_habit)

        self.motivational_quote = QLabel()
        self.update_motivational_quote()

        # Rewards section
        rewards_layout = QGridLayout()
        for i, reward in enumerate(self.rewards):
            reward_btn = QPushButton(f"{reward['name']} ({reward['cost']} pts)")
            reward_btn.clicked.connect(lambda _, r=reward: self.claim_reward(r))
            rewards_layout.addWidget(reward_btn, i // 2, i % 2)

        # Progress chart
        self.figure, self.ax = plt.subplots(figsize=(5, 4))
        self.chart_canvas = FigureCanvas(self.figure)
        self.update_progress_chart()

        right_layout.addWidget(self.points_label)
        right_layout.addWidget(QLabel("Level Progress"))
        right_layout.addWidget(self.level_progress)
        right_layout.addWidget(complete_habit_btn)
        right_layout.addWidget(self.motivational_quote)
        right_layout.addWidget(QLabel("Rewards"))
        right_layout.addLayout(rewards_layout)
        right_layout.addWidget(self.chart_canvas)
        right_layout.addStretch()
        right_widget.setLayout(right_layout)
        right_panel.setWidget(right_widget)
        right_panel.setWidgetResizable(True)

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 1)

        # Stats tab
        stats_tab = QWidget()
        stats_layout = QVBoxLayout()
        stats_tab.setLayout(stats_layout)

        self.stats_figure, self.stats_ax = plt.subplots(2, 2, figsize=(10, 8))
        self.stats_canvas = FigureCanvas(self.stats_figure)
        self.update_stats_charts()

        stats_layout.addWidget(self.stats_canvas)

        # Calendar tab
        calendar_tab = QWidget()
        calendar_layout = QHBoxLayout()
        calendar_tab.setLayout(calendar_layout)

        # Left side: Calendar
        self.calendar = QCalendarWidget()
        self.calendar.setStyleSheet("""
            QCalendarWidget QToolButton {
                color: black;
                icon-size: 24px, 24px;
            }
            QCalendarWidget QMenu {
                width: 150px;
                left: 20px;
                color: white;
                font-size: 18px;
                background-color: rgb(100, 100, 100);
            }
            QCalendarWidget QSpinBox {
                width: 60px;
                font-size: 24px;
                color: white;
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop: 0 #cccccc, stop: 1 #333333);
                selection-background-color: rgb(136, 136, 136);
                selection-color: rgb(255, 255, 255);
            }
            QCalendarWidget QSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 16px; }
            QCalendarWidget QSpinBox::down-button {subcontrol-origin: border; subcontrol-position: bottom right; width: 16px;}
            QCalendarWidget QSpinBox::up-arrow { width: 10px; height: 10px; }
            QCalendarWidget QSpinBox::down-arrow { width: 10px; height: 10px; }
        """)
        self.calendar.clicked.connect(self.show_day_details)

        # Right side: Day details
        day_details_widget = QWidget()
        day_details_layout = QVBoxLayout()
        day_details_widget.setLayout(day_details_layout)

        self.day_habits_list = QListWidget()
        self.day_habits_list.setStyleSheet("""
            QListWidget {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 3px;
                padding: 5px;
                margin: 2px 0;
            }
        """)

        self.day_journal_preview = QTextBrowser()
        self.day_journal_preview.setStyleSheet("""
            QTextBrowser {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 5px;
            }
        """)

        open_journal_btn = QPushButton("Open Full Journal Entry")
        open_journal_btn.setStyleSheet("""
            QPushButton {
                background-color: #008CBA;
                color: white;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #007B9A;
            }
        """)
        open_journal_btn.clicked.connect(self.open_full_journal_entry)

        day_details_layout.addWidget(QLabel("Habits:"))
        day_details_layout.addWidget(self.day_habits_list)
        day_details_layout.addWidget(QLabel("Journal Preview:"))
        day_details_layout.addWidget(self.day_journal_preview)
        day_details_layout.addWidget(open_journal_btn)

        calendar_layout.addWidget(self.calendar, 1)
        calendar_layout.addWidget(day_details_widget, 1)

        # Journal tab
        journal_tab = QWidget()
        journal_layout = QVBoxLayout()
        journal_tab.setLayout(journal_layout)

        journal_header = QLabel("My Journal")
        journal_header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        journal_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        journal_layout.addWidget(journal_header)

        journal_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Entry list and new entry button
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)

        self.journal_list = QListWidget()
        self.journal_list.setStyleSheet("""
            QListWidget {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 3px;
                padding: 5px;
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background-color: #e6f3ff;
                border: 1px solid #99c9ff;
            }
        """)
        self.journal_list.itemClicked.connect(self.load_journal_entry)
        self.load_journal_list()

        new_entry_btn = QPushButton("New Entry")
        new_entry_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        new_entry_btn.clicked.connect(self.new_journal_entry)

        left_layout.addWidget(self.journal_list)
        left_layout.addWidget(new_entry_btn)

        # Right panel: Entry viewer/editor
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)

        self.journal_date_label = QLabel()
        self.journal_date_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.journal_date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.journal_text = QTextEdit()
        self.journal_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 5px;
            }
        """)

        save_journal_btn = QPushButton("Save Entry")
        save_journal_btn.setStyleSheet("""
            QPushButton {
                background-color: #008CBA;
                color: white;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #007B9A;
            }
        """)
        save_journal_btn.clicked.connect(self.save_journal_entry)

        right_layout.addWidget(self.journal_date_label)
        right_layout.addWidget(self.journal_text)
        right_layout.addWidget(save_journal_btn)

        journal_splitter.addWidget(left_panel)
        journal_splitter.addWidget(right_panel)
        journal_splitter.setStretchFactor(0, 1)
        journal_splitter.setStretchFactor(1, 2)

        journal_layout.addWidget(journal_splitter)

        # Add Rewards tab
        rewards_tab = QWidget()
        rewards_layout = QVBoxLayout()
        rewards_tab.setLayout(rewards_layout)

        rewards_header = QLabel("Rewards")
        rewards_header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        rewards_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rewards_layout.addWidget(rewards_header)

        self.rewards_list = QListWidget()
        self.rewards_list.setStyleSheet("""
            QListWidget {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 3px;
                padding: 10px;
                margin: 5px 0;
            }
        """)
        self.update_rewards_list()

        claim_reward_btn = QPushButton("Claim Selected Reward")
        claim_reward_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        claim_reward_btn.clicked.connect(self.claim_selected_reward)

        add_reward_btn = QPushButton("Add New Reward")
        add_reward_btn.setStyleSheet("""
            QPushButton {
                background-color: #008CBA;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #007B9A;
            }
        """)
        add_reward_btn.clicked.connect(self.add_new_reward)

        rewards_layout.addWidget(self.rewards_list)
        rewards_layout.addWidget(claim_reward_btn)
        rewards_layout.addWidget(add_reward_btn)

        # Add tabs to main widget
        central_widget.addTab(main_tab, "Main")
        central_widget.addTab(stats_tab, "Statistics")
        central_widget.addTab(calendar_tab, "Calendar")
        central_widget.addTab(journal_tab, "Journal")
        central_widget.addTab(rewards_tab, "Rewards")

    def update_habit_list(self):
        self.habit_list.clear()
        for habit in self.habits:
            item = QListWidgetItem(f"🏆 {habit.name} ({habit.category}): {habit.streak} day streak")
            self.habit_list.addItem(item)

    def add_habit(self, name, category):
        if name and name not in [h.name for h in self.habits]:
            self.habits.append(Habit(name, category))
            self.save_habits()
            self.update_habit_list()

    def complete_habit(self):
        current_item = self.habit_list.currentItem()
        if current_item:
            habit_name = current_item.text().split(":")[0].split("(")[0].strip("🏆 ")
            habit = next(h for h in self.habits if h.name == habit_name)
            habit.streak += 1
            habit.total_completions += 1
            habit.last_completed = datetime.now()
            self.points += 10
            self.animate_points()
            self.update_level_progress()
            self.save_habits()
            self.save_points()
            self.update_habit_list()
            self.update_motivational_quote()
            self.update_progress_chart()
            self.update_stats_charts()

    def animate_points(self):
        animation = QPropertyAnimation(self.points_label, b"pos")
        animation.setDuration(500)
        animation.setStartValue(self.points_label.pos())
        animation.setEndValue(self.points_label.pos().y() - 20)
        animation.setEasingCurve(QEasingCurve.Type.OutBounce)
        animation.start()
        QTimer.singleShot(500, lambda: self.points_label.setText(f"Points: {self.points}"))

    def update_level_progress(self):
        level = self.points // 100
        progress = self.points % 100
        self.level_progress.setValue(progress)
        self.level_progress.setFormat(f"Level {level} - {progress}%")

    def update_motivational_quote(self):
        quotes = [
            "Every day is a new opportunity!",
            "Small steps lead to big changes!",
            "Consistency is key to success!",
            "You're making great progress!",
            "Keep up the good work!"
        ]
        self.motivational_quote.setText(random.choice(quotes))

    def check_daily_reset(self):
        today = datetime.now().date()
        if self.last_update != str(today):
            self.reset_daily_habits()
            self.last_update = str(today)
            self.save_last_update()

    def reset_daily_habits(self):
        for habit in self.habits:
            if habit.last_completed and (datetime.now() - habit.last_completed).days > 1:
                habit.streak = 0
        self.save_habits()
        self.update_habit_list()

    def claim_reward(self, reward):
        if self.points >= reward['cost']:
            self.points -= reward['cost']
            self.points_label.setText(f"Points: {self.points}")
            self.save_points()
            QMessageBox.information(self, "Reward Claimed", f"You've claimed the reward: {reward['name']}")

    def update_progress_chart(self):
        self.ax.clear()
        dates = [datetime.now().date() - timedelta(days=i) for i in range(7)][::-1]
        completions = [sum(1 for h in self.habits if h.last_completed and h.last_completed.date() == date) for date in dates]
        
        self.ax.bar(range(7), completions)
        self.ax.set_xticks(range(7))
        self.ax.set_xticklabels([date.strftime('%d/%m') for date in dates], rotation=45)
        self.ax.set_ylabel('Habits Completed')
        self.ax.set_title('Habit Completion Progress')
        
        self.figure.tight_layout()
        self.chart_canvas.draw()

    def update_stats_charts(self):
        for ax in self.stats_ax.flat:
            ax.clear()

        # Habit completion by category
        categories = set(h.category for h in self.habits)
        category_completions = {cat: sum(h.total_completions for h in self.habits if h.category == cat) for cat in categories}
        self.stats_ax[0, 0].pie(category_completions.values(), labels=category_completions.keys(), autopct='%1.1f%%')
        self.stats_ax[0, 0].set_title('Habit Completion by Category')

        # Top 5 habits by streak
        top_habits = sorted(self.habits, key=lambda h: h.streak, reverse=True)[:5]
        self.stats_ax[0, 1].barh([h.name for h in top_habits], [h.streak for h in top_habits])
        self.stats_ax[0, 1].set_title('Top 5 Habits by Streak')

        # Total completions over time
        dates = [datetime.now().date() - timedelta(days=i) for i in range(30)][::-1]
        total_completions = [sum(1 for h in self.habits if h.last_completed and h.last_completed.date() <= date) for date in dates]
        self.stats_ax[1, 0].plot(dates, total_completions)
        self.stats_ax[1, 0].set_title('Total Completions Over Time')
        self.stats_ax[1, 0].set_xticks([dates[0], dates[-1]])
        self.stats_ax[1, 0].set_xticklabels([dates[0].strftime('%d/%m'), dates[-1].strftime('%d/%m')])

        # Points earned over time
        self.stats_ax[1, 1].plot(dates, [i * 10 for i in total_completions])
        self.stats_ax[1, 1].set_title('Points Earned Over Time')
        self.stats_ax[1, 1].set_xticks([dates[0], dates[-1]])
        self.stats_ax[1, 1].set_xticklabels([dates[0].strftime('%d/%m'), dates[-1].strftime('%d/%m')])

        self.stats_figure.tight_layout()
        self.stats_canvas.draw()

    def show_day_details(self, date):
        self.update_day_habits(date)
        self.update_day_journal_preview(date)

    def update_day_habits(self, date):
        self.day_habits_list.clear()
        selected_date = date.toPyDate()
        for habit in self.habits:
            if habit.last_completed and habit.last_completed.date() == selected_date:
                self.day_habits_list.addItem(f"✅ {habit.name}")
            else:
                self.day_habits_list.addItem(f"❌ {habit.name}")

    def update_day_journal_preview(self, date):
        date_str = date.toString("yyyy-MM-dd")
        journal_files = [f for f in os.listdir() if f.startswith(f"journal_{date_str}") and f.endswith(".txt")]
        if journal_files:
            with open(journal_files[0], "r") as f:
                content = f.read()
            preview = content[:200] + "..." if len(content) > 200 else content
            self.day_journal_preview.setText(preview)
        else:
            self.day_journal_preview.setText("No journal entry for this day.")

    def open_full_journal_entry(self):
        selected_date = self.calendar.selectedDate()
        date_str = selected_date.toString("yyyy-MM-dd")
        journal_files = [f for f in os.listdir() if f.startswith(f"journal_{date_str}") and f.endswith(".txt")]
        if journal_files:
            self.load_journal_entry(QListWidgetItem(date_str.replace("-", " ")))
            self.centralWidget().setCurrentIndex(3)  # Switch to the Journal tab
        else:
            QMessageBox.information(self, "No Entry", "There is no journal entry for this day.")

    def load_journal_list(self):
        self.journal_list.clear()
        journal_files = [f for f in os.listdir() if f.startswith("journal_") and f.endswith(".txt")]
        journal_files.sort(reverse=True)
        for file in journal_files:
            date_str = file[8:-4].replace("_", " ")
            item = QListWidgetItem(date_str)
            item.setIcon(QIcon("path_to_journal_icon.png"))  # Add an appropriate icon
            self.journal_list.addItem(item)

    def load_journal_entry(self, item):
        date_str = item.text().replace(" ", "_")
        filename = f"journal_{date_str}.txt"
        try:
            with open(filename, "r") as f:
                content = f.read()
            self.journal_date_label.setText(f"Entry for {item.text()}")
            self.journal_text.setPlainText(content)
        except FileNotFoundError:
            self.journal_date_label.setText("No entry found")
            self.journal_text.clear()

    def new_journal_entry(self):
        self.journal_date_label.setText(f"New Entry - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.journal_text.clear()

    def save_journal_entry(self):
        entry = self.journal_text.toPlainText()
        if entry:
            date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"journal_{date}.txt"
            with open(filename, "w") as f:
                f.write(entry)
            QMessageBox.information(self, "Journal Saved", "Your journal entry has been saved.")
            self.load_journal_list()
            self.journal_list.setCurrentRow(0)  # Select the most recent entry

    def update_rewards_list(self):
        self.rewards_list.clear()
        for reward in self.rewards:
            self.rewards_list.addItem(RewardItem(reward))

    def claim_selected_reward(self):
        selected_items = self.rewards_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a reward to claim.")
            return

        reward = selected_items[0].reward
        if self.points >= reward['cost']:
            self.points -= reward['cost']
            self.points_label.setText(f"Points: {self.points}")
            self.save_points()
            self.reward_claimed.emit(reward['name'])
            QMessageBox.information(self, "Reward Claimed", f"You've claimed the reward: {reward['name']}")
        else:
            QMessageBox.warning(self, "Insufficient Points", "You don't have enough points to claim this reward.")

    def add_new_reward(self):
        dialog = AddRewardDialog(self)
        if dialog.exec():
            new_reward = {
                'name': dialog.name_input.text(),
                'cost': dialog.cost_input.value()
            }
            self.rewards.append(new_reward)
            self.save_rewards()
            self.update_rewards_list()

    def save_rewards(self):
        with open("rewards.json", "w") as f:
            json.dump(self.rewards, f)

    def load_habits(self):
        try:
            with open("habits.json", "r") as f:
                data = json.load(f)
                habits = []
                for item in data:
                    if isinstance(item, str):
                        habits.append(Habit(name=item))
                    elif isinstance(item, dict):
                        habits.append(Habit(
                            name=item['name'],
                            category=item.get('category', 'General'),
                            streak=item.get('streak', 0),
                            total_completions=item.get('total_completions', 0),
                            last_completed=item.get('last_completed')
                        ))
                return habits
        except FileNotFoundError:
            return []

    def save_habits(self):
        with open("habits.json", "w") as f:
            json.dump([{
                'name': h.name,
                'category': h.category,
                'streak': h.streak,
                'total_completions': h.total_completions,
                'last_completed': h.last_completed.isoformat() if h.last_completed else None
            } for h in self.habits], f)

    def load_points(self):
        try:
            with open("points.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return 0

    def save_points(self):
        with open("points.json", "w") as f:
            json.dump(self.points, f)

    def load_rewards(self):
        try:
            with open("rewards.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return [
                {"name": "1 Hour of TV", "cost": 50},
                {"name": "Favorite Snack", "cost": 100},
                {"name": "Movie Night", "cost": 200},
                {"name": "New Book", "cost": 300},
            ]

    def load_last_update(self):
        try:
            with open("last_update.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return str(datetime.now().date())

    def save_last_update(self):
        with open("last_update.json", "w") as f:
            json.dump(self.last_update, f)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HabitTracker()
    window.show()
    sys.exit(app.exec())
