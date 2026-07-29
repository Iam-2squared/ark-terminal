let routines = [];
let tasksByDate = {};
let routineCompletionsByDate = {};

const routineInput =
    document.getElementById("routineInput");

const routineButton =
    document.getElementById("addRoutineButton");

const taskInput =
    document.getElementById("taskInput");

const taskButton =
    document.getElementById("addButton");

const routineList =
    document.getElementById("routineList");

const taskList =
    document.getElementById("taskList");

const doneList =
    document.getElementById("doneList");

const selectedDateLabel =
    document.getElementById("selectedDateLabel");

const calendarTitle =
    document.getElementById("calendarTitle");

const calendarDays =
    document.getElementById("calendarDays");

const previousMonthButton =
    document.getElementById("previousMonthButton");

const nextMonthButton =
    document.getElementById("nextMonthButton");

const COMPLETION_ANIMATION_TIME = 550;
const MAX_VISIBLE_CALENDAR_TASKS = 3;

const today = new Date();

today.setHours(0, 0, 0, 0);

let selectedDate = new Date(today);

let displayedYear = selectedDate.getFullYear();
let displayedMonth = selectedDate.getMonth();

/*
    日付を YYYY-MM-DD 形式にする。

    toISOString() は時差によって日付がずれることがあるため、
    ローカル時間から直接作成する。
*/
function createDateKey(date) {
    const year = date.getFullYear();

    const month =
        String(date.getMonth() + 1).padStart(2, "0");

    const day =
        String(date.getDate()).padStart(2, "0");

    return `${year}-${month}-${day}`;
}

function formatSelectedDate(date) {
    return `${date.getMonth() + 1}/${date.getDate()}`;
}

function isSameDate(firstDate, secondDate) {
    return (
        firstDate.getFullYear() === secondDate.getFullYear() &&
        firstDate.getMonth() === secondDate.getMonth() &&
        firstDate.getDate() === secondDate.getDate()
    );
}

function saveData() {
    localStorage.setItem(
        "arkRoutines",
        JSON.stringify(routines)
    );

    localStorage.setItem(
        "arkTasksByDate",
        JSON.stringify(tasksByDate)
    );

    localStorage.setItem(
        "arkRoutineCompletionsByDate",
        JSON.stringify(routineCompletionsByDate)
    );
}

function loadData() {
    try {
        const savedRoutines =
            localStorage.getItem("arkRoutines");

        const savedTasksByDate =
            localStorage.getItem("arkTasksByDate");

        const savedRoutineCompletions =
            localStorage.getItem(
                "arkRoutineCompletionsByDate"
            );

        if (savedRoutines) {
            const parsedRoutines =
                JSON.parse(savedRoutines);

            if (Array.isArray(parsedRoutines)) {
                routines = parsedRoutines;
            }
        }

        if (savedTasksByDate) {
            const parsedTasksByDate =
                JSON.parse(savedTasksByDate);

            if (
                parsedTasksByDate &&
                typeof parsedTasksByDate === "object" &&
                !Array.isArray(parsedTasksByDate)
            ) {
                tasksByDate = parsedTasksByDate;
            }
        }

        if (savedRoutineCompletions) {
            const parsedCompletions =
                JSON.parse(savedRoutineCompletions);

            if (
                parsedCompletions &&
                typeof parsedCompletions === "object" &&
                !Array.isArray(parsedCompletions)
            ) {
                routineCompletionsByDate =
                    parsedCompletions;
            }
        }

        migrateOldData();
    } catch (error) {
        console.error(
            "保存データの読み込みに失敗しました。",
            error
        );

        routines = [];
        tasksByDate = {};
        routineCompletionsByDate = {};
    }
}

