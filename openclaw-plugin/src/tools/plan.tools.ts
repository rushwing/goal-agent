import { AxiosInstance } from "axios";

export function registerPlanTools(client: AxiosInstance) {
  return {
    create_target: async (args: {
      go_getter_id: number;
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

    cancel_target: async (args: { target_id: number }) => {
      // Soft-cancel: preserves plans/milestones/check-in history.
      // Physical deletion is intentionally blocked at the API level.
      const { data } = await client.patch(`/targets/${args.target_id}`, { status: "cancelled" });
      return { success: true, target_id: args.target_id, status: "cancelled", ...data };
    },

    list_targets: async (args: { go_getter_id: number }) => {
      const { data } = await client.get("/targets", { params: { go_getter_id: args.go_getter_id } });
      return data;
    },

    update_plan: async (args: { plan_id: number; title?: string; status?: string }) => {
      const { plan_id, ...body } = args;
      const { data } = await client.patch(`/plans/${plan_id}`, body);
      return data;
    },

    cancel_plan: async (args: { plan_id: number }) => {
      // Soft-cancel: preserves milestones/tasks/check-in history.
      // Physical deletion is intentionally blocked at the API level.
      const { data } = await client.patch(`/plans/${args.plan_id}`, { status: "cancelled" });
      return { success: true, plan_id: args.plan_id, status: "cancelled", ...data };
    },

    list_plans: async (args: { go_getter_id?: number; target_id?: number }) => {
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
