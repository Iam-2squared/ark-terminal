const companyNameInput =
    document.getElementById("companyName");

const stockSymbolInput =
    document.getElementById("stockSymbol");

const predictionPeriodInput =
    document.getElementById("predictionPeriod");

const runPredictionButton =
    document.getElementById("runPredictionButton");

const chartInput =
    document.getElementById("chartInput");

const disclosureInput =
    document.getElementById("disclosureInput");

const sentimentInput =
    document.getElementById("sentimentInput");

const chartInputValue =
    document.getElementById("chartInputValue");

const disclosureInputValue =
    document.getElementById("disclosureInputValue");

const sentimentInputValue =
    document.getElementById("sentimentInputValue");

function updateSliderLabels() {
    chartInputValue.textContent =
        chartInput.value;

    disclosureInputValue.textContent =
        disclosureInput.value;

    sentimentInputValue.textContent =
        sentimentInput.value;
}

function calculateScores() {
    const chartValue =
        Number(chartInput.value);

    const disclosureValue =
        Number(disclosureInput.value);

    const sentimentValue =
        Number(sentimentInput.value);

    const chartScore =
        Math.round(chartValue * 0.4);

    const disclosureScore =
        Math.round(disclosureValue * 0.4);

    const sentimentScore =
        Math.round(sentimentValue * 0.2);

    const totalScore =
        chartScore +
        disclosureScore +
        sentimentScore;

    return {
        chartValue,
        disclosureValue,
        sentimentValue,
        chartScore,
        disclosureScore,
        sentimentScore,
        totalScore
    };
}

function getPredictionResult(totalScore) {
    if (totalScore >= 75) {
        return {
            label: "強気",
            className: "strongBullish",
            riseProbability:
                Math.min(82, totalScore + 5)
        };
    }

    if (totalScore >= 60) {
        return {
            label: "やや強気",
            className: "bullish",
            riseProbability:
                Math.min(72, totalScore + 3)
        };
    }

    if (totalScore >= 40) {
        return {
            label: "中立",
            className: "neutral",
            riseProbability: 50
        };
    }

    if (totalScore >= 25) {
        return {
            label: "やや弱気",
            className: "bearish",
            riseProbability:
                Math.max(28, totalScore - 3)
        };
    }

    return {
        label: "弱気",
        className: "strongBearish",
        riseProbability:
            Math.max(12, totalScore - 5)
    };
}

function getConfidenceLabel(scores) {
    const values = [
        scores.chartValue,
        scores.disclosureValue,
        scores.sentimentValue
    ];

    const average =
        values.reduce(
            (sum, value) => sum + value,
            0
        ) / values.length;

    const spread =
        Math.max(...values) -
        Math.min(...values);

    if (
        spread <= 15 &&
        (
            average >= 65 ||
            average <= 35
        )
    ) {
        return "高";
    }

    if (spread <= 35) {
        return "中";
    }

    return "低";
}

function createReasons(scores) {
    const reasons = [];

    if (scores.chartValue >= 65) {
        reasons.push(
            "チャートは上昇方向のシグナルが優勢です。"
        );
    } else if (scores.chartValue <= 35) {
        reasons.push(
            "チャートは下落方向のシグナルが優勢です。"
        );
    } else {
        reasons.push(
            "チャートは明確な方向感がありません。"
        );
    }

    if (scores.disclosureValue >= 65) {
        reasons.push(
            "適時開示は業績や事業成長にプラスと評価されています。"
        );
    } else if (
        scores.disclosureValue <= 35
    ) {
        reasons.push(
            "適時開示には株価へ悪影響を与える可能性があります。"
        );
    } else {
        reasons.push(
            "適時開示の影響は限定的です。"
        );
    }

    if (scores.sentimentValue >= 75) {
        reasons.push(
            "投資家心理は強気ですが、過熱にも注意が必要です。"
        );
    } else if (
        scores.sentimentValue >= 60
    ) {
        reasons.push(
            "投資家心理はやや強気です。"
        );
    } else if (
        scores.sentimentValue <= 35
    ) {
        reasons.push(
            "投資家心理は弱気に傾いています。"
        );
    } else {
        reasons.push(
            "投資家心理は中立です。"
        );
    }

    return reasons;
}

function renderPrediction() {
    const scores =
        calculateScores();

    const result =
        getPredictionResult(
            scores.totalScore
        );

    const companyName =
        companyNameInput.value.trim() ||
        stockSymbolInput.value.trim() ||
        "未選択";

    const period =
        predictionPeriodInput.value;

    document.getElementById(
        "resultCompanyName"
    ).textContent = companyName;

    document.getElementById(
        "totalScore"
    ).textContent = scores.totalScore;

    document.getElementById(
        "riseProbability"
    ).textContent =
        `${result.riseProbability}%`;

    document.getElementById(
        "predictionPeriodLabel"
    ).textContent =
        `${period}営業日後`;

    document.getElementById(
        "confidenceLabel"
    ).textContent =
        getConfidenceLabel(scores);

    const predictionBadge =
        document.getElementById(
            "predictionBadge"
        );

    predictionBadge.textContent =
        result.label;

    predictionBadge.className =
        `predictionBadge ${result.className}`;

    document.getElementById(
        "chartScore"
    ).textContent =
        scores.chartScore;

    document.getElementById(
        "disclosureScore"
    ).textContent =
        scores.disclosureScore;

    document.getElementById(
        "sentimentScore"
    ).textContent =
        scores.sentimentScore;

    document.getElementById(
        "chartScoreBar"
    ).style.width =
        `${scores.chartScore / 40 * 100}%`;

    document.getElementById(
        "disclosureScoreBar"
    ).style.width =
        `${scores.disclosureScore / 40 * 100}%`;

    document.getElementById(
        "sentimentScoreBar"
    ).style.width =
        `${scores.sentimentScore / 20 * 100}%`;

    const reasons =
        createReasons(scores);

    document.getElementById(
        "reasonList"
    ).innerHTML =
        reasons
            .map(reason => `
                <div class="reasonItem">
                    ${reason}
                </div>
            `)
            .join("");
}

[
    chartInput,
    disclosureInput,
    sentimentInput
].forEach(input => {
    input.addEventListener(
        "input",
        updateSliderLabels
    );
});

runPredictionButton.addEventListener(
    "click",
    renderPrediction
);

updateSliderLabels();
renderPrediction();