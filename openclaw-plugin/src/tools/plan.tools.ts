import { AxiosInstance } from "axios";

export function registerPlanTools(client: AxiosInstance) {
  return {
    create_target: async (args: {
      pupil_id: number;
      title: string;
      subject: string;
      description: string;
      vacation_type?: string;
      vacation_year?: number;
      priority?: number;
    }) => {
      const { data } = await client.post("/targets", args);
      return data;
    },

    update_target: async (args: {
      target_id: number;
      title?: string;
      subject?: string;
      description?: string;
      priority?: number;
      status?: string;
    }) => {
      const { target_id, ...body } = args;
      const { data } = await client.patch(`/targets/${target_id}`, body);
      return data;
    },

    delete_target: async (args: { target_id: number }) => {
      const { data } = await client.delete(`/targets/${args.target_id}`);
      return data;
    },

    list_targets: async (args: { pupil_id: number }) => {
      const { data } = await client.get("/targets", { params: { pupil_id: args.pupil_id } });
      return data;
    },

    generate_plan: async (args: {
      target_id: number;
      start_date: string;
      end_date: string;
      daily_study_minutes?: number;
      preferred_days?: number[];
      extra_instructions?: string;
    }) => {
      const { data } = await client.post("/plans/generate", args);
      return data;
    },

    update_plan: async (args: { plan_id: number; title?: string; status?: string }) => {
      const { plan_id, ...body } = args;
      const { data } = await client.patch(`/plans/${plan_id}`, body);
      return data;
    },

    delete_plan: async (args: { plan_id: number }) => {
      const { data } = await client.delete(`/plans/${args.plan_id}`);
      return data;
    },

    list_plans: async (args: { pupil_id?: number; target_id?: number }) => {
      const { data } = await client.get("/plans", { params: args });
      return data;
    },

    get_plan_detail: async (args: { plan_id: number }) => {
      // Detail endpoint not in REST yet – fall back to list
      const { data } = await client.get("/plans", { params: {} });
      return data.find((p: any) => p.id === args.plan_id) ?? null;
    },
  };
}
