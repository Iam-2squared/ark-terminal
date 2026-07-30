let newsData = [];
const newsSearchInput =
    document.getElementById("newsSearchInput");

const clearSearchButton =
    document.getElementById("clearSearchButton");

let activeFilter = "all";
let searchKeyword = "";
const newsList = document.getElementById("newsList");
const filterButtons =
    document.querySelectorAll(".filterButton");

const params =
    new URLSearchParams(window.location.search);

const selectedCompany =
    params.get("company");

function createNewsCard(news) {
    const importanceText =
        news.importance === "high"
            ? "重要度 ★★★★★"
            : "重要度 ★★★☆☆";

    const safeUrl = news.url || "#";

    return `
        <article class="newsCard">
            <div class="newsMeta">
                <span class="newsTag">
                    ${news.company}
                </span>

                <span>${news.date}</span>

                <span class="importance">
                    ${importanceText}
                </span>
            </div>

            <h2 class="newsTitle">
                ${news.title}
            </h2>

            <p class="newsSummary">
                ${news.summary || "要約はありません。"}
            </p>

            <div class="impactBox">
                <span class="impactLabel">
                    ARK ANALYSIS
                </span>

                <p class="impactText">
                    ${news.impact}
                </p>
            </div>

            <a
                class="newsLink"
                href="${safeUrl}"
                target="_blank"
                rel="noopener noreferrer"
            >
                元の記事を見る →
            </a>
        </article>
    `;
}

function displayNews(filter = "all") {
    let filteredNews = [...newsData];

    // Stocksページから銘柄を指定して来た場合
    if (selectedCompany) {
        const companyAliases = {
            NVIDIA: ["nvidia", "エヌビディア", "nvda"],
            TSMC: ["tsmc", "台湾積体電路", "tsm"],
            AMD: [
                "amd",
                "アドバンスト・マイクロ・デバイセズ"
            ],
            Micron: ["micron", "マイクロン", "mu"]
        };

        const keywords =
            companyAliases[selectedCompany] ||
            [selectedCompany.toLowerCase()];

        filteredNews = filteredNews.filter(news => {
            const text = `
                ${news.company || ""}
                ${news.title || ""}
                ${news.summary || ""}
                ${news.source || ""}
            `.toLowerCase();

            return keywords.some(keyword =>
                text.includes(keyword.toLowerCase())
            );
        });
    }
    if (searchKeyword) {
    const normalizedKeyword =
        searchKeyword.toLowerCase();

    filteredNews = filteredNews.filter(news => {
        const searchableText = `
            ${news.company || ""}
            ${news.title || ""}
            ${news.summary || ""}
            ${news.source || ""}
            ${news.impact || ""}
        `.toLowerCase();

        return searchableText.includes(
            normalizedKeyword
        );
      });
    }

    // 上部ボタンのフィルター
    if (filter === "high") {
        filteredNews = filteredNews.filter(
            news => news.importance === "high"
        );
    }

    if (filter === "company") {
        filteredNews = filteredNews.filter(
            news => news.category === "company"
        );
    }

    if (filter === "market") {
        filteredNews = filteredNews.filter(
            news => news.category === "market"
        );
    }

    if (filteredNews.length === 0) {
        newsList.innerHTML = `
            <p class="emptyMessage">
                該当するニュースはありません。
            </p>
        `;
        return;
    }

    newsList.innerHTML = filteredNews
        .map(createNewsCard)
        .join("");
}
filterButtons.forEach(button => {
    button.addEventListener("click", () => {
        filterButtons.forEach(item =>
            item.classList.remove("active")
        );

        button.classList.add("active");

        activeFilter = button.dataset.filter;
        displayNews(activeFilter);
    });
});

async function loadNews() {
    newsList.innerHTML = `
        <p class="emptyMessage">
            AIニュースを取得しています...
        </p>
    `;

    try {
        const response = await fetch(
            `../data/news.json?t=${Date.now()}`
        );

        if (!response.ok) {
            throw new Error(
                `HTTPエラー: ${response.status}`
            );
        }

        newsData = await response.json();

        if (!Array.isArray(newsData)) {
            throw new Error(
                "ニュースデータの形式が正しくありません。"
            );
        }

        displayNews();

    } catch (error) {
        console.error(error);

        newsList.innerHTML = `
            <p class="emptyMessage">
                ニュースの取得に失敗しました。
            </p>
        `;
    }
}
if (selectedCompany) {
    const pageTitle = document.getElementById("pageTitle");

    if (pageTitle) {
        pageTitle.textContent = `${selectedCompany} News`;
    }
}
newsSearchInput.addEventListener("input", event => {
    searchKeyword =
        event.target.value.trim();

    clearSearchButton.hidden =
        searchKeyword.length === 0;

    displayNews(activeFilter);
});


clearSearchButton.addEventListener("click", () => {
    newsSearchInput.value = "";
    searchKeyword = "";
    clearSearchButton.hidden = true;

    displayNews(activeFilter);
    newsSearchInput.focus();
});
loadNews();