/*
    前のバージョンで作成したデータがある場合、
    今日のデータとして一度だけ引き継ぐ。
*/
function migrateOldData() {
    const migrationFinished =
        localStorage.getItem("arkDateMigrationFinished");

    if (migrationFinished === "true") {
        return;
    }

    const todayKey = createDateKey(today);

    const oldTasksText =
        localStorage.getItem("tasks");

    const oldRoutinesText =
        localStorage.getItem("routines");

    try {
        if (
            oldTasksText &&
            !tasksByDate[todayKey]
        ) {
            const oldTasks =
                JSON.parse(oldTasksText);

            if (Array.isArray(oldTasks)) {
                tasksByDate[todayKey] =
                    oldTasks.map(function (task) {
                        return {
                            text: String(task.text || ""),
                            done: Boolean(task.done)
                        };
                    });
            }
        }

        if (
            oldRoutinesText &&
            routines.length === 0
        ) {
            const oldRoutines =
                JSON.parse(oldRoutinesText);

            if (Array.isArray(oldRoutines)) {
                routines =
                    oldRoutines.map(function (routine) {
                        return {
                            id: createId(),
                            text: String(
                                routine.text || ""
                            )
                        };
                    });

                const completedRoutineIds =
                    oldRoutines
                        .map(function (routine, index) {
                            if (routine.done) {
                                return routines[index].id;
                            }

                            return null;
                        })
                        .filter(Boolean);

                routineCompletionsByDate[todayKey] =
                    completedRoutineIds;
            }
        }
    } catch (error) {
        console.error(
            "以前のデータの引き継ぎに失敗しました。",
            error
        );
    }

    localStorage.setItem(
        "arkDateMigrationFinished",
        "true"
    );

    saveData();
}

function createId() {
    if (
        typeof crypto !== "undefined" &&
        typeof crypto.randomUUID === "function"
    ) {
        return crypto.randomUUID();
    }

    return (
        Date.now().toString(36) +
        Math.random().toString(36).slice(2)
    );
}

function getSelectedDateKey() {
    return createDateKey(selectedDate);
}

function getTasksForDate(dateKey) {
    if (!Array.isArray(tasksByDate[dateKey])) {
        tasksByDate[dateKey] = [];
    }

    return tasksByDate[dateKey];
}

function getCompletedRoutineIds(dateKey) {
    if (
        !Array.isArray(
            routineCompletionsByDate[dateKey]
        )
    ) {
        routineCompletionsByDate[dateKey] = [];
    }

    return routineCompletionsByDate[dateKey];
}

function isRoutineCompleted(routineId, dateKey) {
    return getCompletedRoutineIds(dateKey)
        .includes(routineId);
}

function setRoutineCompleted(
    routineId,
    dateKey,
    completed
) {
    const completedIds =
        getCompletedRoutineIds(dateKey);

    const routineIndex =
        completedIds.indexOf(routineId);

    if (
        completed &&
        routineIndex === -1
    ) {
        completedIds.push(routineId);
    }

    if (
        !completed &&
        routineIndex !== -1
    ) {
        completedIds.splice(routineIndex, 1);
    }
}

function createEmptyMessage(text) {
    const message =
        document.createElement("li");

    message.className = "emptyMessage";
    message.textContent = text;

    return message;
}

function createTaskElement(options) {
    const {
        text,
        done,
        onToggle,
        onDelete
    } = options;

    const taskElement =
        document.createElement("li");

    taskElement.className = "taskItem";

    if (done) {
        taskElement.classList.add("completed");
    }

    const checkbox =
        document.createElement("input");

    checkbox.type = "checkbox";
    checkbox.checked = done;
    checkbox.className = "taskCheckbox";

    checkbox.setAttribute(
        "aria-label",
        `${text}を${done ? "未完了" : "完了"}にする`
    );

    const taskText =
        document.createElement("span");

    taskText.className = "taskText";
    taskText.textContent = text;

    const menuButton =
        document.createElement("button");

    menuButton.type = "button";
    menuButton.className = "menuButton";
    menuButton.textContent = "⋮";

    menuButton.setAttribute(
        "aria-label",
        `${text}を削除する`
    );

    taskElement.appendChild(checkbox);
    taskElement.appendChild(taskText);
    taskElement.appendChild(menuButton);

    checkbox.addEventListener(
        "change",
        function () {
            if (checkbox.checked) {
                checkbox.disabled = true;

                taskElement.classList.add(
                    "completing"
                );

                setTimeout(function () {
                    onToggle(true);
                }, COMPLETION_ANIMATION_TIME);
            } else {
                onToggle(false);
            }
        }
    );

    menuButton.addEventListener(
        "click",
        function () {
            const shouldDelete = confirm(
                `「${text}」を削除しますか？`
            );

            if (shouldDelete) {
                onDelete();
            }
        }
    );

    return taskElement;
}

