function number(value,fallback=0){
    const n=Number(value);
    return Number.isFinite(n)?n:fallback;
}

function clamp(v,min=0,max=100){
    return Math.min(max,Math.max(min,number(v)));
}

function round(v,d=2){
    const f=10**d;
    return Math.round(v*f)/f;
}

export class SelfLearningEngine{

    constructor(){

        this.statistics={};

    }

    learn(records=[]){

        for(const record of records){

            const key=

            String(

            record.strategy??

            "default"

            );

            if(!this.statistics[key]){

                this.statistics[key]={

                    trades:0,

                    wins:0,

                    profit:0

                };

            }

            const s=

            this.statistics[key];

            s.trades++;

            const profit=

            number(record.profit);

            s.profit+=profit;

            if(profit>0){

                s.wins++;

            }

        }

        return this.report();

    }

    report(){

        const result={};

        for(const

        [key,s]

        of

        Object.entries(

        this.statistics

        )){

            result[key]={

                trades:s.trades,

                wins:s.wins,

                winRate:

                round(

                s.trades

                ?s.wins/

                s.trades*100

                :0

                ),

                totalProfit:

                round(

                s.profit

                ),

                score:

                clamp(

                50+

                s.profit/1000+

                s.wins*2

                )

            };

        }

        return result;

    }

    reset(){

        this.statistics={};

    }

}

export const

selfLearningEngine=

new SelfLearningEngine();