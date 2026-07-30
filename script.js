const menuButton =
    document.getElementById("menuButton");

const sideMenu =
    document.getElementById("sideMenu");

const overlay =
    document.getElementById("overlay");

const todayDateElement =
    document.getElementById("todayDate");

const todayWeekdayElement =
    document.getElementById("todayWeekday");
    
const taskSummaryElement =
    document.getElementById("taskSummary");

const todayTaskListElement =
    document.getElementById("todayTaskList");

const taskProgressElement =
    document.getElementById("taskProgress");
const demoChartData = [
    191.2,
    191.6,
    191.4,
    192.0,
    191.8,
    192.6,
    193.1,
    192.7,
    193.4,
    194.2,
    195.6,
    194.8,
    193.9,
    193.2,
    192.1,
    191.7,
    190.9,
    190.01
];

function createChartPoints(values) {
    const width = 320;
    const height = 100;
    const padding = 8;

    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    return values
        .map((value, index) => {
            const x =
                padding +
                (
                    index /
                    (values.length - 1)
                ) *
                (width - padding * 2);

            const y =
                height -
                padding -
                (
                    (value - min) /
                    range
                ) *
                (height - padding * 2);

            return `${x},${y}`;
        })
        .join(" ");
}

function renderHomeMiniChart(latestPrice) {
    const chartLine =
        document.getElementById(
            "homeStockChartLine"
        );

    const chartArea =
        document.getElementById(
            "homeStockChartArea"
        );

    if (!chartLine || !chartArea) {
        return;
    }

    const values = [
        ...demoChartData.slice(0, -1),
        Number(latestPrice)
    ];

    const linePoints =
        createChartPoints(values);

    chartLine.setAttribute(
        "points",
        linePoints
    );

    const areaPoints =
        `6,94 ${linePoints} 314,94`;

    chartArea.setAttribute(
        "points",
        areaPoints
    );
}
function openMenu() {
    sideMenu.classList.add("open");
    overlay.classList.add("show");

    menuButton.setAttribute(
        "aria-label",
        "メニューを閉じる"
    );
}

function closeMenu() {
    sideMenu.classList.remove("open");
    overlay.classList.remove("show");

    menuButton.setAttribute(
        "aria-label",
        "メニューを開く"
    );
}

function toggleMenu() {
    const menuIsOpen =
        sideMenu.classList.contains("open");

    if (menuIsOpen) {
        closeMenu();
    } else {
        openMenu();
    }
}

function displayToday() {
    const today = new Date();

    const year =
        today.getFullYear();

    const month =
        String(today.getMonth() + 1).padStart(2, "0");

    const day =
        String(today.getDate()).padStart(2, "0");

    const weekdays = [
        "日曜日",
        "月曜日",
        "火曜日",
        "水曜日",
        "木曜日",
        "金曜日",
        "土曜日"
    ];

    todayDateElement.textContent =
        `${year}/${month}/${day}`;

    todayWeekdayElement.textContent =
        weekdays[today.getDay()];
}

function getTodayStorageKey() {
    const today = new Date();

    const year =
        today.getFullYear();

    const month =
        String(today.getMonth() + 1).padStart(2, "0");

    const day =
        String(today.getDate()).padStart(2, "0");

    return `${year}-${month}-${day}`;
}

function loadTodayTasks() {
    let tasksByDate = {};

    try {
        tasksByDate =
            JSON.parse(
                localStorage.getItem("arkTasksByDate")
            ) || {};
    } catch (error) {
        console.error(
            "タスクデータの読み込みに失敗しました。",
            error
        );
    }

    const todayKey =
        getTodayStorageKey();

    const todayTasks =
        Array.isArray(tasksByDate[todayKey])
            ? tasksByDate[todayKey]
            : [];

    displayTodayTasks(todayTasks);
}

