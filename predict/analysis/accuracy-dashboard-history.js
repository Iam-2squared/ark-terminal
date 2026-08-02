export class AccuracyDashboardHistory {

constructor(limit=100){

this.limit=limit;
this.rows=[];

}

push(snapshot){

this.rows.unshift(snapshot);

if(this.rows.length>this.limit){
this.rows.length=this.limit;
}

return this.rows.length;

}

all(){

return [...this.rows];

}

latest(){

return this.rows[0]??null;

}

clear(){

this.rows=[];

}

}

export default AccuracyDashboardHistory;
