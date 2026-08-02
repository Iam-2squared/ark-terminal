export function calculateAccuracyTrend(history = []) {

if(history.length < 2){
return{
direction:"flat",
change:0,
};
}

const latest = history[0].accuracy ?? 0;
const previous = history[1].accuracy ?? 0;

const diff = latest - previous;

return{

direction:
diff>0
?"up"
:diff<0
?"down"
:"flat",

change:diff,

};

}

export default calculateAccuracyTrend;