function displayTodayTasks(tasks) {
    todayTaskListElement.innerHTML = "";

    if (tasks.length === 0) {
        taskSummaryElement.textContent =
            "今日の予定はありません。";

        taskProgressElement.textContent =
            "進捗 0%";

        return;
    }

    const completedTasks =
        tasks.filter(function (task) {
            return (
                task.completed === true ||
                task.done === true ||
                task.isCompleted === true
            );
        });

    const remainingCount =
        tasks.length - completedTasks.length;

    const progress =
        Math.round(
            (completedTasks.length / tasks.length) * 100
        );

    taskSummaryElement.textContent =
        `残り ${remainingCount}件`;

    tasks
        .slice(0, 3)
        .forEach(function (task) {
            const taskItem =
                document.createElement("p");

            const taskIsCompleted =
                task.completed === true ||
                task.done === true ||
                task.isCompleted === true;

            const taskName =
                typeof task === "string"
                    ? task
                    : task.text ||
                      task.title ||
                      task.name ||
                      "名称未設定";

            taskItem.className =
                "homeTaskItem";

            taskItem.textContent =
                `${taskIsCompleted ? "☑" : "□"} ${taskName}`;

            if (taskIsCompleted) {
                taskItem.classList.add("completed");
            }

            todayTaskListElement.appendChild(
                taskItem
            );
        });

    if (tasks.length > 3) {
        const moreTasks =
            document.createElement("p");

        moreTasks.className =
            "moreTasks";

        moreTasks.textContent =
            `ほか ${tasks.length - 3}件`;

        todayTaskListElement.appendChild(
            moreTasks
        );
    }

    taskProgressElement.textContent =
        `進捗 ${progress}%`;
}

menuButton.addEventListener(
    "click",
    toggleMenu
);

overlay.addEventListener(
    "click",
    closeMenu
);

window.addEventListener(
    "resize",
    function () {
        if (window.innerWidth > 900) {
            closeMenu();
        }
    }
);

/*
    準備中リンクを押したときに
    画面上部へ移動しないようにする。
*/
document
    .querySelectorAll(".cardLink.disabled")
    .forEach(function (link) {
        link.addEventListener(
            "click",
            function (event) {
                event.preventDefault();
            }
        );
    });

displayToday();
loadTodayTasks();

window.addEventListener(
    "pageshow",
    loadTodayTasks
);

/* PWAのService Workerを登録 */
if ("serviceWorker" in navigator) {
    window.addEventListener(
        "load",
        function () {
            navigator.serviceWorker
                .register("./service-worker.js")
                .then(function () {
                    console.log(
                        "Service Worker registered"
                    );
                })
                .catch(function (error) {
                    console.error(
                        "Service Worker registration failed:",
                        error
                    );
                });
        }
    );
}
const HOME_API =
"https://ark-terminal.vercel.app/api/quote";
async function loadHomeStock(){

    const priceElement =
        document.getElementById("homeStockPrice");

    const changeElement =
        document.getElementById("homeStockChange");

    const timeElement =
        document.getElementById("homeStockTime");

    try{

        const response =
            await fetch(`${HOME_API}?symbol=NVDA`);

        const data =
            await response.json();

        priceElement.textContent =
            `$${data.price.toFixed(2)}`;

        renderHomeMiniChart(data.price);    

        changeElement.textContent =
            `${data.change.toFixed(2)} (${data.changePercent.toFixed(2)}%)`;

        changeElement.className =
            "homeStockChange " +
            (data.change>=0 ? "up":"down");

        timeElement.textContent =
            "更新 " +
            new Date(data.updatedAt).toLocaleTimeString();

    }catch{

        priceElement.textContent="取得失敗";

    }

}
loadHomeStock();
document
    .getElementById("stocksCard")
    .addEventListener("keydown", event => {
        if (
            event.key === "Enter" ||
            event.key === " "
        ) {
            location.href = "./stocks/";
        }
    });
    loadHomeStock();

document
    .getElementById("stocksCard")
    .addEventListener("click", () => {
        location.href = "./stocks/";
    });

document
    .getElementById("stocksCard")
    .addEventListener("keydown", event => {
        if (
            event.key === "Enter" ||
            event.key === " "
        ) {
            location.href = "./stocks/";
        }
    });
