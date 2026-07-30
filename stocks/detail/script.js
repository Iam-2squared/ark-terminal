const params = new URLSearchParams(
    window.location.search
);
const stockPriceElement =
    document.getElementById("stockPrice");
const stockChangeElement =
    document.getElementById("stockChange");

const marketStatusElement =
    document.getElementById("marketStatus");

const lastUpdatedElement =
    document.getElementById("lastUpdated");

const refreshChartButton =
    document.getElementById("refreshChartButton");

const tradingviewChartElement =
    document.getElementById("tradingviewChart");
const symbol = params.get("symbol");
const company = params.get("company");

const stockNameElement =
    document.getElementById("stockName");

const stockSymbolElement =
    document.getElementById("stockSymbol");

const relatedNewsElement =
    document.getElementById("relatedNews");

const newsCountElement =
    document.getElementById("newsCount");

    stockNameElement.textContent =
    company || symbol || "Stock Detail";

stockSymbolElement.textContent =
    symbol || "Unknown Symbol";

document.title =
    `${company || symbol || "Stock"} | Ark Terminal`;

function isRelatedNews(news) {
    const text = `
        ${news.company || ""}
        ${news.title || ""}
        ${news.summary || ""}
    `.toLowerCase();

    const keywords = [
        company,
        symbol
    ]
        .filter(Boolean)
        .map(value => value.toLowerCase());

    return keywords.some(keyword =>
        text.includes(keyword)
    );
}

function renderRelatedNews(newsList) {
    const relatedNews =
        newsList.filter(isRelatedNews);

    newsCountElement.textContent =
        relatedNews.length;

    if (relatedNews.length === 0) {
        relatedNewsElement.innerHTML = `
            <p class="emptyMessage">
                関連ニュースはありません。
            </p>
        `;

        return;
    }

    relatedNewsElement.innerHTML =
        relatedNews
            .slice(0, 8)
            .map(news => `
                <a
                    class="newsItem"
                    href="${news.url || news.link || "#"}"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    <h3>${news.title || "Untitled"}</h3>

                    <p>
                        ${news.date || news.source || ""}
                    </p>
                </a>
            `)
            .join("");
}

async function loadRelatedNews() {
    try {
        const response = await fetch(
            `../../data/news.json?t=${Date.now()}`
        );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }

        const newsList = await response.json();

        renderRelatedNews(
            Array.isArray(newsList)
                ? newsList
                : []
        );
    } catch (error) {
        console.error(
            "関連ニュースの取得に失敗しました。",
            error
        );

        relatedNewsElement.innerHTML = `
            <p class="emptyMessage">
                ニュースを取得できませんでした。
            </p>
        `;
    }
}
const tradingViewSymbols = {
    NVDA: "NASDAQ:NVDA",
    MU: "NASDAQ:MU",
    AMD: "NASDAQ:AMD",
    AAPL: "NASDAQ:AAPL",
    MSFT: "NASDAQ:MSFT",
    TSM: "NYSE:TSM",

    "285A": "TSE:285A",
    "9432": "TSE:9432"
};

function getTradingViewSymbol(stockSymbol) {
    const normalizedSymbol =
        String(stockSymbol || "")
            .trim()
            .toUpperCase();

    if (tradingViewSymbols[normalizedSymbol]) {
        return tradingViewSymbols[normalizedSymbol];
    }

    if (/^\d{4}[A-Z]?$/.test(normalizedSymbol)) {
        return `TSE:${normalizedSymbol}`;
    }

    return `NASDAQ:${normalizedSymbol}`;
}

function updateLastUpdatedTime() {
    const now = new Date();

    lastUpdatedElement.textContent =
        `最終更新 ${now.toLocaleTimeString(
            "ja-JP",
            {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit"
            }
        )}`;
}

function setChartLoading(isLoading) {
    refreshChartButton.disabled = isLoading;

    refreshChartButton.classList.toggle(
        "isLoading",
        isLoading
    );

    marketStatusElement.textContent =
        isLoading
            ? "最新データを取得しています..."
            : "チャート表示中";
}
const STOCK_API_BASE_URL =
    "https://ark-terminal.vercel.app";

