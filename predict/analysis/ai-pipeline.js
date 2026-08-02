import { runAICoordinator }
from "./ai-coordinator.js";

export async function executeAIPipeline(input={}){

    const coordinator=
        await runAICoordinator(input);

    return{
        version:"ai-pipeline-v1",
        ready:true,
        coordinator,
        runtime:coordinator.runtime,
        bootstrap:coordinator.bootstrap
    };
}
