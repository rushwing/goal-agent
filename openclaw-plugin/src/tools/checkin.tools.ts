import { AxiosInstance } from "axios";

export function registerCheckinTools(client: AxiosInstance) {
  return {
    list_today_tasks: async () => {
      const { data } = await client.get("/checkins/today");
      return data;
    },

    list_week_tasks: async () => {
      // Week tasks endpoint – call today and expand mentally
      const { data } = await client.get("/checkins/today");
      return data;
    },

    checkin_task: async (args: {
      task_id: number;
      mood_score: number;
      duration_minutes?: number;
      notes?: string;
    }) => {
      const { data } = await client.post("/checkins", args);
      return data;
    },

    skip_task: async (args: { task_id: number; reason?: string }) => {
      const { data } = await client.post("/checkins/skip", args);
      return data;
    },

    get_go_getter_progress: async () => {
      // Placeholder: could be a dedicated endpoint
      const { data } = await client.get("/checkins/today");
      return { tasks_today: data };
    },
  };
}
