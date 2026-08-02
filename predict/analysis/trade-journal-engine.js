function safeNumber(value,fallback=0){
    const n=Number(value);
    return Number.isFinite(n)?n:fallback;
}

function round(v,d=2){
    const f=10**d;
    return Math.round(v*f)/f;
}

export class TradeJournal{

    constructor(){
        this.records=[];
    }

    add(record={}){

        const entry={

            id:
            crypto.randomUUID?.()
            ??String(Date.now()),

            createdAt:
            new Date().toISOString(),

            symbol:
            String(record.symbol??""),

            action:
            String(record.action??""),

            entryPrice:
            safeNumber(record.entryPrice),

            exitPrice:
            safeNumber(record.exitPrice),

            shares:
            safeNumber(record.shares),

            memo:
            String(record.memo??"")

        };

        entry.profit=

        round(

            (entry.exitPrice-entry.entryPrice)

            *entry.shares

        );

        entry.returnPercent=

        entry.entryPrice>0

        ?round(

        (

        entry.exitPrice-entry.entryPrice

        )

        /entry.entryPrice*100

        )

        :0;

        this.records.push(entry);

        return entry;

    }

    all(){

        return [...this.records];

    }

    summary(){

        if(this.records.length===0){

            return{

                trades:0,

                totalProfit:0,

                winRate:0

            };

        }

        const wins=

        this.records.filter(

        x=>x.profit>0

        ).length;

        return{

            trades:

            this.records.length,

            totalProfit:

            round(

            this.records.reduce(

            (a,b)=>a+b.profit,

            0

            )

            ),

            winRate:

            round(

            wins/

            this.records.length

            *100

            )

        };

    }

    clear(){

        this.records=[];

    }

}

export const
tradeJournal=
new TradeJournal();