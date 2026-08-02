import { bootstrapPredictionLab }
from "./prediction-lab-bootstrap.js";

export async function runAICoordinator(input={}){

    const boot=
        await bootstrapPredictionLab(input);

    return{
        version:"ai-coordinator-v1",
        ready:true,
        bootstrap:boot,
        runtime:boot.runtime
    };
}
