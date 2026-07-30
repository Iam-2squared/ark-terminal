const STORAGE_KEY = "arkStockWatchlist";

const defaultWatchlist = [
    {
        id: crypto.randomUUID(),
        symbol: "NVDA",
        name: "NVIDIA"
    },
    {
        id: crypto.randomUUID(),
        symbol: "TSM",
        name: "TSMC"
    },
    {
        id: crypto.randomUUID(),
        symbol: "AMD",
        name: "AMD"
    },
    {
        id: crypto.randomUUID(),
        symbol: "MU",
        name: "Micron"
    }
];

const watchlistElement =
    document.getElementById("watchlist");

const addStockForm =
    document.getElementById("addStockForm");

const stockNameInput =
    document.getElementById("stockNameInput");

const stockSymbolInput =
    document.getElementById("stockSymbolInput");


function loadWatchlist() {
    const savedData =
        localStorage.getItem(STORAGE_KEY);

    if (!savedData) {
        localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify(defaultWatchlist)
        );

        return defaultWatchlist;
    }

    try {
        const parsedData = JSON.parse(savedData);

        return Array.isArray(parsedData)
            ? parsedData
            : defaultWatchlist;
    } catch (error) {
        console.error(
            "ウォッチリストの読み込みに失敗しました。",
            error
        );

        return defaultWatchlist;
    }
}


function saveWatchlist(watchlist) {
    localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(watchlist)
    );
}


let watchlist = loadWatchlist();


function createStockCard(stock) {
    const companyParameter =
        encodeURIComponent(stock.name);

    return `
        <article class="stockCard">
            <a
                class="stockCardMain"
                href="../news/index.html?company=${companyParameter}"
            >
                <div>
                    <h2>${escapeHtml(stock.name)}</h2>
                    <p>${escapeHtml(stock.symbol)}</p>
                </div>

                <span class="stockCardArrow">
                    News →
                </span>
            </a>

            <button
                class="deleteStockButton"
                type="button"
                data-stock-id="${stock.id}"
                aria-label="${escapeHtml(stock.name)}を削除"
            >
                ×
            </button>
        </article>
    `;
}


function displayWatchlist() {
    if (watchlist.length === 0) {
        watchlistElement.innerHTML = `
            <p class="emptyWatchlist">
                登録されている銘柄はありません。
            </p>
        `;

        return;
    }

    watchlistElement.innerHTML =
        watchlist
            .map(createStockCard)
            .join("");
}


function addStock(name, symbol) {
    const normalizedName = name.trim();
    const normalizedSymbol =
        symbol.trim().toUpperCase();

    const alreadyExists = watchlist.some(stock =>
        stock.symbol.toUpperCase() ===
        normalizedSymbol
    );

    if (alreadyExists) {
        alert("その銘柄コードはすでに登録されています。");
        return;
    }

    const newStock = {
        id: crypto.randomUUID(),
        name: normalizedName,
        symbol: normalizedSymbol
    };

    watchlist.push(newStock);
    saveWatchlist(watchlist);
    displayWatchlist();
}


function deleteStock(stockId) {
    watchlist = watchlist.filter(
        stock => stock.id !== stockId
    );

    saveWatchlist(watchlist);
    displayWatchlist();
}


function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


addStockForm.addEventListener("submit", event => {
    event.preventDefault();

    addStock(
        stockNameInput.value,
        stockSymbolInput.value
    );

    addStockForm.reset();
    stockNameInput.focus();
});


watchlistElement.addEventListener("click", event => {
    const deleteButton =
        event.target.closest(".deleteStockButton");

    if (!deleteButton) {
        return;
    }

    const stockId =
        deleteButton.dataset.stockId;

    deleteStock(stockId);
});


displayWatchlist();