function renderTasks() {
    const dateKey = getSelectedDateKey();

    selectedDateLabel.textContent =
        formatSelectedDate(selectedDate);

    routineList.innerHTML = "";
    taskList.innerHTML = "";
    doneList.innerHTML = "";

    let uncompletedRoutineCount = 0;
    let uncompletedTaskCount = 0;
    let completedCount = 0;

    routines.forEach(function (routine) {
        const done = isRoutineCompleted(
            routine.id,
            dateKey
        );

        const routineElement =
            createTaskElement({
                text: routine.text,
                done: done,

                onToggle: function (completed) {
                    setRoutineCompleted(
                        routine.id,
                        dateKey,
                        completed
                    );

                    saveData();
                    renderTasks();
                },

                onDelete: function () {
                    deleteRoutine(routine.id);
                }
            });

        if (done) {
            doneList.appendChild(routineElement);
            completedCount++;
        } else {
            routineList.appendChild(routineElement);
            uncompletedRoutineCount++;
        }
    });

    const selectedTasks =
        getTasksForDate(dateKey);

    selectedTasks.forEach(function (task, index) {
        const taskElement =
            createTaskElement({
                text: task.text,
                done: task.done,

                onToggle: function (completed) {
                    selectedTasks[index].done =
                        completed;

                    saveData();
                    renderTasks();
                    renderCalendar();
                },

                onDelete: function () {
                    selectedTasks.splice(index, 1);

                    saveData();
                    renderTasks();
                    renderCalendar();
                }
            });

        if (task.done) {
            doneList.appendChild(taskElement);
            completedCount++;
        } else {
            taskList.appendChild(taskElement);
            uncompletedTaskCount++;
        }
    });

    if (uncompletedRoutineCount === 0) {
        routineList.appendChild(
            createEmptyMessage(
                routines.length === 0
                    ? "ルーティンを追加してみよう"
                    : "この日のルーティンは完了！"
            )
        );
    }

    if (uncompletedTaskCount === 0) {
        taskList.appendChild(
            createEmptyMessage(
                selectedTasks.length === 0
                    ? "この日のタスクはまだありません"
                    : "この日のタスクは完了！"
            )
        );
    }

    if (completedCount === 0) {
        doneList.appendChild(
            createEmptyMessage(
                "完了した項目はここに表示されます"
            )
        );
    }
}

function addRoutine() {
    const routineText =
        routineInput.value.trim();

    if (routineText === "") {
        return;
    }

    routines.push({
        id: createId(),
        text: routineText
    });

    routineInput.value = "";

    saveData();
    renderTasks();

    routineInput.focus();
}

function deleteRoutine(routineId) {
    routines = routines.filter(
        function (routine) {
            return routine.id !== routineId;
        }
    );

    Object.keys(
        routineCompletionsByDate
    ).forEach(function (dateKey) {
        routineCompletionsByDate[dateKey] =
            getCompletedRoutineIds(dateKey)
                .filter(function (completedId) {
                    return completedId !== routineId;
                });
    });

    saveData();
    renderTasks();
}

function addTask() {
    const taskText =
        taskInput.value.trim();

    if (taskText === "") {
        return;
    }

    const dateKey =
        getSelectedDateKey();

    const selectedTasks =
        getTasksForDate(dateKey);

    selectedTasks.push({
        id: createId(),
        text: taskText,
        done: false
    });

    taskInput.value = "";

    saveData();
    renderTasks();
    renderCalendar();

    taskInput.focus();
}

function selectDate(date) {
    selectedDate = new Date(
        date.getFullYear(),
        date.getMonth(),
        date.getDate()
    );

    displayedYear =
        selectedDate.getFullYear();

    displayedMonth =
        selectedDate.getMonth();

    renderTasks();
    renderCalendar();
}

