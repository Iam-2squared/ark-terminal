export class AnalysisJobQueue {

  constructor() {
    this.queue = [];
    this.running = false;
    this.completed = [];
  }

  add(job) {
    return new Promise((resolve, reject) => {
      this.queue.push({
        job,
        resolve,
        reject,
      });

      this.#run();
    });
  }

  async #run() {

    if (this.running) {
      return;
    }

    this.running = true;

    while (this.queue.length) {

      const current =
        this.queue.shift();

      try {

        const value =
          await current.job();

        this.completed.push({
          success: true,
          value,
          time: Date.now(),
        });

        current.resolve(value);

      }
      catch (error) {

        this.completed.push({
          success: false,
          error: String(error),
          time: Date.now(),
        });

        current.reject(error);
      }

    }

    this.running = false;

  }

  stats() {

    return {

      queued:
        this.queue.length,

      completed:
        this.completed.length,

      running:
        this.running

    };

  }

  clearHistory() {

    this.completed = [];

  }

}

export const
analysisJobQueue =
new AnalysisJobQueue();