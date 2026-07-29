const newsData = [
    {
        company: "OpenAI",
        category: "company",
        importance: "high",
        date: "仮データ",
        title: "OpenAIが新しいAIモデルを発表",
        summary:
            "新モデルでは推論能力と処理速度が改善され、開発者向け機能も強化されたとされています。",
        impact:
            "AIサービス競争がさらに激しくなり、半導体・クラウド・ソフトウェア企業にも影響する可能性があります。"
    },
    {
        company: "NVIDIA",
        category: "market",
        importance: "high",
        date: "仮データ",
        title: "AI向け半導体の需要が引き続き拡大",
        summary:
            "生成AIの普及により、データセンター向けGPUへの需要が高い状態が続いています。",
        impact:
            "NVIDIAだけでなく、TSMCやメモリ、データセンター関連企業にも注目が集まりやすい状況です。"
    },
    {
        company: "Google",
        category: "company",
        importance: "normal",
        date: "仮データ",
        title: "GoogleがAI機能を検索サービスへ拡大",
        summary:
            "検索結果にAIによる回答や要約を組み込み、従来の検索体験を変える動きが進んでいます。",
        impact:
            "検索広告の仕組みや情報サイトへのアクセス数に変化が起きる可能性があります。"
    }
];

const newsList = document.getElementById("newsList");
const filterButtons = document.querySelectorAll(".filterButton");

function createNewsCard(news) {
    const importanceText =
        news.importance === "high" ? "重要度 ★★★★★" : "重要度 ★★★☆☆";

    return `
        <article class="newsCard">
            <div class="newsMeta">
                <span class="newsTag">${news.company}</span>
                <span>${news.date}</span>
                <span class="importance">${importanceText}</span>
            </div>

            <h2 class="newsTitle">${news.title}</h2>

            <p class="newsSummary">${news.summary}</p>

            <div class="impactBox">
                <span class="impactLabel">ARK ANALYSIS</span>
                <p class="impactText">${news.impact}</p>
            </div>
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

displayNews();