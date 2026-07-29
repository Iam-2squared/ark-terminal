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