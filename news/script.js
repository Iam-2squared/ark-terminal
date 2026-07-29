let newsData = [];
const newsList = document.getElementById("newsList");
const filterButtons = document.querySelectorAll(".filterButton");

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
    let filteredNews = newsData;

    if (filter === "high") {
        filteredNews = newsData.filter(
            news => news.importance === "high"
        );
    }

    if (filter === "company") {
        filteredNews = newsData.filter(
            news => news.category === "company"
        );
    }

    if (filter === "market") {
        filteredNews = newsData.filter(
            news => news.category === "market"
        );
    }

    if (filteredNews.length === 0) {
        newsList.innerHTML =
            `<p class="emptyMessage">該当するニュースはありません。</p>`;
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
        displayNews(button.dataset.filter);
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

loadNews();