function createCalendarDay(date, otherMonth) {
    const dateKey =
        createDateKey(date);

    const dayButton =
        document.createElement("button");

    dayButton.type = "button";
    dayButton.className = "calendarDay";

    if (otherMonth) {
        dayButton.classList.add("otherMonth");
    }

    if (isSameDate(date, today)) {
        dayButton.classList.add("today");
    }

    if (isSameDate(date, selectedDate)) {
        dayButton.classList.add("selected");
    }

    const dayNumber =
        document.createElement("span");

    dayNumber.className = "dayNumber";
    dayNumber.textContent = date.getDate();

    const taskPreviewList =
        document.createElement("div");

    taskPreviewList.className =
        "calendarTaskList";

    const dateTasks =
        Array.isArray(tasksByDate[dateKey])
            ? tasksByDate[dateKey]
            : [];

    const visibleTasks =
        dateTasks.slice(
            0,
            MAX_VISIBLE_CALENDAR_TASKS
        );

    visibleTasks.forEach(function (task) {
        const taskPreview =
            document.createElement("div");

        taskPreview.className =
            "calendarTask";

        if (task.done) {
            taskPreview.classList.add("done");
        }

        taskPreview.textContent = task.text;
        taskPreview.title = task.text;

        taskPreviewList.appendChild(
            taskPreview
        );
    });

    if (
        dateTasks.length >
        MAX_VISIBLE_CALENDAR_TASKS
    ) {
        const remainingTaskCount =
            dateTasks.length -
            MAX_VISIBLE_CALENDAR_TASKS;

        const moreTasks =
            document.createElement("div");

        moreTasks.className = "moreTasks";
        moreTasks.textContent =
            `ほか${remainingTaskCount}件`;

        taskPreviewList.appendChild(
            moreTasks
        );
    }

    dayButton.appendChild(dayNumber);
    dayButton.appendChild(taskPreviewList);

    dayButton.setAttribute(
        "aria-label",
        `${date.getFullYear()}年` +
        `${date.getMonth() + 1}月` +
        `${date.getDate()}日`
    );

    dayButton.addEventListener(
        "click",
        function () {
            selectDate(date);
        }
    );

    return dayButton;
}

function renderCalendar() {
    calendarDays.innerHTML = "";

    calendarTitle.textContent =
        `${displayedYear}年 ${displayedMonth + 1}月`;

    const firstDayOfMonth =
        new Date(
            displayedYear,
            displayedMonth,
            1
        );

    const firstVisibleDate =
        new Date(
            displayedYear,
            displayedMonth,
            1 - firstDayOfMonth.getDay()
        );

    /*
        6週間 × 7日 = 42マスで固定することで、
        月が変わってもカレンダーの高さが大きく変化しない。
    */
    for (
        let cellIndex = 0;
        cellIndex < 42;
        cellIndex++
    ) {
        const date =
            new Date(
                firstVisibleDate.getFullYear(),
                firstVisibleDate.getMonth(),
                firstVisibleDate.getDate() +
                    cellIndex
            );

        const otherMonth =
            date.getMonth() !== displayedMonth;

        calendarDays.appendChild(
            createCalendarDay(
                date,
                otherMonth
            )
        );
    }
}

routineButton.addEventListener(
    "click",
    addRoutine
);

taskButton.addEventListener(
    "click",
    addTask
);

routineInput.addEventListener(
    "keydown",
    function (event) {
        if (event.key === "Enter") {
            addRoutine();
        }
    }
);

taskInput.addEventListener(
    "keydown",
    function (event) {
        if (event.key === "Enter") {
            addTask();
        }
    }
);

previousMonthButton.addEventListener(
    "click",
    function () {
        displayedMonth--;

        if (displayedMonth < 0) {
            displayedMonth = 11;
            displayedYear--;
        }

        renderCalendar();
    }
);

nextMonthButton.addEventListener(
    "click",
    function () {
        displayedMonth++;

        if (displayedMonth > 11) {
            displayedMonth = 0;
            displayedYear++;
        }

        renderCalendar();
    }
);

/* 月のタイトルを押すと今日へ戻る */
calendarTitle.addEventListener(
    "click",
    function () {
        selectDate(today);
    }
);

loadData();
renderTasks();
renderCalendar();

if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
        navigator.serviceWorker
            .register("./service-worker.js")
            .then(function () {
                console.log("Service Worker registered");
            })
            .catch(function (error) {
                console.error(
                    "Service Worker registration failed:",
                    error
                );
            });
    });
}