async function loadStockPrice() {
    if (!symbol) {
        return;
    }

    stockPriceElement.textContent =
        "取得中...";

    stockChangeElement.textContent =
        "--";

    try {
        const response = await fetch(
            `${STOCK_API_BASE_URL}/api/quote` +
            `?symbol=${encodeURIComponent(symbol)}` +
            `&t=${Date.now()}`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                "株価を取得できませんでした。"
            );
        }

        const currencySymbol =
            /^\d/.test(symbol)
                ? "¥"
                : "$";

        stockPriceElement.textContent =
            `${currencySymbol}${Number(
                data.price
            ).toLocaleString(
                "ja-JP",
                {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                }
            )}`;

        const change =
            Number(data.change);

        const changePercent =
            Number(data.changePercent);

        const sign =
            change > 0
                ? "+"
                : "";

        stockChangeElement.textContent =
            `${sign}${change.toFixed(2)} ` +
            `(${sign}${changePercent.toFixed(2)}%)`;

        stockChangeElement.classList.toggle(
            "positive",
            change > 0
        );

        stockChangeElement.classList.toggle(
            "negative",
            change < 0
        );
    } catch (error) {
        console.error(
            "株価の取得に失敗しました。",
            error
        );

        stockPriceElement.textContent =
            "取得失敗";

        stockChangeElement.textContent =
            "--";

        stockChangeElement.classList.remove(
            "positive",
            "negative"
        );
    }
}
function loadStockChart() {
    const restrictedTradingViewSymbols = [
    "285A"
];
    if (!symbol) {
        marketStatusElement.textContent =
            "銘柄コードがありません。";

        return;
    }
if (
    restrictedTradingViewSymbols.includes(
        symbol.toUpperCase()
    )
) {
    tradingviewChartElement.innerHTML = `
        <div class="chartUnavailable">
            <p class="chartUnavailableTitle">
                チャート準備中
            </p>

            <p>
                この銘柄はTradingViewの
                外部埋め込みに対応していません。
            </p>
        </div>
    `;

    marketStatusElement.textContent =
        "外部チャート非対応";

    refreshChartButton.disabled = true;

    return;
}
    setChartLoading(true);

    tradingviewChartElement.innerHTML = "";

    const widgetContainer =
        document.createElement("div");

    widgetContainer.className =
        "tradingview-widget-container";

    widgetContainer.style.width = "100%";
    widgetContainer.style.height = "100%";

    const widgetElement =
        document.createElement("div");

    widgetElement.className =
        "tradingview-widget-container__widget";

    widgetElement.style.width = "100%";
    widgetElement.style.height = "100%";

    const widgetScript =
        document.createElement("script");

    widgetScript.type = "text/javascript";

    widgetScript.src =
        "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";

    widgetScript.async = true;

    widgetScript.textContent = JSON.stringify({
        autosize: true,
        symbol: getTradingViewSymbol(symbol),
        interval: "5",
        timezone: "Asia/Tokyo",
        theme: "dark",
        style: "2",
        locale: "ja",
        backgroundColor: "#0d111d",
        gridColor: "rgba(255, 255, 255, 0.04)",
        hide_top_toolbar: false,
        hide_legend: false,
        save_image: false,
        calendar: false,
        support_host:
            "https://www.tradingview.com"
    });

    widgetContainer.appendChild(widgetElement);
    widgetContainer.appendChild(widgetScript);

    tradingviewChartElement.appendChild(
        widgetContainer
    );

    window.setTimeout(() => {
        setChartLoading(false);
        updateLastUpdatedTime();
    }, 1200);
}

refreshChartButton.addEventListener(
    "click",
    async () => {
        await Promise.all([
            loadStockPrice(),
            Promise.resolve(
                loadStockChart()
            )
        ]);
    }
);
loadRelatedNews();
loadStockChart();
loadStockPrice();