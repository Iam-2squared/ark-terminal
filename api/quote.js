export default async function handler(request, response) {
    response.setHeader(
        "Access-Control-Allow-Origin",
        "*"
    );

    response.setHeader(
        "Access-Control-Allow-Methods",
        "GET, OPTIONS"
    );

    if (request.method === "OPTIONS") {
        return response.status(204).end();
    }

    const symbol = String(
        request.query.symbol || ""
    )
        .trim()
        .toUpperCase();

    if (!symbol) {
        return response.status(400).json({
            error: "銘柄コードが必要です。"
        });
    }

    const apiKey =
        process.env.FINNHUB_API_KEY;

    if (!apiKey) {
        return response.status(500).json({
            error: "APIキーが設定されていません。"
        });
    }

    try {
        const apiUrl =
            `https://finnhub.io/api/v1/quote` +
            `?symbol=${encodeURIComponent(symbol)}` +
            `&token=${encodeURIComponent(apiKey)}`;

        const apiResponse =
            await fetch(apiUrl);

        if (!apiResponse.ok) {
            throw new Error(
                `Finnhub HTTP ${apiResponse.status}`
            );
        }

        const data =
            await apiResponse.json();

        if (!data.c) {
            return response.status(404).json({
                error: "株価を取得できませんでした。",
                symbol
            });
        }

        return response.status(200).json({
            symbol,
            price: data.c,
            change: data.d,
            changePercent: data.dp,
            high: data.h,
            low: data.l,
            open: data.o,
            previousClose: data.pc,
            updatedAt:
                new Date().toISOString()
        });
    } catch (error) {
        console.error(error);

        return response.status(500).json({
            error: "株価の取得に失敗しました。"
        });
    }
}