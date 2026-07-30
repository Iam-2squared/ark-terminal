const STORAGE_KEY = "arkStockWatchlist";
let newsData = [];
const companyAliases = {
    NVIDIA: ["nvidia", "エヌビディア", "nvda"],
    TSMC: ["tsmc", "台湾積体電路", "tsm"],
    AMD: ["amd", "アドバンスト・マイクロ・デバイセズ"],
    Micron: ["micron", "マイクロン", "mu"]
};

function countRelatedNews(stock) {
    const keywords =
        companyAliases[stock.name] ||
        [
            stock.name.toLowerCase(),
            stock.symbol.toLowerCase()
        ];

    return newsData.filter(news => {
        const text = `
            ${news.company || ""}
            ${news.title || ""}
            ${news.summary || ""}
            ${news.source || ""}
        `.toLowerCase();

        return keywords.some(keyword =>
            text.includes(keyword.toLowerCase())
        );
    }).length;
}
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

    const relatedNewsCount =
        countRelatedNews(stock);

    const detailUrl =
        `./detail/index.html?symbol=${encodeURIComponent(stock.symbol)}&company=${encodeURIComponent(stock.name)}`;

    return `
        <article class="stockCard">
                 <a
                   class="stockCardMain"
                   href="${detailUrl}"
                 >
                <div>
                    <h2>${escapeHtml(stock.name)}</h2>
                    <p>${escapeHtml(stock.symbol)}</p>
                </div>

                <span class="stockCardArrow">
                    News →
                </span>

                ${
                    relatedNewsCount > 0
                        ? `
                            <span class="newsBadge">
                                ${relatedNewsCount}
                            </span>
                        `
                        : ""
                }
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


async function loadStocksPage() {
    try {
        const response = await fetch(
            `../data/news.json?t=${Date.now()}`
        );

        if (response.ok) {
            const loadedNews =
                await response.json();

            if (Array.isArray(loadedNews)) {
                newsData = loadedNews;
            }
        }
    } catch (error) {
        console.error(
            "ニュース件数の取得に失敗しました。",
            error
        );
    }

    displayWatchlist();
}

loadStocksPage();